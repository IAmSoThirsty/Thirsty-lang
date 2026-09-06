# Priority corrections and General Purpose Language

Release plan: 2026-09-06. This foundation is prepared for Thirsty-Lang 0.9.0,
following development after `4e493dde5ba822a4e27ad87b4139f72ff7a443c3`. Publication
and remote artifact identity require separate release verification.

## Authority, order, and completion evidence

The user authorized implementation after a read-only repository investigation
and full-suite baseline. The user then directed that robotics and swarm features
stay on the back-burner until priority fixes and the general-purpose language
are implemented. Work is confined to this repository. No other personal project
has supplied code, models, dependencies, or evidence.

The order is: correct unsound behavior, deliver a useful general-purpose
foundation, verify it, then expand language coverage. Robotics is deferred.
Passing tests demonstrate the tested behavior; they do not establish a universal
security theorem, independent acceptance, deployment, or parity with Python.

Baseline evidence: 1497 passed, 1 Windows platform skip, 22 subtests passed,
90.30% coverage; Ruff, Black, mypy, and dependency consistency passed. These are
the baseline results, not the results of this implementation. Final verification
is recorded separately in `operations/IMPLEMENTATION_VERIFICATION.md`.

## Correction register

Each entry includes the failure, the correction, a consequence to test, and a
regression surface. “Implemented” means present in this working tree; the final
verification record determines whether integration passed.

| ID | Fault and correction | Consequence / regression obligation | State |
|---|---|---|---|
| C01 | Structural convergence renamed free variables and could erase meaning. Rename supported local binders only; preserve free names, scopes, and expression structure. Closures, imports, and other binding forms retain exact names. | Incorrectly resolved shadowed names, changed free inputs, and truncated block hashes must not gain proof. `test_shadow_soundness.py`. | Implemented |
| C02 | Symbolic arithmetic diverged from interpreter remainder/assignment/error semantics and generalized untyped Int assumptions. Match supported scalar semantics and report assumptions; conditional results do not become unconditional PROVEN admission evidence. | Negative divisors, zero, type domains, and exceptional paths. `test_shadow_soundness.py`. | Implemented |
| C03 | File imports could detach restrictions or preserve stale authority. Share policy/authority/hardened/path/lock state across imported interpreters and closures. Resolve relative imports from the importing file. | Revocation after import, imported top-level effects, nested imports, and path escape. `test_execution_boundaries.py` and import threat tests. | Implemented |
| C04 | SQLite query could perform writes through read permission. Use a deny-by-default SQL authorizer, disable statement caching, and serialize authorization through fetch. Deny attach/detach/extensions. | CTE writes, PRAGMAs, functions, parameters, and connection reuse. `test_stdlib_integrity.py`. | Implemented |
| C05 | Pure mode rejected surface I/O but allowed aliased/imported effects. Carry a scoped pure-execution context through calls and callbacks. | Effectful callbacks, clock/randomness, aliases, and nested calls; no restriction leakage after an exception. `test_execution_boundaries.py`. | Implemented |
| C06 | Lock hashes bound labels instead of executable bytes. Lock v2 binds manifest, all inventoried local sources, runtime source, and Python version; verify the exact bytes consumed. | Tampering, added imports, stale runtime, empty graphs, and duplicate lock keys. Legacy locks fail and require explicit regeneration. `test_stdlib_integrity.py`, `test_cli_execution_integrity.py`. | Implemented |
| C07 | Crypto helpers used concatenation digests/default keys as signatures. Use HMAC-SHA256, constant-time MAC comparison, explicit Ed25519 keys, and OS randomness. | Old values are not accepted as new signatures; tests use standard-library/cryptography verification. `test_stdlib_integrity.py`. | Implemented |
| C08 | TSCG canonical text lost grouping and admitted collisions. Preserve precedence and associativity; reject invalid AST operators. | Parse/canonicalize/parse must preserve both groupings for each operator pair. `test_tscg_canonical_integrity.py`. | Implemented |
| C09 | Checker coverage did not match executable expressions/statements. Traverse nested bodies and check declaration, assignment, and callable paths. | Unknown names and invalid statements inside previously missed constructs must fail; valid recursive functions remain usable. `test_execution_boundaries.py`. | Implemented; static typing remains deliberately partial |
| C10 | Reserved declarations/security syntax could succeed without semantics. Implement nominal enums and typed structs; explicitly reject unsupported interfaces and shield/detect/defend/sanitize/armor forms. | Existing programs using placeholders now receive a diagnostic. Do not claim protection from parsing a keyword. `test_execution_boundaries.py`. | Implemented |
| C11 | Build targets dropped statements, coercions, and unknown expressions. Validate supported target subsets; reject unsupported programs before emission; test JS against interpreter results. Bind browser runtime source. | Integer precision, zero division, remainder, truthiness, names, arity, unsupported control flow, and source injection. Compiler integrity tests. | Implemented subset; broader compiler is planned |
| C12 | Networking returned success without an OS operation. Implement bounded TCP/UDP handles and explicit accept/send/receive/close, verified on loopback. | Timeouts, refusal, truncated datagrams, partial UTF-8, handle exhaustion, and cleanup. `test_network_stdlib.py`. | Implemented; numeric IP addresses only |
| C13 | Serialization and builtins silently changed types or returned fake fallback values. Use tomllib, validated TOML output, an explicit YAML subset, and argument errors. Repair assert_raises. | Round trips, unsupported values, duplicate fields, and callbacks that do not raise. `test_stdlib_integrity.py`. | Implemented |
| C14 | Thread timeouts could leave analysis running. Replace sampling execution with a bounded scalar AST evaluator and abstain on unsupported input. | Source, depth, step, scalar-size budgets; no arbitrary host callbacks; absent invariants are INAPPLICABLE. `test_shadow_soundness.py`. | Implemented for Shadow analysis |
| C15 | Docs disagreed with context normalization and feature enforcement. Align active contracts, record migrations, regenerate the source-bound manual. | Preserve historical failure/release evidence, verify current PDF digest and rendering. PDF contract suite. | Implemented documentation update |
| C16 | Repository-local PSIA and governance server prototypes manufacture success/pattern-based verdicts without an authority pipeline. Isolate from released language claims and document missing evidence/dependencies. | Do not promote prototype health, signatures, or automatic ALLOW to trusted authority. | Requires separate follow-up work; not a language dependency |
| C17 | Required auditing could silently accept a missing archive or skip persistence on decision-only evaluation. Deny when persistence fails, persist each required decision, and expose CLI audit options. | Disk failure must prevent an effect; independently opened writers must extend one chain. `test_audit_requirements.py`, `test_cli_execution_integrity.py`. | Implemented |
| C18 | A source pass alone does not prove package or release identity. Verify full tests/quality gates, built artifacts, installed import provenance, and documented scope. | Never reuse baseline totals as new results; no remote release claim without remote evidence. | Local evidence recorded; remote release verification pending |

