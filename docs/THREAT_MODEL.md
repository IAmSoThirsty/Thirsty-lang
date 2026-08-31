# Thirsty-Lang Offensive Threat Model

Edition: Thirsty-Lang 0.8.6. This catalog is included in the
[canonical Thirsty-Lang UTF 101 manual](THIRSTY_LANG_UTF_101.md).

## Purpose

This document defines the adversary model for Thirsty-Lang as a governance AI
substrate: a language/runtime layer that mediates human, AI, script, service,
and tool actions before side effects happen.

The defensive claim is not that Thirsty-Lang is a Python replacement. The claim
is narrower and harder: under hostile conditions, a governed runtime should
make unauthorized capability use structurally difficult, auditable, and
fail-closed.

## Security Objective

Thirsty-Lang succeeds when all sensitive action attempts pass through a single
governed decision path:

1. Build a canonical action context.
2. Evaluate policy and contracts.
3. Produce a proof-bearing ALLOW, DENY, or ESCALATE verdict.
4. Execute only on ALLOW.
5. Refuse by default when authority, policy, context, proof, or runtime state is
   missing, stale, malformed, or compromised.

No claim is earned unless it is backed by code, tests, docs, or explicit
roadmap status.

## Existing Resistance Surface

Thirsty-Lang already has several defensive primitives that directly reduce the
attack surface in this model. These are not complete hardening by themselves,
but they are real substrate features rather than future aspirations.

| Feature | Defensive value | Evidence |
|---|---|---|
| Governed mode | Separates ordinary execution from authority-checked execution | `tests/test_governance_maximal.py`; `tests/test_gate_fail_closed.py` |
| Default-deny capability gates | Blocks governed I/O/import and sensitive imported stdlib calls when policy or authority is missing | `tests/test_gate_fail_closed.py` |
| TARL policy engine | Moves authorization into explicit policy instead of code convention | `tests/test_tarl.py`; `tests/test_tarl_composition.py` |
| `ALLOW` / `DENY` / `ESCALATE` verdicts | Supports refusal and human/escalation workflows instead of binary allow-only logic | `tests/test_tarl.py` |
| `requires` / `ensures` / `invariant` contracts | Makes preconditions, postconditions, and invariants executable runtime checks | `tests/test_governance_maximal.py` |
| `GovernanceViolation` hard floor | Prevents application error handlers from swallowing governance denials | `tests/test_gate_fail_closed.py` |
| Proof-carrying evaluation | Binds decision output to policy hash, context hash, verdict, and trace | `tests/test_tarl_proof.py` |
| Ed25519 proof signatures | Provides asymmetric verification for non-repudiable proof records | `tests/test_tarl_proof.py`; `tests/test_cli_tarl.py` |
| Temporal policy windows | Reduces stale authorization and emergency-policy blast radius | `tests/test_tarl_temporal.py` |
| First-match-wins policy order under adaptive execution | Prevents optimization from changing authorization semantics | `tests/test_tarl.py` |
| Safe expression evaluator | Avoids eval/import/state mutation inside policy conditions | `tests/test_tarl.py` |
| Shadow Thirst analyzers | Detects unsafe mutation promotion, determinism failures, and plane leakage | `tests/test_shadow_thirst.py`; `tests/test_verifiers.py` |
| TSCG/TSCG-B integrity surfaces | Provides symbolic constraints and binary-frame integrity checks | `tests/test_tscg.py`; `tests/test_tscg_b.py` |
| UTF-8-safe CLI output | Keeps denial/proof reporting reliable on Windows terminals | `src/utf/console.py`; CLI tests |

The hardening work is therefore not "invent security from nothing." It is to
connect these primitives into a universal capability broker, extend the gates
to every side-effect adapter, and prove the result with offensive challenge
tests.

## Protected Assets

| Asset | Why it matters | Required protection |
|---|---|---|
| Capability gates | They decide whether side effects happen | No bypass path around the gate |
| TARL policies | They encode authority | Hash-bound, versioned, signed before deployment |
| TarlProof records | They are the audit trail | Ed25519 for non-repudiation, replay resistance, trace integrity |
| Authority context | It identifies who or what is acting | Authenticated source, least privilege, no self-asserted authority |
| Runtime context | It drives policy decisions | Canonicalized, validated, no attacker-controlled silent defaults |
| Tool adapters | They bridge to real effects | Every adapter must request capability before effect |
| Audit archive | It preserves what happened | Append-only, tamper-evident, externally verifiable |
| Human escalation path | It handles ambiguous or high-risk actions | Explicit ESCALATE path, quorum or operator confirmation |

## Trust Boundaries

