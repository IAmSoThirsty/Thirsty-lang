# M3.4 callable and iteration consistency: implementation and verification

Date: 2026-09-08. Repository: `T:\01-Projects\thirsty_lang_exploration_0754`.
Branch: `codex/function-expansion-pack`.
Base HEAD: `b09bbfc3dda4654cca2e9872423460667eed9498`.
Metadata remains 0.9.0; cumulative M3.1-M3.4 work is local and unreleased.

## Scope and status

Continued the authorized general-purpose language plan with governance first
and security as default. Thirsty-Lang remains the name. No remote publication,
workflow dispatch, or cross-project material is included. Robotics remains
deferred. The broader language vision and M3-M7 remain open.

**4,322 passed, 1 skipped, 22 subtests passed; 92.44% statement coverage.**
All 94 discovered test modules are represented, with no failures or errors in
the final run. Quality gates, installed-package checks, and deterministic
manual verification pass. This closes the local M3.4 increment; the broader
goal remains open. Earlier M3.1-M3.3 records remain historical and do not
validate the changed source.

## Corrections and consequences

| Surface | Current behavior |
|---|---|
| Callable assignment | Function parameters are contravariant and returns covariant. Type-variable descriptor names remain distinct; this does not implement quantified polymorphism. |
| Callable choices | Internal `FunctionUnionType` retains all known signatures through joins and collections, deduplicating exact descriptors with nominal declaration identity. Calls must satisfy every alternative; no overload dispatch or source annotation syntax was added. |
| Calls and pipes | Calls and both pipe families check all known signatures and infer return types. Arguments are checked/evaluated once. Existing noncallable pipe fallback behavior is preserved. |
| For-each checking | Resolve the iterable before introducing the immutable loop variable. Infer Reservoir elements, dictionary keys, and strings; retain callable/nominal descriptors. Known noniterables report E025. |
| Runtime iteration | Native iteration supports the normal iterator and sequence protocols. Dynamic noniterables raise TypeError instead of silently doing nothing. Iteration order, scopes, return/error propagation, and governance denial remain enforced. |
| Runtime arity | Functions, lambdas, morphs, governed functions, bound methods, and fountain initializers require exact positional counts before entry work. No-initializer fountains accept zero arguments; leading receivers are excluded. Caller argument effects still occur before invocation. Struct field-count validation is preserved. |

## Investigation and validation

Evidence root: `.tmp/m3-callables-20260908-01/`.

- New conformance modules: `test_callable_type_conformance.py` (171 cases),
  `test_iteration_conformance.py` (68), and `test_callable_arity.py` (429).
  Two additional type-system cases cover distinct type variables and invalid
  callable-choice descriptors. The total increase over M3.3 is 670 cases.
- Review found a connected pipe regression: a direct struct constructor had
  been classified as noncallable. Direct nominal constructor names now retain
  their result types; known struct arguments are checked. Ambiguous nominal
  aliases and Task/cascade operands remain explicitly gradual. The final
  callable corpus includes 26 regressions for these boundaries.
- The initial full gate in `final/` ran all 94 test modules: 4,321 passed,
  1 failed, 1 skipped, and 22 subtests passed, with 92.33% coverage. The sole
  failure was the concurrent archive test's 60-second Future wait. Its database
  contained 36 committed rows with an intact chain; observed T: disk pressure
  and broad tool delays are recorded in `archive-delay-observation.json`.
  These are timing and scratch-location observations, not proof of the failure's
  cause, a hardware fault, or a repaired service-level guarantee.
- All 27 unchanged archive tests then passed in 1.79 seconds using a fresh,
  project-specific directory under the normal Windows temporary directory,
  which resolves to `T:\Temp` on this host and is on the same volume.
  Source and evidence stayed in this repository. `archive-recheck/` records
  the exact scratch path, command, log, and JUnit. No assertion, test timeout,
  archive timeout, or runtime behavior was weakened.
- A complete rerun uses the same temporary-storage policy in
  `final-windows-temp/`; it passes all 4,322 tests. This suite writes
  generated test fixtures to its own temporary directory outside the repository;
  it does not import another project's material or use a different volume.
- After that suite completed, the unchanged concurrency test also passed in
  fresh repository-local scratch: one test passed in 2.06 seconds. Its JUnit
  case took 1.707 seconds, compared with 115.671 seconds for the original
  failed case and 19.820 seconds in the passing complete rerun. Evidence is in
  `archive-recheck-repo/` and `archive-delay-final-diagnosis.json`. These runs
  establish no persistent deadlock or directory-specific failure; the original
  cause remains unproven and slow-storage availability is not certified.