## Faults revealed while correcting the baseline

| Finding | Disposition and executable repair / validation path |
|---|---|
| Optimized calls could evaluate an effect twice | Fixed in interpreter; assert invocation count and result at optimization levels 0-3. |
| Debug exception reconstruction could turn a governance denial into a catchable ordinary error | Preserve GovernanceViolation and its proof; test debug and release paths. |
| A failed constructor could leave the wrong lexical environment active | Restore environment in finally; test subsequent calls and field initialization errors. |
| Authority was verified only at binding time | Retain signed validity window and immutable claim snapshot; revalidate before effects; issuer revocation/replacement reaches existing bindings. Test exact expiry and broken configured clocks. |
| SQLite archive locks were per Python object, allowing competing chain heads | Reserve the SQLite writer transaction before reading the head; test four independently opened writers. |
| CLI delegation to Thirst of Gods could drop restriction flags | Refuse restricted delegation explicitly; use a converted Tier 1 program for those options. |
| CLI audit/lock could report success after an integrity or write failure | Return failure status and require successful writes; test storage errors and absent/stale locks. |
| An uncaught core-language throw could be printed as a successful return value | Propagate the uncaught failure to CLI exit status; test malformed application data and ordinary handled exceptions. |
| HTTP accepted file URLs and process calls used an implicit shell with error-shaped success strings | Require HTTP(S), explicit response bounds and redirect handling; require subprocess argv and shell=False, with checked status/time/output. Loopback and direct-child tests verify failures. |
| Core closures could retain weaker mode after hardened/required-audit settings changed | Recheck effective mode at each effect, including exported closures; direct embedding receives the same restrictions as CLI. |
| Authority could expire, be revoked, or be replaced during policy/source/audit evaluation | Bind the entry authority and detect in-flight binding changes; revalidate the same credential before releasing a positive decision to an effect. Persist denial when storage is available. This is not an atomic distributed revocation protocol. |
| Formatter emitted invalid mutable/function/enum/struct/error-handler syntax | Align emitted forms with parser grammar and add parse-format-execute round trips; do not keep tests that assert invalid output. |
| Parser recovery could feed partial ASTs to execution/admission/build | Reject failed parses at boundaries; bind original source and parsed spans together. |
| Prior proof methods retained apparently current authority after soundness repairs | Version Shadow engine/method IDs; historical verification is integrity-only and explicitly requested. It cannot recertify the old method. |
| Time/randomness are effects even without file/network I/O | Pure checks cover those callables. General deterministic replay still requires an injected event/clock/randomness model. |