| Boundary | Trusted by default? | Required rule |
|---|---:|---|
| Thirsty source text | No | Parse, check, and govern before execution |
| TARL policy source | No | Verify hash/signature before use |
| AI-generated code | No | Govern all imports, I/O, tool calls, subprocesses, network, FFI |
| Human operator command | No | Authority must be bound into context by a trusted channel |
| CLI arguments | No | Treat as untrusted input to runtime setup |
| Environment variables | No | Never grant authority from env alone |
| Local filesystem | No | Treat policy/proof/config files as mutable attacker inputs |
| Network services | No | External responses are untrusted context |
| Plugin/MCP/tool adapters | No | Must be capability-brokered |
| Test results | Partially | Useful only when reproducible and mapped to a threat |

## Adversary Classes

| ID | Adversary | Capabilities |
|---|---|---|
| A1 | Prompt-injected AI agent | Can generate tool calls, code, policies, and explanations that look benign |
| A2 | Malicious plugin or tool adapter | Can expose side effects outside the language runtime |
| A3 | Compromised local script | Can call CLI/runtime APIs directly and mutate local files |
| A4 | Insider operator | Has legitimate access but attempts unauthorized actions |
| A5 | Policy downgrader | Can edit, swap, delete, or roll back policy files |
| A6 | Proof forger | Can tamper with or mint audit artifacts |
| A7 | Replay attacker | Can reuse old ALLOW proofs or cached decisions |
| A8 | Context poisoner | Can supply misleading context fields, missing fields, or type-confused values |
| A9 | Parser/semantic attacker | Exploits grammar ambiguity, precedence, parser recovery, or unknown identifiers |
| A10 | Import/FFI attacker | Reaches Python, stdlib, native code, shell, or network outside gates |
| A11 | Archive tamperer | Modifies stored proof history or deletes denials |
| A12 | Availability attacker | Forces fail-open through errors, timeouts, resource pressure, or cache abuse |
| A13 | Build/package attacker | Ships a different package than the audited source |
| A14 | Human-social attacker | Uses urgency, authority language, or false mission framing to trigger unsafe ALLOW |

## Offensive Challenge Catalog

Each challenge is an adversarial success attempt. The expected defensive outcome
is what Thirsty-Lang must do to claim resistance.

