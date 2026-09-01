"""Verification for governed Shadow Thirst change admission."""

from __future__ import annotations

import copy
import json
import sys
from datetime import UTC, datetime

import pytest

from utf.shadow_thirst import cli as shadow_cli
from utf.shadow_thirst.admission import (
    AdmissionEngine,
    AdmissionPolicy,
    ChangeAdmissionRecord,
    EvidenceStatus,
    OriginType,
    Provenance,
)
from utf.shadow_thirst.core import MutationParser, ShadowModule
from utf.shadow_thirst.regression import (
    analyze_complexity_regression,
    analyze_governance_regression,
    analyze_security_regression,
)
from utf.tarl.keystore import ROLE_AUTHORITY_ISSUER, ROLE_PROOF_SIGNER, generate

FIXED_TIME = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


def mutation(shadow: str, canonical: str, invariant: str = "") -> ShadowModule:
    source = f"""
mutation governed_change {{
    validated_canonical {{
        shadow {{ {shadow} }}
        invariant {{ {invariant} }}
        canonical {{ {canonical} }}
    }}
}}
"""
    return MutationParser.parse(source)


def evidence(record, analyzer: str):
    return next(item for item in record.evidence if item.analyzer == analyzer)


def test_identical_change_is_technically_eligible_but_not_authorized():
    module = mutation("return input + 1", "return input + 1")
    record = AdmissionEngine().evaluate(module, generated_at=FIXED_TIME)
    assert record.admission_decision == "ELIGIBLE"
    assert evidence(record, "CanonicalConvergence").status == EvidenceStatus.PROVEN
    assert record.execution_authorized is False
    assert record.authorization_state == "NOT_EVALUATED"


def test_seeded_observation_is_flagged_when_policy_requires_proof():
    module = mutation("return input / 2", "return input / 2")
    # Structural equality proves this pair. Force a different AST shape whose
    # integer division cannot enter the symbolic subset but executes equally.
    module = mutation(
        "drink x = input / 2; return x",
        "return input / 2",
    )
    record = AdmissionEngine().evaluate(module, generated_at=FIXED_TIME)
    convergence = evidence(record, "CanonicalConvergence")
    assert convergence.status == EvidenceStatus.OBSERVED
    assert record.admission_decision == "FLAGGED"
    assert any("requires proven" in reason for reason in record.decision_reasons)


def test_counterexample_rejects_candidate():
    module = mutation("return input + 1", "return input + 2")
    record = AdmissionEngine().evaluate(module, generated_at=FIXED_TIME)
    convergence = evidence(record, "CanonicalConvergence")
    assert convergence.status == EvidenceStatus.VIOLATED
    assert record.admission_decision == "REJECTED"
    assert "counterexample" in convergence.details


def test_new_sensitive_effect_rejects_candidate():
    module = mutation(
        "pour input; return input",
        "return input",
    )
    finding = analyze_security_regression(module)
    assert finding.status == "VIOLATED"
    assert "write:stdout" in finding.details["added_effects"]
    record = AdmissionEngine().evaluate(module, generated_at=FIXED_TIME)
    assert record.admission_decision == "REJECTED"


def test_equal_sensitive_surface_is_observed_not_proven():
    module = mutation(
        "pour input; return input",
        "pour input; return input",
    )
    finding = analyze_security_regression(module)
    assert finding.status == "OBSERVED"
    assert finding.details["candidate_effects"] == ["write:stdout"]


def test_removed_governance_surface_is_rejected_by_regression_rule():
    module = mutation(
        "return input",
        "authorize(); return input",
    )
    finding = analyze_governance_regression(module)
    assert finding.status == "VIOLATED"
    assert finding.details["removed"]["governance-call:authorize"] == 1


def test_complexity_proxy_reports_configured_violation():
    module = mutation(
        "if input > 0 { if input > 1 { if input > 2 { return input } } }; return input",
        "return input",
    )
    finding = analyze_complexity_regression(module, max_ratio=1.0, max_delta=0)
    assert finding.status == "VIOLATED"
    assert finding.details["score_delta"] > 0


