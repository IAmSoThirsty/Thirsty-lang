# Operational Continuity Map

Workstream: **Proof-Carrying Effects Language + TARL Security Corrections**
Updated: 2026-09-13
Branch: `codex/function-expansion-pack`
Workspace: `thirsty_lang_exploration_0754`

---

## 2026-09-13 M4.1 execution control

- M3.1-M3.5 delivery was committed and pushed as
  `e888a847b079048ba29b78a39b8e5ddfebed86ce`; a fresh read-only check confirmed
  matching GitHub/local HEAD and a clean tree before this increment.
- Reproduced concurrent environment corruption, nested-cascade starvation,
  caller-shadowed governance contracts, and repeated successful REPL input.
- Implemented logical ownership, explicit worker transfer, lexical scopes,
  finite cooperative limits and cancellation, shared import scheduler lifetime,
  and CLI setup/exit ownership. Full integration evidence belongs to
  [M4_EXECUTION_CONTROL_VERIFICATION.md](M4_EXECUTION_CONTROL_VERIFICATION.md).
- This is unreleased development after the M3.5 commit. Metadata remains 0.9.0;
  no new release, rename, or cross-project material is part of this work.
  M3-M7, global resource containment, and independent acceptance remain open.

## 2026-09-08 M3.5 constructor and governed value identity

- Continued priority language corrections with robotics deferred. Constructor
  descriptors preserve nominal identity through aliases and callable choices;
  calls, member access, `new`, and pipes distinguish constructors from values.
- Cascade checking follows its actual result, and a dynamic noncallable
  cascade fails after one evaluation of the callee and arguments.
- Governed boundaries project bounded JSON/native values, include receivers,
  detect callback changes to the admitted context, and bind positive policy
  proofs to the exact submitted context. Unsupported values deny with a
  diagnostic certificate; successful projection is not a portable code signature.
- Native metadata keys and the governed parameter name `result` are reserved.
  Ordinary uncontracted computation keeps its existing value representations.
- The manual builder corrects page headings, landscape furniture, and headings
  separated from wide tables. Current verification and limitations are recorded
  in [M3_VALUE_IDENTITY_VERIFICATION.md](M3_VALUE_IDENTITY_VERIFICATION.md).
- Base HEAD and 0.9.0 metadata remain unchanged. Cumulative M3.1-M3.5 work is
  local and unreleased; earlier records retain their historical test evidence.
  No rename, remote action, or cross-project material is part of this increment.
  General-purpose milestones M3-M7 and independent acceptance remain open.

## 2026-09-08 M3.4 callable and iteration consistency

- Continued the authorized general-purpose language plan after M3.3, keeping
  governance first, security as default, and robotics deferred.
- Known callable alternatives retain every signature and nominal identity;
  assignment uses parameter contravariance and return covariance. Calls and
  both pipe families check every possible signature. Explicit Any remains
  gradual; this does not establish whole-language type soundness.
- For-each inference checks the iterable in its enclosing scope, preserves
  collection element/key types, and rejects known noniterables. Runtime uses
  native iteration and reports dynamic noniterables instead of skipping them.
- Runtime exact arity guards reject callable entry before body, contract,
  policy, or fountain default evaluation. Argument expressions retain their
  existing single evaluation and source order.
- Current evidence and remaining issues are recorded in
  [M3_CALLABLE_ITERATION_VERIFICATION.md](M3_CALLABLE_ITERATION_VERIFICATION.md).
  Earlier M3.1-M3.3 verification records remain historical.
- Base HEAD remains `b09bbfc3dda4654cca2e9872423460667eed9498`, metadata 0.9.0,
  branch `codex/function-expansion-pack`. Cumulative work remains unreleased;
  no remote publication or cross-project material is part of this increment.

## 2026-09-08 M3.3 governance and security defaults

- User authorized continuing the language vision with governance first and
  security as default. The existing Thirsty-Lang name remains appropriate;
  no repository rename or cross-project import is needed.
