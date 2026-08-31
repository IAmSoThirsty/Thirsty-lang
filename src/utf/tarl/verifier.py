"""
T.A.R.L. Proof Verifier — Phase 4

Independent verification of TarlProof certificates:
  1. Signature validity (HMAC-SHA256 or Ed25519)
  2. Policy hash match (optional, requires policy source)
  3. Evaluation trace internal consistency
  4. Context representation and transformation coherence

No runtime or policy engine is required — proofs are self-contained.
"""
from __future__ import annotations

import datetime
import hashlib
import hmac
import math
from dataclasses import dataclass, field

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from utf.tarl.context import (
    CONTEXT_REPRESENTATION_ID,
    NORMALIZATION_ALGORITHM_ID,
    NORMALIZATION_VERSION,
    SOURCE_INJECTION_ALGORITHM_ID,
    ContextResolutionError,
    hash_rejected_canonical_binding,
    hash_rejected_context,
    prepare_context,
)
from utf.tarl.core import (
    PolicyParser,
    _check_policy_temporal,
    _policy_authority_expiry,
    _policy_temporal_bounds,
)
from utf.tarl.spec import TarlProof, TarlVerdict


def _decode_canonical_hex(value: object, byte_length: int) -> bytes | None:
    """Decode one exact lowercase hex representation without whitespace."""
    if (
        type(value) is not str
        or len(value) != byte_length * 2
        or any(char not in "0123456789abcdef" for char in value)
    ):
        return None
    try:
        return bytes.fromhex(value)
    except ValueError:
        return None


def _check_proof_structure(proof: object) -> bool:
    """Reject malformed proof objects before any cryptographic lookup."""
    if not isinstance(proof, TarlProof):
        return False
    required_strings = (
        proof.policy_hash,
        proof.context_hash,
        proof.matched_condition,
        proof.evaluated_at,
        proof.signature,
        proof.key_id,
    )
    optional_strings = (
        proof.original_context_hash,
        proof.canonical_context_hash,
        proof.context_representation_id,
        proof.normalization_algorithm_id,
        proof.normalization_version,
        proof.context_conflict_status,
        proof.context_schema_hash,
        proof.context_schema_representation_id,
        proof.context_schema_validation_status,
        proof.expires_at,
    )
    if not all(type(value) is str for value in required_strings):
        return False
    if not all(value is None or type(value) is str for value in optional_strings):
        return False
    if type(proof.rule_index) is not int or proof.rule_index < -1:
        return False
    if not isinstance(proof.verdict, TarlVerdict):
        return False
    if type(proof.trace) is not list or not all(
        type(entry) is dict for entry in proof.trace
    ):
        return False
    try:
        proof.canonical_bytes()
    except (AttributeError, TypeError, ValueError):
        return False
    return True


def canonical_context_hash(context: dict) -> str:
    """SHA-256 of a context, matching how the runtime stamps proof.context_hash.

    Used to bind a proof to the context it was issued for, so an old ALLOW proof
    cannot be replayed against a different context (C023)."""
    return prepare_context(context).canonical_context_hash


def _check_context_coherence(proof: TarlProof) -> bool:
    """Validate the representation metadata bound into a proof.

    A legacy proof without these fields can remain inspectable, but it cannot
    carry a positive authorization verdict.  Invalid/conflicting contexts are
    only coherent for fail-closed non-ALLOW proofs stamped as ``rejected``.
    """
    fields = (
        proof.original_context_hash,
        proof.canonical_context_hash,
        proof.context_representation_id,
        proof.normalization_algorithm_id,
        proof.normalization_version,
        proof.context_conflict_status,
    )
    if all(value is None for value in fields):
        return proof.verdict is not TarlVerdict.ALLOW
    if any(value is None for value in fields):
        return False
    if proof.context_representation_id != CONTEXT_REPRESENTATION_ID:
        return False
    if proof.normalization_version != NORMALIZATION_VERSION:
        return False
    if not isinstance(proof.original_context_hash, str) or not _is_sha256(
        proof.original_context_hash
    ):
        return False

    if proof.normalization_algorithm_id == "rejected":
        return (
            proof.verdict is not TarlVerdict.ALLOW
            and proof.context_conflict_status in {"invalid", "conflict"}
            and isinstance(proof.canonical_context_hash, str)
            and _is_sha256(proof.canonical_context_hash)
            and proof.canonical_context_hash
            == hash_rejected_canonical_binding(
                proof.original_context_hash,
                proof.context_conflict_status,
            )
            and proof.context_hash == proof.canonical_context_hash
        )

    if proof.normalization_algorithm_id not in {
        NORMALIZATION_ALGORITHM_ID,
        SOURCE_INJECTION_ALGORITHM_ID,
        "identity",
        "tarl.registered-source-injection",
    }:
        return False
    if proof.context_conflict_status != "none":
        return False
    if not isinstance(proof.canonical_context_hash, str) or not _is_sha256(
        proof.canonical_context_hash
    ):
        return False
    if proof.context_hash != proof.canonical_context_hash:
        return False
    if (
        proof.normalization_algorithm_id == "identity"
        and proof.original_context_hash != proof.canonical_context_hash
    ):
        return False
    return True