def test_origin_does_not_change_analysis_or_grant_authority():
    module = mutation("return input", "return input")
    human = AdmissionEngine().evaluate(
        module,
        provenance=Provenance(OriginType.HUMAN, actor_id="human-1"),
        generated_at=FIXED_TIME,
    )
    ai = AdmissionEngine().evaluate(
        module,
        provenance=Provenance(OriginType.AI, actor_id="agent-1", model="model-x"),
        generated_at=FIXED_TIME,
    )
    assert human.analysis_id == ai.analysis_id
    assert human.admission_decision == ai.admission_decision == "ELIGIBLE"
    assert human.execution_authorized is ai.execution_authorized is False
    assert human.record_hash != ai.record_hash


def test_unsigned_record_hash_verifies_and_tampering_fails():
    record = AdmissionEngine().evaluate(
        mutation("return input", "return input"), generated_at=FIXED_TIME
    )
    assert record.verify() == (True, "unsigned record hash is valid")
    record.mutation_name = "tampered"
    valid, reason = record.verify()
    assert valid is False
    assert reason == "record hash mismatch"


def test_signed_record_verifies_with_proof_signer_and_rejects_wrong_key():
    record = AdmissionEngine().evaluate(
        mutation("return input", "return input"), generated_at=FIXED_TIME
    )
    signer = generate("shadow-admission-2026", ROLE_PROOF_SIGNER)
    wrong = generate("wrong", ROLE_PROOF_SIGNER)
    record.sign(signer)
    assert record.verify(signer.public_only()) == (True, "signed record is valid")
    valid, reason = record.verify(wrong.public_only())
    assert valid is False
    assert reason == "signer key identity or role mismatch"


def test_non_proof_signer_cannot_sign_admission_record():
    record = AdmissionEngine().evaluate(
        mutation("return input", "return input"), generated_at=FIXED_TIME
    )
    wrong_role = generate("authority", ROLE_AUTHORITY_ISSUER)
    with pytest.raises(ValueError, match="proof-signer"):
        record.sign(wrong_role)


def test_record_round_trip_preserves_hash_and_evidence():
    original = AdmissionEngine().evaluate(
        mutation("return input", "return input"), generated_at=FIXED_TIME
    )
    reconstructed = ChangeAdmissionRecord.from_dict(original.to_dict())
    assert reconstructed.to_dict() == original.to_dict()
    assert reconstructed.verify()[0] is True


def test_record_cannot_claim_execution_authority():
    record = AdmissionEngine().evaluate(
        mutation("return input", "return input"), generated_at=FIXED_TIME
    )
    data = record.to_dict()
    data["execution_authorized"] = True
    with pytest.raises(ValueError, match="cannot authorize execution"):
        ChangeAdmissionRecord.from_dict(data)


def test_policy_rejects_unknown_fields_and_invalid_thresholds():
    with pytest.raises(ValueError, match="unknown admission policy fields"):
        AdmissionPolicy.from_dict({"confidence": 0.9})
    with pytest.raises(ValueError, match="at least 1.0"):
        AdmissionPolicy(max_complexity_ratio=0.9)
    with pytest.raises(ValueError, match="finite number"):
        AdmissionPolicy(max_complexity_ratio=float("nan"))
    with pytest.raises(ValueError, match="must be a boolean"):
        AdmissionPolicy(require_proven_equivalence=1)  # type: ignore[arg-type]


def test_provenance_rejects_unknown_fields_and_invalid_origin():
    with pytest.raises(ValueError, match="unknown provenance fields"):
        Provenance.from_dict({"authority": "self"})
    with pytest.raises(ValueError, match="invalid provenance origin_type"):
        Provenance.from_dict({"origin_type": "SUPERUSER"})


def test_naive_record_time_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        AdmissionEngine().evaluate(
            mutation("return input", "return input"),
            generated_at=datetime(2026, 8, 31, 12, 0),
        )


def test_fixed_inputs_produce_deterministic_record_hash():
    module = mutation("return input", "return input")
    first = AdmissionEngine().evaluate(module, generated_at=FIXED_TIME)
    second = AdmissionEngine().evaluate(module, generated_at=FIXED_TIME)
    assert first.analysis_id == second.analysis_id
    assert first.record_hash == second.record_hash


