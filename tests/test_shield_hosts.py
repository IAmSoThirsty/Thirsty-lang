"""The same one-use stdout authority must survive both execution hosts."""

import datetime as dt
import io
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from queue import Queue

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from utf.tarl.authority import AuthorityIssuer, AuthorityVerifier
from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
from utf.thirsty_lang import cli, js_host, shield_node
from utf.thirsty_lang.interpreter import GovernanceViolation, Interpreter
from utf.thirsty_lang.shield import ShieldDenied, ShieldRun, stdout_grant

SITE = (2, 1)
ALLOW = 'when authority_authenticated == true and action == "write" and target == "stdout" => ALLOW\nwhen true => DENY\n'
DENY = "when true => DENY\n"


def module(*statements):
    return (
        "module status: governed\nshield {\n"
        + "".join(f"    {statement}\n" for statement in statements)
        + "}\n"
    )


READY = module('pour "ready"')
TWICE = module('pour "ready"', 'pour "ready"')
SURRENDER = module("surrender()", 'pour "ready"')


def signed(source=READY, site=SITE, text="ready", *, now=None, ttl=300):
    issuer = AuthorityIssuer("local-issuer", Ed25519PrivateKey.generate())
    verifier = AuthorityVerifier().add_ed25519_key(
        issuer.key_id, issuer.public_key_bytes()
    )
    claim = issuer.issue(
        "status-worker", [stdout_grant(source, site, text)], ttl_seconds=ttl, now=now
    )
    result = verifier.verify(claim, now=now)
    assert result.valid and result.authority is not None
    return result.authority, verifier


@pytest.fixture(autouse=True)
def no_publication_outside_the_bound_sink(capfd):
    yield
    assert capfd.readouterr().out == ""


@pytest.fixture(params=["reference", "node"])
def prepare(request, tmp_path):
    def program(source, policy=ALLOW):
        if request.param == "node":
            if shutil.which("node") is None:
                pytest.skip("Node.js is required for the installed shield protocol")
            path = tmp_path / "status.thirsty"
            path.write_text(source, encoding="utf-8")
            tree, checked = cli._checked_build_source(path)
            artifact = path.with_suffix(".js")
            artifact.write_bytes(
                cli._compile_governed_js(tree, checked, policy).encode()
            )

            def execute(handle):
                return js_host.run_shield(artifact, policy, handle)

        else:

            def execute(handle):
                runtime = TarlRuntime(PolicyParser.parse(policy))
                try:
                    with Interpreter() as machine:
                        machine.attach_tarl(runtime)
                        if handle.authority is not None:
                            machine.set_verified_authority(handle.authority)
                        machine.interpret_shield(source, handle)
                finally:
                    runtime.shutdown()
                return 0

        def status(handle):
            try:
                return execute(handle)
            except (ShieldDenied, GovernanceViolation):
                return 2

        return status

    return program


@pytest.mark.parametrize(
    ("source", "status", "expected", "outcome"),
    [
        (READY, 0, b"ready\n", "published"),
        (
            module("drink n: Int = 3", "drink doubled = n + n", 'pour "ready"'),
            0,
            b"ready\n",
            "published",
        ),
        (TWICE, 2, b"ready\n", "published"),
        (SURRENDER, 2, b"", "unused"),
        (module("surrender()"), 0, b"", "unused"),
    ],
    ids=[
        "publish-once",
        "local-int-calculation",
        "second-write-refused",
        "holder-surrenders",
        "surrender-only",
    ],
)
def test_publication_budget(prepare, source, status, expected, outcome):
    execute = prepare(source)
    authority, _ = signed(source)
    sink = io.BytesIO()
    with ShieldRun(source, SITE, authority, sink) as run:
        assert execute(run) == status
        assert run.outcome == outcome
        assert sink.getvalue() == expected


