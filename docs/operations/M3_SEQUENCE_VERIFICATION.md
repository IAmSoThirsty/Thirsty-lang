# M3.1 sequence semantics: implementation and verification

Date: 2026-09-06. Repository:
`T:\01-Projects\thirsty_lang_exploration_0754`.
Branch: `codex/function-expansion-pack`.
Base and unchanged HEAD: `b09bbfc3dda4654cca2e9872423460667eed9498`.
Package metadata remains 0.9.0. These changes are local, uncommitted, and
unreleased; the candidate artifacts below are not the published PyPI 0.9.0
artifacts. No new dependency was added.

## Result and scope

**2,255 passed, 1 skipped, 22 subtests passed; 91.98% statement coverage.**
All 83 discovered test modules are represented in the final JUnit report.
There are no test failures or errors. Optional Z3 and documentation dependencies
were available, so their tests ran. This completes the M3.1 sequence increment;
the broader M3 milestone and subsequent general-purpose milestones remain open
in [DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md). Robotics remains deferred.

The user directed continued work from the plan after the completed 0.9.0
release and said broad GitHub verification was unnecessary. This increment
used the current checkout and its local release receipt. It made no remote
repository, workflow, tag, publication, or merge changes. No other personal
project supplied code, dependencies, or evidence.

## Changes and consequences verified

| Surface | Implemented behavior and regression evidence |
|---|---|
| `ast.py`, `parser.py` | Slice AST with receiver/start/stop/step; omitted bounds, chaining, precedence, malformed-input refusal, closing-bracket spans, and actual unary-operator spans. Slice assignment marks source parsing as failed. |
| `sequences.py`, `interpreter.py` | Exact native list/string/tuple/bytes indexing and slicing; negative and huge integer handling; non-Boolean Int indices; immutable assignment refusal; dictionary key behavior preserved. Receiver and bounds execute once in order; exceptions/denials stop later operands. Slice assignment is refused before operand effects even through a supplied AST. |
| `checker.py` | Preserve known string/list result types; validate known index and bound types; check annotated literals through slices conservatively; infer division as Float and logical operators from their operands; accept mixed Int/Float arithmetic and comparison in either order. Dynamic Any remains a boundary. |
| `formatter.py` | Slice formatting and parser round trips; semicolons keep following array, parenthesized, or negative expressions from merging into the prior statement. |
| Shadow and compiler gates | JS/LLVM reject unsupported slices before creating artifacts; Pyodide retains exact source/runtime binding. Structural and effect traversals retain every slice operand; unsupported semantic analysis abstains. Unknown AST subclasses cannot inherit modeled behavior silently. |
| Stored proof compatibility | Shadow engine 0.3.0 and convergence methods v3 replace 0.2.0/v2 as current assurance. Old records require reanalysis; explicit historical verification checks integrity only and does not replay the analysis. |
| Documentation | Plan, general-purpose reference, grammar, specification, feature reference, continuity map, generated API HTML, and source-bound manual reflect this unreleased increment. |

The three new test modules contain 269 cases: 41 sequence-helper tests,
179 language conformance tests, and 49 compiler/proof boundary tests.
The helper corpus includes 19,600 bounded slice comparisons, 588 index cases,
and 147 list-assignment cases. These inner corpus comparisons are not counted
as additional pytest test cases. The existing PDF subtitle contract was updated
to distinguish the unreleased sequence increment on the manual cover.

The first integrated run found one downstream failure: accurate Float division
inference made `24 / (6 / 2)` fail the asymmetric numeric checker. The checker
was corrected and both operand orders gained regression coverage. Formatter
statement merging, unary spans, and stale proof method identity were also fixed
within this increment. No test was disabled or relaxed to recover a pass.

## Validation commands and evidence

Runtime: repository `.venv\Scripts\python.exe`, Python 3.11.9 on Windows.
The source suite imports this checkout. Evidence root:
`.tmp/m3-sequences-20260906-01/`. These logs and candidate build products are
ignored local evidence, not published release artifacts.