## General Purpose Language

The executable API and migration reference is
[GENERAL_PURPOSE_LANGUAGE.md](GENERAL_PURPOSE_LANGUAGE.md).

The language deserves continued engineering only if it becomes useful and its
claims remain inspectable. The near-term product is a readable application
language with explicit effects and reliable ordinary data processing. Rivaling
Python means usefulness, libraries, tooling, portability, diagnostics, and
maintenance over time; syntax count alone cannot achieve that.

### Foundation delivered in this working tree

- Ordinary functions, recursion, closures, loops, exceptions, classes, imports,
  arrays, strings, arithmetic, and strict/pure/governed modes continue to work.
- Nominal enum values and typed mutable struct fields have runtime semantics.
- Dictionary literals and collection helpers support data ingestion and
  aggregation; tuples and bytes expose explicit immutable representations.
- Real file, HTTP, process, SQLite, TCP/UDP, JSON, TOML, cryptographic, and
  collection utilities support small applications. Each API has its own limits;
  network sends do not prove remote application completion.
- A repository example ingests a synthetic JSON dataset, checks values,
  aggregates records, and emits a JSON report. Its end-to-end test is part of
  the suite, rather than a fabricated usage or performance claim.
- The interpreter is the reference execution path. JS supports a checked
  subset. LLVM is a bounded closed-scalar evaluator emitting a verified i32
  result, not a general runtime. Browser execution binds expected source.

The language is not Python-compatible, and these additions do not complete the
remaining milestones below. Unsupported syntax must produce diagnostics until
its semantics, tests, and docs are delivered together.

### Milestones and dependency order

| Milestone | Work and prerequisites | Exit evidence |
|---|---|---|
| M1: trustworthy existing behavior | C01-C15 and C17, authority lifetime, all newly revealed regressions | Full test suite with optional analysis/docs enabled, coverage floor, Ruff/Black/mypy, no unexplained failures, artifact verification |
| M2: usable data/application foundation | M1; collections, dictionary literals, enums/structs, binary/text conversion, real bounded network, practical application example | End-to-end .thirsty programs, malformed data controls, capability denial before effect, cleanup on failures |
| M3: language semantics and tooling | M2; specify numeric domains, Unicode/indexing, default/named args, optional/result values, iterators/generators/comprehensions/slicing, protocols/generics; improve diagnostics and debugger | Executable language conformance corpus; formatter/parser round trips; error-span tests; supported-feature matrix |
| M4: one complete portable execution target | M3; typed/effect-aware IR, reference semantics, resource accounting, cancellation, scheduler ownership and deterministic teardown | Interpreter/backend differential corpus; fuzzing and adversarial resource tests; documented architecture/OS matrix |
| M5: practical standard library and interoperability | M3-M4; paths and atomic I/O, decimal/statistics/date/time, async streams, TLS/DNS, serialization schemas, constrained Python/FFI adapter | Real integration fixtures; permission and error tests; defined ownership/encoding/cancellation across every foreign boundary |
| M6: distribution and ecosystem | M4-M5; package identity, artifact signatures, resolver constraints, transitive lock graph, isolated dependency builds, language server and documentation tooling | Reproducible clean installation, offline locked operation, malicious package tests, upgrade/rollback compatibility corpus |
| M7: sustained usefulness | M2 onward; CLI automation, report processing, small local services, database programs and package consumers | Maintained applications; published reproducible benchmarks with workload/hardware/version data; compatibility policy |
| M8: ecological robotics and swarms | Deferred by user; start only after priority fixes and general-purpose implementation | A separate approved requirements/assurance plan before physical-world features |

There is no invented completion date or performance claim. Each milestone is
split into independently reviewable increments. New failures become entries in
this register before their milestone can close.

## Distinctive security features worth pursuing

These are language-specific proposals unless explicitly marked implemented.
They need concrete syntax/semantics and tests before being advertised as features.