| ID | Challenge | Expected defensive outcome | Current status |
|---|---|---|---|
| C001 | Run `pour` in governed mode with no policy | DENY with proof | Covered by `tests/test_gate_fail_closed.py` |
| C002 | Run callable stdout builtin `print(...)` in governed mode with no policy | DENY with proof | Covered by `tests/test_gate_fail_closed.py` |
| C003 | Read stdin with `sip` in governed mode with no policy | DENY with proof | Covered by `tests/test_gate_fail_closed.py` |
| C004 | Import a module in governed mode with no policy | DENY with proof | Covered by `tests/test_gate_fail_closed.py` |
| C005 | Allow write policy, then attempt read/import | DENY non-matching capability | Covered by `tests/test_gate_fail_closed.py::test_write_allow_does_not_grant_read_or_import` |
| C006 | Wrap a governed denial in `spillage` | Denial propagates; handler cannot swallow it | Covered by governance behavior |
| C007 | Call governed function from core mode | DENY via cross-mode guard/static E053 | Covered by status matrix tests |
| C008 | Use contract predicate ambiguity to invert policy meaning | Parser precedence must preserve author intent | Covered by precedence tests |
| C009 | Tamper TarlProof verdict after signing | Verification fails | Covered by proof tests |
| C010 | Verify Ed25519 proof with wrong public key | Verification fails | Covered by proof tests |
| C011 | Verify Ed25519 proof with no public key | Verification fails | Covered by proof tests |
| C012 | Verify HMAC proof with wrong shared key | Verification fails | Covered by proof tests |
| C013 | Use HMAC as non-repudiation | Documentation must reject claim | Covered by docs; not a runtime block |
| C014 | Replace policy source after proof generation | Policy hash verification fails | Covered by proof verifier tests |
| C015 | Submit malformed proof JSON | CLI verification exits non-zero | Covered by CLI proof tests |
| C016 | Use expired temporal policy | DENY or configured non-ALLOW expiry verdict | Covered by temporal tests |
| C017 | Cache a time-bound ALLOW past expiry | Runtime must not cache temporal decisions | Covered by runtime behavior |
| C018 | Use unknown identifiers to silently allow | Unknown identifiers fail safe | Covered by TARL semantics |
| C019 | Inject malformed context JSON through CLI | CLI exits non-zero | Covered by CLI tests |
| C020 | Mutate policy ordering to exploit adaptive evaluation | First-match-wins must remain policy order | Covered by TARL tests |
| C021 | Trigger evaluator exception inside rule condition | Rule fails safe and throw is observable | Covered by runtime throw stats tests |
| C022 | Store tampered proof in archive and query without verifier | Must be documented as unverified unless verifier supplied | Covered by `tests/test_threat_model_audit_chain.py` (hash-linked chain) and archive `query(verifier=...)` |
| C023 | Replay old ALLOW proof for new context | Must reject by context hash and freshness policy | Covered by `tests/test_threat_model_replay.py` — `ProofVerifier(expected_context=...)` rejects context-mismatched replay |
| C024 | Replay current ALLOW proof for same context after policy revocation | Must reject by policy version/freshness | Covered by `tests/test_threat_model_replay.py` — freshness (`max_age_seconds`), `revoked_policy_hashes`, and `ReplayGuard` |
| C025 | Downgrade Ed25519 proof to unsigned proof | Verifiers must reject unsigned proofs unless unsigned inspection is explicit | Covered by `tests/test_threat_model_proof_strictness.py` and `tests/test_peer_review_0_8_1_tarl_regressions.py` — `ProofVerifier()` and `tarl verify` require signatures by default; `require_signature=False` / `--allow-unsigned` is explicit |
| C026 | Delete DENY proof from audit archive | Hash-linked append-only audit must reveal gap | Covered by `tests/test_threat_model_audit_chain.py` — deleting a record breaks the hash chain (`verify_chain`) |
| C027 | Forge authority by setting CLI `--authority admin` | Authority must come from authenticated identity, not string input alone | Covered by `tests/test_threat_model_authority.py` — signed `AuthorityClaim` required; bare `--authority` denied in hardened mode |
| C028 | Put authority in environment variable | Must not grant authority from env alone | Covered by `tests/test_threat_model_authority.py` — authority is `authority_authenticated == False` unless a signed claim verifies |
| C029 | Use stdlib `thirst::fs` to write file without gate | Must route filesystem writes through capability broker | Covered by `tests/test_threat_model_capability_broker.py` and `tests/test_gate_fail_closed.py`; every sensitive callable has an explicit action in `module_system.SENSITIVE_STDLIB_CAPABILITIES`. **Deferred (medium):** path-root/canonicalization policy (see C042) |
| C030 | Use stdlib `thirst::http` or `thirst::net` without gate | Must route network through capability broker | Covered by `tests/test_threat_model_capability_broker.py` and `tests/test_gate_fail_closed.py`. **Deferred (medium):** external adapter / real-egress coverage |
| C031 | Use stdlib `thirst::process.run` without gate | Must route subprocess through capability broker | Covered by `tests/test_threat_model_capability_broker.py` and `tests/test_gate_fail_closed.py`. **Deferred (medium):** CLI build subprocesses (`llc`/`clang`/`lli`) are a separate, non-governed surface |
| C032 | Use `thirst::env.set` to poison later decisions | Must route env mutation through capability broker | Covered by `tests/test_threat_model_capability_broker.py` and `tests/test_gate_fail_closed.py` |
| C033 | Use FFI/native extension to perform side effects | Must deny or broker FFI | Covered by `tests/test_threat_model_broker.py` — `CapabilityBroker` denies FFI/`execute` by default; no native reach in-language |
| C034 | Use generated JS build output to skip governed runtime | Build artifacts must preserve or declare governance loss | Covered by `tests/test_threat_model_build_outputs.py` — `thirsty build` refuses governance-dropping targets for governed source by default; `--allow-governance-loss` is required, warns on stderr, and records `build.governance_loss` in the manifest |
| C035 | Use package manager or import path confusion to load malicious module | Imports and dependency integrity must be governed | Covered by `tests/test_threat_model_file_imports.py` — imported `.thirsty` modules execute under the **caller's** governed runtime (policy + authority), so top-level effects and returned closures are gated, not run in a detached core interpreter. **Deferred (medium):** dependency-pin/signature integrity for remote packages |
| C036 | Use parser recovery to smuggle executable statements after an error | Parser errors must fail closed for execution | Covered by `tests/test_threat_model_parser_fail_closed.py` — a governed module with any parse error yields zero statements and the interpreter refuses to run it (DENY proof) |
| C037 | Use resource exhaustion to force fail-open | Runtime errors must DENY, not ALLOW | Covered by `tests/test_threat_model_failclosed.py` — evaluator errors fail closed (DENY), surfaced as a non-swallowable denial |
| C038 | Use denial-of-service to suppress audit writing | Execution should fail closed when required audit cannot persist | Covered by `tests/test_threat_model_failclosed.py` — `set_require_audit` downgrades to DENY when a required proof cannot persist |
| C039 | Use AI-generated policy with broad `when true => ALLOW` | Policy analysis must flag broad allow and require review | Covered by `tests/test_threat_model_lint_quorum.py` — `lint_policy` flags broad/ungated ALLOW (`tarl lint`) |
| C040 | Use prompt injection to instruct an agent to bypass Thirsty | Agent adapters must enforce broker outside model text | Covered by `tests/test_threat_model_broker.py` — agent/tool effects must call `CapabilityBroker.require`; denied by default |
| C041 | Use MCP/tool call directly from agent runtime | Tool adapter must call broker before tool invocation | Covered by `tests/test_threat_model_broker.py` — MCP/tool adapters broker before invocation (`ACTION_TOOL`) |
| C042 | Use filesystem symlink/path traversal to escape allowed root | Path canonicalization and root policy required | Covered by `tests/test_threat_model_pathguard.py` — `PathGuard` confines canonical paths; traversal/symlink escape denied |
| C043 | Use time spoofing or make a configured time authority fail so runtime falls back to the host clock | Trusted clock values must be signed and timezone-aware; a missing, malformed, naive, or failing configured clock denies without host fallback | Covered by `tests/test_threat_model_clock.py` — `TrustedClock` verifies signed zoned time and invalid configured clocks fail closed |
| C044 | Use stale cached decision after context changes | Cache key and invalidation must bind all relevant context | Covered by `tests/test_tarl_composition.py::TestRuntimeRegisterSource::test_callable_source_updated_dynamically` and `test_source_does_not_leak_between_contexts` |
| C045 | Use partial context omission to get safer defaults wrong | Missing required context must DENY or ESCALATE | Covered by `tests/test_threat_model_context_schema.py` — missing required field fails closed before rule evaluation |
| C046 | Use type confusion in policy context | Context schema validation required | Covered by `tests/test_threat_model_context_schema.py` — type-confused context value fails closed (`ContextSchema`) |
| C047 | Use policy include/composition cycle | Must raise composition error, not fail open | Covered by composition tests |
| C048 | Use parallel evaluation race to alter first-match semantics | Policy order must win | Covered by TARL tests |
| C049 | Use archive query without signature verification as proof of validity | CLI/docs must distinguish stored from verified | Covered by `tests/test_threat_model_audit_chain.py` and `tarl audit verify-chain`; `query(verifier=...)` distinguishes stored from verified |
| C050 | Use social pressure language to force high-risk ALLOW | ESCALATE rules and proof-bound quorum required | Covered by `tests/test_threat_model_lint_quorum.py` — promotion requires a signature-verified policy/schema-bound proof and distinct digest-bound approvals |
| C051 | Claim governed readiness for a program without enumerating effects/proof obligations | Static report must list governed calls, sensitive stdlib calls, capabilities, TARL actions, context schema, authority, contracts, and unresolved gaps before execution | Covered by `tests/test_proof_obligations.py` — `thirsty prove` emits a machine-readable obligation report without running side effects |
| C052 | Infer an unsafe or ambiguous policy context schema | Derived schema must be marked incomplete and make `thirsty prove` fail closed unless an explicit schema is supplied | Covered by `tests/test_proof_obligations.py` — ambiguous field references produce `context_schema.status = incomplete` and exit non-zero |
| C053 | Use numeric strings to bypass ordering thresholds or exploit silent string-to-number conversion | Comparisons are type-strict: integers and floats interoperate, while every string/number comparison fails closed without conversion | Covered by `tests/test_peer_review_0_8_1_tarl_regressions.py` and `tests/test_tarl_context_security_boundaries.py` |
| C054 | Hide a malformed DENY guard before a broad ALLOW | Policy load and residual runtime evaluation errors must reject or DENY, never skip to a later ALLOW | Covered by `tests/test_peer_review_0_8_1_tarl_regressions.py` and `tests/test_tarl.py::TestThrowStats` |
| C055 | Accept a forged unsigned proof as valid by default | Verification default must require a signature and trace consistency must reject verdict mismatch when trace declares a verdict | Covered by `tests/test_peer_review_0_8_1_tarl_regressions.py` |
| C056 | Evaluate a policy window, time-bound verdict, `CURRENT_*`, or `ELAPSED_SINCE` from spoofed host time through `tarl eval` | Every time-dependent CLI evaluation must require an explicitly zoned trusted time | Covered by `tests/test_peer_review_0_8_1_tarl_regressions.py` — `tarl eval` refuses all time-dependent rules without zoned `--now` |
| C057 | Generate auto-TARL policies keyed on a context field the runtime never supplies | Generated policies must use `action`, matching governed runtime context | Covered by `tests/test_peer_review_0_8_1_tarl_regressions.py` |
| C058 | Supply a flat dotted key, nested object, or both so schema and evaluator observe different values | One authoritative nested representation; flat dotted keys and every mixed representation DENY explicitly | Covered in released 0.8.6 by `tests/test_tarl_context_resolution_integrity.py`; independent Competence Register acceptance remains pending |
| C059 | Use `!=`, `not`, membership, or a safe function to turn an unresolved path into ALLOW | MISSING and TYPE_ERROR short-circuit the rule and produce fail-closed DENY; a resolved boolean `false` remains distinct | Covered in released 0.8.6 by `tests/test_tarl_context_resolution_integrity.py`; the confirmed 0.8.5 bypass is preserved as regression evidence |
| C060 | Present a positive proof whose schema context differs from the evaluated context | Positive proof is inadmissible unless representation metadata and original/canonical hashes are coherent and signature-bound | Covered in released 0.8.6 by `tests/test_tarl_context_resolution_integrity.py`; independent Competence Register acceptance remains pending |
| C061 | Supply Python-only, cyclic, or non-finite context values, or exploit Python equality between booleans and numbers | Context and registered sources are restricted to finite JSON; incompatible values cannot enter boolean, comparison, membership, arithmetic, or safe-function algebra | Covered by `tests/test_tarl_context_security_boundaries.py` |
| C062 | Feed an unbound evaluator ALLOW directly into a broker or governed effect | Load-bearing consumers require an admissible positive proof with a passed explicit or complete derived schema; otherwise they replace ALLOW with DENY | Covered by `tests/test_tarl_context_security_boundaries.py` and `tests/test_tarl_proof.py` |
| C063 | Inject a reserved source field or forge a source-enriched context that also changes caller data | Registered-source injection is the sole transformation; proofs preserve original/evaluated bindings and verification requires both contexts while permitting only valid top-level source additions | Covered by `tests/test_tarl_context_security_boundaries.py` and `tests/test_tarl_proof.py` |
| C064 | Launder an explicit schema through duplicate/conflicting representation metadata, coercive fields, unknown kinds, or `on_violation: ALLOW` | Schema JSON and metadata are parsed strictly; unsupported, ambiguous, duplicate, or fail-open declarations are rejected | Covered by `tests/test_tarl_context_security_boundaries.py` |
| C065 | Hide a missing, malformed, or type-invalid value behind a decisive boolean operand, an earlier decisive quantifier element, or vacuous truth over an empty collection | Both boolean operands and every predicate application over the supplied collection are evaluated before the combined result is accepted; any resolution/type failure or empty quantifier collection denies the decision | Covered by `tests/test_tarl_context_security_boundaries.py` |
| C066 | Supply `NaN`, infinity, or overflow through numeric values/arithmetic, or send a numeric-looking string where the policy expects a number | Numeric operands and arithmetic outputs must be finite, and strings never coerce to numbers; violations raise a fail-closed evaluation error | Covered by `tests/test_tarl_context_security_boundaries.py` |
| C067 | Shadow trusted runtime state by naming a quantifier binder `__tarl_trusted_now` or another internal identifier | The `__tarl_*` binder namespace is reserved and rejected at parse and evaluation boundaries | Covered by `tests/test_tarl_context_security_boundaries.py` |
| C068 | Derive a schema for one policy, then evaluate a different `policy_text` override under the stale base schema | Derived-schema origin is tracked; each differing override receives a fresh complete derivation and proof binding, or fails closed when derivation is incomplete | Covered by `tests/test_tarl_context_security_boundaries.py` |
| C069 | Promote a fabricated, unsigned, tampered, wrong-policy, schema-unbound, differently approved, stale, replayed, expired, expiry-stripped, or request-unbound ESCALATE artifact | Quorum requires the exact request context, trusted aware time, freshness and replay enforcement, and independent signature verification against the exact policy/rule and a passed authoritative schema; each distinct approver signs the complete proof digest, and time-bound promotion preserves the verified signed expiry | Covered by `tests/test_threat_model_lint_quorum.py` |
| C070 | Re-encode the same valid signature with uppercase or embedded whitespace to obtain a second replay identity | Proof signatures have one exact lowercase hexadecimal encoding; replay identity binds the complete canonical proof, key, algorithm, and decoded signature bytes, with durable legacy-ID compatibility | Covered by `tests/test_tarl_proof.py::TestProofVerifier::test_ed25519_signature_encoding_cannot_bypass_replay_guard` and `tests/test_durable_state.py` |
| C071 | Reuse or promote a fresh proof after the governing policy window ended, or let a rule duration outlive that window | Every matched verdict and proof expires at the earliest exclusive policy or rule cutoff; verifier and quorum independently derive and enforce the same bound | Covered by `tests/test_tarl_proof.py::TestProofExpiryBinding` and `tests/test_threat_model_lint_quorum.py::test_quorum_cannot_promote_after_governing_policy_cutoff` |
| C072 | Misspell a temporal date, rule duration, succession duration, or expiry verdict so the restriction is silently discarded | The parser rejects malformed temporal directives and durations; direct invalid policy models fail closed | Covered by `tests/test_tarl_temporal.py::TestTemporalWindowParsing::test_malformed_temporal_metadata_is_rejected` and `TestRuleDurationParsing::test_malformed_rule_duration_is_rejected` |
| C073 | Configure `on_expiry: ALLOW` or present an unmatched positive proof to an authority consumer | Expiry cannot grant ALLOW, and positive authority requires a structurally coherent matched-rule trace plus passed context/schema binding | Covered by `tests/test_broker_unified_gate.py::test_invalid_on_expiry_allow_cannot_authorize_a_brokered_effect` and `tests/test_tarl_proof.py::TestContextSchemaProofBinding::test_unmatched_allow_proof_is_never_context_authority` |

