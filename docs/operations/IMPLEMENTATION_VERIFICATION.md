# Priority corrections and general-purpose foundation: local verification

Date: 2026-09-06. Repository:
`T:\01-Projects\thirsty_lang_exploration_0754`.
Branch: `codex/function-expansion-pack`.
Base and unchanged HEAD: `4e493dde5ba822a4e27ad87b4139f72ff7a443c3`.
Package metadata: `thirsty-lang` 0.8.6; local development changes are uncommitted.

## Scope and result

The user authorized implementation after the read-only investigation and full
baseline suite, then explicitly deferred robotics and swarm features. This
increment implements the priority language/runtime repairs and a usable
general-purpose foundation. It does not complete the remaining language,
compiler, interoperability, or ecosystem milestones in
[DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md). Robotics remains deferred.

**Final integrated result: 1,986 passed, 1 skipped, 22 subtests passed;
91.86% statement coverage.** All 80 discovered test modules are represented in
the JUnit result. Ruff, Black, mypy, dependency consistency, and final diff
whitespace checks pass. Package installation/provenance smoke and deterministic
PDF verification pass within the boundaries described below.

The read-only baseline was 1,497 passed, 1 skipped, 22 subtests passed, with
90.30% coverage. These baseline numbers are historical comparisons, not evidence
for the changed implementation.

## Changes verified

The complete correction register, consequences, and regression paths are in
the development plan. The executable API reference is
[GENERAL_PURPOSE_LANGUAGE.md](../GENERAL_PURPOSE_LANGUAGE.md).

- Interpreter and checker: shared restrictions across imports and closures,
  pure-effect propagation, authority changes during execution, strict parse
  boundaries, explicit unsupported syntax, correct failure propagation, and
  formatter round trips.
- TARL and CLI: authority lifetime/revocation checks and immutable verified
  claim snapshots; binding-change detection; required audit persistence;
  serialized audit-chain writers; restricted delegation; actual source locks;
  explicit key roles and failure exit status.
- Shadow and compilation: scope-aware structural comparison, conditional
  symbolic evidence, bounded scalar sampling, source-bound admission, versioned
  methods, checked JS/LLVM subsets, and browser runtime source binding.
- Standard library and application data: nominal enums, typed structs,
  dictionary literals, collection/tuple/bytes operations, strict serialization,
  real cryptography, SQLite read authorization, bounded network and HTTP/process
  adapters, and a validated synthetic data-report application.
- Documentation and distribution: active contracts reconciled, API HTML
  regenerated, canonical PDF rebuilt, CI test extras expanded to include the
  PDF contract, and the current source built and installed as a wheel.

No source or evidence was imported from another personal project. The existing
repository-local PSIA/governance prototypes were inspected and classified;
they are not shipped in the `utf` language package or used as its authority
dependency. No prototype service was started. Existing historical evidence,
ignored artifacts, and independent acceptance records were preserved.

## Full suite and quality gates

Runtime: Windows, repository `.venv\Scripts\python.exe`, Python 3.11.9.
Imports resolve to this repository's `src\utf` tree for the source suite.
The optional Z3 analysis and PDF dependencies were available, so those test
modules ran. Coverage measured the configured `utf` package; it does not imply
coverage of the excluded prototype services.

Evidence root, relative to the repository:
`.tmp/implementation-20260906-01/`. These local logs are ignored working
artifacts, not committed release evidence.

| Gate | Final result | Evidence under the evidence root |
|---|---|---|
| Full pytest suite | 1,986 passed; 1 skipped; 22 subtests passed; 31.91 seconds | `final-suite/pytest.log`, `final-suite/junit.xml` |
| Discovery coverage | All 80 test modules represented; 1,987 test cases; no failures/errors | `final-suite/junit.xml`, `final-validation.json` |
| Statement coverage | 11,708 / 12,746 statements; 1,038 missing; 91.85626863329672%; required floor 90% | `final-suite/coverage.json`, `final-suite/coverage.xml` |
| Ruff | Pass | `final-suite/ruff.log` |
| Black | Pass; 140 files unchanged | `final-suite/black.log` |
| mypy | Pass; 56 source files | `final-suite/mypy.log` |
| Dependency consistency | No broken requirements | `final-suite/dependencies.log` |
| Diff whitespace | Pass after generated-document whitespace normalization | `final-suite/diff-check-final.log`, `final-suite/quality-results-final.json` |
| CLI examples | All three Tier 1 examples run; Gods example check passes | `examples.json` |
| General-purpose documentation snippets | Both snippets lex, parse, check, and execute in an additional documentation smoke check | `documentation-snippets.json` |
| Installed package | Six tier imports, version, source identity, dictionary/aggregation program, seven registered entrypoints | `package-final-02/package-smoke.log` |
| Installed CLI dispatch | Seven entrypoint callables return success for `--help` | `package-final-02/entrypoint-help.json` |

