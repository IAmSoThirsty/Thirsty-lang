"""Required evidence cannot disappear silently; concurrent appends stay linear."""

import concurrent.futures
import threading

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
    archives = [TarlAuditArchive(path) for _ in range(4)]
    start = threading.Barrier(len(archives))

    def append(archive):
        start.wait(timeout=10)
        return [archive.store(proof) for _ in range(12)]

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(append, archive) for archive in archives]
            ids = [row for future in futures for row in future.result(timeout=30)]
        assert len(set(ids)) == 48
        assert archives[0].count() == 48
        assert archives[0].verify_chain().valid
    finally:
        for archive in archives:
            archive.close()