1. **Effect types and capability attenuation.** Build on implemented runtime
   gates and pure-call propagation. A function declares read/write/network/execute
   effects; callbacks and imported closures carry a checked upper bound. Delegation
   may narrow targets, time, and budgets but cannot manufacture authority. Test
   higher-order functions, aliases, recursion, and inference failures.
2. **Authority lifetime as a value property.** Current effects revalidate signed
   identity windows and live issuer trust. Extend this to single-use or affine
   capability handles with explicit transfer/revocation and request-bound receipts.
   A decision proof must never be mistaken for authority to repeat an effect.
3. **Reproducible governed execution.** Existing proof fields bind policy,
   context, schema, time, and normalization. Extend receipts to code/runtime/lock
   identities and adapter inputs/results, with redacted commitments for secrets.
   Define trusted input boundaries; signatures do not prove truthful sensors or
   external service responses.
4. **Resource effects and bounded evaluation.** Shadow sampling now has real AST
   budgets. Extend CPU/memory/output/network/time budgets to the runtime, ensure
   cancellation reaches blocking adapters, and use OS isolation for hostile code.
   AST estimates and host threads are not a process sandbox.
5. **Typed data provenance and units.** Add validated data types, units, schema
   versions, and explicit conversions useful in ordinary applications. Reject
   implicit narrowing, ambiguous encodings, and invalid numeric values at trust
   boundaries. No physical-device implementation is part of this increment.
6. **Proof-aware mutation admission.** Current Shadow records distinguish PROVEN,
   OBSERVED, UNKNOWN, VIOLATED, and INAPPLICABLE and never authorize execution.
   Extend evidence only for specified semantics; unsupported programs abstain.
   Method upgrades invalidate stale claims without erasing historical records.
7. **Auditable foreign interfaces.** Add a narrow explicit Python bridge only
   after effects, schemas, ownership, cancellation, and process isolation are
   specified. Returning arbitrary Python objects or unrestricted getattr would
   break the intended boundary and is not an acceptable shortcut to Python's
   library ecosystem.

## Remaining issues and repair paths

| Issue | Classification | Next concrete work |
|---|---|---|
| File path check/open races against a concurrent hostile filesystem writer | Requires separate follow-up work | Implement descriptor/handle-relative no-follow opens per OS; deterministic race fixtures; state the OS-specific boundary before a confinement claim. |
| Runtime loops, arbitrary allocations, thread pools, DNS/total HTTP elapsed time, and subprocess descendants lack one global execution budget | Requires separate follow-up work | M4 cancellation/resource-accounting API, bounded adapters, process-isolated hostile workload tests. HTTP/process/network/Shadow limits are local, not whole-runtime containment. |
| Mutable collections can be shared through closures and callbacks | Not blocking this foundation; semantics work remains | M3 ownership/aliasing specification; mutation/effect tests; optional immutable data boundaries. Pure currently restricts mediated external effects, not a proof of referential transparency. |
| General static typing is incomplete for dynamic Any and foreign values | Requires separate follow-up work | M3 inference and runtime boundary validation; no claim of whole-program type soundness. |
| PSIA / governance prototype services are excluded from the shipped `utf` package, require undeclared FastAPI/Pydantic/uvicorn, and contain simulated signatures/automatic or keyword-based decisions | Environment/dependency issue and separate follow-up | Keep outside the language authority path. Before activation, replace fake verdict/evidence paths, declare an optional dependency group, require authentication and broker integration, add service tests. No service was started in this task. |
| No complete TLS/DNS socket layer or remote package resolver | Requires separate follow-up work | M5/M6; numeric socket endpoints and local/stdlib package resolution fail explicitly outside supported scope. |
| No complete compiled backend or Python ecosystem compatibility | Requires separate follow-up work | M3-M6 conformance and interoperability plan above. |
| Windows cannot exercise POSIX private-key permission enforcement | Environment/platform issue | Run the Linux CI matrix; preserve skip separately from pass. |
| Independent Competence Register acceptance remains pending | Requires separate follow-up work | Submit current context-contract evidence for independent acceptance; do not rewrite historical FAIL entries into a new review outcome. |

## Change discipline

Before every semantic change: inspect callers, record the failing case, update
the implementation and affected tests/docs, and run focused validation. Then
run the integrated suite. Do not weaken checks to recover a green result.
Version changed artifact formats/methods, document migration, and preserve old
evidence. No new dependency, generated bundle, or declared capability may cross
another project's boundary without explicit source/destination authorization.