- Default execution now requires governance across the interpreter, CLI,
  REPL, scaffold, and Gods runtime. Source modes select semantics and cannot
  opt out. Trusted host compatibility requires an explicit option/disclosure.
- Defining/calling restrictions and import locks combine across callbacks,
  retained functions, methods, aliases, and cascade. Credential callbacks
  cannot silently replace an already-authorized binding before release.
- Lexical/parser failures survive token transport and reject execution,
  checking, formatting, and public builds. Stdlib exports are exhaustively
  classified; all public build targets require a persisted loss disclosure.
- Final local evidence and remaining issues are recorded separately in
  [M3_SECURITY_DEFAULTS_VERIFICATION.md](M3_SECURITY_DEFAULTS_VERIFICATION.md).
  Earlier increment records remain historical and are not current validation.
- Base commit and 0.9.0 metadata remain unchanged; this work is unreleased.
  No remote publication or broad GitHub investigation occurred. Broader M3-M7
  work and independent acceptance remain open; robotics remains deferred.

## 2026-09-07 M3.2 Boolean and type coherence

- User authorized proceeding with the next M3 correction increment. The current
  checkout still starts from `b09bbfc3dda4654cca2e9872423460667eed9498`, metadata
  0.9.0, with M3.1 and M3.2 local/unreleased work preserved together.
- Scope: scalar Boolean arithmetic/comparison rules; nested nominal generic
  identity, forward signatures, dictionary key checks; connected malformed
  declaration parser and cascade checker repairs. Runtime declaration order
  and native container/dictionary equality remain unchanged.
- A real Z3 defect could treat `return true` and `return 1` as equivalent.
  Engine 0.4.0/v4 corrects it and requires reanalysis of older assurance claims.
  Historical records retain explicit integrity-only verification.
- Current results and remaining issues:
  [M3_TYPE_COHERENCE_VERIFICATION.md](M3_TYPE_COHERENCE_VERIFICATION.md).
  Previous M3.1 evidence below is preserved as historical evidence.
- No remote publication, workflow, tag, or merge operation is part of this
  increment. No cross-project material was introduced. Robotics stays deferred.

## 2026-09-06 M3.1 sequence increment after the 0.9.0 release

- Current base: `b09bbfc3dda4654cca2e9872423460667eed9498` on
  `codex/function-expansion-pack`, package metadata 0.9.0. M3.1 changes are
  local and unreleased; no new version or publication is claimed.
- User directed continued implementation from the plan and said a broad
  GitHub verification was unnecessary. Work remains inside this repository.
- M3.1 implements native sequence indexing/slicing, precise known sequence
  result types, numeric inference corrections needed by bounds, formatter
  statement separation, and conservative compiler/proof boundaries.
- Current verification and remaining issues:
  [M3_SEQUENCE_VERIFICATION.md](M3_SEQUENCE_VERIFICATION.md). M3 as a whole
  remains open; robotics remains deferred.
- The earlier 0.9.0 publication completed at the base commit. The preserved
  local receipt is `.tmp/release-0.9.0-20260906/published/release-receipt.json`:
  release workflow `34053055171` and CI `34053057407` succeeded, and the public
  wheel and sdist hashes matched their workflow artifacts. This is recorded
  release evidence, not a fresh remote investigation in M3.1.
- The verified release tag was `pypi-release-v0.9.0`. The earlier
  `pypi-v0.9.0` tag and failed initial run remain preserved historical evidence.

## 2026-09-06 priority corrections and general-purpose foundation

- Base commit: `4e493dde5ba822a4e27ad87b4139f72ff7a443c3`, package 0.8.6.
- Release target: 0.9.0. GitHub and PyPI publication are user-authorized;
  publication and remote artifact identity require separate release verification.
- User authorized implementation after the read-only review/full-suite baseline,
  then explicitly deferred robotics and swarm features until priority fixes and
  general-purpose language work are implemented.
