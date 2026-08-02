"""
T.A.R.L. Runtime — LRU-cached, parallel policy evaluation.

Phase 2: register_source(name, provider) — bind a live data provider to
         source:name references in policy conditions.
Phase 4: evaluate_with_proof() — evaluate and return a TarlProof alongside
         the TarlDecision. The proof is unsigned unless a signing key is
         registered; HMAC-SHA256 is retained for compatibility, and Ed25519 is
         available for non-repudiable asymmetric signatures.
"""
import datetime
import hashlib
import hmac
from collections import OrderedDict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from utf.tarl.context import (
    ContextResolutionError,
    ContextResolutionState,
    PreparedContext,
    compose_context_layers,
    hash_context,
    prepare_context,
    rejected_context_binding,
)
from utf.tarl.core import (
    _TEMPORAL_BUILTINS,
    PolicyParser,
    SafeExpr,
    _check_policy_temporal,
    _policy_authority_expiry,
)
from utf.tarl.schema import ContextSchema
from utf.tarl.spec import (
    DEFAULT_DENY,
    TarlDecision,
    TarlPolicy,
    TarlProof,
    TarlRule,
    TarlVerdict,
)


def _is_temporally_constrained(policy: TarlPolicy) -> bool:
    """Return True if the policy has any temporal constraints that make caching unsafe."""
    if policy.valid_from or policy.valid_until or policy.if_unresolved_after:
        return True
    if any(r.duration_seconds for r in policy.rules):
        return True
    temporal_names = _TEMPORAL_BUILTINS | {"ELAPSED_SINCE"}
    for rule in policy.rules:
        try:
            tokens = PolicyParser._tokenize(rule.condition)
        except Exception:
            return True
        if any(
            isinstance(token.value, str)
            and token.value.upper() in temporal_names
            for token in tokens
        ):
            return True
    return False


class LRUCache:
    """Simple LRU cache with maximum size."""

    def __init__(self, maxsize: int = 128):
        self.maxsize = maxsize
        self._cache: OrderedDict[str, TarlDecision] = OrderedDict()

    def get(self, key: str) -> TarlDecision | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key: str, value: TarlDecision):
        self._cache[key] = value
        self._cache.move_to_end(key)
        if len(self._cache) > self.maxsize:
            self._cache.popitem(last=False)

    def invalidate(self, key: str):
        self._cache.pop(key, None)

    def clear(self):
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


