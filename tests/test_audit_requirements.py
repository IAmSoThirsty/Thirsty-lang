"""Required evidence cannot disappear silently; concurrent appends stay linear."""

import concurrent.futures
import sqlite3
import threading
from decimal import Decimal

import pytest

from utf.tarl.archive import TarlAuditArchive
from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
from utf.tarl.spec import TarlVerdict


@pytest.mark.parametrize("proof_api", [False, True])
def test_required_audit_without_archive_denies(proof_api):
    runtime = TarlRuntime(PolicyParser.parse("when true => ALLOW"))
    runtime.set_require_audit(True)
    try:
        if proof_api:
            decision, proof = runtime.evaluate_with_proof({})
            assert proof.verdict is TarlVerdict.DENY
            assert proof.trace[0]["kind"] == "audit-fail"
        else:
            decision = runtime.evaluate({})
        assert decision.verdict is TarlVerdict.DENY
        assert "not configured" in decision.reason
    finally:
        runtime.shutdown()


def test_required_audit_is_used_by_decision_only_api(tmp_path):
    runtime = TarlRuntime(PolicyParser.parse("when true => ALLOW"))
    try:
        with TarlAuditArchive(str(tmp_path / "audit.db")) as archive:
            runtime.set_archive(archive).set_require_audit(True)
            assert runtime.evaluate({}).verdict is TarlVerdict.ALLOW
            assert runtime.evaluate({}).verdict is TarlVerdict.ALLOW
            assert archive.count() == 2  # cached verdicts cannot skip required evidence
    finally:
        runtime.shutdown()


def test_concurrent_archive_instances_preserve_chain(tmp_path):
    path = str(tmp_path / "audit.db")
    runtime = TarlRuntime(PolicyParser.parse("when true => DENY"))
    try:
        _, proof = runtime.evaluate_with_proof({})
    finally:
        runtime.shutdown()
    archives = [TarlAuditArchive(path, lock_timeout_seconds=30) for _ in range(4)]
    start = threading.Barrier(len(archives))

    def append(archive):
        start.wait(timeout=10)
        return [archive.store(proof) for _ in range(12)]

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(append, archive) for archive in archives]
            ids = [row for future in futures for row in future.result(timeout=60)]
        assert len(set(ids)) == 48
        assert archives[0].count() == 48
        assert archives[0].verify_chain().valid
    finally:
        for archive in archives:
            archive.close()


@pytest.mark.parametrize(
    ("options", "milliseconds"),
    [
        ({}, 5000),
        ({"lock_timeout_seconds": 0}, 0),
        ({"lock_timeout_seconds": 0.125}, 125),
        ({"lock_timeout_seconds": 5.0}, 5000),
        ({"lock_timeout_seconds": 30}, 30000),
        ({"lock_timeout_seconds": 300}, 300000),
    ],
)
def test_archive_lock_timeout_configures_initial_and_reopened_connection(
    tmp_path, options, milliseconds
):
    with TarlAuditArchive(str(tmp_path / "audit.db"), **options) as archive:
        first_connection = archive._connect()
        assert first_connection.execute("PRAGMA busy_timeout").fetchone() == (
            milliseconds,
        )
        archive.close()
        assert archive.count() == 0
        reopened_connection = archive._connect()
        assert reopened_connection is not first_connection
        assert reopened_connection.execute("PRAGMA busy_timeout").fetchone() == (
            milliseconds,
        )


class _IntSubclass(int):
    pass


class _FloatSubclass(float):
    pass


@pytest.mark.parametrize(
    ("timeout", "error"),
    [
        pytest.param(True, TypeError, id="true"),
        pytest.param(False, TypeError, id="false"),
        pytest.param(None, TypeError, id="none"),
        pytest.param("5", TypeError, id="string"),
        pytest.param(Decimal("5"), TypeError, id="decimal"),
        pytest.param(_IntSubclass(5), TypeError, id="int-subclass"),
        pytest.param(_FloatSubclass(5), TypeError, id="float-subclass"),
        pytest.param(-0.1, ValueError, id="negative"),
        pytest.param(300.001, ValueError, id="over-max-fraction"),
        pytest.param(301, ValueError, id="over-max-int"),
        pytest.param(float("nan"), ValueError, id="nan"),
        pytest.param(float("inf"), ValueError, id="infinity"),
        pytest.param(float("-inf"), ValueError, id="negative-infinity"),
        pytest.param(10**400, ValueError, id="huge-int"),
        pytest.param(-(10**400), ValueError, id="negative-huge-int"),
    ],
)
def test_archive_invalid_lock_timeout_does_not_create_database(
    tmp_path, timeout, error
):
    path = tmp_path / "invalid.db"
    with pytest.raises(error, match="lock_timeout_seconds"):
        TarlAuditArchive(str(path), lock_timeout_seconds=timeout)
    assert not path.exists()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("proof_api", [False, True])
def test_archive_lock_exhaustion_denies_required_audit_and_recovers(
    tmp_path, proof_api
):
    path = str(tmp_path / "audit.db")
    runtime = TarlRuntime(PolicyParser.parse("when true => ALLOW"))
    try:
        _, proof = runtime.evaluate_with_proof({})
        with TarlAuditArchive(path, lock_timeout_seconds=0) as archive:
            runtime.set_archive(archive).set_require_audit(True)
            external = sqlite3.connect(path)
            try:
                external.execute("BEGIN IMMEDIATE")
                with pytest.raises(sqlite3.OperationalError, match="locked"):
                    archive.store(proof)
                assert archive.count() == 0
                if proof_api:
                    decision, denied_proof = runtime.evaluate_with_proof({})
                    assert denied_proof.verdict is TarlVerdict.DENY
                    assert denied_proof.trace[0]["kind"] == "audit-fail"
                    assert "locked" in denied_proof.trace[0]["reason"]
                else:
                    decision = runtime.evaluate({})
                assert decision.verdict is TarlVerdict.DENY
                assert "required audit could not be persisted" in decision.reason
                assert "locked" in decision.reason
                assert archive.count() == 0
                assert archive.verify_chain().valid
            finally:
                external.rollback()
                external.close()

            assert archive.store(proof) == 1
            if proof_api:
                recovered, recovered_proof = runtime.evaluate_with_proof({})
                assert recovered_proof.verdict is TarlVerdict.ALLOW
            else:
                recovered = runtime.evaluate({})
            assert recovered.verdict is TarlVerdict.ALLOW
            assert archive.count() == 2
            assert archive.count(verdict="ALLOW") == 2
            chain = archive.verify_chain()
            assert chain.valid
            assert chain.length == 2
    finally:
        runtime.shutdown()