- Current correction register and milestone order:
  [DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md).
- Current APIs and compatibility changes:
  [GENERAL_PURPOSE_LANGUAGE.md](../GENERAL_PURPOSE_LANGUAGE.md).
- Exact final local checks and limitations are recorded separately in
  [IMPLEMENTATION_VERIFICATION.md](IMPLEMENTATION_VERIFICATION.md).
- No other personal project supplied material. No remote commit, push,
  publication, deployment, or independent acceptance is claimed here.
- Historical entries below retain their original scope and outcomes. Statements
  about rejecting flat/equal mixed contexts in those entries describe the earlier
  contract; current `prepare_context()` normalizes equivalent forms with proof
  binding and rejects conflicts.

## 2026-08-02 v0.8.6 Release Closure and Documentation Reconciliation

- Release commit: `60f226a69059b5803b0035f037d09e6f7f9c45a2`.
- Annotated tag: `v0.8.6`; tag object
  `d89bbbc80a165ab6340cbe7855dfd6af2b086d1a`, peeling to the release commit.
- Branch CI run `30756636768`, tagged validation/PyPI run `30756676570`, and
  multi-architecture container run `30756676576` completed successfully.
- Local release gate: 1,463 passed, 1 skipped, 22 subtests, 90.60 percent
  coverage. A clean environment installed the published PyPI 0.8.6 package and
  reproduced the permanent context matrix.
- GHCR 0.8.6 publishes `linux/amd64` and `linux/arm64` under digest
  `sha256:6f3f516b8e979437dd414373afe581716b8c890dc4758b8675cbbcad9b94b13c`.
  Docker Hub remains stale at 0.8.1 and is not an authoritative 0.8.6 source.
- The preserved 0.8.5 reproduction remains anchored by evidence-manifest hash
  `4DD3E6A4CF017E3E34A25C62A398D29A6F93D279890C4CCDF2A4528C6333F8D5`.
- `CR-TARL-ALLOW` and `CR-TARL-DENY` remain PASS. The released repair does not
  itself change `CR-CONTEXT-COHERENCE` or
  `CR-CONTEXT-RESOLUTION-INTEGRITY`; both remain critical FAIL pending
  independent constitutional acceptance.
- Documentation is being reconciled to the released behavior and assembled
  into `docs/THIRSTY_LANG_UTF_101.md` plus the generated single-file canonical PDF.

---

## 2026-08-02 Context Resolution Integrity Repair

- An isolated install of published `thirsty-lang==0.8.5` preserved the canonical
  four-case context matrix. Nested `user.role` and simple `role` ALLOW paths
  work; flat dotted input and guest control return DENY. Evidence manifest:
  `4DD3E6A4CF017E3E34A25C62A398D29A6F93D279890C4CCDF2A4528C6333F8D5`.
- Adversarial evaluation confirmed a critical authorization bypass: unresolved
  dotted paths were converted to `False`, so negation and inequality could
  produce ALLOW. Published 0.8.5 is not admissible for load-bearing positive
  verdict authority.
- Active source now uses typed resolution states (`RESOLVED`, `MISSING`,
  `TYPE_ERROR`, `REPRESENTATION_CONFLICT`) and one nested context
  representation. Flat dotted keys, all mixed forms, duplicate keys, and
  trusted-layer collisions fail closed.
- Proofs bind original and canonical context hashes, representation identity,
  transformation algorithm/version, and conflict status. Positive legacy
  proofs without coherent context metadata are inadmissible even when unsigned
  inspection mode is selected.
- Permanent fixtures and tests are in
  `tests/fixtures/tarl_context_coherence/` and
  `tests/test_tarl_context_resolution_integrity.py`. The matrix runs through
  SafeExpr, `evaluate_policy`, `TarlRuntime`, `tarl eval`, schema/proof
  obligations, proof creation/verification, and governed Thirsty-Lang routing.