- First API generation failed opening an existing HTML output with OS error
  22. The file remained readable; regeneration with an absolute output path
  passed. Both logs are preserved. Cause is unproven; no runtime fix is claimed.
- Pre-commit normalized generated HTML whitespace, then passed for all tracked
  files and every new file. The initial hook output is retained separately.

| Gate | Result | Evidence |
|---|---|---|
| Complete final suite | 4,322 passed, 1 skipped, 22 subtests; all 94 modules | `final-windows-temp/pytest.log`, `final-windows-temp/junit.xml`, `final-windows-temp/verification.json` |
| Statement coverage, floor 90% | 12,280 / 13,284 statements, 92.44203553146643%; 1,004 missing; 22 exclusions unchanged | `final-windows-temp/coverage.json`, `final-windows-temp/coverage.xml` |
| Ruff and Black | Pass; 154 Python files unchanged by Black | `final-windows-temp/ruff.log`, `final-windows-temp/black.log` |
| Mypy Windows and Linux | Pass; 58 source files each | `final-windows-temp/mypy-windows.log`, `final-windows-temp/mypy-linux.log` |
| Dependencies and diff | Pass | `final-windows-temp/dependencies.log`, `final-windows-temp/diff.log` |
| Pre-commit, tracked and new files | Pass | `precommit-final.log`, `precommit-new-files.log` |
| Source-bound package and installed smokes | Pass | `package/verification.json` |
| Deterministic manual and structural checks | Pass; 146 pages, no structural warnings/errors | `pdf-verify.json`, `pdf-verify.log` |
| Manual visual and geometry review | All 146 pages through five contact sheets; 13 detailed pages; 66,446 word boxes, none outside pages | `pdf-geometry.json` |
| Final source/artifact drift and isolation | 89 changed paths remain inside this repository; no tracked deletion or rename; package inputs and tested source remain stable | `closure.json`, `post-gate-drift.json` |

The sole skip is the POSIX permission assertion in `tests/test_keystore.py:44`
on Windows. Linux-target mypy does not establish Linux runtime verification.
Existing 22 coverage exclusions remain unchanged.
The final pytest run took 251.94 seconds as reported by pytest. All seven
commands in `final-windows-temp/checks.json` returned exit code zero.

Reproduction from this repository root:

```powershell
.venv\Scripts\python.exe -B -X utf8 -m pytest tests -q -ra --cov=utf --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider
.venv\Scripts\python.exe -B -X utf8 -m ruff check src tests
.venv\Scripts\python.exe -B -X utf8 -m black --check src tests
.venv\Scripts\python.exe -B -X utf8 -m mypy -p utf --platform win32
.venv\Scripts\python.exe -B -X utf8 -m mypy -p utf --platform linux
.venv\Scripts\python.exe -B -X utf8 -m pip check
.venv\Scripts\python.exe -B -X utf8 -m pre_commit run --all-files
.venv\Scripts\python.exe -B -X utf8 scripts/verify_thirsty_lang_utf_101.py --check-determinism
git diff --check
```

## Artifact identity

All 77 snapshot inputs match current source, including README. All 56 shipped
Python files match source, snapshot, sdist, wheel, and the isolated installed
target. The existing package selection excludes 13 snapshot inputs (examples,
`src/__init__.py`, and `src/psia`); the manifest records them explicitly.
The PEP 561 marker, six-tier installed imports, seven metadata entrypoint help
dispatches, and Twine checks pass. Native Windows launchers were not exercised.
Build dependencies were isolated; runtime smokes use the repository venv's
dependencies with an isolated installed import target, not a clean machine.

Installed checks preserve 10 security cases, 12 semantic cases with formatting
roundtrips, six rejections, two proof checks, three archive checks, and the
complete stdlib classification. M3.4 adds 39 callable, 13 iteration, and 56
runtime arity cases. One initial smoke fixture omitted the exact resolved
file-import grant and was correctly denied. Failed evidence remains preserved;
the corrected helper adds that exact grant and passes against the same artifacts.

| Local artifact | SHA-256 |
|---|---|
| Wheel, unreleased metadata 0.9.0 | `4f67f742ac0febb5c9f368ce3f03bf7f336e90ce3ca1407163cd90a08e2eaca7` |
| Sdist, unreleased metadata 0.9.0 | `bd915dd65d0070972472473d6bdac00b16efb6b6c3ca144c97a5f0718a6377e4` |
| Canonical PDF | `79ace2fcca94c67d36ec4ab0db55a7ef451865d68f4003d8143452d76476cfa5` |
| Canonical manual source set | `c76707408b4c39e90e5c174eb2a16e51d609eb11d6c65433417c941a1a4822de` |