## Mandatory Invariants

These invariants define the substrate. Violating any of them downgrades
Thirsty-Lang from "active resistance runtime" to "policy library."

1. **No effect before verdict.** A side effect cannot happen before ALLOW.
2. **No policy means DENY.** Missing policy never grants authority.
3. **No authority means DENY.** Missing authority never grants authority.
4. **No proof means no audit claim.** Execution without proof cannot be called
   governed execution.
5. **No unsigned proof in hardened mode.** Hardened deployments require Ed25519.
6. **No stale proof as authority.** Proofs describe decisions; they are not
   reusable permission tokens unless a freshness policy says so.
7. **No adapter side doors.** All tool, file, network, subprocess, import, FFI,
   database, and model-action paths go through the broker.
8. **No catch-and-continue for governance denials.** Application error handling
   must not swallow a denial.
9. **No silent downgrade.** If signing, policy, audit, or identity verification
   is required and unavailable, the runtime fails closed.
10. **No unverifiable readiness claim.** Security claims cite tests or are
    labeled roadmap.
11. **Missing is not false. Invalid is not false. Unresolved is not evidence.**
    `MISSING`, `TYPE_ERROR`, and `REPRESENTATION_CONFLICT` never participate in
    comparison, negation, membership, functions, or boolean algebra; they
    short-circuit to DENY or ESCALATE with an explicit reason.