| Gate | Result | Evidence relative to the evidence root |
|---|---|---|
| Full pytest suite | 2,255 passed; 1 skipped; 22 subtests passed; 48.49 seconds | `final/pytest.log`, `final/junit.xml` |
| Discovery | 2,256 cases from all 83 test modules; zero failures/errors | `final/verification.json` |
| Coverage | 11,837 / 12,869 statements; 1,032 missing; 91.98072888336313%; required floor 90% | `final/coverage.json`, `final/coverage.xml` |
| Ruff and Black | Pass; Black reports 142 source/test files unchanged | `final/ruff.log`, `final/black.log` |
| mypy Windows and Linux target checks | Both pass; 57 source files | `final/mypy-windows.log`, `final/mypy-linux.log` |
| Dependency consistency and diff whitespace | Pass | `final/dependencies.log`, `final/diff.log` |
| Pre-commit | All applicable hooks pass after generated HTML whitespace and PDF test formatting; new untracked files checked explicitly too | Tool execution record; repeated in final closure |
| Package and installation | Both build formats, Twine, byte identity, isolated import provenance, and six language/formatter smokes pass | `package/verification.json`, `package/commands.json`, `package/installed-smoke.json` |
| Manual | Deterministic build, all 132 pages rendered, contact-sheet review plus detailed changed pages; no out-of-page words | `pdf-geometry.json`; renders in `tmp/pdfs/m3-sequences-20260906-01/` |

The only test skip is `tests/test_keystore.py:44`, POSIX file modes on Windows.
It is an environment/platform limitation, not a pass. Linux-target mypy is a
static check, not a Linux runtime run. The 0.9.0 Linux release matrix is older
evidence and does not establish Linux execution of M3.1. Coverage retains its
existing exclusions (22 excluded lines); no validation bypass was added.

Representative reproduction commands from the repository root:

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

Exact commands, output paths, exit codes, and elapsed times for the measured
suite and quality checks are in `final/checks.json`. Build/install commands
are in `package/commands.json`. The installed candidate uses its own target
directory; no released installation was replaced.

## Artifact identity

All 55 shipped Python files match across the current source, 76-file build
snapshot, wheel, sdist, and installed copy, including `sequences.py`. All six
tier imports resolve exclusively to the installed candidate; its seven console
entrypoints are present. Six installed language cases and six formatter round
trips cover typed lists, Unicode, bytes, tuples, nested indexing, and division.

| Local candidate artifact | SHA-256 |
|---|---|
| Wheel, metadata 0.9.0, unreleased | `36dfa6bcd4daead25435bbdf58795b8a1534a0d8c839a5584d3a4d860e4d5a1c` |
| Source distribution, metadata 0.9.0, unreleased | `44d1531eb0852d8ccb18bf09db187fe93cba44eea2e8114365b77f42209178bd` |
| Canonical PDF | `3e3612983cbdf40f22757792f2f663aaed32550190c1245c4152c3c45851c527` |
| Canonical manual source set | `f90f5547b18bf16536bcb4cb8122097cbcfb7943f0d2d8d1805e47741c817b1a` |

Candidate runtime fingerprint:
`sha256-be10e2375d330093e6eb6380cbafc9684a176cb7b062eb8e1b49177cee87a4c7`.
The manual has 132 pages (120 portrait, 12 landscape) and 329 outline entries.
This verification note is linked from the manual's sources but is not itself
an input to the manual, avoiding a self-referential artifact hash.

## Remaining issues and next increment

| Issue | Classification | Next executable path |
|---|---|---|
| Runtime Boolean arithmetic lacks a complete consistent numeric contract | Requires separate follow-up work | Specify rejection versus explicit conversion; align runtime/checker/backend tests for arithmetic, unary operations, comparisons, and errors. |
| Nominal types within generic arguments can resolve to Any | Requires separate follow-up work | Preserve enum/struct identity recursively through annotation resolution; test declarations, calls, returns, and nested containers. |
| Dictionary key annotations are not enforced for indexed reads/writes | Requires separate follow-up work | Check known key types while retaining documented hash/equality behavior; define validation at dynamic boundaries. |
| Tuple/bytes imports remain statically Any; alias mutation and broad resource limits remain incomplete | Requires separate follow-up work | Continue M3 typing/ownership and M4 accounting; retain runtime sequence checks and explicit embedding boundaries. |
| Slice assignment and JS/LLVM slice execution are unsupported | Explicitly isolated; not blocking M3.1 | Keep current refusal until specified semantics and backend conformance tests are delivered. |
| POSIX enforcement is not executable in this Windows run | Environment/platform issue | Run the later candidate's suite on Linux through its normal CI/release path; do not reuse 0.9.0 runtime results. |

The next M3 increment should close these type-coherence gaps before adding
iterators, comprehensions, or default/named arguments. No robotics or swarm
feature was implemented.