- Post-audit expression hardening now evaluates both boolean operands and every
  supplied quantifier element, treats an empty quantifier collection as no
  authorization evidence, forbids string-to-number comparison coercion, rejects
  non-finite numeric operands/results, and reserves `__tarl_*` quantifier
  binders for trusted runtime state.
- Trusted-time hardening rejects naive signed assertions and CLI times. Once a
  runtime clock is configured, a missing, malformed, or failing value denies
  without falling back to host time. CLI `--now` is required for windows,
  time-bound verdicts, `CURRENT_*`, and `ELAPSED_SINCE`.
- Derived schemas now follow exact policy identity. A differing `policy_text`
  override receives a fresh complete derivation and proof binding; incomplete
  override derivation fails closed rather than inheriting the base policy's
  derived schema.
- Quorum promotion now requires independent cryptographic verification of the
  signed exact-policy/rule, schema-passed ESCALATE proof before distinct
  Ed25519 approvals over the complete proof digest are counted. The resolver
  also requires the exact request context, an explicit timezone-aware trusted
  clock, verifier freshness and replay enforcement, and the exact evaluated
  context for registered-source proofs. Time-bound promotion retains its
  verified signed expiry. Regression coverage is in
  `tests/test_threat_model_lint_quorum.py`.
- Threat-model cases C065–C073 permanently record the eager-expression,
  finite-result, reserved-binder, per-policy-schema, proof-bound-quorum,
  canonical replay-identity, and strict temporal-authority protections.
  Active-source coverage does not itself satisfy package-level independent
  acceptance.
- Competence Register state is in `docs/STATUS.md`. Context coherence and
  resolution integrity remain critical FAIL pending independent constitutional
  acceptance; the repaired 0.8.6 package and release gates have passed.

---

## 2026-07-29 Sync and Release Fix Workstream

Workstream: **Upstream README Sync + PyPI Trusted Publisher Fix**
Branch: `iamsothirsty-sync-and-fix-release`

### What Was Read

- Local HEAD at `d64e7ff` (Release 0.8.5: repair PyPI publishing).
- GitHub master ahead by 7 commits (`d35d179` through `2317dcc`); all README
  documentation/cosmetic changes via PR #22.
- Remote tag `v0.8.5` = `1da4a9735d06811ec82a10554ef5695cbc601df4` matches
  local tag exactly. Release identity/plumbing was verified at that time; the
  later 2026-08-02 context-resolution finding supersedes any broader claim that
  the public evaluator implementation was correct.
- `.github/workflows/release.yml` had `permissions: id-token: write` and used
  `pypa/gh-action-pypi-publish` but had **no `environment:` field on the job**.
- GitHub repo environments API: only `copilot` environment exists; no `release`
  or `IAmSoThirsty` environment was previously configured on 2026-07-29 start.
  By end of session: `release` environment exists (user-created), containing
  secret `IAMSOTHIRSTY` (PyPI API token). `IAmSoThirsty` environment was
  auto-created by GitHub during the failed OIDC run and is now unused.
- GitHub Actions run log for `29914952475` (v0.8.5 release, failed):
  `invalid-publisher: valid token, but no corresponding publisher` and
  `environment: MISSING`. This is the definitive root cause.

### What Was Changed

- `.github/workflows/release.yml`: corrected `environment: release` (was
  `IAmSoThirsty`). Added `user: __token__` and `password: ${{ secrets.IAMSOTHIRSTY }}`
  to the publish step. Auth method is token-based (PyPI API token stored in the
  `release` environment secret `IAMSOTHIRSTY`); OIDC trusted publishing is not
  used despite `id-token: write` remaining in the top-level permissions.
- `README.md`: fast-forwarded from upstream master via `git merge FETCH_HEAD`.
  132 insertions / 94 deletions — cosmetic hero-banner and badge additions only.
  No logic or API change.
- `docs/operations/CONTINUITY_MAP.md`: this update.

### Verified