@pytest.mark.parametrize(
    "mismatch",
    [
        "missing",
        "source",
        "site",
        "text",
        "expired",
        "unbounded",
        "copied",
        "revoked",
        "policy",
    ],
)
def test_authority_and_policy_both_required(prepare, mismatch):
    # Even a final blank line changes the signed source.
    signed_source = READY + "\n" if mismatch == "source" else READY
    signed_site = (3, 1) if mismatch == "site" else SITE
    signed_text = "different" if mismatch == "text" else "ready"
    issued = (
        dt.datetime.now(dt.UTC) - dt.timedelta(days=1)
        if mismatch == "expired"
        else None
    )
    authority, verifier = signed(
        signed_source,
        signed_site,
        signed_text,
        now=issued,
        ttl=None if mismatch == "unbounded" else 300,
    )
    if mismatch == "copied":
        authority = replace(authority)
    execute = prepare(READY, DENY if mismatch == "policy" else ALLOW)
    sink = io.BytesIO()
    with ShieldRun(
        READY, SITE, None if mismatch == "missing" else authority, sink
    ) as run:
        if mismatch == "revoked":
            verifier.revoke_key("local-issuer")
        assert execute(run) == 2
        assert run.outcome == "unused"
    assert sink.getvalue() == b""


def test_two_workers_share_one_record(prepare):
    execute = prepare(READY)
    authority, _ = signed()
    sink = io.BytesIO()
    start = threading.Barrier(2)

    def worker(child):
        start.wait(timeout=30)
        return execute(child)

    with ShieldRun(READY, SITE, authority, sink) as root:
        with root.derive() as first, root.derive() as second:
            with ThreadPoolExecutor(max_workers=2) as pool:
                jobs = [pool.submit(worker, child) for child in (first, second)]
                assert sorted(job.result(timeout=60) for job in jobs) == [0, 2]
        assert root.outcome == "published"
    assert sink.getvalue() == b"ready\n"


def test_surrender_leaves_sibling_eligible(prepare):
    execute = prepare(READY)
    authority, _ = signed()
    sink = io.BytesIO()
    with ShieldRun(READY, SITE, authority, sink) as root:
        with root.derive() as first, root.derive() as sibling:
            with first.derive() as descendant:
                first.surrender()
                assert execute(first) == 2
                assert execute(descendant) == 2
            assert root.outcome == "unused"
            assert sink.getvalue() == b""
            assert execute(sibling) == 0
        assert root.outcome == "published"
    assert sink.getvalue() == b"ready\n"


def test_stop_after_authorization_before_handoff(prepare, monkeypatch):
    execute = prepare(READY)
    authority, _ = signed()
    checked = threading.Event()
    release = threading.Event()
    dispatch = ShieldRun.dispatch

    def paused_dispatch(self, text, authorize):
        def checked_authorize():
            result = authorize()
            checked.set()
            assert release.wait(timeout=60)
            return result

        return dispatch(self, text, checked_authorize)

    monkeypatch.setattr(ShieldRun, "dispatch", paused_dispatch)
    sink = io.BytesIO()
    with (
        ShieldRun(READY, SITE, authority, sink) as run,
        ThreadPoolExecutor(max_workers=2) as pool,
    ):
        pending = pool.submit(execute, run)
        try:
            assert checked.wait(
                timeout=30
            ), "worker never reached the authorized handoff"
            pool.submit(run.stop).result(timeout=10)
            assert run.outcome == "unused"
        finally:
            release.set()
        assert pending.result(timeout=30) == 2
        assert sink.getvalue() == b""


def change_issuer(verifier, operation):
    if operation == "revoke":
        verifier.revoke_key("local-issuer")
    else:
        replacement = AuthorityIssuer("local-issuer", Ed25519PrivateKey.generate())
        verifier.add_ed25519_key(replacement.key_id, replacement.public_key_bytes())


