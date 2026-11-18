# M4.1 execution control verification

Date: 2026-09-13. Workspace: `thirsty_lang_exploration_0754`.
Base commit: `e888a847b079048ba29b78a39b8e5ddfebed86ce` on
`codex/function-expansion-pack`. Package metadata remains 0.9.0; this candidate
is unreleased and is not the published 0.9.0 artifact.

## Integration status

The local M4.1 execution-control increment passed the full suite, quality,
package/install, and manual verification described below. The working changes
are uncommitted and unreleased. M3.5 remains committed and pushed as the base
above; the live GitHub branch was checked at that exact commit with zero ahead
and zero behind. This record does not claim publication of M4.1.

Evidence is collected under `.tmp/m4-execution-20260913-01/` without replacing
the prior M3.1-M3.5 records. The final gate, input hashes, and evidence hashes
are retained in that directory's `closure.json`.

## Implemented scope

- Exclusive logical execution across the interpreter, captured caller/definer
  domains, and file-import graph; owned cascade thread handoff and nested work
  on the active worker.
- Finite cooperative step, deadline, and call-depth limits; inherited tighter
  limits account for already spent work and remain active until outer return.
- Latched cancellation, guest catch/finalizer refusal after a stop, interrupted
  waiter ownership retention, and idle scheduler close.
- Lexical defining scope for governed functions, morphs, and fountain methods,
  including contract predicates and receiver binding.
- CLI-created resource cleanup on setup/runtime exits; finite host flags;
  REPL execution of each submission once with persistent static context and
  explicit `.clear` recovery after runtime failure.

The detailed contract is [EXECUTION_CONTROL.md](../EXECUTION_CONTROL.md).

## Findings and disposition

| Finding | Classification and repair |
| --- | --- |
| Concurrent escaped calls returned the other call's argument, raised NameError, and left the active environment unrestored | Fixed now: domain claim before callable binding or interpret mode changes; competing calls fail immediately. |
| Five outstanding awaited cascades deadlocked a four-worker pool | Fixed now: explicit initial transfer, nested work on the active worker; bounded depth controls and original-handle interruption tests. |
| Caller shadows changed governed preconditions/postconditions and method lookup | Fixed now: captured defining scopes across native callable forms; 55 lexical conformance cases. |
| Successful REPL input replayed earlier effects; clearing only the source buffer erased static context | Fixed now: check-only declaration history, execute new AST once, persistent module header, `.clear` recovery after partial runtime failure. |
| Initial builtin ownership wrappers lost capture of pure/governed lookup restrictions | Fixed now: retain registered builtin identity and bind lookup restrictions; original security regressions pass without weakening expectations. |
| Cancelled input could write a guest binding before the enclosing statement noticed the stop | Fixed now: foreign-call postcheck before assignment; cancellation in lock verification also prevents module resolution. |
| The expanded manual orphaned a code-language label at the bottom of page 160 | Fixed now: keep labels with the first code segment while retaining multi-page splitting; both boundary regressions failed before the repair and passed afterward. |
| First full integration run retained a test assertion for the old M3.5-only manual subtitle | Fixed now: update the assertion to the intentional M4.1 subtitle and require the execution-control document in the manual manifest; the complete suite passed afterward. |
| Verification wrapper could not print Black's Unicode output through the default Windows encoding | Environment/tooling issue, fixed for this run: invoke the helper with `-X utf8`; preserve the failed wrapper and subsequent complete results. |
| Generated API HTML contained trailing whitespace and missing final newlines | Fixed now: apply the configured pre-commit normalization to generated output and recheck the changed paths. |
| Writable `Reservoir[Int]` and `Dict[String, Int]` values can be widened to Float containers, mutated through aliases, and read back as Int | Requires separate follow-up work: concrete mutable-container invariance with contextual literal construction, followed by shared runtime mutation constraints and typed dynamic boundaries. Reproduced without Any; this is not repaired by M4.1. |
| Arbitrary host threads can start separate interpreter budgets | Requires separate follow-up work: supported foreign execution bridge and descendant quotas. Ordinary TARL sources resolve synchronously and retain the current run; this is not a host sandbox. |
| Frontend work, individual allocations, output, blocking adapters, and process descendants lack whole-runtime containment | Requires separate follow-up work: M4 allocation/frontend quotas, adapter cancellation, process-isolated execution and OS-specific tests. |
| Direct host source-module cache has no explicit lifetime handle; TARL shutdown does not await all workers | Requires separate follow-up work: owned loader/cache lifecycle and policy-worker teardown contract with escaped-value tests. Interpreter close owns its file-import scheduler only. |

## Final verification

All commands use the repository's `.venv/Scripts/python.exe`, Python 3.11.9,
with imports resolved to this checkout. Evidence paths below are relative to
`.tmp/m4-execution-20260913-01/`.

