# Feature Status

Edition: Thirsty-Lang 0.8.6. The integrated navigation and reference layer is
[THIRSTY_LANG_101.md](THIRSTY_LANG_101.md); security acceptance details remain
authoritative in [THREAT_MODEL.md](THREAT_MODEL.md).

Every capability below is marked **Real** (implemented and enforced, with a
test that proves it) or **Roadmap** (reserved surface, not yet enforced). The
test reference is the authority — if a row says Real, the cited test fails when
the behaviour regresses. Run the whole matrix with:

```
pytest tests/ -q
```

The optional Z3 layer is exercised only when the `analysis` extra is installed
(`pip install thirsty-lang[analysis]`); its tests `importorskip("z3")` otherwise.

## Bootstrap Competence Register

This register distinguishes verdict execution from context-contract integrity.
The PASS entries are evidenced by the preserved 0.8.5 package reproduction.
The repairs shipped in 0.8.6 at commit
`60f226a69059b5803b0035f037d09e6f7f9c45a2`; the branch CI, PyPI release, and
multi-architecture GHCR workflows all passed, and a fresh PyPI installation
reproduced the permanent ALLOW/DENY matrix. The critical FAIL entries remain
in place because release evidence is not the same thing as independent
constitutional acceptance. Until that acceptance is recorded, they continue
to block load-bearing positive authority. Regression authority is provided by
`tests/test_tarl_context_resolution_integrity.py`,
`tests/test_tarl_context_security_boundaries.py`, and
`tests/test_threat_model_lint_quorum.py`.

```yaml
- competence_id: CR-TARL-ALLOW
  title: Positive policy verdict executes
  status: PASS
  evidence:
    - nested dotted-path case returned ALLOW
    - simple identifier case returned ALLOW

- competence_id: CR-TARL-DENY
  title: Negative and default-deny paths execute
  status: PASS
  evidence:
    - flat dotted-key mismatch returned DENY
    - guest control returned DENY

- competence_id: CR-CONTEXT-COHERENCE
  title: Schema, CLI, evaluator, proofs, and documentation share one context model
  status: FAIL
  severity: critical
  repair_status: released_in_0_8_6_pending_independent_acceptance
  blocks:
    - policy_engine_load_bearing_authority
    - trusted_state_promotion
    - signed_positive_verdict_reliance

- competence_id: CR-CONTEXT-RESOLUTION-INTEGRITY
  title: Context resolution preserves missing and invalid states
  status: FAIL
  severity: critical
  security_impact: confirmed_authorization_bypass
  repair_status: released_in_0_8_6_pending_independent_acceptance
  blocks:
    - all_dotted_path_policy_authority
    - competence_advancement_authorization
    - trusted_state_promotion
    - positive_verdict_proof_reliance
```

Preserved reproduction evidence manifest SHA-256:
`4DD3E6A4CF017E3E34A25C62A398D29A6F93D279890C4CCDF2A4528C6333F8D5`.

## Language core (Thirsty-Lang)