12. **One context representation.** Dotted policy names are paths into nested
    objects. A JSON key containing a dot is not an alternative spelling. Flat
    dotted keys, equal mixed forms, contradictory mixed forms, duplicate keys,
    and reserved-layer collisions fail closed; no conversion occurs silently.
13. **Positive proof context coherence.** A positive policy verdict is
    inadmissible as advancement authority unless the exact context
    representation used for schema validation is the representation evaluated
    by the policy engine and bound into the proof. The proof binds the original
    context hash, canonical context hash, representation identifier,
    normalization algorithm identifier and version, and collision/conflict
    status. Identity evaluation requires the original and canonical hashes to
    match.
14. **Strict JSON and type algebra.** Contexts and registered sources contain
    only JSON objects, arrays, strings, booleans, finite numbers, and null.
    Python-specific values and incompatible cross-kind coercions fail closed;
    resolved boolean `false` is never equal to numeric zero.
15. **Load-bearing consumer gate.** Plain evaluation may report `ALLOW`, but a
    broker or governed runtime advances only when the positive proof carries a
    passed schema binding for the evaluated representation.
16. **One explicit source transformation.** Callers cannot provide `source:*`.
    Registered sources may add valid top-level source fields only, and a
    verifier must bind both the original and evaluated contexts before accepting
    a transformed positive proof.
