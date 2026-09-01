"""Governed change admission for Shadow Thirst.

This module is intentionally an admission boundary, not an execution boundary.
It can declare a candidate ``ELIGIBLE``, ``FLAGGED``, or ``REJECTED`` and can
produce a signed Change Admission Record, but it never replaces canonical state
and never converts an analysis result into execution authority.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from cryptography.exceptions import InvalidSignature

from utf.shadow_thirst import convergence
from utf.shadow_thirst.core import (
    AnalysisLevel,
    AnalysisResult,
    PromotionEngine,
    ShadowModule,
    _structural_signature,
)
from utf.shadow_thirst.regression import (
    RegressionFinding,
    analyze_complexity_regression,
    analyze_explainability_regression,
    analyze_governance_regression,
    analyze_security_regression,
)
from utf.tarl.keystore import ROLE_PROOF_SIGNER, KeyFile

RECORD_FORMAT = "shadow-thirst-change-admission/v1"
ENGINE_VERSION = "0.1.0"


class EvidenceStatus(StrEnum):
    PROVEN = "PROVEN"
    OBSERVED = "OBSERVED"
    VIOLATED = "VIOLATED"
    UNKNOWN = "UNKNOWN"
    INAPPLICABLE = "INAPPLICABLE"


class AdmissionDecision(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    FLAGGED = "FLAGGED"
    REJECTED = "REJECTED"


class OriginType(StrEnum):
    HUMAN = "HUMAN"
    AI = "AI"
    JOINT = "JOINT"
    AUTOMATION = "AUTOMATION"
    UNSPECIFIED = "UNSPECIFIED"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


@dataclass(frozen=True)
class Provenance:
    """Origin metadata. Origin never grants authority or changes evidence."""

    origin_type: OriginType = OriginType.UNSPECIFIED
    actor_id: str = ""
    generator: str = ""
    model: str = ""
    request_id: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Provenance:
        data = data or {}
        allowed = {field.name for field in dataclasses.fields(cls)}
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"unknown provenance fields: {sorted(unknown)}")
        try:
            origin_type = OriginType(data.get("origin_type", "UNSPECIFIED"))
        except ValueError as exc:
            raise ValueError("invalid provenance origin_type") from exc
        values = {
            name: data.get(name, "")
            for name in ("actor_id", "generator", "model", "request_id")
        }
        if any(not isinstance(value, str) for value in values.values()):
            raise ValueError("provenance identity fields must be strings")
        return cls(origin_type=origin_type, **values)

    def to_dict(self) -> dict[str, str]:
        result = asdict(self)
        result["origin_type"] = self.origin_type.value
        return result


@dataclass(frozen=True)
class AdmissionPolicy:
    """Deterministic policy for translating evidence into eligibility."""

    policy_id: str = "shadow-thirst/default-governed-change/v1"
    require_proven_equivalence: bool = True
    block_security_regression: bool = True
    block_governance_regression: bool = True
    flag_unknown_required_evidence: bool = True
    max_complexity_ratio: float = 1.5
    max_complexity_delta: int = 20
    max_explainability_depth_delta: int = 2

    def __post_init__(self) -> None:
        boolean_fields = (
            "require_proven_equivalence",
            "block_security_regression",
            "block_governance_regression",
            "flag_unknown_required_evidence",
        )
        for name in boolean_fields:
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be a boolean")
        if not isinstance(self.policy_id, str) or not self.policy_id.strip():
            raise ValueError("policy_id must be non-empty")
        if (
            isinstance(self.max_complexity_ratio, bool)
            or not isinstance(self.max_complexity_ratio, (int, float))
            or not math.isfinite(self.max_complexity_ratio)
        ):
            raise ValueError("max_complexity_ratio must be a finite number")
        if self.max_complexity_ratio < 1.0:
            raise ValueError("max_complexity_ratio must be at least 1.0")
        if isinstance(self.max_complexity_delta, bool) or not isinstance(
            self.max_complexity_delta, int
        ):
            raise ValueError("max_complexity_delta must be an integer")
        if self.max_complexity_delta < 0:
            raise ValueError("max_complexity_delta must be non-negative")
        if isinstance(self.max_explainability_depth_delta, bool) or not isinstance(
            self.max_explainability_depth_delta, int
        ):
            raise ValueError("max_explainability_depth_delta must be an integer")
        if self.max_explainability_depth_delta < 0:
            raise ValueError("max_explainability_depth_delta must be non-negative")

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> AdmissionPolicy:
        data = data or {}
        allowed = {field.name for field in dataclasses.fields(cls)}
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"unknown admission policy fields: {sorted(unknown)}")
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceItem:
    code: str
    analyzer: str
    status: EvidenceStatus
    severity: str
    method: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    required_for_eligibility: bool = False

    @classmethod
    def from_regression(cls, finding: RegressionFinding) -> EvidenceItem:
        return cls(
            code=finding.code,
            analyzer=finding.analyzer,
            status=EvidenceStatus(finding.status),
            severity=finding.severity,
            method=finding.method,
            summary=finding.summary,
            details=finding.details,
            required_for_eligibility=finding.required_for_eligibility,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceItem:
        allowed = {field.name for field in dataclasses.fields(cls)}
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"unknown evidence fields: {sorted(unknown)}")
        required = allowed - {"details", "required_for_eligibility"}
        missing = required - set(data)
        if missing:
            raise ValueError(f"missing evidence fields: {sorted(missing)}")
        string_fields = ("code", "analyzer", "severity", "method", "summary")
        if any(not isinstance(data[name], str) for name in string_fields):
            raise ValueError("evidence identity and summary fields must be strings")
        details = data.get("details", {})
        if not isinstance(details, dict):
            raise ValueError("evidence details must be an object")
        required_value = data.get("required_for_eligibility", False)
        if type(required_value) is not bool:
            raise ValueError("required_for_eligibility must be a boolean")
        return cls(
            code=data["code"],
            analyzer=data["analyzer"],
            status=EvidenceStatus(data["status"]),
            severity=data["severity"],
            method=data["method"],
            summary=data["summary"],
            details=dict(details),
            required_for_eligibility=required_value,
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        return result


@dataclass
class ChangeAdmissionRecord:
    format: str
    engine_version: str
    generated_at: str
    analysis_id: str
    mutation_name: str
    source_sha256: str
    candidate_sha256: str
    canonical_sha256: str
    invariant_sha256: str
    policy: dict[str, Any]
    provenance: dict[str, str]
    legacy_verdict: str
    admission_decision: str
    decision_reasons: list[str]
    evidence: list[EvidenceItem]
    execution_authorized: bool = False
    authorization_state: str = "NOT_EVALUATED"
    signer_key_id: str = ""
    signature_alg: str = ""
    record_hash: str = ""
    signature: str = ""

    def __post_init__(self) -> None:
        if self.execution_authorized:
            raise ValueError("change admission records cannot authorize execution")
        if self.authorization_state != "NOT_EVALUATED":
            raise ValueError(
                "authorization must remain outside Shadow Thirst admission"
            )

    def _body_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "engine_version": self.engine_version,
            "generated_at": self.generated_at,
            "analysis_id": self.analysis_id,
            "mutation_name": self.mutation_name,
            "source_sha256": self.source_sha256,
            "candidate_sha256": self.candidate_sha256,
            "canonical_sha256": self.canonical_sha256,
            "invariant_sha256": self.invariant_sha256,
            "policy": self.policy,
            "provenance": self.provenance,
            "legacy_verdict": self.legacy_verdict,
            "admission_decision": self.admission_decision,
            "decision_reasons": self.decision_reasons,
            "evidence": [item.to_dict() for item in self.evidence],
            "execution_authorized": False,
            "authorization_state": "NOT_EVALUATED",
            "signer_key_id": self.signer_key_id,
            "signature_alg": self.signature_alg,
        }

    def compute_hash(self) -> str:
        return _sha256_text(_canonical_json(self._body_dict()))

    def seal_unsigned(self) -> ChangeAdmissionRecord:
        self.signer_key_id = ""
        self.signature_alg = ""
        self.signature = ""
        self.record_hash = self.compute_hash()
        return self

    def sign(self, key: KeyFile) -> ChangeAdmissionRecord:
        if key.role != ROLE_PROOF_SIGNER:
            raise ValueError(f"admission records require a {ROLE_PROOF_SIGNER!r} key")
        if not key.has_private:
            raise ValueError("admission signing key is public-only")
        self.signer_key_id = key.key_id
        self.signature_alg = "ed25519"
        self.record_hash = self.compute_hash()
        self.signature = key.private_key().sign(bytes.fromhex(self.record_hash)).hex()
        return self

    def verify(self, key: KeyFile | None = None) -> tuple[bool, str]:
        expected_hash = self.compute_hash()
        if self.record_hash != expected_hash:
            return False, "record hash mismatch"
        if not self.signature:
            if self.signature_alg or self.signer_key_id:
                return False, "incomplete signature metadata"
            return True, "unsigned record hash is valid"
        if self.signature_alg != "ed25519":
            return False, "unsupported signature algorithm"
        if key is None:
            return False, "public key is required for signed record"
        if key.role != ROLE_PROOF_SIGNER or key.key_id != self.signer_key_id:
            return False, "signer key identity or role mismatch"
        try:
            signature = bytes.fromhex(self.signature)
        except ValueError:
            return False, "signature is not canonical hexadecimal"
        if self.signature != self.signature.lower():
            return False, "signature is not canonical lowercase hexadecimal"
        try:
            key.public_key().verify(signature, bytes.fromhex(self.record_hash))
        except (InvalidSignature, ValueError):
            return False, "invalid Ed25519 signature"
        return True, "signed record is valid"

    def to_dict(self) -> dict[str, Any]:
        result = self._body_dict()
        result["record_hash"] = self.record_hash
        result["signature"] = self.signature
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, allow_nan=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChangeAdmissionRecord:
        allowed = {field.name for field in dataclasses.fields(cls)}
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"unknown admission record fields: {sorted(unknown)}")
        missing = allowed - set(data)
        if missing:
            raise ValueError(f"missing admission record fields: {sorted(missing)}")
        if data.get("format") != RECORD_FORMAT:
            raise ValueError(
                f"unsupported admission record format: {data.get('format')!r}"
            )
        if data.get("engine_version") != ENGINE_VERSION:
            raise ValueError(
                f"unsupported admission engine version: {data.get('engine_version')!r}"
            )
        decision_value = data.get("admission_decision")
        if not isinstance(decision_value, str):
            raise ValueError("invalid admission decision")
        try:
            AdmissionDecision(decision_value)
        except ValueError as exc:
            raise ValueError("invalid admission decision") from exc
        if data.get("legacy_verdict") not in {"PROMOTE", "FLAGGED", "REJECT"}:
            raise ValueError("invalid legacy Shadow Thirst verdict")
        string_fields = (
            "mutation_name",
            "signer_key_id",
            "signature_alg",
            "signature",
        )
        if any(not isinstance(data.get(name), str) for name in string_fields):
            raise ValueError("record identity and signature fields must be strings")
        if type(data.get("execution_authorized")) is not bool:
            raise ValueError("execution_authorized must be a boolean")
        if data.get("execution_authorized") is not False:
            raise ValueError("change admission records cannot authorize execution")
        if data.get("authorization_state") != "NOT_EVALUATED":
            raise ValueError(
                "authorization must remain outside Shadow Thirst admission"
            )
        generated_at = data.get("generated_at")
        if not isinstance(generated_at, str):
            raise ValueError("generated_at must be a string")
        try:
            parsed_at = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("generated_at must be valid ISO-8601") from exc
        if parsed_at.tzinfo is None or parsed_at.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")
        hash_fields = (
            "analysis_id",
            "source_sha256",
            "candidate_sha256",
            "canonical_sha256",
            "invariant_sha256",
            "record_hash",
        )
        for name in hash_fields:
            value = data.get(name)
            if (
                not isinstance(value, str)
                or len(value) != 64
                or value != value.lower()
                or any(char not in "0123456789abcdef" for char in value)
            ):
                raise ValueError(f"{name} must be canonical lowercase SHA-256 hex")
        policy_data = data.get("policy")
        provenance_data = data.get("provenance")
        if not isinstance(policy_data, dict) or not isinstance(provenance_data, dict):
            raise ValueError("policy and provenance must be objects")
        policy = AdmissionPolicy.from_dict(policy_data)
        provenance = Provenance.from_dict(provenance_data)
        raw_evidence = data.get("evidence")
        if not isinstance(raw_evidence, list):
            raise ValueError("evidence must be an array")
        evidence = []
        for item in raw_evidence:
            if not isinstance(item, dict):
                raise ValueError("each evidence item must be an object")
            evidence.append(EvidenceItem.from_dict(item))
        reasons = data.get("decision_reasons")
        if not isinstance(reasons, list) or any(
            not isinstance(reason, str) for reason in reasons
        ):
            raise ValueError("decision_reasons must be an array of strings")
        values = dict(data)
        values["evidence"] = evidence
        values["policy"] = policy.to_dict()
        values["provenance"] = provenance.to_dict()
        return cls(**values)


def _base_evidence(
    module: ShadowModule,
    result: AnalysisResult,
) -> EvidenceItem:
    ast_by_analyzer = {
        "PlaneIsolation": module.shadow_ast,
        "Determinism": module.shadow_ast,
        "ResourceEstimator": module.shadow_ast,
        "ResourceEstimation": module.shadow_ast,
        "PuritySpring": module.invariant_ast,
        "MemoryEvaporation": module.shadow_ast,
    }
    ast_available = ast_by_analyzer.get(result.analyzer) is not None
    if result.passed and ast_available:
        status = EvidenceStatus.OBSERVED
    elif result.passed:
        status = EvidenceStatus.UNKNOWN
    else:
        status = EvidenceStatus.VIOLATED
    return EvidenceItem(
        code=f"ST-B-{result.analyzer.upper()}",
        analyzer=result.analyzer,
        status=status,
        severity=("CRITICAL" if result.level == AnalysisLevel.CRITICAL else "WARNING"),
        method="existing-analyzer/ast-v0.8.6" if ast_available else "lexical-fallback",
        summary=result.message,
        details={"legacy_passed": result.passed, "legacy_level": result.level},
        required_for_eligibility=result.level == AnalysisLevel.CRITICAL,
    )


def _convergence_evidence(module: ShadowModule) -> EvidenceItem:
    if not module.shadow_code or not module.canonical_code:
        return EvidenceItem(
            code="ST-E001",
            analyzer="CanonicalConvergence",
            status=EvidenceStatus.VIOLATED,
            severity="CRITICAL",
            method="presence-check",
            summary="Both shadow and canonical blocks are required",
            required_for_eligibility=True,
        )
    if module.shadow_ast is None or module.canonical_ast is None:
        return EvidenceItem(
            code="ST-E002",
            analyzer="CanonicalConvergence",
            status=EvidenceStatus.UNKNOWN,
            severity="CRITICAL",
            method="ast-unavailable",
            summary="Equivalence is unknown because one or both blocks did not parse",
            required_for_eligibility=True,
        )
    if _structural_signature(module.shadow_ast, {}) == _structural_signature(
        module.canonical_ast, {}
    ):
        return EvidenceItem(
            code="ST-E003",
            analyzer="CanonicalConvergence",
            status=EvidenceStatus.PROVEN,
            severity="INFO",
            method="alpha-renamed-ast-equivalence/v1",
            summary="Structural equivalence is a sufficient proof for this pair",
            required_for_eligibility=True,
        )

    symbolic = convergence.z3_equivalence(module.shadow_ast, module.canonical_ast)
    if symbolic.status == "equivalent":
        return EvidenceItem(
            code="ST-E004",
            analyzer="CanonicalConvergence",
            status=EvidenceStatus.PROVEN,
            severity="INFO",
            method="z3-symbolic-equivalence/v1",
            summary=symbolic.detail,
            required_for_eligibility=True,
        )
    if symbolic.status == "diverge":
        return EvidenceItem(
            code="ST-E005",
            analyzer="CanonicalConvergence",
            status=EvidenceStatus.VIOLATED,
            severity="CRITICAL",
            method="z3-symbolic-counterexample/v1",
            summary=symbolic.detail,
            details={"counterexample": symbolic.counterexample or {}},
            required_for_eligibility=True,
        )

    sampled = convergence.execute_and_compare(module.shadow_ast, module.canonical_ast)
    if sampled.status == "equivalent":
        return EvidenceItem(
            code="ST-E006",
            analyzer="CanonicalConvergence",
            status=EvidenceStatus.OBSERVED,
            severity="WARNING",
            method="seeded-execute-and-compare/v1",
            summary=sampled.detail,
            details={"symbolic_layer": symbolic.status},
            required_for_eligibility=True,
        )
    if sampled.status == "diverge":
        return EvidenceItem(
            code="ST-E007",
            analyzer="CanonicalConvergence",
            status=EvidenceStatus.VIOLATED,
            severity="CRITICAL",
            method="seeded-divergence-witness/v1",
            summary=sampled.detail,
            details={"counterexample": sampled.counterexample or {}},
            required_for_eligibility=True,
        )
    return EvidenceItem(
        code="ST-E008",
        analyzer="CanonicalConvergence",
        status=EvidenceStatus.UNKNOWN,
        severity="CRITICAL",
        method="conservative-abstention/v1",
        summary="Equivalence remains unknown after symbolic and sampling layers abstained",
        details={
            "symbolic_layer": symbolic.status,
            "symbolic_detail": symbolic.detail,
            "sampling_layer": sampled.status,
            "sampling_detail": sampled.detail,
        },
        required_for_eligibility=True,
    )


class AdmissionEngine:
    """Evaluate technical eligibility without authorizing canonical mutation."""

    def __init__(self, policy: AdmissionPolicy | None = None):
        self.policy = policy or AdmissionPolicy()

    def evaluate(
        self,
        module: ShadowModule,
        *,
        provenance: Provenance | None = None,
        generated_at: datetime | None = None,
    ) -> ChangeAdmissionRecord:
        provenance = provenance or Provenance()
        legacy_verdict, base_results = PromotionEngine().evaluate(module)
        evidence = [
            _base_evidence(module, result)
            for result in base_results
            if result.analyzer != "CanonicalConvergence"
        ]
        evidence.append(_convergence_evidence(module))
        evidence.extend(
            [
                EvidenceItem.from_regression(analyze_security_regression(module)),
                EvidenceItem.from_regression(analyze_governance_regression(module)),
                EvidenceItem.from_regression(
                    analyze_complexity_regression(
                        module,
                        max_ratio=self.policy.max_complexity_ratio,
                        max_delta=self.policy.max_complexity_delta,
                    )
                ),
                EvidenceItem.from_regression(
                    analyze_explainability_regression(
                        module,
                        max_depth_delta=(self.policy.max_explainability_depth_delta),
                    )
                ),
            ]
        )

        decision, reasons = self._decide(evidence, legacy_verdict)
        policy_dict = self.policy.to_dict()
        candidate_sha256 = _sha256_text(module.shadow_code)
        canonical_sha256 = _sha256_text(module.canonical_code)
        invariant_sha256 = _sha256_text(module.invariant_code)
        analysis_material: dict[str, Any] = {
            "engine_version": ENGINE_VERSION,
            "mutation_name": module.name,
            "source_sha256": module.replay_hash(),
            "candidate_sha256": candidate_sha256,
            "canonical_sha256": canonical_sha256,
            "invariant_sha256": invariant_sha256,
            "policy": policy_dict,
        }
        at = generated_at or datetime.now(UTC)
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")
        record = ChangeAdmissionRecord(
            format=RECORD_FORMAT,
            engine_version=ENGINE_VERSION,
            generated_at=at.astimezone(UTC).isoformat(timespec="seconds"),
            analysis_id=_sha256_text(_canonical_json(analysis_material)),
            mutation_name=module.name,
            source_sha256=module.replay_hash(),
            candidate_sha256=candidate_sha256,
            canonical_sha256=canonical_sha256,
            invariant_sha256=invariant_sha256,
            policy=policy_dict,
            provenance=provenance.to_dict(),
            legacy_verdict=legacy_verdict,
            admission_decision=decision.value,
            decision_reasons=reasons,
            evidence=evidence,
        )
        return record.seal_unsigned()

    def _decide(
        self,
        evidence: list[EvidenceItem],
        legacy_verdict: str,
    ) -> tuple[AdmissionDecision, list[str]]:
        reject_reasons: list[str] = []
        flag_reasons: list[str] = []

        for item in evidence:
            if item.status == EvidenceStatus.VIOLATED:
                if item.analyzer == "SecurityRegression":
                    target = (
                        reject_reasons
                        if self.policy.block_security_regression
                        else flag_reasons
                    )
                elif item.analyzer == "GovernanceRegression":
                    target = (
                        reject_reasons
                        if self.policy.block_governance_regression
                        else flag_reasons
                    )
                elif item.severity == "CRITICAL":
                    target = reject_reasons
                else:
                    target = flag_reasons
                target.append(f"{item.code}: {item.summary}")
            elif (
                item.status == EvidenceStatus.UNKNOWN
                and item.required_for_eligibility
                and self.policy.flag_unknown_required_evidence
            ):
                flag_reasons.append(f"{item.code}: {item.summary}")

        convergence_item = next(
            item for item in evidence if item.analyzer == "CanonicalConvergence"
        )
        if (
            self.policy.require_proven_equivalence
            and convergence_item.status == EvidenceStatus.OBSERVED
        ):
            flag_reasons.append(
                "ST-P001: configured policy requires proven, not merely observed, equivalence"
            )

        if legacy_verdict == "REJECT" and not reject_reasons:
            flag_reasons.append(
                "ST-P002: legacy Shadow Thirst rejected or could not clear the candidate"
            )

        if reject_reasons:
            return AdmissionDecision.REJECTED, reject_reasons
        if flag_reasons:
            return AdmissionDecision.FLAGGED, flag_reasons
        return AdmissionDecision.ELIGIBLE, [
            "All configured technical admission requirements were satisfied; "
            "separate authority is still required to mutate canonical state"
        ]


__all__ = [
    "AdmissionDecision",
    "AdmissionEngine",
    "AdmissionPolicy",
    "ChangeAdmissionRecord",
    "ENGINE_VERSION",
    "EvidenceItem",
    "EvidenceStatus",
    "OriginType",
    "Provenance",
    "RECORD_FORMAT",
]