| Capability | Status | Test reference |
|---|---|---|
| Array / reservoir literals `[1,2,3]` evaluate to a real list | Real | `tests/test_thirsty_lang.py`; `tests/test_examples.py` |
| `flood` / `evaporate` / `new` over reservoirs and fountains | Real | `tests/test_thirsty_lang.py`; `tests/test_examples.py` |
| Variable reassignment (`x = …`) mutates the binding | Real | `tests/test_thirsty_lang.py` |
| OOP: member read/write, method dispatch (`obj.f()`, `obj.x = …`) | Real | `tests/test_thirsty_lang.py`; `tests/test_examples.py` (`gods.thirstofgods`) |
| `cascade` awaits and yields a value (not a Future) | Real | `tests/test_examples.py` |
| `spillage` / `error` / `cleanup` / `finally` control flow | Real | `tests/test_examples.py`; `tests/test_thirst_of_gods.py` |
| `refill (x in xs)` loop accumulation | Real | `tests/test_examples.py` |
| UTF-8-safe CLI output on Windows (cp1252) | Real | `src/utf/console.py` (`enable_utf8`), shared by all CLIs |
| Every shipped example parses, type-checks, and runs clean | Real | `tests/test_examples.py` |
| `let` (immutable binding), `for … in` keyword loop, `:=` (define mutable) | Real | `tests/test_language_features.py` |
| `strict` (requires initialization) / `pure` (no I/O) module modes | Real | `tests/test_language_features.py` |
| Self- and mutual recursion (correct arity, no false E030) | Real | `tests/test_language_fixes.py` |
| `this` keyword, member assignment, fountain field default initializers | Real | `tests/test_language_fixes.py` |
| Closures capture their lexical (defining) scope | Real | `tests/test_language_fixes.py` |
| `\|>` pipe operator (and bare `\|`); `error (name)` binds the thrown value | Real | `tests/test_language_fixes.py` |
| `times N { … }` repeat loop | Real | `tests/test_new_language_features.py` |
| C-style `refill(init; cond; step)` loop (counter implicitly mutable) | Real | `tests/test_new_language_features.py` |
| Anonymous functions / lambdas `glass(params) { … }` as values | Real | `tests/test_new_language_features.py` |
| Subscript indexing `xs[i]` (reservoir/dict/string), read + assign, bounds-checked | Real | `tests/test_review_0_8_1.py` |
| Un-annotated functions return `Any` (value-use + recursion type-check) | Real | `tests/test_review_0_8_1.py` |
| Combine `^`/`\|\|` require both operands bool; mixed bool/non-bool rejected (no fail-open) | Real | `tests/test_review_0_8_1.py` |

## Governance (maximal)

| Capability | Status | Test reference |
|---|---|---|
| `requires` precondition on governed functions | Real | `tests/test_governance_maximal.py::TestContracts` |
| `ensures` postcondition (`result` bound after the body) | Real | `tests/test_governance_maximal.py::TestContracts::test_ensures_*` |
| `invariant` checked at entry **and** exit | Real | `tests/test_governance_maximal.py::TestContracts::test_invariant_entry_and_exit` |
| Contracts on methods (design-by-contract, any mode) | Real | `tests/test_governance_maximal.py::TestContracts::test_method_contract_any_mode` |
| Capability gates: imports + I/O routed through TARL, deny-by-default | Real | `tests/test_governance_maximal.py::TestCapabilityGates` |
| Sensitive imported stdlib calls require their own capability verdict after import | Real | `tests/test_gate_fail_closed.py::test_import_allow_does_not_grant_sensitive_stdlib_calls` |
| Denials carry a `TarlProof`; proofs are unsigned unless runtime signing is configured | Real | `tests/test_governance_maximal.py::TestCapabilityGates::test_write_denied_with_proof`; `tests/test_gate_fail_closed.py` |
| Temporal windows govern a call (allow/deny) | Real | `tests/test_governance_maximal.py::TestTemporal` |
| Static E053 for a governed call from `core` mode | Real | `tests/test_governance_maximal.py::TestStatic::test_e053_governed_call_from_core` |
| Forward-reference / mutual-recursion hoisting | Real | `tests/test_governance_maximal.py::TestStatic::test_forward_reference_resolves` |
| Offensive threat model and challenge catalog | Real | `docs/THREAT_MODEL.md` |
| Imported `.thirsty` modules run under the caller's governed gate (not detached core) | Real | `tests/test_threat_model_file_imports.py` |
| Governed module with a parse error fails closed (no statements execute) | Real | `tests/test_threat_model_parser_fail_closed.py` |
| Secure-by-default proof verification (signature required unless unsigned mode is explicit; Ed25519-only / policy source options) | Real | `tests/test_threat_model_proof_strictness.py`; `tests/test_peer_review_0_8_1_tarl_regressions.py` |
| Governed build refuses governance-dropping targets unless explicitly disclosed | Real | `tests/test_threat_model_build_outputs.py` |
| Import-only policy grants no sensitive stdlib side effect | Real | `tests/test_threat_model_capability_broker.py` |
| Static proof-obligation manifest (`thirsty prove`) without executing side effects | Real | `tests/test_proof_obligations.py` |
| Derived context schema from TARL policy references, fail-closed when incomplete | Real | `tests/test_proof_obligations.py`; `tests/test_threat_model_context_schema.py` |
| Denial explanation for missing policy/context/authority/proof conditions | Real | `tests/test_proof_obligations.py` |
| Build manifest records source/policy hashes, capabilities, schema, proof/audit requirements, Shadow status, and governance-loss status | Real | `tests/test_proof_obligations.py`; `tests/test_threat_model_build_outputs.py` |
| TARL numeric comparison is type-strict: int/float interoperate; strings never coerce to numbers | Real in released 0.8.6; independent acceptance pending | `tests/test_peer_review_0_8_1_tarl_regressions.py`; `tests/test_tarl_context_security_boundaries.py` |
| TARL policy load and runtime evaluation reject or deny malformed/unsafe rules instead of falling through | Real | `tests/test_peer_review_0_8_1_tarl_regressions.py`; `tests/test_tarl.py::TestThrowStats` |
| Runtime and `tarl eval` require valid zoned trusted time for configured clocks, policy windows, time-bound verdicts, `CURRENT_*`, and `ELAPSED_SINCE`; invalid configured clocks never fall back to host time | Real | `tests/test_threat_model_clock.py`; `tests/test_peer_review_0_8_1_tarl_regressions.py` |
| `thirsty govern --auto-tarl` emits policies keyed on runtime `action` context | Real | `tests/test_peer_review_0_8_1_tarl_regressions.py` |