@pytest.mark.parametrize("operation", ["stop", "revoke", "rotate"])
def test_revocation_acknowledges_in_flight_write(prepare, operation):
    execute = prepare(READY)
    authority, verifier = signed()
    writing = threading.Event()
    release = threading.Event()

    class PausingSink(io.BytesIO):
        def write(self, record):
            written = super().write(record)
            writing.set()
            assert release.wait(timeout=60)
            return written

    sink = PausingSink()
    with (
        ShieldRun(READY, SITE, authority, sink) as run,
        ThreadPoolExecutor(max_workers=2) as pool,
    ):
        pending = pool.submit(execute, run)
        try:
            assert writing.wait(timeout=30), "trusted sink did not receive the record"
            if operation == "stop":
                pool.submit(run.stop).result(timeout=10)
            else:
                pool.submit(change_issuer, verifier, operation).result(timeout=10)
            assert run.outcome == "in_flight"
            assert sink.getvalue() == b"ready\n"
        finally:
            release.set()
        assert pending.result(timeout=30) == 0
        assert run.outcome == "published"
        assert execute(run) == 2
    assert sink.getvalue() == b"ready\n"


def test_stopping_one_root_preserves_an_independent_run(prepare):
    execute = prepare(READY)
    first_authority, _ = signed()
    second_authority, _ = signed()
    first, second = io.BytesIO(), io.BytesIO()
    with ShieldRun(READY, SITE, first_authority, first) as stopped:
        with ShieldRun(READY, SITE, second_authority, second) as independent:
            stopped.stop()
            assert execute(stopped) == 2
            assert execute(independent) == 0
    assert first.getvalue() == b""
    assert second.getvalue() == b"ready\n"


def test_partial_publication_cannot_be_retried(prepare):
    class PartialSink(io.BytesIO):
        def write(self, record):
            return super().write(record[:2])

    execute = prepare(READY)
    authority, _ = signed()
    sink = PartialSink()
    with ShieldRun(READY, SITE, authority, sink) as run:
        assert execute(run) == 2
        assert run.outcome == "unknown"
        assert sink.getvalue() == b"re"
        assert execute(run) == 2
        assert sink.getvalue() == b"re"


@pytest.mark.parametrize(
    "source",
    [
        module("drink count = 1", "pour count"),
        module('pour "rea" + "dy"'),
        module('import "thirst::json" as data'),
        module('glass callback() { pour "ready" }', "callback()"),
        module('shield { pour "ready" }'),
        READY + "drink outside = 1\n",
    ],
    ids=["dynamic", "nonliteral", "import", "callback", "nested", "mixed-module"],
)
def test_static_bound_rejects_unsupported_source(tmp_path, monkeypatch, capfd, source):
    path = tmp_path / "protected.thirsty"
    path.write_text(source, encoding="utf-8")
    policy = tmp_path / "policy.tarl"
    policy.write_text(ALLOW, encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["thirsty", "build", str(path), "--target", "js", "--policy", str(policy)],
    )
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 1
    diagnostics = capfd.readouterr()
    assert diagnostics.out == ""
    assert "shield" in diagnostics.err.lower()
    assert set(tmp_path.iterdir()) == {path, policy}


@pytest.mark.parametrize("target", ["js", "wasm-pyodide", "llvm-ir"])
def test_shield_refuses_compatibility_builds_before_emission(
    tmp_path, monkeypatch, capfd, target
):
    path = tmp_path / "protected.thirsty"
    path.write_text(READY, encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["thirsty", "build", str(path), "--target", target, "--allow-governance-loss"],
    )
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 1
    diagnostics = capfd.readouterr()
    assert diagnostics.out == ""
    assert "shield" in diagnostics.err.lower()
    assert set(tmp_path.iterdir()) == {path}


@pytest.mark.parametrize("operation", ["revoke", "rotate"])
def test_issuer_change_before_final_admission_refuses_stale_worker(
    prepare, monkeypatch, operation
):
    execute = prepare(READY)
    authority, verifier = signed()
    waiting = threading.Event()
    release = threading.Event()
    guard = AuthorityVerifier.admission_guard

    @contextmanager
    def at_admission(cls, subject):
        # The preliminary eligibility checks and TARL decision already passed.
        # Hold the worker at the verifier boundary before the slot transfers.
        waiting.set()
        assert release.wait(timeout=60)
        with guard(subject) as reason:
            yield reason

    monkeypatch.setattr(AuthorityVerifier, "admission_guard", classmethod(at_admission))
    sink = io.BytesIO()
    with ShieldRun(READY, SITE, authority, sink) as run, run.derive() as child:
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = pool.submit(execute, child)
            try:
                assert waiting.wait(
                    timeout=30
                ), "worker did not reach the final issuer check"
                pool.submit(change_issuer, verifier, operation).result(timeout=10)
            finally:
                release.set()
            assert pending.result(timeout=30) == 2
        with child.derive() as descendant:
            assert execute(descendant) == 2
        assert run.outcome == "unused"
        assert sink.getvalue() == b""