def test_unknown_record_fields_fail_closed():
    record = AdmissionEngine().evaluate(
        mutation("return input", "return input"), generated_at=FIXED_TIME
    )
    data = copy.deepcopy(record.to_dict())
    data["confidence"] = 1.0
    with pytest.raises(ValueError, match="unknown admission record fields"):
        ChangeAdmissionRecord.from_dict(data)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("format", "shadow-thirst-change-admission/v2", "unsupported"),
        ("admission_decision", "PROMOTE", "invalid admission decision"),
        ("execution_authorized", 1, "must be a boolean"),
        ("generated_at", "2026-08-31T12:00:00", "timezone-aware"),
        ("record_hash", "not-a-hash", "canonical lowercase SHA-256"),
    ],
)
def test_malformed_record_fields_fail_closed(field, value, message):
    record = AdmissionEngine().evaluate(
        mutation("return input", "return input"), generated_at=FIXED_TIME
    )
    data = record.to_dict()
    data[field] = value
    with pytest.raises(ValueError, match=message):
        ChangeAdmissionRecord.from_dict(data)


def test_evidence_unknown_fields_and_string_boolean_fail_closed():
    record = AdmissionEngine().evaluate(
        mutation("return input", "return input"), generated_at=FIXED_TIME
    )
    data = record.to_dict()
    data["evidence"][0]["confidence"] = 1.0
    with pytest.raises(ValueError, match="unknown evidence fields"):
        ChangeAdmissionRecord.from_dict(data)

    data = record.to_dict()
    data["evidence"][0]["required_for_eligibility"] = "false"
    with pytest.raises(ValueError, match="must be a boolean"):
        ChangeAdmissionRecord.from_dict(data)


def test_cli_admit_and_verify_unsigned_record(monkeypatch, tmp_path, capsys):
    mutation_file = tmp_path / "change.thirsty"
    record_file = tmp_path / "admission.json"
    mutation_file.write_text(
        """mutation c { validated_canonical {
        shadow { return input }
        invariant { input == input }
        canonical { return input }
        } }""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "shadow-thirst",
            "admit",
            str(mutation_file),
            "--record",
            str(record_file),
        ],
    )
    shadow_cli.main()
    payload = json.loads(record_file.read_text(encoding="utf-8"))
    assert payload["admission_decision"] == "ELIGIBLE"
    assert payload["execution_authorized"] is False

    monkeypatch.setattr(
        sys,
        "argv",
        ["shadow-thirst", "verify-admission", str(record_file), "--json"],
    )
    shadow_cli.main()
    output = capsys.readouterr().out
    assert '"valid": true' in output


def test_cli_require_signature_rejects_unsigned_record(monkeypatch, tmp_path, capsys):
    record = AdmissionEngine().evaluate(
        mutation("return input", "return input"), generated_at=FIXED_TIME
    )
    record_file = tmp_path / "admission.json"
    record_file.write_text(record.to_json(), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "shadow-thirst",
            "verify-admission",
            str(record_file),
            "--require-signature",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        shadow_cli.main()
    assert exc.value.code == 1
    assert "signature is required" in capsys.readouterr().out


def test_cli_rejects_duplicate_policy_keys(monkeypatch, tmp_path, capsys):
    mutation_file = tmp_path / "change.thirsty"
    record_file = tmp_path / "admission.json"
    policy_file = tmp_path / "policy.json"
    mutation_file.write_text(
        "mutation c { validated_canonical { shadow { return input } "
        "canonical { return input } } }",
        encoding="utf-8",
    )
    policy_file.write_text(
        '{"max_complexity_delta": 10, "max_complexity_delta": 20}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "shadow-thirst",
            "admit",
            str(mutation_file),
            "--policy",
            str(policy_file),
            "--record",
            str(record_file),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        shadow_cli.main()
    assert exc.value.code == 1
    assert "duplicate JSON key" in capsys.readouterr().err
    assert not record_file.exists()
