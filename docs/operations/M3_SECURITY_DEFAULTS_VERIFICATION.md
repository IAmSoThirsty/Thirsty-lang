# M3.3 governance and security defaults: implementation and verification

Date: 2026-09-08. Repository: `T:\01-Projects\thirsty_lang_exploration_0754`.
Branch: `codex/function-expansion-pack`.
Base HEAD: `b09bbfc3dda4654cca2e9872423460667eed9498`.
Metadata remains 0.9.0; this candidate includes local, uncommitted M3.1-M3.3
work and is not the published PyPI 0.9.0 artifact.

## Scope and status

The user authorized continued general-purpose language work with governance
first and security as default. Thirsty-Lang remains the language name. No
repository rename, foreign-project material, remote publication, workflow
dispatch, or broad GitHub investigation is part of this increment. Robotics
remains deferred. The broader language vision and M3-M7 are still open in
[DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md).

**3,652 passed, 1 skipped, 22 subtests passed; 92.19% statement coverage.**
All 91 discovered test modules are represented, with no failures or errors.
Quality, installed-package, deterministic manual, and visual review checks pass.
This closes the local M3.3 increment; the broader goal remains open.
Prior M3.1/M3.2 records remain
historical; their totals and artifact hashes do not validate this source.

## Corrections and consequences

| Surface | Current behavior and evidence |
|---|---|
| Shared execution posture | Interpreter, CLI, REPL, project scaffolds, checker, proof descriptions, and Gods execution default to governance. Source modes choose semantics and cannot remove the governance floor. Explicit trusted-host opt-out uses `allow_ungoverned=True` or disclosed CLI `--unsafe-core`; declared governed mode and attached runtime restrictions still apply. |
| Retained calls and live authority | Defining and calling restrictions combine across functions, lambdas, morphs, constructors, methods, builtins, stdlib functions, and cascade. Each distinct policy/authority/guard binding authorizes effects and governed function entry. Identical bindings avoid duplicate decisions. All original bindings are rechecked after callback-capable credential validation, closing a reproduced revocation race. |
| File and stdlib imports | Every active caller/definer lock checks imports. Disagreeing verified source strings reject execution; the checked source is parsed without a fresh read. Child source can strengthen semantics and retains live restrictions. File execution bypasses the global cache. |
| Source failure provenance | EOF tokens preserve lexical errors across copied token lists. Unknown modes and malformed source fail through parser, runtime, checker, formatter, and public build routes. Trailing backslash in an unterminated string reports a lexical error. Formatter never writes recovered source as valid code. |
| Stdlib classification | All 99 exports are explicitly reviewed: 43 direct effect exports and 56 without direct ambient effects. Missing, extra, unknown, or noncallable exports reject exposure. Path absolute/relative resolution is a `read`; `assert_raises` cannot swallow a governance denial. Callback and guest-mutation operations remain subject to active frames. |
| Public build boundaries | JS, LLVM, Pyodide, and Gods builds require explicit governance-loss acknowledgment and a mandatory persisted manifest before executable output/toolchain launch. Unsupported-target preflight still fails without artifacts. A disclosure can remain after a later build failure and is not a success receipt. |
| Examples and compatibility tests | Ordinary examples run with limited action/target grants. Core language-only fixtures explicitly select host compatibility semantics. Secure-default negative tests retain denial/no-effect assertions; partial stdlib mocks now use complete export maps. No validation bypass or coverage exclusion was added. |
| Documentation and metadata | Updated current references, generated API pages, source-bound manual, and Docker's stale version label to match package metadata. CI's example loop now supplies a stdout-only policy; equivalent local CLI commands pass. No container build, remote workflow execution, or registry propagation is claimed. |
| PDF running headers | Visual review found that ReportLab multiBuild retained the final section heading into later TOC passes. Reset per-document heading state in the builder; a four-page regression reproduces the failure and verifies the correction without changing page flow. |

## Investigation and validation

Evidence root: `.tmp/security-defaults-20260908-01/`.

- Initial complete diagnostic: 191 failed, 3,339 passed, 1 skipped, 22 subtests
  passed. Failure report and JUnit are preserved in `diagnostic.log` and
  `diagnostic.xml`. Failures were investigated and classified as expected
  default migration, strict export mock migration, or connected corrections.