17. **Strict schema metadata.** Representation fields, path model,
    normalization, violation verdict, field kinds, required flags, and field
    names are validated without duplicate-key acceptance or coercion.
18. **No hidden invalid operand.** Boolean operators evaluate both operands,
    and quantifiers evaluate their predicate for every supplied element before
    accepting the aggregate result. Resolution/type failure anywhere in that
    evaluated surface, or an empty quantifier collection, fails closed.
19. **Type-strict finite numeric evaluation.** Integers and floats may
    interoperate, but strings never coerce to numbers. Numeric operands and
    arithmetic outputs must be finite; `NaN`, infinity, and overflow to
    infinity never participate in a verdict condition.
20. **Reserved evaluator bindings.** A policy cannot bind a quantifier variable
    in the `__tarl_*` namespace used for trusted internal evaluation state.
21. **Policy/schema identity.** A derived schema belongs to the exact policy
    from which it was derived. A different policy override receives a fresh
    complete derivation and proof binding or is denied.
22. **Proof-bound quorum.** ESCALATE promotion requires a cryptographically
    signed proof independently verified against the exact policy, exact rule,
    passed schema, exact original request context, explicit trusted aware time,
    maximum proof age, and replay guard. Registered-source proofs also bind the
    exact evaluated context. Approvals bind the complete proof digest and are
    distinct by identity and key material. Time-bound promotion preserves its
    verified signed expiry.

## Offensive Test Suites

Implemented this hardening pass:

| Suite | Purpose |
|---|---|
| `tests/test_threat_model_capability_broker.py` | Asserts an import-only policy grants no fs/http/net/process/env/log/test/sqlite side effect (C029–C032) |
| `tests/test_threat_model_broker.py` | FFI/native, subprocess, and MCP/agent-tool effects must call `CapabilityBroker.require`; denied by default (C033, C040–C041) |
| `tests/test_threat_model_file_imports.py` | Imported `.thirsty` modules run under the caller's governed gate, not a detached core interpreter (C035) |
| `tests/test_threat_model_proof_strictness.py` | Strict verification rejects unsigned/HMAC/wrong-key/tampered proofs and missing policy source (C025) |
| `tests/test_threat_model_replay.py` | Rejects replayed proofs by context hash, freshness window, and revoked policy hash (C023–C024) |
| `tests/test_threat_model_authority.py` | Authority must come from a signed `AuthorityClaim`; bare `--authority`/env grants nothing in hardened mode (C027–C028) |
| `tests/test_threat_model_context_schema.py` | Missing or type-confused context fields fail closed before rule evaluation (C045–C046) |
| `tests/test_threat_model_audit_chain.py` | Hash-linked append-only audit; edits, deletions, and reordering break `verify_chain` (C022/C026/C049) |
| `tests/test_threat_model_pathguard.py` | `PathGuard` confines canonical (symlink-resolved) paths; traversal/symlink escape denied (C042) |
| `tests/test_threat_model_clock.py` | Temporal windows evaluate against signed, zoned `TrustedClock` time; invalid configured clocks deny without host fallback (C043) |
| `tests/test_threat_model_failclosed.py` | Evaluator errors and failed required-audit writes surface as non-swallowable denials (C037–C038) |
| `tests/test_threat_model_lint_quorum.py` | `lint_policy` flags broad/ungated ALLOW; `QuorumResolver` requires current-request binding, explicit trusted time, freshness/replay enforcement, and an independently verified signed policy/rule/schema-bound ESCALATE proof with distinct complete-digest approvals and preserved signed expiry (C039/C050/C069) |
| `tests/test_threat_model_build_outputs.py` | Governance-dropping build targets are refused for governed source unless explicitly opted in and disclosed (C034) |
| `tests/test_threat_model_parser_fail_closed.py` | Governed parse errors fail closed: no executable statements survive recovery (C036) |
| `tests/test_proof_obligations.py` | Static proof-obligation extraction, derived schema, build-manifest proof metadata, denial explanation, no-side-effect prove path, and proof/audit regression coverage (C051–C052) |
| `tests/test_peer_review_0_8_1_tarl_regressions.py` | TARL adversarial peer-review regressions for comparison typing, fail-closed evaluation, secure verifier defaults, trusted CLI time, and auto-TARL action context (C053–C057) |
| `tests/test_tarl_context_resolution_integrity.py` | Preserved context matrix across SafeExpr, evaluator, runtime, CLI, schema/proof obligations, proof creation/verification, and governed runtime; missing/type/conflict bypass regressions (C058–C060) |
| `tests/test_tarl_context_security_boundaries.py` | Strict JSON/type algebra, eager expression integrity, reserved binders, load-bearing schema authority, registered-source transformation, strict explicit-schema metadata, and per-override derivation (C061–C068) |

The earlier "still required" suites (proof replay, policy downgrade, context
poisoning, archive tamper, agent tools, resource failure) were implemented under
the consolidated filenames above: replay → `_replay.py`, downgrade →
`_proof_strictness.py`, context poisoning → `_context_schema.py`, archive tamper
→ `_audit_chain.py`, agent tools → `_broker.py`, resource failure →
`_failclosed.py`. No offensive suite remains deferred; see Remaining Gaps for
breadth/operational items.

## Current Defensive Evidence

The following surfaces are implemented and tested today:

- Governed `pour`, `sip`, `import`, callable `print(...)`, and sensitive
  imported stdlib calls fail closed without policy authority.
- Governed denials carry `TarlProof`.
- Contract ALLOW and DENY decisions carry proof records.
- `GovernanceViolation` is not swallowed by `spillage`.
- Ed25519 proof signing and public-key verification are implemented.
- HMAC proof signing remains supported but documented as symmetric and not
  non-repudiable.
- Policy hash, trace consistency, malformed proof, and signature verification
  checks are covered by tests.
- Temporal policy windows and first-match-wins semantics are covered by tests.
- Imported `.thirsty` modules execute under the caller's governed runtime, so
  their top-level effects and returned closures are gated (not run detached).
- Proof verification requires a signature by default, can restrict the signature
  family to Ed25519 (`ProofVerifier` / `tarl verify --ed25519-only`), and only
  accepts unsigned proofs when `require_signature=False` or `--allow-unsigned`
  is explicit. Signature permissiveness does not admit a positive legacy proof
  that lacks coherent context-representation binding.
- The active source uses nested objects as the sole context representation.
  Dotted policy references resolve as paths; flat dotted keys and mixed forms
  fail closed before any rule can match.
- Runtime proofs bind both original and evaluated context hashes plus the
  representation and transformation identity. The verifier rejects positive
  proofs whose binding metadata is missing, contradictory, or unsupported.
- `CapabilityBroker` and the governed interpreter call the runtime's schema
  assurance path and independently reject a positive proof that is not
  context-authority admissible. Plain evaluation without a schema remains
  available, but its `ALLOW` cannot authorize an effect through those consumers.
- Registered-source verification requires the expected original and evaluated
  contexts and proves that removing only valid top-level `source:<name>` fields
  reproduces the original request exactly.