## Hardened runtime (offensive catalog C022–C073)

| Capability | Status | Test reference |
|---|---|---|
| Authenticated authority provenance; hardened mode requires signed authority + Ed25519 proofs | Real | `tests/test_threat_model_authority.py` |
| Context schema validation fails closed on missing/type-confused fields | Real | `tests/test_threat_model_context_schema.py` |
| One authoritative nested context representation across schema, CLI, evaluator, proof, and governed runtime | Real in released 0.8.6; independent acceptance pending | `tests/test_tarl_context_resolution_integrity.py` |
| Missing, malformed, and conflicting context states short-circuit to DENY and never enter boolean algebra | Real in released 0.8.6; independent acceptance pending | `tests/test_tarl_context_resolution_integrity.py` |
| Positive proofs bind original/canonical hashes, representation, algorithm/version, and conflict status | Real in released 0.8.6; independent acceptance pending | `tests/test_tarl_context_resolution_integrity.py` |
| Context and registered sources use strict finite JSON; incompatible expression kinds cannot coerce into ALLOW | Real in released 0.8.6; independent acceptance pending | `tests/test_tarl_context_security_boundaries.py` |
| Broker and governed runtime require a passed, proof-bound explicit or complete derived schema before ALLOW can advance authority | Real in released 0.8.6; independent acceptance pending | `tests/test_tarl_context_security_boundaries.py` |
| Registered-source proofs preserve original/evaluated contexts and verification permits only valid source-field additions | Real in released 0.8.6; independent acceptance pending | `tests/test_tarl_context_security_boundaries.py`; `tests/test_tarl_proof.py` |
| Explicit schema representation and field metadata are parsed strictly without duplicate-key acceptance or coercion | Real in released 0.8.6; independent acceptance pending | `tests/test_tarl_context_security_boundaries.py` |
| Boolean operands and every supplied quantifier element are validated eagerly, and empty quantifier collections fail closed, so decisive or vacuous results cannot hide resolution/type failures | Real in released 0.8.6; independent acceptance pending | `tests/test_tarl_context_security_boundaries.py` |
| Numeric operands and arithmetic results must remain finite; strings never coerce to numbers | Real in released 0.8.6; independent acceptance pending | `tests/test_tarl_context_security_boundaries.py` |
| Quantifier binders cannot shadow the reserved `__tarl_*` evaluator namespace | Real in released 0.8.6; independent acceptance pending | `tests/test_tarl_context_security_boundaries.py` |
| When the runtime schema is derived, a differing `policy_text` override receives its own complete derived schema and proof binding, or fails closed; an explicitly attached schema remains caller-authoritative | Real in released 0.8.6; independent acceptance pending | `tests/test_tarl_context_security_boundaries.py` |
| Quorum promotion requires the exact request context, trusted aware time, freshness and replay enforcement, plus an independently verified, signed, exact-policy/rule, schema-passed ESCALATE proof with distinct approvals over its complete digest and preserved signed expiry | Real in released 0.8.6; independent acceptance pending | `tests/test_threat_model_lint_quorum.py` |
| Replay/freshness/revocation rejection in the proof verifier | Real | `tests/test_threat_model_replay.py` |
| Canonical proof signatures and complete semantic replay identity prevent alternate-encoding reuse | Real in released 0.8.6; independent acceptance pending | `tests/test_tarl_proof.py`; `tests/test_durable_state.py` |
| Temporal directives parse strictly, expiry cannot grant ALLOW, and proof/quorum authority is capped at the earliest exclusive policy or rule cutoff | Real in released 0.8.6; independent acceptance pending | `tests/test_tarl_temporal.py`; `tests/test_tarl_proof.py`; `tests/test_threat_model_lint_quorum.py`; `tests/test_broker_unified_gate.py` |
| Tamper-evident hash-linked audit chain (`verify_chain`) | Real | `tests/test_threat_model_audit_chain.py` |
| Universal capability broker (FFI/native + agent/MCP tools) | Real | `tests/test_threat_model_broker.py` |
| Fail-closed under evaluator error / required-audit failure | Real | `tests/test_threat_model_failclosed.py` |
| Filesystem path confinement (traversal/symlink escape) | Real | `tests/test_threat_model_pathguard.py` |
| Broad-ALLOW policy lint + proof-bound signed ESCALATE quorum | Real in released 0.8.6; independent acceptance pending | `tests/test_threat_model_lint_quorum.py` |
| Trusted signed-time source for temporal policy | Real | `tests/test_threat_model_clock.py` |
| CLI: `tarl lint`, `tarl audit verify-chain`, strict `tarl verify` flags | Real | `tests/test_cli_tarl_hardening.py` |