- Runtime plus import-lock conformance: 585 focused cases passed after the
  credential callback and foreign governed-function policy corrections.
- Five new conformance modules contain 942 cases: `test_security_defaults.py`
  (465), `test_import_lock_callers.py` (120), `test_source_failure_provenance.py`
  (212), `test_stdlib_export_classification.py` (83), and
  `test_governance_entrypoint_defaults.py` (62). One additional locked-resolver
  denial test separates authority from integrity in the existing corpus.
- The first full gate in `final/` passed 3,651 tests before visual review found
  the running-header defect. Its evidence and original PDF QA are preserved.
  After the five-line builder correction and one regression test, the entire
  suite and quality gates were rerun in `final-corrected/`. Shipped package
  inputs remain identical; the manual has a new source/PDF hash.

| Gate | Result | Evidence |
|---|---|---|
| Full suite with optional analysis/docs dependencies | 3,652 passed, 1 skipped, 22 subtests; all 91 modules | `final-corrected/pytest.log`, `final-corrected/junit.xml`, `final-corrected/verification.json` |
| Statement coverage, floor 90% | 12,175 / 13,206 statements, 92.19294260184765%; 1,031 missing; existing 22 excluded lines unchanged | `final-corrected/coverage.json`, `final-corrected/coverage.xml` |
| Ruff and Black | Pass; 151 Python files unchanged by final Black check | `final-corrected/ruff.log`, `final-corrected/black.log` |
| Mypy Windows and Linux targets | Pass, 58 source files each | `final-corrected/mypy-windows.log`, `final-corrected/mypy-linux.log` |
| Installed dependencies and Git diff | Pass | `final-corrected/dependencies.log`, `final-corrected/diff.log` |
| Pre-commit, tracked and newly created files | Pass; initial generated HTML whitespace normalization recorded separately | `precommit-initial.log`, `precommit-final.log`, `precommit-new-files.log` |
| Final PDF builder/test and verification-record hooks | Pass | `precommit-pdf-corrected.log`, `precommit-report-closure.log` |
| Source-bound package and installed smokes | Pass; details below | `package/verification.json`, `package/final-drift-after-docs-freeze.json` |
| PDF validation/deterministic rebuild | Pass, no warnings/errors, all 141 pages rendered | `pdf-verify-corrected.json`, `pdf-verify-corrected.log` |
| PDF visual/geometry review | All 141 pages through five contact sheets; 14 detailed pages; 63,454 word boxes and none outside pages; no remaining observed layout defects | `pdf-geometry-corrected.json`, `tmp/pdfs/security-defaults-20260908-01-corrected/` from repository root |
| Repository isolation | 82 changed paths resolve within this repository; no unexpected cross-project additions found | `isolation-check-corrected.json` |

The sole skip is `tests/test_keystore.py:44`, POSIX file modes on Windows.
Linux-target mypy is static analysis, not Linux runtime verification. The final
pytest run took 53.87 seconds as reported by pytest. All seven sequential
commands in `final-corrected/checks.json` returned exit code zero.

Reproduction commands from this repository root:

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

All 77 package inputs, including README, match the frozen source. All 56 shipped
Python files match source, snapshot, sdist, wheel, and isolated installed target.
Six-tier import provenance and seven installed metadata entrypoint dispatches
pass; native Windows launcher executables were not exercised. The isolated
installed target uses this repository venv's existing dependencies, while the
build uses isolated declared build dependencies. This is not a dependency-free
or clean-machine acceptance claim.

Installed smokes pass 10 security cases, 12 semantic cases with formatting
roundtrips, six rejections, two proof checks, three archive checks, exhaustive
stdlib inventory, and Twine validation. Snapshot inputs were rechecked after
the documentation freeze without drift.

| Local artifact | SHA-256 |
|---|---|
| Wheel, unreleased metadata 0.9.0 | `0a6e6a8a88515861e49a24295356c9d5d25b28954a724d442fb5f543ab6054cb` |
| Sdist, unreleased metadata 0.9.0 | `d2cecc19a8ec379a8188fe8e267128034fb4e08910dabebc2940eb863a328420` |
| Canonical PDF | `9a7258680e80dfffef905ae763389b1b7dea3188ebb8c281dc7eb6efe590cda6` |
| Canonical manual source set | `5bbe1aa26d8c74d84e88978012df344fff8997eaf73493de257feaa36cb154b0` |