def _is_sha256(value: str) -> bool:
    prefix, separator, digest = value.partition(":")
    if prefix != "sha256" or not separator or len(digest) != 64:
        return False
    try:
        int(digest, 16)
    except ValueError:
        return False
    return True


def _check_context_schema_coherence(proof: TarlProof) -> bool:
    """Require positive proofs to attest a passed explicit schema check."""
    fields = (
        proof.context_schema_hash,
        proof.context_schema_representation_id,
        proof.context_schema_validation_status,
    )
    if all(value is None for value in fields):
        return proof.verdict is not TarlVerdict.ALLOW
    if any(value is None for value in fields):
        return False

    status = proof.context_schema_validation_status
    schema_hash = proof.context_schema_hash
    schema_representation = proof.context_schema_representation_id

    if status == "not_configured":
        return (
            proof.verdict is not TarlVerdict.ALLOW
            and schema_hash == ""
            and schema_representation == ""
        )
    if status == "error" and schema_hash == "" and schema_representation == "":
        return proof.verdict is not TarlVerdict.ALLOW
    if status not in {"passed", "failed", "not_evaluated", "error"}:
        return False
    if schema_representation != proof.context_representation_id:
        return False
    if schema_representation != CONTEXT_REPRESENTATION_ID:
        return False
    if not isinstance(schema_hash, str) or not _is_sha256(schema_hash):
        return False
    if proof.verdict is TarlVerdict.ALLOW:
        return status == "passed"
    return True


def context_authority_admissible(
    proof: TarlProof,
    expected_verdict: TarlVerdict,
) -> bool:
    """Return whether a proof can participate in an authority transition.

    This requires a structurally coherent matched-rule proof plus context and
    schema coherence. Consumers that accept proofs across a trust boundary must
    still use :class:`ProofVerifier` for signatures, policy binding, freshness,
    replay, temporal authority, and expected contexts.
    """
    return (
        _check_proof_structure(proof)
        and proof.verdict is expected_verdict
        and proof.rule_index >= 0
        and _check_trace(proof)
        and _check_context_coherence(proof)
        and _check_context_schema_coherence(proof)
        and proof.context_schema_validation_status == "passed"
    )


def positive_context_authority_admissible(proof: TarlProof) -> bool:
    """Return whether an ALLOW proof is context-safe for authority consumers."""
    return context_authority_admissible(proof, TarlVerdict.ALLOW)


def _check_source_injection_relation(
    original_context: dict,
    evaluated_context: dict,
) -> bool:
    """Validate the sole permitted source-injection transformation.

    Evaluation may add one or more top-level ``source:<name>`` fields. Source
    names use the same non-empty alphanumeric/underscore grammar as TARL's
    tokenizer. Removing those additions must reproduce the original context
    byte-for-byte under the authoritative canonical JSON encoding.
    """
    restored: dict = {}
    source_count = 0
    for key, value in evaluated_context.items():
        if key.startswith("source:"):
            source_name = key.removeprefix("source:")
            if not source_name or not all(
                char.isalnum() or char == "_" for char in source_name
            ):
                return False
            source_count += 1
            continue
        restored[key] = value

    if source_count == 0:
        return False
    try:
        restored_context = prepare_context(restored)
        original = prepare_context(original_context)
    except ContextResolutionError:
        return False
    return (
        restored_context.canonical_context_hash
        == original.canonical_context_hash
    )