| Gate | Verified result | Evidence |
| --- | --- | --- |
| Complete `tests` suite | 5,084 passed, 1 skipped, 22 subtests passed; 103 discovered modules represented, no missing modules, no failures or errors | `final-pdf-corrected/verification.json`, `junit.xml`, `pytest.log` |
| Coverage, minimum 90% | 92.96395290038286%; 12,869 of 13,843 statements covered | `final-pdf-corrected/coverage.json`, `coverage.xml` |
| Ruff and Black | Passed over `src` and `tests`; Black checked 164 files | `final-pdf-corrected/checks.json` and individual logs |
| mypy | Passed for both Windows and Linux platform settings; 59 source files each | `final-pdf-corrected/mypy-windows.log`, `mypy-linux.log` |
| Dependency consistency | `pip check` passed | `final-pdf-corrected/dependencies.log` |
| Package build, Twine, isolated import/install checks | Passed; all 78 package inputs matched the snapshot; all 57 shipped Python files matched source, snapshot, sdist, wheel, and installed target | `package/verification.json` and identity manifests |
| Installed execution control | 19 M4.1 cases passed, including bounded cascade subprocesses, limit composition, cancellation, closed calls, lexical denial, CLI limits, and REPL effects once | `package/installed-smoke.json` |
| Retained installed behavior | 33 M3.5 value, 10 security, 39 callable, 13 iteration, 56 arity, 12 semantic/format, 6 rejection, 2 proof, and 3 archive cases passed; six-tier provenance and seven entrypoint dispatches passed | `package/verification.json` |
| Standard-library classification | 16 namespaces, 43 effect exports, 56 exports without ambient authority checked | `package/verification.json` |
| Manual structure and reproducibility | 169 pages (153 portrait, 16 landscape), 375 outline entries, deterministic rebuild, all pages rendered; no structural errors or warnings | `pdf-corrected/pdf-verify.json` |
| Manual geometry | 79,316 word boxes checked; none outside page bounds at 0.5-point tolerance | `pdf-corrected/pdf-geometry.json` |
| Actual visual inspection | All 169 pages inspected at contact-sheet scale; detail pages 1, 6, 7, 83-88, 149, 150, 159-161, and 169 inspected; no remaining observed layout defect in that scope | `pdf-corrected/review-first.json`, `review-middle.json`, `review-last.json` |

The single skip is `tests.test_keystore.test_private_key_file_is_0600`, which
requires POSIX file modes. Linux mypy is a static platform check, not a Linux
runtime execution. The full suite contains 216 additional passing test cases
relative to M3.5: 214 execution regressions and two PDF boundary regressions.

The final full-suite helper command was:

```powershell
.venv\Scripts\python.exe -X utf8 .tmp/m4-execution-20260913-01/verify.py final-pdf-corrected
```

It runs pytest over all `tests`, coverage with a 90% minimum, Ruff, Black,
Windows and Linux mypy, `pip check`, and `git diff --check`. Exact argument
arrays, exit codes, and durations are in `final-pdf-corrected/checks.json`.
The final changed-path hook command and inventory are recorded in
`precommit-final.json`; package commands are in `package/commands.json`.
The PDF verifier command was:

```powershell
.venv\Scripts\python.exe -B -X utf8 scripts/verify_thirsty_lang_utf_101.py --check-determinism --render-dir tmp/pdfs/m4-execution-20260913-02 --render-dpi 65
```

Earlier evidence is retained: `final/` records 5,081 passes and the stale
subtitle failure, `final-corrected/` records 5,082 passes before the two PDF
regressions, and `pdf-final/` records the first visual failure. The final
5,084-case pass includes the PDF builder correction and both new regressions.
No test expectation was weakened to bypass an execution-control failure.

## Artifact identity and limits

| Artifact | SHA-256 |
| --- | --- |
| Local wheel | `3ea716ea5b7eb56ed3a5c1e612e4a6a60ad6804187b37898ea508e2ea1023d7f` |
| Local sdist | `f8dec587a062394369026414a1f923e2d43858825e778f2aaa0f865e5cb51d15` |
| Runtime source integrity | `080d1d37bd39a7a1decc675be7ada2e6debe4682d38fa21252e389a6b5466700` |
| Corrected UTF 101 PDF | `551b335a092349fad090bc66b185c27c60c6f3157e687df543c536c046496a37` |
| PDF aggregate source manifest | `f0af3ed568c1586a508f1de526b05f84ebf79331519ebbf4e384bd95095e02f5` |

The package import path was isolated with `-I`, using an installed target and
the repository virtual environment's declared dependencies. This is not a
clean-machine installation test. Native Windows launcher execution, live
Pyodide execution, process-wide containment, and TARL worker termination are
not proven by these checks. No tag, version increment, PyPI workflow run, or
new publication was performed for this candidate.

Execution limits are cooperative. A blocking foreign call may delay a stop;
frontend work, host allocations and native operations are not comprehensively
metered. No rollback is promised after partial execution. Retaining ownership
while a worker finishes prevents concurrent reuse, but does not prove that a
blocking adapter will finish. Interpreter close does not take ownership of
borrowed policy runtimes, archives, or standard-library handles.

## Next correctness increment

Read-only probes in `next-review/mutable-alias-results.json` cover 15 cases:
14 pass the checker; 13 produce values inconsistent with an Int or nominal
annotation. One direct typed list write is rejected statically, and one whole
struct-field replacement is rejected at runtime. Those controls do not protect
nested aliases, mutation callables, or dynamic argument/return boundaries.

`next-review/repair-analysis.json` records the smallest next correction:
reject concrete writable-container covariance in assignment and callable
signatures while preserving safe scalar widening and contextual construction
of fresh literals. Live alias constraints and bounded runtime checks remain
coupled follow-up work. Invariance alone must not be reported as complete
mutable-value integrity, and these probes do not prove a TARL policy bypass.

## Completion boundary

M3-M7 remain open, including a complete portable target, mutable-alias safety,
foreign interface/provenance, distribution, sustained application evidence, and
independent acceptance. Robotics and swarm features remain deferred. This
increment makes no global sandbox, rollback, Python parity, or release claim.
