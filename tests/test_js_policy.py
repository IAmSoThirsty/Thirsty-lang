"""The governed Node stdout adapter uses the reference broker and proof route."""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from utf.tarl.broker import CapabilityBroker
from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
from utf.thirsty_lang.js_policy import _serve, validate_js_policy


def exchange(request):
    data = (
        request if isinstance(request, bytes) else json.dumps(request).encode("utf-8")
    )
    stdout = io.BytesIO()
    stderr = io.StringIO()
    status = _serve(io.BytesIO(data), stdout, stderr)
    return status, stdout.getvalue(), stderr.getvalue()


def envelope(policy, operation="write", subject="worker"):
    request = {"op": operation, "policy": policy, "authority": subject}
    if operation == "write":
        request["text"] = "café\n🚰"
    return request


@pytest.mark.parametrize(
    "policy,subject",
    [
        (
            'policy stdout:\nwhen action == "write" and target == "stdout" => ALLOW',
            "worker",
        ),
        ('when authority == "named" => ALLOW\nwhen true => DENY', "named"),
        ('when authority_subject == "named" => ALLOW\nwhen true => DENY', "other"),
        (
            'when not authority_authenticated and "write" not in authority_grants => ALLOW',
            "user",
        ),
        ("when authority_authenticated => ALLOW", "signed-looking"),
        ('when target == "stdout" => DENY\nwhen action == "write" => ALLOW', "user"),
        ('when target == "stdout" => ESCALATE\nwhen true => ALLOW', "user"),
        ('when action in ["read", "write"] => ALLOW', "user"),
        ('when STARTS_WITH(authority, "trusted/") => ALLOW', "trusted/editor"),
        ('when action == "read" => ALLOW', "user"),
        ('when authority == "a#//b" => ALLOW  # comment', "a#//b"),
    ],
)
def test_check_and_output_follow_reference_broker(policy, subject):
    validate_js_policy(policy)
    runtime = TarlRuntime(PolicyParser.parse(policy))
    try:
        decision = CapabilityBroker(runtime, authority=subject).request(
            "write", "stdout"
        )
        assert decision.proof.verdict == decision.verdict.value
    finally:
        runtime.shutdown()

    assert exchange(envelope(policy, "bind", subject)) == (0, b"", "")
    for operation in ("check-write", "write"):
        status, output, error = exchange(envelope(policy, operation, subject))
        if decision.allowed:
            assert status == 0 and error == ""
            assert output == ("café\n🚰\n".encode() if operation == "write" else b"")
        else:
            assert status == 2 and output == b""
            assert decision.verdict.value in error


@pytest.mark.parametrize(
    "policy",
    [
        "",
        "# only comments",
        "policy empty",
        "policy a:\npolicy a:\nwhen true => ALLOW",
        "policy a:\nwhen true => ALLOW\npolicy b:\nwhen false => DENY",
        "policy a EXTENDS b:\nwhen true => ALLOW",
        "policy a: ignored\nwhen true => ALLOW",
        'INCLUDE "other.tarl"\nwhen true => ALLOW',
        "valid_until: 2030-01-01\nwhen true => ALLOW",
        "when true => ALLOW for: 3h",
        "policy_set a:\ncombine UNION [other]\ndefault: ALLOW",
        "otherwise DENY\nwhen true => ALLOW",
        "when true => DENY\nwhen (true) => ALLOW",
        "when action == missing => ALLOW",
        'when role == "admin" => ALLOW',
        'when target.title == "stdout" => ALLOW',
        'when "grant" in source:grants => ALLOW',
        'when action == "unfinished => ALLOW',
        'when action in ["read" "write"] => ALLOW',
        'when action in ["write",] => ALLOW',
        'when CONTAINS(target "out") => ALLOW',
        "when CONTAINS(target,) => ALLOW",
        "when CONTAINS(target) => ALLOW",
        "when unknown(action) => ALLOW",
        "when action == 7 => ALLOW",
        "when action == target => ALLOW",
    ],
)
def test_build_and_helper_reject_unsupported_or_ambiguous_policy(policy):
    with pytest.raises(ValueError):
        validate_js_policy(policy)
    assert exchange(envelope(policy))[0:2] == (1, b"")


@pytest.mark.parametrize("operation", ["bind", "check-write", "write"])
@pytest.mark.parametrize("subject", [None, "", " \t\n", False, {"subject": "user"}])
def test_host_requires_a_nonblank_string_subject(operation, subject):
    assert exchange(envelope("when true => ALLOW", operation, subject))[0:2] == (1, b"")


@pytest.mark.parametrize(
    "raw_request",
    [
        b"[]",
        b"\xff",
        b'{"op":"bind","op":"write"}',
        b"{} {}",
        {"op": "write", "authority": "worker", "policy": "when true => ALLOW"},
        dict(envelope("when true => ALLOW"), text=3),
        dict(envelope("when true => ALLOW"), text="\ud800"),
        dict(envelope("when true => ALLOW"), authority="\ud800"),
        envelope('when authority == "\ud800" => ALLOW'),
        dict(envelope("when true => ALLOW"), target="/tmp/output"),
        dict(envelope("when true => ALLOW"), action="read"),
        dict(envelope("when true => ALLOW"), authority_authenticated=True),
        dict(envelope("when true => ALLOW"), context_schema={}),
        dict(envelope("when true => ALLOW", "bind"), text="unused"),
    ],
)
def test_invalid_envelopes_have_no_output(raw_request):
    status, output, error = exchange(raw_request)
    assert status == 1 and output == b""
    assert error and "Traceback" not in error


def test_unavailable_schema_or_broker_stops_publication(monkeypatch):
    def unavailable(self, action, target):
        raise RuntimeError("internal diagnostic")

    monkeypatch.setattr(CapabilityBroker, "require", unavailable)
    status, data, error = exchange(envelope("when true => ALLOW"))
    assert status == 2 and not data and "internal diagnostic" not in error

    monkeypatch.setattr(TarlRuntime, "ensure_context_schema", lambda self: False)
    assert exchange(envelope("when true => ALLOW", "bind"))[:2] == (1, b"")


def test_check_then_write_requests_two_fresh_canonical_proofs(monkeypatch):
    calls = []
    real = CapabilityBroker.require

    def checked(self, action, target):
        decision = real(self, action, target)
        calls.append((action, target, decision.proof))
        return decision

    monkeypatch.setattr(CapabilityBroker, "require", checked)
    for operation in ("bind", "check-write", "write"):
        assert exchange(envelope("when true => ALLOW", operation))[0] == 0
    assert [(action, target) for action, target, _ in calls] == [
        ("write", "stdout")
    ] * 2
    assert calls[0][2] is not calls[1][2]


def test_module_protocol_has_utf8_stdout_and_a_process_exit_status(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    for policy, expected_status in (
        ("when true => ALLOW", 0),
        ("when true => ESCALATE", 2),
    ):
        result = subprocess.run(
            [sys.executable, "-m", "utf.thirsty_lang.js_policy"],
            cwd=tmp_path,
            env=env,
            input=json.dumps(envelope(policy)).encode(),
            capture_output=True,
            check=False,
            timeout=60,
        )
        assert result.returncode == expected_status
        assert result.stdout == ("café\n🚰\n".encode() if expected_status == 0 else b"")
        assert b"Traceback" not in result.stderr