Runtime source fingerprint:
`sha256-51053cec0cd04175d59d7f6c434ba830d9ffdcf1766436d8106cb18793c8f471`.
The manual has 146 pages (132 portrait, 14 landscape), 341 outlines, and 427,516
extracted characters. This record is linked by manual inputs but is not itself
an input, preventing self-referential hashes.

## Remaining issues and next executable paths

| Issue | Classification | Next path |
|---|---|---|
| Any, lambda/import inference, heterogeneous noncallable joins, mutable container aliases, and some constructor typing remain gradual | Requires separate follow-up work | Continue M3 with explicit mutable-container and callable/constructor contracts plus conformance evidence. Do not claim whole-language soundness. |
| Nominal descriptors conflate constructors and instances; ambiguous pipe aliases remain Any | Requires separate follow-up work | Introduce a distinct constructor value descriptor and migrate resolution, aliases, calls, members, and new expressions together. Direct declaration names are recognized by the current pipe correction. |
| Cascade is typed as Task even though runtime waits and returns the call's value | Requires separate follow-up work | Align awaited-value inference with actual cascade semantics and add nested call/return/collection conformance. Pipes keep these uncertain operands Any until that correction. |
| A contracted method with an explicit self receiver can fail TARL context preparation because FountainInstance is not an admitted context value | Requires separate follow-up work; fail-closed and not blocking this increment | Specify a bounded canonical receiver projection and test policy field access, alias mutation, and replay before admitting instance data. Do not bypass context validation or silently drop self. |
| Foreign callable defining-source identity and composite decision receipts remain incomplete | Requires separate follow-up work | Bind source identity and specify replayable receipts for all active policy bindings. M3.3 governance conjunction remains enforced. |
| Runtime resources, filesystem races, package signatures/resolution, compiled targets, and constrained FFI remain open | Requires separate follow-up work | Continue M4-M6 acceptance gates; current host embeddings are trusted and do not provide OS isolation. |
| Linux runtime and POSIX permission acceptance are not exercised on this Windows host | Environment/platform issue | Run the Linux CI/release matrix when delivery is authorized. Linux-target mypy is static checking only. |
| Concurrent archive validation exceeded its wait under observed T: I/O pressure; unchanged reruns pass in both scratch locations on T: | Timing/environment observation; original cause unproven, not a repaired latency guarantee | Keep failed and passing evidence. Separately characterize archive service latency and resource budgets under slow storage; no persistent directory failure was established. |
| Some PDF section-start running headers retain the preceding heading; landscape footers use portrait-width alignment; one milestone heading precedes its table on the next page | Not blocking this increment; cosmetic follow-up | Review page-header timing and landscape page templates with focused layout regressions. Current reviewed text and tables remain legible. |
| Python ecosystem parity, independent acceptance, and robotics safety are not established | Requires separate follow-up work | Complete the development plan and independent acceptance; robotics stays deferred. |

This increment advances the language foundation and does not close the broader
goal or establish production/robotics readiness.

### Reproduced method receiver limitation

With an attached `when true => ALLOW` TARL policy and an authority, this parsed
program reaches exact-arity validation successfully but fails context admission:

```thirsty
fountain Box {
    glass take(self, value) requires true { return value }
}
drink box = new Box()
box.take(7)
```

The current result is `GovernanceViolation` with a DENY proof and reason
`context representation violation: field 'self' has unsupported type FountainInstance`.
The exact executable reproducer and output are preserved in
`receiver-context-repro.py` and `receiver-context-repro.log` under the evidence root.
This is an availability/representation gap, not a reason to weaken policy context
validation. Arity tests isolate method contracts using explicit host compatibility
while retaining negative arity, contract, default, and body-effect assertions.

### Next bounded M3 correction

1. Separate nominal constructor values from nominal instances in the checker.
   Inspect declaration resolution, annotations, aliases, collections, calls,
   member access, `new`, and both pipe families together. Preserve runtime
   interfaces and declaration identity; cover shadowing and mixed choices.
2. Align cascade inference with the runtime's awaited result. Cover direct
   calls, nested callbacks, collections, assignment, returns, and diagnostics;
   do not introduce unimplemented asynchronous scheduling semantics.
3. Specify the method/record governance context boundary before admitting
   runtime instances. The proposal must define supported projections, nominal
   identity, mutation timing, recursion/resource bounds, and reproducible proof
   context. Keep unsupported values fail-closed until that contract is tested.
4. Run focused conformance first and the complete release-equivalent checks
   before closing the next increment. Preserve this record as historical
   evidence after source changes; no robotics or publication is implied.
