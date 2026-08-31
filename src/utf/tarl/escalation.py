"""
ESCALATE resolution via signed quorum approval (THREAT_MODEL C050).

Urgency/authority language can pressure a single operator into a high-risk ALLOW.
The defense is structural: high-risk requests resolve to **ESCALATE**, and an
ESCALATE only becomes ALLOW when a quorum of distinct approvers each
cryptographically sign their approval of *that exact verified proof*. A
duplicate identity or key counts once; a replay from another policy or a
forged approval cannot meet quorum.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from utf.tarl.context import SOURCE_INJECTION_ALGORITHM_ID
from utf.tarl.core import PolicyParser
from utf.tarl.spec import TarlDecision, TarlProof, TarlVerdict
from utf.tarl.verifier import (
    ProofVerifier,
    context_authority_admissible,
)


def proof_digest(proof: TarlProof) -> str:
    """Hash the complete proof artifact, including its signature and key id."""
    encoded = json.dumps(
        proof.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


@dataclass
class Approval:
    """A signed approval bound to one exact escalated proof artifact."""

    approver: str
    context_hash: str
    proof_hash: str = ""
    key_id: str = ""
    signature: str = ""  # "ed25519:<hex>"

    def signing_bytes(self) -> bytes:
        return json.dumps(
            {
                "approver": self.approver,
                "context_hash": self.context_hash,
                "proof_hash": self.proof_hash,
                "key_id": self.key_id,
            },
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")


class ApprovalIssuer:
    """An individual approver: signs approvals for escalated decisions."""

    def __init__(
        self, approver: str, key_id: str,
        private_key: bytes | Ed25519PrivateKey,
    ):
        if not approver or not key_id:
            raise ValueError("approver and key_id must be non-empty")
        if isinstance(private_key, Ed25519PrivateKey):
            self._key = private_key
        else:
            self._key = Ed25519PrivateKey.from_private_bytes(private_key)
        self.approver = approver
        self.key_id = key_id

    def public_key_bytes(self) -> bytes:
        return self._key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def approve(self, proof: TarlProof) -> Approval:
        approval = Approval(
            approver=self.approver,
            context_hash=proof.context_hash,
            proof_hash=proof_digest(proof),
            key_id=self.key_id,
        )
        approval.signature = "ed25519:" + self._key.sign(
            approval.signing_bytes()).hex()
        return approval


@dataclass
class QuorumResult:
    """Outcome of resolving an escalation."""

    decision: TarlDecision
    approvals_counted: int
    threshold: int
    reason: str = ""


class QuorumResolver:
    """Upgrades an ESCALATE decision to ALLOW once a quorum of distinct,
    validly-signed approvals over a verified proof is reached."""

    def __init__(
        self,
        threshold: int,
        *,
        proof_verifier: ProofVerifier | None = None,
        policy_source: str | None = None,
        clock: Callable[[], datetime.datetime | None] | None = None,
    ):
        if threshold < 1:
            raise ValueError("quorum threshold must be >= 1")
        if proof_verifier is not None and not isinstance(
            proof_verifier, ProofVerifier
        ):
            raise TypeError("proof verifier must be a ProofVerifier")
        if policy_source is not None and (
            not isinstance(policy_source, str) or not policy_source
        ):
            raise ValueError("policy_source must be non-empty")
        self.threshold = threshold
        self._keys: dict[str, Ed25519PublicKey] = {}
        self._proof_verifier = proof_verifier
        self._policy_source = policy_source
        self._clock = clock

    def set_proof_verifier(
        self,
        verifier: ProofVerifier,
        *,
        policy_source: str,
    ) -> QuorumResolver:
        """Configure the independent verifier and exact governing policy."""
        if not isinstance(verifier, ProofVerifier):
            raise TypeError("proof verifier must be a ProofVerifier")
        if not isinstance(policy_source, str) or not policy_source:
            raise ValueError("policy_source must be non-empty")
        self._proof_verifier = verifier
        self._policy_source = policy_source
        return self

    def set_clock(
        self,
        clock: Callable[[], datetime.datetime | None],
    ) -> QuorumResolver:
        """Set the explicit trusted time source used during promotion."""
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._clock = clock
        return self

    def _verification_time(self) -> tuple[datetime.datetime | None, str]:
        if self._clock is None:
            return None, "trusted verification time is required"
        try:
            now = self._clock()
        except Exception as exc:
            return None, f"trusted verification time is unavailable: {exc}"
        if not isinstance(now, datetime.datetime):
            return None, "trusted verification time must be a datetime"
        if now.tzinfo is None or now.utcoffset() is None:
            return None, "trusted verification time must be timezone-aware"
        return now.astimezone(datetime.UTC), ""

    def add_approver_key(
        self, key_id: str, public_key: bytes | Ed25519PublicKey
    ) -> QuorumResolver:
        if not isinstance(key_id, str) or not key_id:
            raise ValueError("approver key_id must be non-empty")
        if isinstance(public_key, Ed25519PublicKey):
            key = public_key
        else:
            key = Ed25519PublicKey.from_public_bytes(public_key)
        self._keys[key_id] = key
        return self

    def _valid(self, approval: Approval, proof: TarlProof) -> bool:
        if (
            not isinstance(approval.approver, str)
            or not approval.approver
            or approval.context_hash != proof.context_hash
        ):
            return False  # approval is for a different decision
        try:
            if approval.proof_hash != proof_digest(proof):
                return False
        except (TypeError, ValueError):
            return False
        alg, _, sig_hex = approval.signature.partition(":")
        if alg != "ed25519" or not sig_hex:
            return False
        key = self._keys.get(approval.key_id)
        if key is None:
            return False
        try:
            key.verify(bytes.fromhex(sig_hex), approval.signing_bytes())
            return True
        except (ValueError, InvalidSignature):
            return False

    def _proof_is_authoritative(
        self,
        decision: TarlDecision,
        proof: TarlProof,
        *,
        expected_context: dict | None,
        expected_evaluated_context: dict | None,
    ) -> tuple[bool, str]:
        if self._proof_verifier is None or not self._policy_source:
            return False, "proof verifier and policy source are required"
        if (
            self._proof_verifier.max_age_seconds is None
            or self._proof_verifier.replay_guard is None
        ):
            return False, (
                "proof verifier freshness and replay enforcement are required"
            )
        verification_now, time_error = self._verification_time()
        if verification_now is None:
            return False, time_error
        if proof.verdict is not TarlVerdict.ESCALATE:
            return False, "proof verdict does not authorize escalation"
        if decision.rule_index != proof.rule_index:
            return False, "decision and proof rule indices do not match"
        if proof.rule_index < 0:
            return False, "only a matched ESCALATE rule can be resolved"
        try:
            policy = PolicyParser.parse(self._policy_source)
            rule = policy.rules[proof.rule_index]
        except Exception as exc:
            return False, f"escalation rule cannot be resolved: {exc}"
        if (
            rule.verdict is not TarlVerdict.ESCALATE
            or proof.matched_condition != rule.condition
            or decision.matched_rule != str(rule)
        ):
            return False, "decision, proof, and policy rule do not match"
        if decision.expires_at != proof.expires_at:
            return False, "decision expiry does not match proof"
        if proof.expires_at is not None:
            try:
                expires_at = datetime.datetime.fromisoformat(
                    proof.expires_at.replace("Z", "+00:00")
                )
                if (
                    expires_at.tzinfo is None
                    or expires_at.utcoffset() is None
                ):
                    return False, (
                        "time-bound escalation timestamps must be timezone-aware"
                    )
                expires_at = expires_at.astimezone(datetime.UTC)
            except (TypeError, ValueError) as exc:
                return False, f"time-bound escalation expiry is invalid: {exc}"
            if verification_now >= expires_at:
                return False, "escalated decision has expired"
        if proof.normalization_algorithm_id in {
            SOURCE_INJECTION_ALGORITHM_ID,
            "tarl.registered-source-injection",
        }:
            if expected_context is None or expected_evaluated_context is None:
                return False, (
                    "source-injected escalation requires original and "
                    "evaluated contexts"
                )
        verification = self._proof_verifier.verify(
            proof,
            policy_source=self._policy_source,
            expected_context=expected_context,
            expected_evaluated_context=expected_evaluated_context,
            now=verification_now,
        )
        if (
            not verification.valid
            or verification.checks.get("signature") is not True
        ):
            return False, f"escalation proof is invalid: {verification.message}"
        if not context_authority_admissible(proof, TarlVerdict.ESCALATE):
            return False, (
                "escalation proof lacks a passed authoritative context schema"
            )
        return True, ""

    def resolve(
        self,
        decision: TarlDecision,
        proof: TarlProof,
        approvals: list[Approval],
        *,
        expected_context: dict | None = None,
        expected_evaluated_context: dict | None = None,
    ) -> QuorumResult:
        """Resolve an escalated decision against a set of approvals.

        Only ESCALATE decisions are resolvable. Counts **distinct** approvers
        (duplicate approver identities or keys count once) whose approval
        validly signs this exact proof. The proof itself must be signed,
        policy-bound, internally consistent, and schema-admissible. Threshold
        met → ALLOW; otherwise the decision stays ESCALATE.
        """
        if decision.verdict != TarlVerdict.ESCALATE:
            return QuorumResult(
                decision, 0, self.threshold,
                "not an ESCALATE decision; nothing to resolve")
        if (
            proof.normalization_algorithm_id
            in {
                SOURCE_INJECTION_ALGORITHM_ID,
                "tarl.registered-source-injection",
            }
            and (
                expected_context is None
                or expected_evaluated_context is None
            )
        ):
            return QuorumResult(
                decision,
                0,
                self.threshold,
                "inadmissible escalation proof: source-injected escalation "
                "requires original and evaluated contexts",
            )
        if expected_context is None:
            return QuorumResult(
                decision,
                0,
                self.threshold,
                "inadmissible escalation proof: original request context is required",
            )
        distinct: set[str] = set()
        distinct_keys: set[bytes] = set()
        for approval in approvals:
            if self._valid(approval, proof):
                key = self._keys[approval.key_id]
                key_material = key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                )
                if (
                    approval.approver in distinct
                    or key_material in distinct_keys
                ):
                    continue
                distinct.add(approval.approver)
                distinct_keys.add(key_material)
        counted = len(distinct)
        if counted >= self.threshold:
            proof_ok, proof_reason = self._proof_is_authoritative(
                decision,
                proof,
                expected_context=expected_context,
                expected_evaluated_context=expected_evaluated_context,
            )
            if not proof_ok:
                return QuorumResult(
                    decision,
                    0,
                    self.threshold,
                    f"inadmissible escalation proof: {proof_reason}",
                )
            allowed = TarlDecision(
                verdict=TarlVerdict.ALLOW,
                reason=(f"escalation approved by quorum "
                        f"({counted}/{self.threshold}): "
                        f"{', '.join(sorted(distinct))}"),
                rule_index=decision.rule_index,
                matched_rule=decision.matched_rule,
                expires_at=decision.expires_at,
            )
            return QuorumResult(allowed, counted, self.threshold, "quorum met")
        return QuorumResult(
            decision, counted, self.threshold,
            f"insufficient approvals ({counted}/{self.threshold}); "
            "decision remains ESCALATE")


__all__ = [
    "Approval", "ApprovalIssuer", "QuorumResolver", "QuorumResult",
    "proof_digest",
]