def test_last_public_derivation_can_publish_once(prepare):
    execute = prepare(READY)
    authority, _ = signed()
    sink = io.BytesIO()
    with ShieldRun(READY, SITE, authority, sink) as root:
        leaf = root
        for _ in range(64):
            leaf = leaf.derive()
        with pytest.raises(ShieldDenied):
            leaf.derive()
        assert execute(leaf) == 0
        assert execute(leaf) == 2
        assert root.outcome == "published"
        assert sink.getvalue() == b"ready\n"


def test_node_watchdog_cancels_only_its_pending_handoff(tmp_path, monkeypatch):
    if shutil.which("node") is None:
        pytest.skip("Node.js is required for the shield protocol")
    path = tmp_path / "status.thirsty"
    path.write_text(READY, encoding="utf-8")
    tree, source = cli._checked_build_source(path)
    artifact = path.with_suffix(".js")
    artifact.write_bytes(cli._compile_governed_js(tree, source, ALLOW).encode())
    timers = Queue()
    checked = threading.Event()
    release = threading.Event()
    dispatch = ShieldRun.dispatch

    class ObservedTimer(threading.Timer):
        def start(self):
            super().start()
            timers.put(self)

    def paused_dispatch(self, text, authorize):
        def after_worker_liveness_check():
            decision = authorize()
            checked.set()
            assert release.wait(timeout=60)
            return decision

        return dispatch(self, text, after_worker_liveness_check)

    authority, _ = signed()
    sink = io.BytesIO()
    with ShieldRun(READY, SITE, authority, sink) as run:
        with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
            patch.setattr(shield_node, "Timer", ObservedTimer)
            patch.setattr(ShieldRun, "dispatch", paused_dispatch)
            pending = pool.submit(js_host.run_shield, artifact, ALLOW, run)
            try:
                assert checked.wait(
                    timeout=30
                ), "worker never passed its liveness check"
                # Fire the installed watchdog callback now, without sleeping for its deadline.
                timer = timers.get(timeout=5)
                pool.submit(timer.function).result(timeout=10)
            finally:
                release.set()
            with pytest.raises(ShieldDenied):
                pending.result(timeout=30)
        assert sink.getvalue() == b""
        assert run.outcome == "unused"
        assert js_host.run_shield(artifact, ALLOW, run) == 0
        assert sink.getvalue() == b"ready\n"


def test_slot_transfer_is_inside_issuer_guard(prepare, monkeypatch):
    execute = prepare(READY)
    authority, verifier = signed()
    sink = io.BytesIO()
    guard = AuthorityVerifier.admission_guard
    held_during_transfer = []

    def issuer_key_lock_held():
        # Check from a different thread so a reentrant key lock cannot mask a mismatch.
        if verifier._keys_lock.acquire(blocking=False):
            verifier._keys_lock.release()
            return False
        return True

    with (
        ShieldRun(READY, SITE, authority, sink) as run,
        ThreadPoolExecutor(max_workers=1) as pool,
    ):

        @contextmanager
        def observe(cls, subject):
            with guard(subject) as reason:
                # The public outcome accessor would reacquire this run's held state lock.
                before = run._shared.outcome
                yield reason
                if before == "unused" and run._shared.outcome == "in_flight":
                    held_during_transfer.append(
                        pool.submit(issuer_key_lock_held).result(timeout=5)
                    )

        monkeypatch.setattr(AuthorityVerifier, "admission_guard", classmethod(observe))
        assert execute(run) == 0
        assert held_during_transfer == [True]
        assert sink.getvalue() == b"ready\n"