def _check_freshness(
    proof: TarlProof,
    max_age_seconds: float,
    now: datetime.datetime | None,
) -> bool:
    """True if proof.evaluated_at is within max_age_seconds of ``now``."""
    if (
        isinstance(max_age_seconds, bool)
        or not isinstance(max_age_seconds, (int, float))
        or not math.isfinite(max_age_seconds)
        or max_age_seconds < 0
    ):
        return False
    trusted_now = now if now is not None else datetime.datetime.now(datetime.UTC)
    if (
        not isinstance(trusted_now, datetime.datetime)
        or trusted_now.tzinfo is None
        or trusted_now.utcoffset() is None
    ):
        return False
    evaluated_at = _parse_bound_datetime(proof.evaluated_at)
    if evaluated_at is None:
        return False
    age = (
        trusted_now.astimezone(datetime.UTC) - evaluated_at
    ).total_seconds()
    # Allow small clock skew into the future; reject anything older than the bound.
    return -60.0 <= age <= max_age_seconds


def _parse_bound_datetime(value: object) -> datetime.datetime | None:
    """Parse one proof-bound timestamp without inventing a timezone."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(datetime.UTC)


def _check_policy_expiry(
    proof: TarlProof,
    policy_source: str | None,
    now: datetime.datetime | None,
) -> tuple[bool | None, str]:
    """Validate a proof's matched-rule expiry against its governing policy.

    Untimed proofs retain the verifier's existing optional-policy behavior.
    A proof that carries an expiry is different: independent verification must
    have the exact policy source to derive the duration, and an explicit
    timezone-aware trusted ``now`` to decide whether authority remains live.
    The host clock is deliberately never used for this check.
    """
    if policy_source is None:
        if proof.expires_at is None:
            return None, ""
        return False, "time-bound proof requires the governing policy source"

    try:
        policy = PolicyParser.parse(policy_source)
    except Exception as exc:
        return False, f"governing policy could not be parsed: {exc}"

    evaluated_at = _parse_bound_datetime(proof.evaluated_at)
    if evaluated_at is None:
        return False, "proof evaluated_at must be timezone-aware ISO-8601"

    temporal_at_evaluation = _check_policy_temporal(policy, now=evaluated_at)
    if temporal_at_evaluation is not None:
        if (
            proof.rule_index < 0
            and proof.expires_at is None
            and proof.verdict is temporal_at_evaluation.verdict
        ):
            return True, "proof records the governing temporal fallback verdict"
        return False, "proof was issued outside the governing policy window"

    if proof.rule_index < 0:
        if proof.expires_at is not None:
            return False, "proof without a matched rule carries an expiry"
        return True, "proof has no matched-rule expiry"

    try:
        rule = policy.rules[proof.rule_index]
    except (IndexError, TypeError):
        return False, "proof rule index is absent from the governing policy"

    if (
        proof.matched_condition != rule.condition
        or proof.verdict is not rule.verdict
    ):
        return False, "proof does not bind the matched governing-policy rule"

    try:
        valid_from, effective_until = _policy_temporal_bounds(policy)
        expected_expiry = _policy_authority_expiry(
            policy, rule, evaluated_at
        )
    except (ContextResolutionError, OverflowError, TypeError, ValueError) as exc:
        return False, f"governing policy temporal metadata is invalid: {exc}"

    has_temporal_authority = (
        valid_from is not None
        or effective_until is not None
        or rule.duration_seconds is not None
    )
    if expected_expiry is None:
        if proof.expires_at is not None:
            return False, "unbounded governing rule carries a proof expiry"
        if not has_temporal_authority:
            return True, "matched policy rule is unbounded"
    else:
        expires_at = _parse_bound_datetime(proof.expires_at)
        if expires_at is None:
            return False, "time-bound proof expiry must be timezone-aware ISO-8601"
        if expires_at != expected_expiry:
            return False, (
                "proof expiry does not match the earliest rule or policy cutoff"
            )

    if not has_temporal_authority:
        return True, "matched policy rule is unbounded"
    if (
        not isinstance(now, datetime.datetime)
        or now.tzinfo is None
        or now.utcoffset() is None
    ):
        return False, (
            "temporal proof requires an explicit trusted verification time"
        )
    trusted_now = now.astimezone(datetime.UTC)
    temporal_now = _check_policy_temporal(policy, now=trusted_now)
    if temporal_now is not None:
        return False, "governing policy is not effective at verification time"
    if expected_expiry is not None and trusted_now >= expected_expiry:
        return False, "proof authorization has expired"
    return True, "proof temporal authority is live"


class ReplayGuard:
    """Records accepted proofs and rejects exact reuse (single-use enforcement).

    Identity binds the complete signed proof semantics and canonical signature
    bytes. A duplicate is a replay. State is in-memory by default; back it with
    durable storage for cross-process enforcement."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    @staticmethod
    def proof_id(proof: TarlProof) -> str:
        alg, separator, raw_hex = proof.signature.partition(":")
        try:
            signature_bytes = bytes.fromhex(raw_hex) if separator else b""
        except ValueError:
            signature_bytes = proof.signature.encode("utf-8", errors="replace")
        material = b"\0".join((
            b"tarl.replay.v2",
            proof.canonical_bytes(),
            proof.key_id.encode("utf-8"),
            alg.encode("ascii", errors="replace"),
            signature_bytes,
        ))
        return "sha256:" + hashlib.sha256(material).hexdigest()

    @staticmethod
    def legacy_proof_id(proof: TarlProof) -> str:
        """Canonicalized 0.8.5 identity for durable-store compatibility."""
        signature = proof.signature
        alg, separator, raw_hex = signature.partition(":")
        if separator:
            try:
                signature = f"{alg}:{bytes.fromhex(raw_hex).hex()}"
            except ValueError:
                pass
        return f"{proof.context_hash}|{proof.evaluated_at}|{signature}"

    def check_and_record(self, proof: TarlProof) -> bool:
        """Return True the first time a proof is seen, False on every reuse."""
        identifiers = {self.proof_id(proof), self.legacy_proof_id(proof)}
        if self._seen.intersection(identifiers):
            return False
        self._seen.update(identifiers)
        return True