- `git merge FETCH_HEAD` completed as fast-forward. Working tree clean.
- `release.yml` confirmed correct after edit (all existing steps preserved;
  `environment: release` + token credentials added; confirmed `release`
  environment exists with secret `IAMSOTHIRSTY`.

### Not Verified / Requires User Action

1. ~~**PyPI environment name**~~ — **Resolved.** Auth method is token-based.
   GitHub Actions environment is `release`. PyPI API token is stored as secret
   `IAMSOTHIRSTY` in the `release` environment. Workflow passes `user: __token__`
   and `password: ${{ secrets.IAMSOTHIRSTY }}`.
2. ~~**GitHub environment creation**~~ — **Resolved.** `release` environment
   exists (created 2026-07-29T14:09:14Z).
3. **Re-tag and push**: The v0.8.5 tag already exists on PyPI's side with
   failed publish. To re-publish, the user must either push a new tag (e.g.
   v0.8.5.post1 if PyPI allows it) or delete/re-create the GitHub release and
   retag if the PyPI release slot is still empty. Check PyPI project page first.
4. **Commit and push this fix**: This session's changes are uncommitted.
   The user must commit `.github/workflows/release.yml` and `README.md` and
   push to master (or merge this branch), then tag the next release.

### Recommended Next Steps

1. ~~Verify PyPI trusted publisher environment name~~ — Resolved: token-based auth.
2. ~~Create `IAmSoThirsty` GitHub environment~~ — Resolved: `release` environment exists.
3. Commit: `git add .github/workflows/release.yml README.md docs/operations/CONTINUITY_MAP.md`
4. Push to master and create a new release tag (or re-trigger v0.8.5 if PyPI
   slot is still vacant).

### Open Issues

- PyPI still shows stale metadata for `thirsty-lang`; v0.8.5 never published.
- No packaging validation ran (no dist artifacts in worktree; existing tests
  not re-run since no source code changed).

---

## Baseline

- Starting branch: `master`.
- Starting git state: clean before this work began.
- Baseline continuity document read before edits.
- Existing governance surfaces inspected: parser/checker/interpreter CLI build,
  T.A.R.L. policy/proof/audit APIs, capability broker, Shadow Thirst, docs, and
  threat-model tests.
- Current problems rule applied: discovered issues are either fixed or listed
  under Open Issues instead of dismissed as pre-existing.
- Dirty state rule applied: current modified/untracked files are from this
  workstream.

## Implemented

- `thirsty prove program.thirsty --policy policy.tarl --emit-manifest` emits a
  machine-readable static proof-obligation report without executing program
  side effects.
- Proof-obligation reports include functions, imports, sensitive stdlib calls,
  governed calls, required TARL actions, required capabilities, context schema,
  authority requirements, contract obligations, proof mode, audit requirement,
  build governance-loss status, Shadow status when statically visible,
  diagnostics, and unresolved proof gaps.
- Required TARL actions include capability actions and governed function-call
  actions.
- TARL policy references can derive simple context schema fields. Explicit JSON
  context schemas remain authoritative. Ambiguous or incomplete derived schemas
  fail closed in `thirsty prove`.
- Explicit JSON context schemas accept both list form and mapping form
  (`{"fields": {"name": "kind"}}`) and reject malformed entries with clear
  validation errors.
- Contract obligations preserve string literals in recorded annotations, so
  `requires path != ""` and `ensures result == "ok"` remain faithful in proof
  reports and manifests.
- `thirsty explain-denial program.thirsty --policy policy.tarl` emits a
  machine-readable explanation of missing policy, context, authority, and proof
  conditions.
- Build manifests now record source hash, optional policy hash, required
  capabilities, context schema, authority mode, proof verification mode, audit
  requirement, Shadow status when available, and governance-loss status.
- Checker-level effect warnings are available in prove/strict-style checking
  paths without changing normal checker behavior.
- TARL ordering comparisons compare numeric-looking strings numerically and
  fail closed on unorderable values instead of falling through.
- TARL policy load validates rule expressions; residual runtime evaluation
  errors produce DENY rather than skipping to a later rule.
- `ProofVerifier` and `tarl verify` reject unsigned proofs by default. Unsigned
  proof inspection must opt in explicitly with `require_signature=False` or
  `--allow-unsigned`.
- `tarl eval` refuses temporal policy windows and `CURRENT_*` builtins unless
  `--now` supplies a trusted evaluation time.
- `thirsty govern --auto-tarl` emits rules keyed on `action`, matching the
  governed runtime context.
- Package metadata is bumped to `0.8.2` for a non-colliding patch release tag.

## Files Modified

- `src/utf/thirsty_lang/proof_obligations.py` — proof-obligation model,
  extraction, derived schema, denial explanation, and effect-warning helpers.
- `src/utf/thirsty_lang/cli.py` — `prove`, `explain-denial`, and
  policy/context-aware manifest output.
- `src/utf/thirsty_lang/checker.py` — optional proof-effect warning diagnostics.
- `src/utf/thirsty_lang/parser.py` — preserves string literals when storing
  contract annotation text.
- `tests/test_proof_obligations.py` — minimum proof tests for extraction,
  schema derivation, fail-closed schema behavior, sensitive stdlib obligations,
  build manifest proof metadata, denial explanation, no-side-effect prove
  behavior, explicit schema mapping shape, contract string-literal preservation,
  and replay/audit/proof regression.
- `README.md` — user-facing CLI additions.
- `docs/STATUS.md` — implemented/tested status rows for proof obligations.
- `docs/THREAT_MODEL.md` — C051/C052 challenge rows and current evidence.
- `docs/governance_model.md` — static proof-obligation model and CLI behavior.
- `docs/operations/CONTINUITY_MAP.md` — this continuity update.
- `src/utf/tarl/core.py` — type-safe comparisons, expression validation,
  trusted-time threading, and fail-closed `evaluate_policy`.
- `src/utf/tarl/runtime.py` — fail-closed runtime rule errors and verdict-aware
  proof traces.
- `src/utf/tarl/verifier.py` — secure-by-default signature requirement and
  trace verdict checks.
- `src/utf/tarl/cli.py` — `tarl eval --now` and `tarl verify --allow-unsigned`.
- `src/utf/tarl/spec.py` — proof documentation aligned with secure verifier
  defaults.
- `tests/test_peer_review_0_8_1_tarl_regressions.py` — adversarial regression
  coverage for the five adversarial TARL review findings.
- `pyproject.toml`, `src/utf/thirsty_lang/__init__.py`, `Dockerfile`,
  `docs/WHITEPAPER.md`, `docs/LANGUAGE_SPEC.md`, and `docs/SIGNING.md` —
  0.8.2 release metadata and stale-doc corrections.

## Tested

- `python -m pytest tests/test_cli_build.py::test_build_emit_manifest -q`
  passed: 1 passed.
- `python -m pytest tests/test_proof_obligations.py -q`
  passed: 10 passed.
- `python -m pytest tests/test_cli_build.py tests/test_threat_model_build_outputs.py -q`
  passed: 23 passed.
- `python -m pytest tests/test_thirsty_lang_governance.py tests/test_tarl_proof.py tests/test_threat_model_context_schema.py -q`
  passed: 110 passed.
- `ruff check src tests` passed.
- `mypy -p utf` passed: no issues in 52 source files.
- `python -m pytest tests/ -q --cov=utf --cov-fail-under=90 --basetemp .tmp_pytest\basetemp`
  passed: 1233 passed, 1 skipped, 7 subtests passed, total coverage 90.77%.
- `python -m build --wheel --no-isolation --verbose` passed and built
  the prior patch wheel before the 0.8.2 correction work.
- `python -m build --sdist --no-isolation --verbose` passed and built
  the prior patch sdist before the 0.8.2 correction work.
- `python -m build --verbose` passed and built
  the prior patch sdist and wheel before the 0.8.2 correction work.
- Fresh venv installed the prior patch wheel and verified
  installed `thirsty` CLI support from a `C:\Temp` venv for `prove`,
  `explain-denial`, and `build --emit-manifest --policy --context-schema`,
  including no side effects during prove, explicit schema mapping, preserved
  contract strings, source and policy hashes, and governance-loss status.
- `python -m pytest tests/test_peer_review_0_8_1_tarl_regressions.py tests/test_cli_tarl.py -q`
  passed: 51 passed.
- `ruff check src tests` passed after the 0.8.2 corrections.
- `mypy -p utf` passed after the 0.8.2 corrections: no issues in 52 source
  files.
- `python -m pytest tests/ -q --cov=utf --cov-fail-under=90 --basetemp .tmp_pytest\basetemp`
  passed after the final CLI correction: 1234 passed, 1 skipped, 7 subtests
  passed, total coverage 90.75%.
- `python -m build --verbose` passed and built
  `thirsty_lang-0.8.2.tar.gz` and
  `thirsty_lang-0.8.2-py3-none-any.whl`.
- `python -m twine check dist\thirsty_lang-0.8.2.tar.gz dist\thirsty_lang-0.8.2-py3-none-any.whl`
  passed for both artifacts.
- Fresh venv installed `dist\thirsty_lang-0.8.2-py3-none-any.whl` from
  `C:\Temp\thirsty-0.8.2-smoke-final` and verified imports/version, all console
  script help commands, numeric-string DENY, malformed-policy clean CLI error,
  temporal `--now`, unsigned-proof default rejection plus explicit unsigned
  mode, and auto-TARL `action` generation.

## Not Yet Verified

- None for this workstream's acceptance gates.

## Behavior Contracts

- `thirsty prove` is a static proof-obligation extractor. It reports obligations
  and unresolved gaps before execution. Runtime TARL verdict enforcement, proof
  verification, broker mediation, and audit append behavior remain runtime
  responsibilities.
- Derived context schema is fail-closed by design. Policy expressions that
  cannot be statically resolved produce an incomplete schema and require an
  explicit schema file before `thirsty prove` can claim schema completeness.
- TARL proof verification is secure by default; unsigned proof verification is
  an explicit compatibility/inspection mode.
- Temporal CLI evaluation requires explicit trusted time when policy windows or
  temporal builtins are present.
- Shadow convergence status is reported when it is present in the statically
  extracted source metadata. `thirsty prove` does not run a separate Shadow
  analysis pass.

## Open Issues

- Git commit, GitHub push, and release tag push remain pending for the 0.8.2
  correction work.

## Resolved Validation Notes

- First `python -m build` attempt timed out after 10 minutes. A later exact
  isolated verbose build passed after build dependencies were cached.
- Installed-wheel smoke initially exposed explicit schema mapping handling and
  contract string-literal preservation bugs. Both were fixed and covered by
  regression tests plus fresh installed-wheel smoke verification.
- A venv launcher under the repo `.tmp` path was blocked by Windows Application
  Control. The same built wheel installed into a fresh `C:\Temp` venv ran the
  generated `thirsty.exe` launcher and passed the full proof/build smoke. This
  is resolved for acceptance by verifying the real console launcher from an
  allowed fresh venv path.

## Future Work

- Extend obligation extraction to richer policy expression inference if the
  TARL grammar grows structured schema declarations.
- Promote selected checker effect warnings from diagnostic-only to strict-mode
  errors if a future release defines that compatibility boundary.
- Add richer Shadow Thirst convergence integration when a stable static
  analysis hook is exposed for ordinary `.thirsty` sources.

## Safe to Continue

Yes. Targeted tests, full coverage gate, lint, type check, wheel build, sdist
build, isolated verbose package build, and fresh installed-wheel CLI smoke are
green.
