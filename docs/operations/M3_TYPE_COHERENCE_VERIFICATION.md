# M3.2 Boolean and type coherence: implementation and verification

Completed: 2026-09-08. Work and evidence began 2026-09-06/07.
Repository: `T:\01-Projects\thirsty_lang_exploration_0754`.
Branch: `codex/function-expansion-pack`.
Unchanged HEAD: `b09bbfc3dda4654cca2e9872423460667eed9498`.
Package metadata remains 0.9.0. M3.1 and M3.2 are local, uncommitted, and
unreleased. Candidate artifacts are not the published PyPI 0.9.0 artifacts.

## Result and scope

**2,708 passed, 1 skipped, 22 subtests passed;
92.14% statement coverage.** All 86 discovered test
modules are represented in the final JUnit report, with zero failures/errors.
Optional Z3 and documentation dependencies were available and their tests ran.
This closes M3.2's local implementation and validation increment. The broader
M3 and general-purpose language milestones remain open in
[DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md). Robotics remains deferred.

The user authorized continued priority/general-purpose work after 0.9.0 and
said broad GitHub verification was unnecessary. This increment made no remote
repository, workflow, tag, publication, or merge changes. No rename was needed.
Existing M3.1 edits and its historical verification record were preserved.
No other personal project supplied code, dependencies, or evidence. Existing
declared build dependencies were used; no project dependency was added.

## Corrections and consequences

| Surface | Implemented behavior and regression evidence |
|---|---|
| `thirsty_lang/interpreter.py`, `checker.py`, `cli.py` | Scalar Bool arithmetic, ordering, negation, and Bool/non-Bool equality reject invalid operands. Bool/Bool equality and logical truthiness remain supported. Reference execution, JS, LLVM refusal, callbacks, imports, cascades, and optimization levels have regression coverage. Operand effects execute once in source order. |
| `thirsty_lang/typesys.py`, `checker.py`, `interpreter.py` | Resolve nominal names recursively through generic arguments, preserving per-declaration identity, recursive struct placeholders, aliases, and deliberate primitive-name shadowing. Every generic descriptor checks all arguments and arity. Malformed/excess annotation arguments are diagnosed. |
| `thirsty_lang/checker.py` | Prepare nominal descriptors before top-level function signatures; resolve the whole signature in declaration scope before parameter bindings. Preserve duplicate callable/type diagnostics in both source orders. Check known dictionary index key types on reads/writes and retain annotations on uninitialized bindings. Standalone cascade operands now receive checking. |
| `thirsty_lang/parser.py` | Malformed struct/interface members always advance or finish, preventing repeated diagnostics on one token. Bounded CLI subprocess regressions verify refusal without executing source. |
| `shadow_thirst/convergence.py`, `admission.py` | Distinguish Boolean and numeric symbolic result sorts. `return true` versus `return 1` no longer receives an equivalence proof. Current admission engine is 0.4.0 with v4 convergence methods. Older records require reanalysis; explicit historical verification checks integrity only. |
| `tarl/archive.py`, `test_audit_requirements.py` | Add keyword-only `lock_timeout_seconds`, retaining the existing 5-second default. Exact Int/Float values from 0 through 300 seconds are accepted; Bool, nonfinite/out-of-range values, and other types fail before database creation. This configures SQLite lock waiting, not an overall transaction or runtime deadline. No write retry or transaction weakening was introduced. |
| Documentation and artifacts | Update the plan, general-purpose reference, grammar, specification, features, continuity record, generated API pages, and source-bound manual. Keep released 0.9.0 and historical M3.1 results distinct from the current increment. |

The three M3.2 language regression modules contain 430 cases: 190 backend/proof
cases, 67 nominal type cases, and 173 checker/runtime cases. Additional audit
timeout tests cover configuration and held-lock denial/recovery. Existing
compiler expectations and the manual subtitle assertion were updated to match
the intentional contracts; no test was disabled or coverage exclusion added.

The scalar Bool contract deliberately retains native nested-container
comparison and dictionary hashing/equality, including `true`/`1` key collisions.
Known dictionary key annotations reject mismatches; dynamic Any remains an
execution boundary. Runtime declaration order, Core initialization to none,
and gradual variable/function annotations retain their documented behavior.

## Failures investigated before final closure

Both earlier full-run logs remain intact in the evidence directory:

1. `final/`: 2,684 passed, one failed, one skipped, 22 subtests. Concurrent
   archive writers exceeded SQLite's default five-second lock wait. An unchanged
   focused rerun passed four tests, but the failure recurred in the full suite.
2. `final-isolated/`: 2,683 passed, two failed, one skipped, 22 subtests. The
   archive failure recurred without competing artifact jobs. A process overflow
   fixture also reached its two-second startup deadline before producing output.

These were addressed explicitly. The archive now exposes the bounded lock wait
above; the concurrency fixture selects 30 seconds and retains four writers,
48 unique record IDs, the exact record count, and an intact chain assertion.
Its future wait is 60 seconds. Deterministic external writer locks with zero
wait verify direct-store failure, required-audit DENY without insertion, and
successful recovery after lock release. Deployments can still time out when
their configured wait is exhausted; required audit remains fail closed.

The process fixture uses ten seconds for its output/empty-output paths while
retaining the separate 50 ms timeout assertion, 32-byte overflow threshold,
zero-byte empty-output threshold, expected exceptions, and child reaping checks.
Production process deadlines were unchanged. Its focused module passed all 15
tests before final integration. These repairs classify the discovered issues
as fixed test/configuration boundaries, not proof of unbounded availability.