@dataclass
class VerificationResult:
    """Result of verifying a TarlProof."""
    valid: bool
    checks: dict[str, bool | None] = field(default_factory=dict)
    message: str = ""

    def __str__(self) -> str:
        status = "VALID" if self.valid else "INVALID"
        return f"[{status}] {self.message}"

    @property
    def summary(self) -> str:
        lines = [str(self)]
        for check, result in self.checks.items():
            if result is True:
                mark = "✓"
            elif result is False:
                mark = "✗"
            else:
                mark = "-"
            lines.append(f"  {mark} {check}")
        return "\n".join(lines)


class ProofVerifier:
    """
    Verifies TarlProof certificates independently of the runtime.

    Usage::

        verifier = ProofVerifier()
        verifier.add_hmac_key("key1", b"my-secret")
        verifier.add_ed25519_key("key2", ed25519_public_key)
        result = verifier.verify(proof, policy_source=policy_text)
        assert result.valid
    """

    def __init__(
        self,
        require_signature: bool = True,
        allowed_signature_algorithms: set[str] | None = None,
        require_policy_source: bool = False,
        max_age_seconds: float | None = None,
        revoked_policy_hashes: set[str] | None = None,
        replay_guard: ReplayGuard | None = None,
    ) -> None:
        """
        Verification options:

          require_signature             — an unsigned proof is INVALID by
                                          default; pass False only for explicit
                                          local/permissive inspection.
          allowed_signature_algorithms  — restrict accepted signature families
                                          (e.g. {"ed25519"} rejects HMAC proofs).
                                          Compared against the algorithm family
                                          (``hmac`` / ``ed25519``).
          require_policy_source         — verification without a policy_source to
                                          bind policy_hash against is INVALID.
          max_age_seconds               — reject proofs whose evaluated_at is
                                          older than this (freshness; C024).
          revoked_policy_hashes         — proofs bound to a revoked policy hash
                                          are INVALID (policy revocation; C024).
          replay_guard                  — a ReplayGuard; a proof already seen is
                                          rejected as a replay (C023/C024).
        """
        self._hmac_keys: dict[str, bytes] = {}
        self._ed25519_keys: dict[str, Ed25519PublicKey] = {}
        self.require_signature = require_signature
        self.allowed_signature_algorithms = (
            {a.lower() for a in allowed_signature_algorithms}
            if allowed_signature_algorithms is not None
            else None
        )
        self.require_policy_source = require_policy_source
        self.max_age_seconds = max_age_seconds
        self.revoked_policy_hashes = revoked_policy_hashes or set()
        self.replay_guard = replay_guard

    def add_hmac_key(self, key_id: str, secret: bytes) -> ProofVerifier:
        """Register an HMAC-SHA256 key for signature verification."""
        self._hmac_keys[key_id] = secret
        return self

    def add_ed25519_key(
        self, key_id: str, public_key: bytes | Ed25519PublicKey
    ) -> ProofVerifier:
        """Register an Ed25519 public key for signature verification."""
        if isinstance(public_key, Ed25519PublicKey):
            key = public_key
        else:
            key = Ed25519PublicKey.from_public_bytes(public_key)
        self._ed25519_keys[key_id] = key
        return self

    def verify(
        self,
        proof: TarlProof,
        policy_source: str | None = None,
        expected_context: dict | None = None,
        expected_evaluated_context: dict | None = None,
        now: datetime.datetime | None = None,
    ) -> VerificationResult:
        """
        Verify a TarlProof.

        Checks performed:
          signature    — HMAC-SHA256 or Ed25519 valid (or None if unsigned)
          policy_hash  — matches provided policy_source (or None if not given)
          trace        — internal consistency (k is first True in T)
          context_coherence — positive proof binds an accepted representation
                              and a supported transformation
          context_schema_coherence — positive proof binds a passed schema
                                     validation using that representation
          context_binding   — original/evaluated hashes match expected_context
          evaluated_context_binding — source-injected evaluated context matches
                                      expected_evaluated_context
          source_transformation — evaluated context differs only by valid,
                                  top-level source namespace additions
          expiry          — a time-bound proof matches the governing rule and
                            remains live at an explicit trusted verification time

        valid = True requires:
          - signature is True, or None only when unsigned proofs were
            explicitly allowed
          - policy_hash is True or None (not provided)
          - trace is True
          - context_coherence is True
          - context_schema_coherence is True
        """
        checks: dict[str, bool | None] = {}
        messages: list[str] = []

        structure_ok = _check_proof_structure(proof)
        checks["structure"] = structure_ok
        if not structure_ok:
            return VerificationResult(
                valid=False,
                checks=checks,
                message="proof structure INVALID",
            )

        # ── 1. Signature ──────────────────────────────────────────────────────
        sig_result = self._check_signature(proof)
        if self.require_signature and sig_result is None:
            # Strict mode: an unsigned proof is not acceptable.
            sig_result = False
        checks["signature"] = sig_result
        if sig_result is True:
            messages.append("signature valid")
        elif sig_result is False:
            messages.append(
                "signature INVALID"
                if proof.signature or not self.require_signature
                else "signature REQUIRED but proof is unsigned"
            )
        else:
            messages.append("signature skipped (unsigned)")

        # ── 2. Policy hash ────────────────────────────────────────────────────
        if policy_source is not None:
            ph_ok = _check_policy_hash(proof, policy_source)
            checks["policy_hash"] = ph_ok
            messages.append(
                "policy hash valid" if ph_ok else "policy hash MISMATCH"
            )
        elif self.require_policy_source:
            # Strict mode: cannot certify policy binding without the source.
            checks["policy_hash"] = False
            messages.append("policy source REQUIRED but not provided")
        else:
            checks["policy_hash"] = None

        # ── 3. Trace consistency ──────────────────────────────────────────────
        trace_ok = _check_trace(proof)
        checks["trace"] = trace_ok
        messages.append(
            "trace consistent" if trace_ok else "trace INCONSISTENT"
        )

        # ── 4. Context representation coherence ──────────────────────────────
        coherence_ok = _check_context_coherence(proof)
        checks["context_coherence"] = coherence_ok
        messages.append(
            "context representation coherent"
            if coherence_ok
            else "context representation INADMISSIBLE"
        )

        schema_coherence_ok = _check_context_schema_coherence(proof)
        checks["context_schema_coherence"] = schema_coherence_ok
        messages.append(
            "context schema binding coherent"
            if schema_coherence_ok
            else "context schema binding INADMISSIBLE"
        )

        # ── 5. Context binding (C023: replay an old proof for a new context) ──
        source_transformed = proof.normalization_algorithm_id in {
            SOURCE_INJECTION_ALGORITHM_ID,
            "tarl.registered-source-injection",
        }
        prepared_expected_context = None
        prepared_expected_evaluated_context = None
        if expected_context is not None:
            try:
                prepared_expected_context = prepare_context(expected_context)
            except ContextResolutionError:
                if proof.normalization_algorithm_id == "rejected":
                    rejected_original_hash = hash_rejected_context(
                        expected_context
                    )
                    cb_ok = (
                        proof.original_context_hash
                        == rejected_original_hash
                        and proof.canonical_context_hash
                        == hash_rejected_canonical_binding(
                            rejected_original_hash,
                            proof.context_conflict_status or "invalid",
                        )
                        == proof.context_hash
                    )
                else:
                    cb_ok = False
            else:
                # The caller supplies the original request representation.  An
                # identity evaluation must bind that same snapshot as canonical;
                # a declared source-injection step may have a different evaluated
                # hash, but must still bind the exact original request hash.
                cb_ok = (
                    proof.original_context_hash
                    == prepared_expected_context.original_context_hash
                )
                if not source_transformed:
                    cb_ok = cb_ok and (
                        proof.canonical_context_hash
                        == prepared_expected_context.canonical_context_hash
                        == proof.context_hash
                    )
            checks["context_binding"] = cb_ok
            messages.append(
                "context binds" if cb_ok else "context hash MISMATCH"
            )
        else:
            checks["context_binding"] = False if source_transformed else None
            if source_transformed:
                messages.append(
                    "original context REQUIRED for source-injected proof"
                )

        if expected_evaluated_context is not None:
            try:
                prepared_expected_evaluated_context = prepare_context(
                    expected_evaluated_context,
                    allow_source_keys=True,
                )
            except ContextResolutionError:
                evaluated_cb_ok = False
            else:
                evaluated_cb_ok = (
                    proof.canonical_context_hash
                    == prepared_expected_evaluated_context.canonical_context_hash
                    == proof.context_hash
                )
            checks["evaluated_context_binding"] = evaluated_cb_ok
            messages.append(
                "evaluated context binds"
                if evaluated_cb_ok
                else "evaluated context hash MISMATCH"
            )
        else:
            checks["evaluated_context_binding"] = (
                False if source_transformed else None
            )
            if source_transformed:
                messages.append(
                    "evaluated context REQUIRED for source-injected proof"
                )

        if source_transformed:
            source_relation_ok = (
                prepared_expected_context is not None
                and prepared_expected_evaluated_context is not None
                and _check_source_injection_relation(
                    prepared_expected_context.canonical,
                    prepared_expected_evaluated_context.canonical,
                )
            )
            checks["source_transformation"] = source_relation_ok
            messages.append(
                "source transformation valid"
                if source_relation_ok
                else "source transformation INVALID"
            )
        else:
            checks["source_transformation"] = None

        expiry_ok, expiry_message = _check_policy_expiry(
            proof,
            policy_source,
            now,
        )
        checks["expiry"] = expiry_ok
        if expiry_message:
            messages.append(expiry_message)

        # Freshness (C024: replay a stale ALLOW)
        if self.max_age_seconds is not None:
            fr_ok = _check_freshness(proof, self.max_age_seconds, now)
            checks["freshness"] = fr_ok
            messages.append("fresh" if fr_ok else "proof is STALE")
        else:
            checks["freshness"] = None

        # ── 7. Policy revocation (C024) ───────────────────────────────────────
        if self.revoked_policy_hashes:
            nr_ok = proof.policy_hash not in self.revoked_policy_hashes
            checks["not_revoked"] = nr_ok
            messages.append("policy current" if nr_ok else "policy REVOKED")
        else:
            checks["not_revoked"] = None

        # ── 8. Replay (exact reuse of a previously-accepted proof) ────────────
        non_replay_valid = (
            sig_result is not False
            and checks["policy_hash"] is not False
            and trace_ok
            and coherence_ok
            and schema_coherence_ok
            and checks["context_binding"] is not False
            and checks["evaluated_context_binding"] is not False
            and checks["source_transformation"] is not False
            and checks["expiry"] is not False
            and checks["freshness"] is not False
            and checks["not_revoked"] is not False
        )

        if self.replay_guard is None:
            checks["not_replayed"] = None
        elif not non_replay_valid:
            checks["not_replayed"] = None
            messages.append("replay recording skipped for invalid proof")
        else:
            fresh = self.replay_guard.check_and_record(proof)
            checks["not_replayed"] = fresh
            messages.append("first use" if fresh else "REPLAYED proof")

        valid = (
            non_replay_valid
            and checks["not_replayed"] is not False
        )

        return VerificationResult(
            valid=valid,
            checks=checks,
            message="; ".join(messages),
        )

    def _check_signature(self, proof: TarlProof) -> bool | None:
        """
        Returns True if the signature is cryptographically valid.
        Returns False if invalid or the key is unknown.
        Returns None if the proof has no signature.
        """
        if not proof.signature:
            return None

        alg, sep, sig_hex = proof.signature.partition(":")
        if not sep:
            return False

        # Strict mode: reject signature families outside the allow-list (e.g.
        # an HMAC proof presented to an Ed25519-only verifier).
        if self.allowed_signature_algorithms is not None:
            family = alg.split("-", 1)[0].lower()
            if family not in self.allowed_signature_algorithms:
                return False

        if alg == "hmac-sha256":
            secret = self._hmac_keys.get(proof.key_id)
            if secret is None:
                return False
            supplied = _decode_canonical_hex(sig_hex, hashlib.sha256().digest_size)
            if supplied is None:
                return False
            expected = hmac.new(
                secret, proof.canonical_bytes(), hashlib.sha256
            ).digest()
            return hmac.compare_digest(expected, supplied)

        if alg == "ed25519":
            public_key = self._ed25519_keys.get(proof.key_id)
            if public_key is None:
                return False
            supplied = _decode_canonical_hex(sig_hex, 64)
            if supplied is None:
                return False
            try:
                public_key.verify(
                    supplied, proof.canonical_bytes()
                )
                return True
            except (ValueError, InvalidSignature):
                return False

        return False  # unknown algorithm