- Boolean evaluation checks both operands, and `ALL`/`ANY` evaluates every
  supplied element's predicate before accepting the aggregate result. Numeric
  comparisons are type-strict, numeric operands/arithmetic outputs must be
  finite, empty quantifier collections fail closed, and binders cannot use the
  reserved `__tarl_*` namespace.
- A derived context schema is bound to the policy that produced it. Differing
  `policy_text` overrides receive a fresh complete derivation and proof binding;
  incomplete override derivation denies.
- Quorum promotion independently verifies the exact policy-bound,
  exact-rule, schema-passed, signed ESCALATE proof before counting distinct
  approvals. Each approval signs the digest of the complete proof artifact,
  and a time-bound promotion preserves its verified expiry.
- Governance-dropping build targets are refused for governed source unless
  `--allow-governance-loss` is given, which warns and records the loss in the
  emitted manifest.
- Governed modules that fail to parse fail closed: no recovered statement
  executes, and the interpreter raises a denial.
- `thirsty prove program.thirsty --policy policy.tarl` parses and checks source
  and emits a machine-readable proof-obligation report without executing program
  side effects. The report lists functions, imports, sensitive stdlib calls,
  governed calls, required TARL actions, derived or attached context schema,
  authority requirements, contract obligations, proof mode, audit requirement,
  Shadow Thirst status, governance-loss status, and unresolved proof gaps.
- `thirsty explain-denial program.thirsty --policy policy.tarl` reports which
  policy, context, authority, or proof condition is missing for the static
  obligation set.

## Remaining Gaps

Release 0.8.6 covers C058-C073 and replaces the vulnerable 0.8.5 evaluator.
The tagged commit passed the branch, tagged-release, PyPI, and multi-architecture
container workflows; a fresh PyPI installation reproduced the permanent
context matrix. The Competence Register still keeps context coherence and
resolution integrity at critical FAIL until an independent constitutional
acceptance records that the released artifact satisfies the gate. Other
remaining work is:

1. **Adapter rollout.** Shipped governed stdlib effects and the reference
   external adapters use `CapabilityBroker`; deployments must preserve that
   path for every additional adapter they introduce.
2. **Durable-state placement.** SQLite-backed replay/revocation stores and audit
   checkpoints are implemented, but deployments must place them on shared,
   access-controlled storage and export checkpoints to an independently trusted
   location.
3. **Trust-root custody.** Key formats, generation, loading, and rotation flows
   are implemented; deployments still own private-key custody, distribution of
   trusted public keys, and rotation/revocation operations.
4. **Independent acceptance.** Review the released 0.8.6 artifacts and recorded
   matrix evidence under an authority independent of the implementing agent;
   only that acceptance may unblock load-bearing positive verdict reliance.

## Proof-Obligation Behavior Contracts

- Plain evaluation can run without a schema, but its positive result is not
  advancement authority. Load-bearing broker and governed-runtime consumers
  require a passed schema binding and attempt only complete schema derivation.
  `thirsty prove` derives simple field kinds from TARL policy references.
- Ambiguous context references remain incomplete and fail closed; use an
  explicit schema file for policy expressions the static derivation cannot
  prove.
- `thirsty prove` is intentionally static: it produces the proof-obligation
  report before execution and does not replace runtime TARL verdict enforcement,
  proof verification, broker mediation, or audit append behavior.

## Acceptance Bar For Hardened Runtime

Thirsty-Lang can claim hardened governance-substrate status when:

1. Every challenge in the catalog is passing with a test or documented out of
   scope. **Met in released 0.8.6** - C001-C073 have coverage; independent
   Competence Register acceptance for C058-C073 remains open.
2. All side-effect adapters are mediated by the same broker. **Met (mechanism)**
   — `utf.tarl.broker.CapabilityBroker`; deployment adapter rollout tracked in
   Remaining Gaps #1.
3. Hardened mode requires Ed25519 proof signatures. **Met** —
   `Interpreter.set_hardened()` fails closed without authenticated authority and
   Ed25519-signed proofs (`tests/test_threat_model_authority.py`).
4. Policy and context schemas use the representation evaluated by the engine.
   **Met in released 0.8.6** - `utf.tarl.context`, `utf.tarl.schema`, and
   `tests/test_tarl_context_resolution_integrity.py`; the load-bearing consumer
   gate is covered by `tests/test_tarl_context_security_boundaries.py`;
   independent Competence Register acceptance remains open.
5. Audit persistence is hash-linked and tamper-evident. **Met** —
   `TarlAuditArchive.verify_chain` (`tests/test_threat_model_audit_chain.py`).
6. Replay and downgrade attacks are rejected. **Met** —
   `tests/test_threat_model_replay.py`, `tests/test_threat_model_proof_strictness.py`.
7. The full offensive challenge suite passes locally and in CI. **Met for
   0.8.6** - the local gate reported 1,463 passed, 1 skipped, 22 subtests, and
   90.60% coverage; branch CI run `30756636768` and tagged release validation
   run `30756676570` completed successfully.