## Semantic verifiers

| Capability | Status | Test reference |
|---|---|---|
| Convergence: structural (alpha-renamed AST) pre-check | Real | `tests/test_verifiers.py::TestConvergence::test_structural_alpha_equivalent_promotes` |
| Convergence: Z3 symbolic proof + counterexample (arith subset) | Real (opt) | `tests/test_verifiers.py::TestConvergenceZ3` |
| Convergence: execute-and-compare over seeded inputs | Real | `tests/test_verifiers.py::TestConvergence::test_execute_and_compare_finds_diverging_input` |
| Convergence abstains on blocks with observable effects | Real | `tests/test_verifiers.py::TestConvergence::test_execute_and_compare_abstains_on_effects` |
| Determinism: taint dataflow follows non-determinism through aliases | Real | `tests/test_verifiers.py::TestEffectPass` |
| Thirst of Gods: each cascade linked to an enclosing spillage handler | Real | `tests/test_verifiers.py::TestCascadeLinking`; `tests/test_thirst_of_gods.py` |
| Shadow Thirst 6-analyzer promote/reject flow (AST-based) | Real | `tests/test_shadow_thirst.py` |

## T.A.R.L. policy engine

| Capability | Status | Test reference |
|---|---|---|
| Policy parsing, first-match-wins evaluation, verdicts | Real | `tests/test_tarl.py` |
| HMAC-signed proof certificates | Real | `tests/test_tarl_proof.py` |
| Ed25519-signed proof certificates | Real | `tests/test_tarl_proof.py` |
| Temporal windows (`valid_from`/`valid_until`, durations) | Real | `tests/test_tarl_temporal.py` |
| Policy composition | Real | `tests/test_tarl_composition.py` |
| Z3 static analysis (coverage / shadows / conflicts / equiv / refines) | Real (opt) | `tests/test_tarl_analyzer.py` |

## Stability

| Capability | Status | Test reference |
|---|---|---|
| Lint gate (ruff) clean under the project config | Real | CI `lint-and-test` job; `ruff check src tests` |
| Full suite on 3.11 + 3.12 with a coverage floor | Real | CI `lint-and-test` job (`--cov-fail-under=90`) |
| Examples executed through their CLIs in CI | Real | CI `lint-and-test` job |
| Package builds and imports cleanly | Real | CI `package-smoke` job |
