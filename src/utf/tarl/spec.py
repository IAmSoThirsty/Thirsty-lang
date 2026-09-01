"""
T.A.R.L. Specification Types

Verdict lattice:  DENY ≺ ESCALATE ≺ ALLOW
Restrictive meet: a ∧ b = min(a, b)   — DENY beats all
Permissive join:  a ∨ b = max(a, b)   — ALLOW beats all
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

# Safety ordering: DENY=0 < ESCALATE=1 < ALLOW=2
_VERDICT_RANK: dict[TarlVerdict, int] = {}


class TarlVerdict(StrEnum):
    DENY = "DENY"
    ESCALATE = "ESCALATE"
    ALLOW = "ALLOW"

    def __str__(self) -> str:
        return self.value

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, TarlVerdict):
            return NotImplemented
        return _VERDICT_RANK[self] < _VERDICT_RANK[other]

    def __le__(self, other: object) -> bool:
        if not isinstance(other, TarlVerdict):
            return NotImplemented
        return _VERDICT_RANK[self] <= _VERDICT_RANK[other]

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, TarlVerdict):
            return NotImplemented
        return _VERDICT_RANK[self] > _VERDICT_RANK[other]

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, TarlVerdict):
            return NotImplemented
        return _VERDICT_RANK[self] >= _VERDICT_RANK[other]

    @staticmethod
    def meet(a: TarlVerdict, b: TarlVerdict) -> TarlVerdict:
        """Restrictive composition (∧): min in safety ordering."""
        return a if _VERDICT_RANK[a] <= _VERDICT_RANK[b] else b

    @staticmethod
    def join(a: TarlVerdict, b: TarlVerdict) -> TarlVerdict:  # type: ignore[override]
        """Permissive composition (∨): max in safety ordering.

        Intentionally shadows ``str.join`` (this enum subclasses ``str``); it is
        the lattice join over verdicts, not string concatenation.
        """
        return a if _VERDICT_RANK[a] >= _VERDICT_RANK[b] else b


# Populate rank table after enum is defined
_VERDICT_RANK.update(
    {
        TarlVerdict.DENY: 0,
        TarlVerdict.ESCALATE: 1,
        TarlVerdict.ALLOW: 2,
    }
)


class CompositionOp(StrEnum):
    """How a child policy composes with its parent."""

    EXTENDS = "EXTENDS"
    RESTRICTS = "RESTRICTS"

    def __str__(self) -> str:
        return self.value


class SetOp(StrEnum):
    """How policies in a policy_set group are combined."""

    UNION = "UNION"
    INTERSECT = "INTERSECT"
    MAJORITY = "MAJORITY"

    def __str__(self) -> str:
        return self.value


@dataclass
class TarlPolicyRef:
    """A reference to another policy in a composition directive."""

    name: str
    alias: str | None = None
    is_file: bool = False


@dataclass
class TarlRule:
    """A single `when <condition> => VERDICT [for: <duration>]` rule."""

    condition: str
    verdict: TarlVerdict
    source_line: int = 0
    duration_seconds: int | None = None  # time-bound verdict ("for: 4h")

    def __str__(self) -> str:
        s = f"when {self.condition} => {self.verdict.value}"
        if self.duration_seconds:
            ds = self.duration_seconds
            if ds % 3600 == 0:
                s += f" for: {ds // 3600}h"
            elif ds % 60 == 0:
                s += f" for: {ds // 60}m"
            else:
                s += f" for: {ds}s"
        return s


@dataclass
class TarlPolicy:
    """Ordered decision function: P = [r₁, r₂, ..., rₙ] over context space."""

    rules: list[TarlRule] = field(default_factory=list)
    source: str = ""
    name: str = "unnamed"
    # Phase 2: composition
    parent: str | None = None
    composition: CompositionOp | None = None
    includes: list[TarlPolicyRef] = field(default_factory=list)
    has_stop: bool = False
    # Phase 5: temporal governance
    version: str | None = None
    supersedes: str | None = None
    valid_from: str | None = None  # ISO-8601; policy not effective before this
    valid_until: str | None = None  # ISO-8601; policy expires after this
    on_expiry: TarlVerdict | None = (
        None  # verdict when outside window (default ESCALATE)
    )
    if_unresolved_after: int | None = None  # seconds; auto-expire from valid_from
    revert_to: str | None = None  # policy name to evaluate on succession

    def __str__(self) -> str:
        header = f"policy {self.name}"
        if self.composition and self.parent:
            header += f" {self.composition.value} {self.parent}"
        if self.version:
            header += f" v{self.version}"
        lines = [f"{header}:"]
        if self.valid_from:
            lines.append(f"  valid_from: {self.valid_from}")
        if self.valid_until:
            lines.append(f"  valid_until: {self.valid_until}")
        if self.supersedes:
            lines.append(f"  supersedes: {self.supersedes}")
        if self.on_expiry:
            lines.append(f"  on_expiry: {self.on_expiry.value}")
        if self.if_unresolved_after is not None and self.revert_to:
            ds = self.if_unresolved_after
            if ds % 3600 == 0:
                dur = f"{ds // 3600}h"
            elif ds % 60 == 0:
                dur = f"{ds // 60}m"
            else:
                dur = f"{ds}s"
            lines.append(f"  if_unresolved_after: {dur} => revert_to: {self.revert_to}")
        for ref in self.includes:
            alias_part = f" AS {ref.alias}" if ref.alias else ""
            if ref.is_file:
                lines.append(f'  INCLUDE "{ref.name}"{alias_part}')
            else:
                lines.append(f"  INCLUDE {ref.name}{alias_part}")
        for r in self.rules:
            lines.append(f"  {r}")
        if self.has_stop:
            lines.append("  STOP")
        return "\n".join(lines)


@dataclass
class TarlDecision:
    """Result of evaluating a T.A.R.L. policy against a context."""

    verdict: TarlVerdict
    reason: str = ""
    rule_index: int = -1
    matched_rule: str | None = None
    expires_at: str | None = None  # ISO-8601 UTC; set for time-bound verdicts

    def __str__(self) -> str:
        s = f"[{self.verdict.value}] {self.reason}"
        if self.expires_at:
            s += f" (expires: {self.expires_at})"
        return s

    def is_expired(self) -> bool:
        """
        Return True if this decision carried a time-bound verdict that has
        now elapsed.  Always False when expires_at is not set.

        The engine stamps expires_at at evaluation time but never
        re-evaluates automatically.  Callers that cache decisions must call
        this method before acting on a stored result and re-evaluate when it
        returns True.
        """
        if self.expires_at is None:
            return False
        import datetime

        try:
            exp = datetime.datetime.fromisoformat(
                self.expires_at.replace("Z", "+00:00")
            )
            if exp.tzinfo is None or exp.utcoffset() is None:
                return True
            return datetime.datetime.now(datetime.UTC) >= exp
        except (AttributeError, TypeError, ValueError):
            return True


@dataclass
class TarlPolicySet:
    """
    A named composition of multiple policies evaluated with set operators.

    groups: list of (SetOp, [policy_name, ...])
    Each group produces a verdict via its operator.
    The final verdict is the meet (∧) of all group verdicts.
    """

    name: str
    groups: list[tuple[SetOp, list[str]]] = field(default_factory=list)
    default_verdict: TarlVerdict = TarlVerdict.DENY
    source: str = ""

    def __str__(self) -> str:
        lines = [f"policy_set {self.name}:"]
        for op, names in self.groups:
            lines.append(f"  combine {op.value} [{', '.join(names)}]")
        lines.append(f"  default: {self.default_verdict.value}")
        return "\n".join(lines)


@dataclass
class TarlProof:
    """
    Integrity certificate of a policy evaluation.

    Π = (H(P), H(original-c), H(canonical-c), R, N, C, H(S), S,
         k, v, t_exp, T, σ)
      H(P) — SHA-256 of exact policy source used
      H(original-c) — SHA-256 of the caller-supplied context snapshot
      H(canonical-c) — SHA-256 of the exact representation evaluated
      R    — authoritative context representation identifier
      N    — transformation/normalization algorithm identifier and version
      C    — representation collision/conflict status
      H(S) — SHA-256 fingerprint of the explicit context schema
      S    — schema representation identifier and validation status
      k    — matched rule index (-1 = DEFAULT_DENY)
      v    — final verdict
      t_exp — optional expiry of a time-bound matched-rule verdict
      T    — evaluation trace: [{rule_index, condition, matched}, ...]
      σ    — optional HMAC-SHA256 tag or Ed25519 signature over the canonical
             encoding

    Runtime-generated proofs can be unsigned when no signing key is configured,
    but the verifier rejects unsigned proofs by default. HMAC-SHA256 remains
    available as a symmetric compatibility mode: it is forgeable by any party
    that holds the key, including a verifier. Use Ed25519 for non-repudiable
    asymmetric proof signatures where the verifier has only the public key.
    """

    policy_hash: str  # "sha256:<hex>"
    context_hash: str  # "sha256:<hex>"
    rule_index: int  # -1 = DEFAULT_DENY
    matched_condition: str  # "" for DEFAULT_DENY
    verdict: TarlVerdict
    evaluated_at: str  # ISO-8601 UTC
    trace: list[dict]  # [{rule_index, condition, matched}, ...]
    signature: str  # "hmac-sha256:<hex>", "ed25519:<hex>", or ""
    key_id: str  # signing key identifier or ""
    original_context_hash: str | None = None
    canonical_context_hash: str | None = None
    context_representation_id: str | None = None
    normalization_algorithm_id: str | None = None
    normalization_version: str | None = None
    context_conflict_status: str | None = None
    context_schema_hash: str | None = None
    context_schema_representation_id: str | None = None
    context_schema_validation_status: str | None = None
    expires_at: str | None = None

    def _context_binding(self) -> dict[str, str | None]:
        return {
            "original_context_hash": self.original_context_hash,
            "canonical_context_hash": self.canonical_context_hash,
            "context_representation_id": self.context_representation_id,
            "normalization_algorithm_id": self.normalization_algorithm_id,
            "normalization_version": self.normalization_version,
            "context_conflict_status": self.context_conflict_status,
        }

    def _schema_binding(self) -> dict[str, str | None]:
        return {
            "context_schema_hash": self.context_schema_hash,
            "context_schema_representation_id": (self.context_schema_representation_id),
            "context_schema_validation_status": (self.context_schema_validation_status),
        }

    def canonical_bytes(self) -> bytes:
        """Deterministic serialisation used for signing and verification."""
        import json

        data = {
            "policy_hash": self.policy_hash,
            "context_hash": self.context_hash,
            "rule_index": self.rule_index,
            "matched_condition": self.matched_condition,
            "verdict": self.verdict.value,
            "evaluated_at": self.evaluated_at,
            "trace": self.trace,
        }
        if self.expires_at is not None:
            data["expires_at"] = self.expires_at
        binding = self._context_binding()
        if any(value is not None for value in binding.values()):
            data["context_binding"] = binding
        schema_binding = self._schema_binding()
        if any(value is not None for value in schema_binding.values()):
            data["context_schema_binding"] = schema_binding
        return json.dumps(
            data, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")

    def to_dict(self) -> dict:
        data = {
            "policy_hash": self.policy_hash,
            "context_hash": self.context_hash,
            "rule_index": self.rule_index,
            "matched_condition": self.matched_condition,
            "verdict": self.verdict.value,
            "evaluated_at": self.evaluated_at,
            "expires_at": self.expires_at,
            "trace": list(self.trace),
            "signature": self.signature,
            "key_id": self.key_id,
        }
        data.update(self._context_binding())
        data.update(self._schema_binding())
        return data

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=2, allow_nan=False)

    @classmethod
    def from_dict(cls, d: dict) -> TarlProof:
        return cls(
            policy_hash=d["policy_hash"],
            context_hash=d["context_hash"],
            rule_index=d["rule_index"],
            matched_condition=d.get("matched_condition", ""),
            verdict=TarlVerdict(d["verdict"]),
            evaluated_at=d["evaluated_at"],
            trace=d.get("trace", []),
            signature=d.get("signature", ""),
            key_id=d.get("key_id", ""),
            original_context_hash=d.get("original_context_hash"),
            canonical_context_hash=d.get("canonical_context_hash"),
            context_representation_id=d.get("context_representation_id"),
            normalization_algorithm_id=d.get("normalization_algorithm_id"),
            normalization_version=d.get("normalization_version"),
            context_conflict_status=d.get("context_conflict_status"),
            context_schema_hash=d.get("context_schema_hash"),
            context_schema_representation_id=d.get("context_schema_representation_id"),
            context_schema_validation_status=d.get("context_schema_validation_status"),
            expires_at=d.get("expires_at"),
        )

    @classmethod
    def from_json(cls, s: str) -> TarlProof:
        from utf.tarl.context import load_context_json

        decoded = load_context_json(s)
        if not isinstance(decoded, dict):
            raise ValueError("TARL proof must be a JSON object")
        return cls.from_dict(decoded)


# Ground state. Nothing crosses without an explicit ALLOW.
DEFAULT_DENY = TarlDecision(
    verdict=TarlVerdict.DENY,
    reason="default-deny: no rule matched",
    rule_index=-1,
    matched_rule=None,
)