class TarlRuntime:
    """
    TARL policy runtime:
    - LRU decision cache (128 entries)
    - ThreadPoolExecutor for parallel rule evaluation
    - Adaptive ordering (most-frequently-matched rules evaluated first)
    - Dynamic source registry for source:name condition references
    """

    def __init__(
        self,
        policy: TarlPolicy | None = None,
        max_workers: int = 4,
    ):
        self.policy = policy or TarlPolicy()
        self.cache = LRUCache(maxsize=128)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._hit_counts: dict = {}
        self._throw_counts: dict = {}   # rule_index -> number of evaluation exceptions
        self._sources: dict = {}
        self._signing_keys: dict = {}   # key_id -> bytes (HMAC secrets)
        self._ed25519_signing_keys: dict = {}  # key_id -> Ed25519PrivateKey
        self._signing_key_id: str = ""  # active key
        self._signing_alg: str = ""     # "hmac-sha256" or "ed25519"
        self._archive = None            # TarlAuditArchive | None
        self._context_schema: ContextSchema | None = None
        self._context_schema_origin = "none"
        self._require_audit = False     # fail closed if audit cannot persist
        # Trusted time source for temporal checks; None => host clock.
        self._clock: Callable[[], datetime.datetime | None] | None = None

    def set_clock(self, clock) -> "TarlRuntime":
        """Use a trusted time source for temporal-policy checks instead of the
        host clock. ``clock`` is a zero-arg callable returning a timezone-aware
        ``datetime`` (typically obtained by verifying a signed-time assertion via
        ``utf.tarl.clock.TrustedClock``). A spoofed system clock then cannot
        satisfy a temporal window (C043). Returns self."""
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._clock = clock
        return self

    def _now(self) -> datetime.datetime | None:
        if self._clock is None:
            return None
        try:
            current = self._clock()
        except Exception as exc:
            raise ContextResolutionError(
                f"trusted clock failure: {exc}",
                state=ContextResolutionState.TYPE_ERROR,
            ) from exc
        if not isinstance(current, datetime.datetime):
            raise ContextResolutionError(
                "trusted clock failure: expected a datetime value",
                state=ContextResolutionState.TYPE_ERROR,
            )
        if current.tzinfo is None or current.utcoffset() is None:
            raise ContextResolutionError(
                "trusted clock failure: datetime must be timezone-aware",
                state=ContextResolutionState.TYPE_ERROR,
            )
        return current.astimezone(datetime.UTC)

    def set_require_audit(self, required: bool = True) -> "TarlRuntime":
        """When True and an audit archive is attached, a failure to persist a
        proof downgrades the decision to a fail-closed DENY (C038): execution
        cannot proceed if the required audit record could not be written."""
        self._require_audit = required
        return self

    def _persist(
        self,
        policy: TarlPolicy,
        ctx: PreparedContext,
        decision: TarlDecision,
        proof: TarlProof,
    ) -> tuple[TarlDecision, TarlProof]:
        """Store the proof; on a persistence failure, fail closed when audit is
        required. Returns the (possibly downgraded) ``(decision, proof)``."""
        if self._archive is None:
            return decision, proof
        try:
            self._archive.store(proof, expires_at=decision.expires_at)
            return decision, proof
        except Exception as exc:  # disk full, DoS on the audit sink, etc.
            if not self._require_audit:
                return decision, proof
            denied = TarlDecision(
                verdict=TarlVerdict.DENY,
                reason=f"fail-closed: required audit could not be persisted: {exc}",
            )
            denied_proof = self._generate_proof(
                policy, ctx, denied, -1,
                [{"kind": "audit-fail", "matched": False, "reason": str(exc)}],
                schema_binding={
                    "hash": proof.context_schema_hash or "",
                    "representation_id": (
                        proof.context_schema_representation_id or ""
                    ),
                    "status": (
                        proof.context_schema_validation_status
                        or "not_evaluated"
                    ),
                },
                evaluation_time=datetime.datetime.fromisoformat(
                    proof.evaluated_at.replace("Z", "+00:00")
                ),
            )
            return denied, denied_proof

    # ── Context schema ────────────────────────────────────────────────────────

    def set_context_schema(self, schema: ContextSchema) -> "TarlRuntime":
        """Attach a ``utf.tarl.schema.ContextSchema``. When set, every context is
        validated before any rule runs; a missing required field or a
        type-confused value short-circuits to the schema's fail-closed verdict
        (DENY by default) instead of silently matching a permissive later rule.
        Returns self for chaining."""
        if type(schema) is not ContextSchema:
            raise TypeError("context schema must be a ContextSchema")
        # Validate and fingerprint at registration time so malformed schema
        # configuration cannot reach an authorization path.
        schema.fingerprint()
        self._context_schema = schema
        self._context_schema_origin = "explicit"
        return self

    def ensure_context_schema(self) -> bool:
        """Attach a complete derived schema when authority use needs one.

        Plain evaluation remains available without a schema, but load-bearing
        consumers call this method before relying on ALLOW.  Incomplete or
        ambiguous derivation leaves the runtime unbound so the consumer's
        positive-proof admissibility gate fails closed.
        """
        if self._context_schema is not None:
            return True
        try:
            from utf.thirsty_lang.proof_obligations import derive_context_schema

            derived = derive_context_schema(self.policy.source)
            if not derived.complete:
                return False
            self.set_context_schema(ContextSchema.from_dict(derived.to_dict()))
            self._context_schema_origin = "derived"
        except Exception:
            return False
        return True

    def _schema_for_evaluation(
        self,
        policy: TarlPolicy,
        *,
        policy_override: bool,
    ) -> tuple[ContextSchema | None, str]:
        """Resolve the schema that belongs to the policy being evaluated.

        A schema derived for ``self.policy`` must never be reused for a
        different ``policy_text`` override. Explicit schemas are caller-bound
        and remain applicable; derived schemas are regenerated per override.
        """
        if not policy_override or self._context_schema_origin != "derived":
            return self._context_schema, ""
        try:
            from utf.thirsty_lang.proof_obligations import derive_context_schema

            derived = derive_context_schema(policy.source)
            if not derived.complete:
                return None, (
                    "context schema could not be derived completely for the "
                    "evaluated policy override"
                )
            return ContextSchema.from_dict(derived.to_dict()), ""
        except Exception as exc:
            return None, (
                "context schema could not be derived for the evaluated "
                f"policy override: {exc}"
            )

    @staticmethod
    def _binding_for_schema(
        schema: ContextSchema | None,
        status: str,
    ) -> dict[str, str]:
        """Return proof metadata for one exact context schema."""
        if schema is None:
            return {
                "hash": "",
                "representation_id": "",
                "status": "error" if status == "error" else "not_configured",
            }
        try:
            schema_hash = schema.fingerprint()
            representation_id = schema.representation_id
        except Exception:
            return {
                "hash": "",
                "representation_id": "",
                "status": "error",
            }
        return {
            "hash": schema_hash,
            "representation_id": representation_id,
            "status": status,
        }

    def _schema_binding(self, status: str) -> dict[str, str]:
        """Return proof metadata for the runtime's configured schema."""
        return self._binding_for_schema(self._context_schema, status)

    def _validate_context_schema(
        self,
        context: PreparedContext,
        schema: ContextSchema | None,
    ) -> tuple["TarlDecision | None", dict[str, str]]:
        """Validate once and return both decision and proof-bound result."""
        if schema is None:
            return None, self._binding_for_schema(None, "not_configured")

        before_binding = self._binding_for_schema(schema, "not_evaluated")
        if before_binding["status"] == "error":
            return (
                TarlDecision(
                    verdict=TarlVerdict.DENY,
                    reason="context schema configuration is invalid",
                ),
                before_binding,
            )
        schema_violation_verdict = schema.on_violation

        try:
            violations = ContextSchema.validate(schema, context)
            context_unchanged = (
                hash_context(context.canonical) == context.canonical_context_hash
            )
            after_binding = self._binding_for_schema(schema, "passed")
        except Exception as exc:
            binding = self._binding_for_schema(schema, "error")
            binding["status"] = "error"
            return (
                TarlDecision(
                    verdict=TarlVerdict.DENY,
                    reason=f"context schema validation failed: {exc}",
                ),
                binding,
            )

        if (
            not context_unchanged
            or after_binding["hash"] != before_binding["hash"]
            or after_binding["representation_id"]
            != before_binding["representation_id"]
        ):
            after_binding["status"] = "error"
            return (
                TarlDecision(
                    verdict=TarlVerdict.DENY,
                    reason=(
                        "context schema validation mutated its schema or "
                        "evaluation context"
                    ),
                ),
                after_binding,
            )

        if not violations:
            return None, after_binding

        after_binding["status"] = "failed"
        return (
            TarlDecision(
                verdict=schema_violation_verdict,
                reason="context schema violation: " + "; ".join(violations),
            ),
            after_binding,
        )

    def _schema_decision(
        self,
        context: PreparedContext,
        schema: ContextSchema | None,
    ) -> "TarlDecision | None":
        """Return a fail-closed decision when ``context`` violates the schema,
        else None."""
        decision, _binding = self._validate_context_schema(context, schema)
        return decision

    # ── Audit archive ─────────────────────────────────────────────────────────

    def set_archive(self, archive) -> "TarlRuntime":
        """
        Attach a TarlAuditArchive.  Proofs generated by evaluate_with_proof()
        are stored automatically.  Returns self for chaining.
        """
        self._archive = archive
        return self

    # ── Signing key registry ──────────────────────────────────────────────────

    def set_signing_key(
        self, key_id: str, secret: bytes
    ) -> "TarlRuntime":
        """
        Register an HMAC-SHA256 signing key for proof generation.
        The most recently set key becomes the active key.
        Returns self for chaining.
        """
        self._signing_keys[key_id] = secret
        self._signing_key_id = key_id
        self._signing_alg = "hmac-sha256"
        return self

    def set_ed25519_signing_key(
        self, key_id: str, private_key: bytes | Ed25519PrivateKey
    ) -> "TarlRuntime":
        """
        Register an Ed25519 private key for proof generation.

        ``private_key`` may be a cryptography Ed25519PrivateKey or the raw
        32-byte private seed accepted by Ed25519PrivateKey.from_private_bytes().
        The most recently set key becomes the active key.
        """
        if isinstance(private_key, Ed25519PrivateKey):
            key = private_key
        else:
            key = Ed25519PrivateKey.from_private_bytes(private_key)
        self._ed25519_signing_keys[key_id] = key
        self._signing_key_id = key_id
        self._signing_alg = "ed25519"
        return self

    # ── Source registry ───────────────────────────────────────────────────────

    def register_source(
        self, name: str, provider
    ) -> "TarlRuntime":
        """
        Bind a data provider to source:<name> condition references.

        provider — a strict JSON value (commonly a list) or a zero-arg
                   callable that returns one each time it is called.
        Returns self for chaining.
        """
        if (
            type(name) is not str
            or not name
            or not all(char.isalnum() or char == "_" for char in name)
        ):
            raise ValueError(
                "registered source name must be non-empty and contain only "
                "letters, numbers, or underscores"
            )
        self._sources[name] = provider
        return self

    def _inject_sources(self, context: dict) -> dict:
        """Resolve all registered sources and inject into a context copy."""
        if not self._sources:
            return dict(context)
        source_context = {}
        for name, provider in self._sources.items():
            try:
                value = provider() if callable(provider) else provider
            except Exception as exc:
                raise ContextResolutionError(
                    f"registered source '{name}' could not be resolved: {exc}",
                    state=ContextResolutionState.MISSING,
                    path=f"source:{name}",
                ) from exc
            source_context[f"source:{name}"] = value
        return compose_context_layers(
            ("caller context", context),
            ("registered sources", source_context),
        )

    def _prepare_evaluation_context(self, context: dict) -> PreparedContext:
        """Freeze caller input, inject sources, then freeze the evaluated state."""
        original = prepare_context(context)
        enriched = self._inject_sources(original.canonical)
        evaluated = prepare_context(enriched, allow_source_keys=True)
        algorithm = (
            "identity"
            if original.original_context_hash == evaluated.canonical_context_hash
            else "tarl.registered-source-injection"
        )
        return PreparedContext(
            canonical=evaluated.canonical,
            original_context_hash=original.original_context_hash,
            canonical_context_hash=evaluated.canonical_context_hash,
            normalization_algorithm_id=algorithm,
        )

    # ── Policy management ─────────────────────────────────────────────────────

    def throw_stats(self) -> dict:
        """
        Return throw counts per rule index.

        **What the number means:**
        Counts reflect distinct contexts that missed the cache and threw, not
        total call frequency.  A rule that throws on one bad context evaluated
        a thousand times shows throw_count == 1, not 1000, because cached
        results bypass rule evaluation entirely.  The stat answers "how many
        distinct inputs break this rule," not "how often throwing happens in
        production."  Do not use it to gauge live-traffic blast radius without
        accounting for cache hit rate.

        **Predicates:**
        - throw_count > 0 and hit_count == 0 → dead-by-exception: the rule
          has never matched cleanly and throws on every context seen so far.
        - throw_count > 0 and hit_count > 0 → partial-throw: the rule matches
          on some inputs but throws on others.  hit_count > 0 does not mean
          healthy; partial-throw is a distinct broken state.
        """
        return dict(self._throw_counts)

    def set_policy(self, new_policy: TarlPolicy):
        """Replace the active policy and reset the cache and hit counts."""
        self.policy = new_policy
        if self._context_schema_origin == "derived":
            self._context_schema = None
            self._context_schema_origin = "none"
        self.cache.clear()
        self._hit_counts = dict.fromkeys(range(len(new_policy.rules)), 0)
        self._throw_counts = {}

    # ── Evaluation ────────────────────────────────────────────────────────────

    def evaluate(
        self,
        context: dict,
        policy_text: str | None = None,
    ) -> TarlDecision:
        """
        Evaluate the active policy (or policy_text if supplied) against
        context. Sources are resolved before evaluation. Returns the
        first matching rule's verdict, or DEFAULT_DENY.
        """
        if policy_text is not None:
            policy = PolicyParser.parse(policy_text)
        else:
            policy = self.policy
        policy_override = (
            policy_text is not None and policy.source != self.policy.source
        )
        evaluation_schema, schema_resolution_error = self._schema_for_evaluation(
            policy,
            policy_override=policy_override,
        )
        try:
            evaluation_now = self._now()
            if evaluation_now is None:
                evaluation_now = datetime.datetime.now(datetime.UTC)
        except ContextResolutionError as exc:
            return TarlDecision(
                verdict=TarlVerdict.DENY,
                reason=f"fail-closed: {exc}",
            )

        try:
            prepared = self._prepare_evaluation_context(context)
        except ContextResolutionError as exc:
            return TarlDecision(verdict=TarlVerdict.DENY, reason=str(exc))

        if schema_resolution_error:
            return TarlDecision(
                verdict=TarlVerdict.DENY,
                reason=f"fail-closed: {schema_resolution_error}",
            )

        # Context schema validation fails closed before any rule evaluation.
        schema_decision = self._schema_decision(prepared, evaluation_schema)
        if schema_decision is not None:
            return schema_decision

        policy_hash = hashlib.sha256(policy.source.encode("utf-8")).hexdigest()
        cache_key = "|".join(
            (
                policy_hash,
                prepared.original_context_hash,
                prepared.canonical_context_hash,
                prepared.normalization_algorithm_id,
                prepared.normalization_version,
                self._binding_for_schema(
                    evaluation_schema, "not_evaluated"
                )["hash"],
            )
        )

        # Phase 5: enforce temporal window before any rule evaluation
        temporal = _check_policy_temporal(policy, now=evaluation_now)
        if temporal is not None:
            return temporal

        if not policy.rules:
            return DEFAULT_DENY

        # Policies with temporal constraints must not be cached — the window
        # check and expires_at timestamps would be stale on subsequent calls.
        use_cache = not _is_temporally_constrained(policy)

        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        ordered_indices = sorted(
            range(len(policy.rules)),
            key=lambda i: self._hit_counts.get(i, 0),
            reverse=True,
        )

        futures_by_idx = {}
        trusted_now = evaluation_now
        for idx in ordered_indices:
            rule = policy.rules[idx]
            future = self.executor.submit(
                self._evaluate_rule, rule, prepared, trusted_now
            )
            futures_by_idx[idx] = (future, rule)

        results = {}
        for idx, (future, rule) in futures_by_idx.items():
            try:
                matched, decision, threw = future.result()
                results[idx] = (matched, decision, rule, threw)
            except Exception:
                results[idx] = (
                    False,
                    TarlDecision(
                        verdict=TarlVerdict.DENY,
                        reason="Evaluation error",
                    ),
                    rule,
                    True,
                )

        # Iterate in POLICY ORDER (not hit-count order) to honour
        # first-match-wins semantics. Adaptive ordering affects which
        # futures are submitted first, not which result wins.
        for idx in range(len(policy.rules)):
            matched, decision, rule, threw = results[idx]
            if threw:
                self._throw_counts[idx] = (
                    self._throw_counts.get(idx, 0) + 1
                )
                return TarlDecision(
                    verdict=TarlVerdict.DENY,
                    reason=(
                        f"fail-closed: rule {idx} could not be evaluated: "
                        f"{decision.reason}"
                    ),
                    rule_index=idx,
                    matched_rule=str(rule),
                )
            if matched:
                self._hit_counts[idx] = (
                    self._hit_counts.get(idx, 0) + 1
                )
                authority_expiry = _policy_authority_expiry(
                    policy, rule, trusted_now
                )
                expires_at = (
                    authority_expiry.isoformat(timespec="seconds")
                    if authority_expiry is not None
                    else None
                )
                result = TarlDecision(
                    verdict=decision.verdict,
                    reason=decision.reason or f"Rule matched: {rule}",
                    rule_index=idx,
                    matched_rule=str(rule),
                    expires_at=expires_at,
                )
                if use_cache:
                    self.cache.put(cache_key, result)
                return result

        if use_cache:
            self.cache.put(cache_key, DEFAULT_DENY)
        return DEFAULT_DENY

    def _evaluate_rule(
        self,
        rule: TarlRule,
        context: PreparedContext,
        now: datetime.datetime | None = None,
    ) -> tuple:
        """
        Evaluate one rule. Returns (matched: bool, TarlDecision, threw: bool).

        threw=True when the condition raised an exception.  The rule is
        treated as non-matching in either case (fail-safe), but callers
        increment _throw_counts so persistent exception behaviour is visible
        via throw_stats().
        """
        try:
            tokens = PolicyParser._tokenize(rule.condition)
            matched = SafeExpr.evaluate(tokens, context, now=now)
            if matched:
                return True, TarlDecision(
                    verdict=rule.verdict,
                    reason=f"Condition '{rule.condition}' matched",
                ), False
            return False, TarlDecision(
                verdict=rule.verdict,
                reason="Condition did not match",
            ), False
        except Exception as exc:
            return False, TarlDecision(
                verdict=TarlVerdict.DENY,
                reason=f"Evaluation error: {exc}",
            ), True

    # ── Proof-carrying evaluation ─────────────────────────────────────────────

    def evaluate_with_proof(
        self,
        context: dict,
        policy_text: str | None = None,
    ) -> tuple[TarlDecision, TarlProof]:
        """
        Evaluate sequentially, recording a full evaluation trace, then sign.

        Returns (TarlDecision, TarlProof). The proof contains:
          - SHA-256 hash of policy source
          - SHA-256 hash of canonical context
          - Per-rule trace up to (and including) the first match
          - HMAC-SHA256 or Ed25519 signature if a signing key is registered
        """
        if policy_text is not None:
            policy = PolicyParser.parse(policy_text)
        else:
            policy = self.policy
        policy_override = (
            policy_text is not None and policy.source != self.policy.source
        )
        evaluation_schema, schema_resolution_error = self._schema_for_evaluation(
            policy,
            policy_override=policy_override,
        )

        try:
            evaluation_now = self._now()
            if evaluation_now is None:
                evaluation_now = datetime.datetime.now(datetime.UTC)
        except ContextResolutionError as exc:
            try:
                prepared = prepare_context(context)
            except ContextResolutionError as context_exc:
                prepared = rejected_context_binding(
                    context,
                    conflict_status=context_exc.conflict_status,
                )
            decision = TarlDecision(
                verdict=TarlVerdict.DENY,
                reason=f"fail-closed: {exc}",
            )
            trace = [{
                "kind": "trusted-time-failure",
                "matched": False,
                "reason": str(exc),
                "state": exc.state.value,
            }]
            proof = self._generate_proof(
                policy,
                prepared,
                decision,
                -1,
                trace,
                schema_binding=self._binding_for_schema(
                    evaluation_schema,
                    "error" if schema_resolution_error else "not_evaluated",
                ),
                evaluation_time=datetime.datetime.now(datetime.UTC),
            )
            return self._persist(policy, prepared, decision, proof)

        try:
            prepared = self._prepare_evaluation_context(context)
        except ContextResolutionError as exc:
            rejected = rejected_context_binding(
                context, conflict_status=exc.conflict_status
            )
            decision = TarlDecision(verdict=TarlVerdict.DENY, reason=str(exc))
            trace = [
                {
                    "kind": "context-resolution-failure",
                    "matched": False,
                    "reason": str(exc),
                    "state": exc.state.value,
                }
            ]
            proof = self._generate_proof(
                policy,
                rejected,
                decision,
                -1,
                trace,
                schema_binding=self._binding_for_schema(
                    evaluation_schema,
                    "error" if schema_resolution_error else "not_evaluated",
                ),
                evaluation_time=evaluation_now,
            )
            return self._persist(policy, rejected, decision, proof)

        if schema_resolution_error:
            decision = TarlDecision(
                verdict=TarlVerdict.DENY,
                reason=f"fail-closed: {schema_resolution_error}",
            )
            trace = [{
                "kind": "context-schema-unavailable",
                "matched": False,
                "reason": schema_resolution_error,
            }]
            proof = self._generate_proof(
                policy,
                prepared,
                decision,
                -1,
                trace,
                schema_binding=self._binding_for_schema(None, "error"),
                evaluation_time=evaluation_now,
            )
            return self._persist(policy, prepared, decision, proof)

        # Context schema validation fails closed before any rule evaluation,
        # carrying a proof that records which fields were missing or mistyped.
        schema_decision, schema_binding = self._validate_context_schema(
            prepared,
            evaluation_schema,
        )
        if schema_decision is not None:
            trace = [{"kind": "schema-violation", "matched": False,
                      "reason": schema_decision.reason}]
            proof = self._generate_proof(
                policy,
                prepared,
                schema_decision,
                -1,
                trace,
                schema_binding=schema_binding,
                evaluation_time=evaluation_now,
            )
            return self._persist(policy, prepared, schema_decision, proof)

        # Phase 5: temporal window check — return early with proof if outside window
        temporal = _check_policy_temporal(policy, now=evaluation_now)
        if temporal is not None:
            proof = self._generate_proof(
                policy,
                prepared,
                temporal,
                -1,
                [],
                schema_binding=schema_binding,
                evaluation_time=evaluation_now,
            )
            return self._persist(policy, prepared, temporal, proof)

        trace = []
        decision = DEFAULT_DENY
        matched_idx = -1
        trusted_now = evaluation_now

        for i, rule in enumerate(policy.rules):
            matched, rule_dec, threw = self._evaluate_rule(
                rule, prepared, trusted_now
            )
            if threw:
                self._throw_counts[i] = (
                    self._throw_counts.get(i, 0) + 1
                )
            trace.append({
                **({"kind": "evaluation-error"} if threw else {}),
                "rule_index": i,
                "condition": rule.condition,
                "verdict": rule.verdict.value,
                "matched": matched,
                **({"error": rule_dec.reason} if threw else {}),
            })
            if threw:
                decision = TarlDecision(
                    verdict=TarlVerdict.DENY,
                    reason=(
                        f"fail-closed: rule {i} could not be evaluated: "
                        f"{rule_dec.reason}"
                    ),
                    rule_index=i,
                    matched_rule=str(rule),
                )
                matched_idx = -1
                break
            if matched:
                matched_idx = i
                authority_expiry = _policy_authority_expiry(
                    policy, rule, trusted_now
                )
                expires_at = (
                    authority_expiry.isoformat(timespec="seconds")
                    if authority_expiry is not None
                    else None
                )
                decision = TarlDecision(
                    verdict=rule_dec.verdict,
                    reason=f"Condition '{rule.condition}' matched",
                    rule_index=i,
                    matched_rule=str(rule),
                    expires_at=expires_at,
                )
                break

        proof = self._generate_proof(
            policy,
            prepared,
            decision,
            matched_idx,
            trace,
            schema_binding=schema_binding,
            evaluation_time=evaluation_now,
        )
        return self._persist(policy, prepared, decision, proof)

    def _generate_proof(
        self,
        policy: TarlPolicy,
        context: PreparedContext,
        decision: TarlDecision,
        matched_idx: int,
        trace: list,
        schema_binding: dict[str, str] | None = None,
        evaluation_time: datetime.datetime | None = None,
    ) -> TarlProof:
        policy_hash = "sha256:" + hashlib.sha256(
            policy.source.encode("utf-8")
        ).hexdigest()
        context_hash = (
            context.canonical_context_hash or context.original_context_hash
        )
        if evaluation_time is None:
            evaluation_time = datetime.datetime.now(datetime.UTC)
        if (
            evaluation_time.tzinfo is None
            or evaluation_time.utcoffset() is None
        ):
            raise ValueError("proof evaluation time must be timezone-aware")
        evaluated_at = (
            evaluation_time.astimezone(datetime.UTC)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
        matched_condition = (
            policy.rules[matched_idx].condition if matched_idx >= 0 else ""
        )
        schema_binding = schema_binding or self._schema_binding("not_evaluated")
        proof = TarlProof(
            policy_hash=policy_hash,
            context_hash=context_hash,
            rule_index=matched_idx,
            matched_condition=matched_condition,
            verdict=decision.verdict,
            evaluated_at=evaluated_at,
            trace=trace,
            signature="",
            key_id="",
            original_context_hash=context.original_context_hash,
            canonical_context_hash=context.canonical_context_hash,
            context_representation_id=context.context_representation_id,
            normalization_algorithm_id=context.normalization_algorithm_id,
            normalization_version=context.normalization_version,
            context_conflict_status=context.context_conflict_status,
            context_schema_hash=schema_binding["hash"],
            context_schema_representation_id=(
                schema_binding["representation_id"]
            ),
            context_schema_validation_status=schema_binding["status"],
            expires_at=decision.expires_at,
        )
        if self._signing_key_id and self._signing_alg == "hmac-sha256":
            secret = self._signing_keys.get(self._signing_key_id)
            if secret is not None:
                sig_hex = hmac.new(
                    secret, proof.canonical_bytes(), hashlib.sha256
                ).hexdigest()
                proof.signature = f"hmac-sha256:{sig_hex}"
                proof.key_id = self._signing_key_id
        elif self._signing_key_id and self._signing_alg == "ed25519":
            key = self._ed25519_signing_keys.get(self._signing_key_id)
            if key is not None:
                sig_hex = key.sign(proof.canonical_bytes()).hex()
                proof.signature = f"ed25519:{sig_hex}"
                proof.key_id = self._signing_key_id
        return proof

    def shutdown(self):
        """Clean up the thread pool."""
        self.executor.shutdown(wait=False)