# ── standalone check functions ─────────────────────────────────────────────────

def _check_policy_hash(proof: TarlProof, policy_source: str) -> bool:
    """Verify proof.policy_hash matches SHA-256 of policy_source."""
    alg, sep, stored_hex = proof.policy_hash.partition(":")
    if not sep or alg != "sha256":
        return False
    actual = hashlib.sha256(policy_source.encode("utf-8")).hexdigest()
    return hmac.compare_digest(actual, stored_hex)


def _check_trace(proof: TarlProof) -> bool:
    """
    Verify internal consistency of the evaluation trace:
      - All entries before the matched index must have matched=False
      - The entry at matched_index must have matched=True (or rule_index==-1)
      - If a matched trace entry carries a declared verdict, proof.verdict
        must match it
      - No entries after the first match
    """
    if not isinstance(proof.trace, list):
        return False

    if proof.rule_index == -1:
        # No matched rule may not produce ALLOW; fail-closed DENY/ESCALATE
        # decisions such as default-deny, schema denial, or temporal expiry
        # can all carry rule_index=-1.
        if proof.verdict is TarlVerdict.ALLOW or not all(
            isinstance(entry, dict) and entry.get("matched") is False
            for entry in proof.trace
        ):
            return False

        error_indices = [
            index
            for index, entry in enumerate(proof.trace)
            if entry.get("kind") == "evaluation-error" or "error" in entry
        ]
        if not error_indices:
            return True

        terminal_index = len(proof.trace) - 1
        if error_indices != [terminal_index]:
            return False
        terminal = proof.trace[terminal_index]
        error = terminal.get("error")
        if (
            terminal.get("kind") != "evaluation-error"
            or not isinstance(error, str)
            or not error.strip()
        ):
            return False
        return all(
            entry.get("rule_index") == index
            for index, entry in enumerate(proof.trace)
        )

    for i, entry in enumerate(proof.trace):
        if not isinstance(entry, dict):
            return False
        idx = entry.get("rule_index")
        matched = entry.get("matched", False)
        if idx != i:
            return False
        if i < proof.rule_index and matched:
            return False  # earlier rule incorrectly claims it matched
        if i == proof.rule_index:
            if not matched:
                return False  # claimed match but trace says no
            declared_verdict = entry.get("verdict")
            if declared_verdict is not None:
                try:
                    if TarlVerdict(declared_verdict) != proof.verdict:
                        return False
                except ValueError:
                    return False
            break
        # i can never exceed rule_index: the matched entry above breaks the loop.

    # Trace must end at rule_index (length == rule_index + 1)
    if len(proof.trace) != proof.rule_index + 1:
        return False

    return True