Runtime source fingerprint:
`sha256-369f6d9328db9970ac6328dfad5f6f7160c74028765e43d47c91023187e1f66e`.
The manual has 141 pages (128 portrait, 13 landscape), 337 outline entries,
and 405,580 extracted characters. This verification record is linked from
manual inputs but is not itself a manual input, avoiding self-referential hashes.
Corrected contents/first-section headers were checked in detail; all 139
interior body crops match the preserved first render, confirming unchanged
pagination/content layout. Visual review covers thumbnails of every page and
selected full-page detail; it does not establish physical-print, accessibility,
or alternate-viewer acceptance.

## Remaining issues and next executable paths

| Issue | Classification | Next path |
|---|---|---|
| Host-injected foreign callable defining-source identity is not bound to lockfile inventory | Requires separate follow-up work | Add callable/module content provenance and an explicit trusted foreign boundary. Current tests establish subsequent import-lock conjunction only. |
| Multiple policy decisions are independent records; the last proof is not a composite proof of the entire call chain | Requires separate follow-up work | Specify composite decision receipts and replay/verification semantics before claiming one proof certifies every active binding. |
| Host Python embeddings and process resources remain trusted/unbounded in some paths | Requires separate follow-up work | M4 budget/cancellation and isolation work; existing mediation is not an OS sandbox or whole-runtime containment claim. |
| Gradual typing, mutable aliases, callable assignability, loop inference, and several general-purpose facilities remain incomplete | Requires separate follow-up work | Resume M3 semantics and conformance work in the plan before broad syntax or ecosystem claims. |
| Callable parameters use covariant assignment checks; mixed-arity common types inherit the first signature | Requires separate follow-up work; reproduced by read-only next-increment probes | Check parameter contravariance/return covariance and define symmetric, conservative callable joins before exposing function types through loop inference. |
| Loop checker binds an Any loop variable before checking the iterable; dynamic noniterables silently skip at runtime | Requires separate follow-up work; reproduced by read-only next-increment probes | Resolve the iterable in the enclosing scope, infer supported element/key types, and explicitly reject noniterables while preserving evaluation order and per-iteration scope. |
| Filesystem races, package signatures/resolution, complete compiled targets and constrained FFI remain open | Requires separate follow-up work | Follow M4-M6 acceptance gates and independently reproduce supported target behavior. |
| POSIX permission behavior and this increment's Linux runtime are not locally exercised | Environment/platform issue | Run normal Linux CI/release matrix when delivery is authorized; Linux-target mypy is static validation only. |
| A failed late-stage build may leave its disclosure manifest | Documented, not blocking this increment | Treat manifests as disclosures; require a separate artifact success receipt and hash before delivery. |
| Historical constitutional acceptance entries remain open | Requires separate follow-up work | Obtain independent acceptance; local tests do not grant it. |

The implemented default is a necessary language foundation. It does not close
the broader goal, prove Python ecosystem parity, or establish safe robotics.

### Next M3 correction increment

1. Repair callable assignability and common-type calculation in
   `src/utf/thirsty_lang/typesys.py`. `(Int) -> Int` currently substitutes for
   `(Float) -> Int` unsafely; differing arities return the first operand's
   signature. Cover both operand orders, nominal identity, higher-order
   reassignment, and explicitly gradual Any. Update the existing first-signature
   expectation in `tests/test_typesys.py` intentionally.
2. Check each foreach iterable in its enclosing scope before creating the loop
   binding in `checker.py`; infer Reservoir elements, dictionary keys, and
   strings. Current probes accept `refill (missing in missing) {}` and let Int
   elements flow into String declarations without a diagnostic.
3. Replace silent runtime skipping of noniterables in `interpreter.py` with an
   explicit iteration error. Verify single iterable evaluation, loop ordering,
   empty/heterogeneous values, immutable loop bindings, outer-name shadowing,
   callback/nominal collections, and spillage/error propagation. Imported
   tuple/bytes and lambda inference stay gradual until separately specified.

These items are planned follow-up work, not changes included in the passing
M3.3 package or full-suite results above.