## Validation commands and evidence

Runtime: repository `.venv\Scripts\python.exe`, Python 3.11.9 on Windows.
Imports resolve to this checkout. Evidence root:
`.tmp/m3-types-20260907-01/`. Logs and candidate products are ignored local
evidence; historical failed runs and the earlier package snapshot are preserved.

| Gate | Result | Evidence relative to the evidence root |
|---|---|---|
| Full pytest suite | 2,708 passed; one skipped; 22 subtests passed | `final-corrected/pytest.log`, `final-corrected/junit.xml` |
| Discovery | 2,709 cases across all 86 test modules; no missing modules | `final-corrected/verification.json` |
| Coverage | 11,957 / 12,977 statements; 1,020 missing; 92.13993989365801%; floor 90% | `final-corrected/coverage.json`, `final-corrected/coverage.xml` |
| Ruff and Black | Pass; 145 source/test files checked by Black | `final-corrected/ruff.log`, `final-corrected/black.log` |
| mypy Windows and Linux targets | Both pass; 57 source files | `final-corrected/mypy-windows.log`, `final-corrected/mypy-linux.log` |
| Dependencies and diff whitespace | Pass | `final-corrected/dependencies.log`, `final-corrected/diff.log` |
| Pre-commit | Applicable hooks pass, including explicit checks of untracked new files | Final closure tool record and local logs |
| Candidate packaging | Build, Twine, byte identity, installed imports, language/proof/archive smokes pass | `package-audit-repair/verification.json`, `commands.json`, `installed-smoke.json` in that directory |
| Manual | Deterministic rebuild; 134 pages rendered and reviewed via contact sheets and selected detailed pages; no out-of-page words | `pdf-geometry.json`; renders in `tmp/pdfs/m3-types-20260907-01/` |

The sole skip is `tests/test_keystore.py:44`, POSIX file modes on Windows.
It is an environment/platform limitation, not a pass. Linux-target mypy is
static validation, not Linux execution. The older 0.9.0 release matrix cannot
establish Linux runtime validation for these edits. The existing 22 excluded
coverage lines remain unchanged.

Reproduction commands from the repository root:

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

Exact suite/check commands, exit codes, and times are in
`final-corrected/checks.json`; package commands are recorded separately.

## Artifact identity

All 55 shipped Python files match the source, 76-file build snapshot, sdist,
wheel, and installed candidate. Six-tier imports resolve to that isolated
target. The installed smokes use the repository venv's existing dependencies;
they are not a dependency-free environment. Seven installed entrypoint metadata
callables dispatch successfully; native Windows launchers were not exercised.

| Local artifact | SHA-256 |
|---|---|
| Wheel, metadata 0.9.0, unreleased | `22114c58c7e5c8ca430a2e5bae3e25d6a361ce1d7ed9b867274b16f0116d3029` |
| Source distribution, metadata 0.9.0, unreleased | `de439dee34f9794e7e7221b33d05be057bada42065650ef38100d95c3258b0c9` |
| Canonical PDF | `52636044fae7549dc9f83f94f27c4e950260d0d67898bf7a6b0b92505496003c` |
| Canonical manual source set | `83ae4f81c8a944bbf1285707f1fe1dd80d5e00dffc8b4894b81b572c207fcf0f` |

Current candidate runtime fingerprint:
`sha256-8e0110b96ed7648419cf2893fe275b0788a2ca41c3db4ba493298b779bd87b77`.
The manual contains 134 pages (122 portrait, 12 landscape), 333 outline entries,
and 374,973 extracted characters. Its September 7 source set remains current;
the final archive API is documented in its generated API page and this record.
This record is linked from the manual's sources but is not a manual input,
avoiding a self-referential artifact hash.

## Remaining issues and next increment

| Issue | Classification | Next executable path |
|---|---|---|
| Loop elements and imported tuple/bytes values remain statically Any | Requires separate follow-up work | Infer known iterable element/key types and preserve nested nominal identity; test body operations and dynamic fallbacks. |
| Unknown annotation names fall back to Any; omitted generic arguments use compatibility defaults | Requires separate follow-up work | Specify unresolved-name diagnostics and forward/dynamic import behavior before tightening compatibility. |
| Function parameter variance and arity-mismatch unification remain incomplete | Requires separate follow-up work | Specify callable assignability/common-type rules and test higher-order callbacks. |
| Alias mutation can bypass annotations; uninitialized Core bindings begin as none | Requires separate follow-up work | Define mutation validation/ownership and definite-assignment analysis across branches, loops, closures, and callbacks. |
| SQLite contention can exhaust any configured lock wait | Documented runtime limit; not blocking this increment | Choose the explicit per-connection wait for the application and handle required-audit DENY; broader cancellation and accounting belong to M4. |
| Whole-runtime resource budgets, filesystem races, complete backends and FFI/ecosystem support remain incomplete | Requires separate follow-up work | Follow the M3-M6 dependency order and existing correction register; no sandbox, Python parity, or whole-program soundness claim. |
| Slice assignment and JS/LLVM slices remain unsupported | Explicitly isolated; not blocking M3.2 | Retain refusal until specified semantics and conformance tests exist. |
| POSIX permissions and this increment's Linux runtime were not exercised | Environment/platform issue | Run the final candidate through the normal Linux CI/release matrix when delivery is authorized. |

The next increment should address loop inference and callable type consistency
before broader syntax expansion. No robotics or swarm feature was implemented.