The sole skip is `tests/test_keystore.py:44`, which requires POSIX file modes.
It is an environment/platform limitation, not a pass. Coverage exclusions were
not weakened: the existing conventional entrypoint/type-checking exclusions
remain in place, with 22 excluded lines in the final coverage result.

The final suite command, run from the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
$env:COVERAGE_FILE = 'T:/01-Projects/thirsty_lang_exploration_0754/.tmp/implementation-20260906-01/final-suite/.coverage'
.venv\Scripts\python.exe -B -X utf8 -m pytest tests -q -ra --cov=utf --cov-report=term-missing --cov-report=xml:.tmp/implementation-20260906-01/final-suite/coverage.xml --cov-report=json:.tmp/implementation-20260906-01/final-suite/coverage.json --cov-fail-under=90 --junitxml=.tmp/implementation-20260906-01/final-suite/junit.xml -p no:cacheprovider --basetemp=.tmp/implementation-20260906-01/final-suite/pytest-work
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m black --check src tests
.venv\Scripts\python.exe -m mypy -p utf
.venv\Scripts\python.exe -m pip check
git diff --check
```

Use a fresh named evidence/basetemp directory for a future run to preserve these
logs. The commands above identify the completed run; they are not a request to
overwrite its artifacts.

## Failed integration and corrected expectations

The first integrated run is preserved in `pytest.log`, `junit.xml`, and
`coverage.json` at the evidence root: 1,980 passed, 3 failed, 1 skipped,
22 subtests passed, and 91.88% coverage. Each failure was diagnosed and fixed:

| Failure | Correction and disposition |
|---|---|
| `TestInterpreter::test_if_stmt` used invalid missing-parentheses syntax that previously executed a recovery AST | Fixed now: valid grammar plus explicit lexer/parser error assertions; malformed AST rejection retained. |
| `TestCrossModeGuard::test_governance_not_swallowed_by_spillage` used an invalid handler form | Fixed now: valid `error` handler and parse assertions; the governance-denial assertion remains intact. |
| Governed build-manifest fixture expected JS to silently accept unsupported imports/contracts | Fixed now: use the supported Pyodide launcher and preserve every manifest assertion; add JS/LLVM refusal tests proving governance-loss disclosure cannot bypass target validation. |

The final full suite followed these corrections and the authority snapshot
regression. Focused test totals are not added to the full-suite total.

Two artifact-tooling failures were also resolved and retained as evidence:

- Initial PDF rendering requested `.tmp/.../pdf-pages`, which the repository
  verifier rejects because renders must live under `tmp/pdfs`. Determinism had
  already passed; rendering was rerun successfully at the permitted path.
- pdoc output contained trailing whitespace. Generated HTML/JS whitespace was
  normalized and `git diff --check` passed. The initial `quality-results.json`
  retains `diff: 2`; `quality-results-final.json` records the completed gate.

## Built wheel and provenance

The ignored helper `package_check.py` made a scoped source snapshot inside this
repository, built a wheel in an isolated build environment, installed it with
`pip --no-deps --target` into a fresh directory, and executed an installed-target
smoke through Python `-I`. Existing build outputs were preserved. The interpreter
and already installed dependencies came from the repository venv: this was not
a wholly dependency-isolated new runtime environment.

Final artifact:
`.tmp/implementation-20260906-01/package-final-02/wheels/thirsty_lang-0.8.6-py3-none-any.whl`

SHA-256:
`6fa351286d428f8250eab8bc05f4b94ae69e6d8cb807f8f3ed8275aa8bde0c94`

The build/install logs and `package-source-sha256.json` are beside the wheel's
parent directory. A final comparison found zero source drift against this
snapshot. Installed runtime source identity:
`sha256-76a4541b79b27162b308ac2ab8c91d369f7adca1641e740724f5f148385dca5b`.

All seven console registrations were loaded from the installed distribution
and their callables executed with `--help`. Native Windows `.exe` launchers were
not exercised in this run. No sdist, remote package, or publication is claimed.
Earlier wheel snapshots remain present but are not the final artifact above.

## Canonical manual and API documentation

Canonical manual: `output/pdf/Thirsty-Lang-UTF-101.pdf`.

- 127 pages: 115 portrait, 12 landscape; 325 outline entries.
- 344,546 extracted text characters; all 127 pages rendered for review.
- Page geometry found no words outside page bounds. Contact sheets covering all
  pages and detailed views of the new plan/API pages were visually inspected;
  no clipping or overlap was observed in that review.
- Source digest:
  `e0ee784dfb94f1949e247da6a4ba130f93893397cc3e5b4c05e36492a1c67166`.
- PDF SHA-256:
  `6c8298b3f2fb0b974e20591bda78aa1c21a69e9753d6050e51224bf1b114f09e`.
- Deterministic rebuild produced the identical PDF hash.

Commands used included `scripts/build_thirsty_lang_utf_101.py` and
`scripts/verify_thirsty_lang_utf_101.py --check-determinism`, followed by
rendering with `--render-dir tmp/pdfs/implementation-20260906-01 --render-dpi 70`.
See `pdf-build.log`, `pdf-verification.log`, `pdf-verification-02.log`, and
`pdf-geometry.json` under the evidence root. This verification report is not a
PDF manifest source; the manual includes the plan/reference while this report
records the resulting artifact identity.

API HTML was regenerated with the declared pdoc 16.0.0 dependency:

```powershell
.venv\Scripts\python.exe -m pdoc utf utf.shadow_thirst.cli utf.shadow_thirst.convergence utf.shadow_thirst.core --output-directory docs/src
```

## Remaining issues and next executable work

| Issue | Classification | Next repair or verification path |
|---|---|---|
| Runtime-wide resource accounting, hostile-code process isolation, path check/open races, subprocess descendants, and HTTP DNS/total-time bounds remain incomplete | Requires separate follow-up work | M4: define cancellation/ownership/budgets; add OS-specific handle-relative file operations and isolated adversarial workloads. Current adapter limits are not whole-runtime containment. |
| Dynamic typing and mutable aliases limit static/pure guarantees | Requires separate follow-up work; not blocking this foundation | M3: specify aliasing and numeric/value semantics; add conformance tests and boundary validation. Typed fields do not intercept every later nested-container mutation. |
| General compiler, TLS/DNS socket API, remote package resolver, and constrained Python interoperability remain incomplete | Requires separate follow-up work | Implement M3-M6 in dependency order; preserve explicit unsupported-operation diagnostics. |
| LLVM native execution was not tested because `llc`, `lli`, and `clang` were unavailable | Environment/dependency issue | Run the emitted supported subset under an installed LLVM toolchain and compare with the interpreter. Node v25.9.0 did execute the JS differential tests locally. |
| Real browser/Pyodide installation was not tested; a matching published/browser-installed runtime was not verified | Requires separate follow-up work | Provide and verify a matching package, then test browser loading and mismatch refusal. Current source fingerprint checks deliberately reject a different runtime; local bootstrap/order/syntax tests passed. |
| POSIX permissions and Python 3.12/Linux CI were not exercised locally | Environment/platform issue | Run the configured CI matrix. The changed workflow itself was not executed remotely in this task. |
| PSIA/governance prototypes contain simulated signatures or automatic/pattern decisions and require undeclared FastAPI/Pydantic/uvicorn | Environment/dependency issue and separate follow-up work | Keep isolated from language authority; before activation, implement authenticated broker integration and real evidence, declare optional dependencies, and add service tests. |
| Independent Competence Register acceptance remains pending | Requires separate follow-up work | Submit current evidence for independent acceptance; historical critical FAIL entries remain unchanged. Local tests do not substitute for that review. |
| TSCG grouping and Shadow method repairs invalidate prior semantic assumptions | Compatibility migration | Rebuild canonical policy artifacts from original source where old canonicalization lost grouping. Verify old Shadow records only as explicitly historical integrity evidence; recertify with current methods for new claims. |

No unclassified full-suite failure remains. These follow-up issues remain open;
they are not dismissed because they existed before this increment. The current
work makes no claim of Python parity, production readiness, universal safety,
independent acceptance, release, deployment, or physical-system assurance.

The final changed-file SHA-256 inventory and machine-readable gate summary are
`changed-files-sha256.json` and `final-validation.json` under the evidence root.
No tracked files were deleted, and no commit, push, or publication was performed.
