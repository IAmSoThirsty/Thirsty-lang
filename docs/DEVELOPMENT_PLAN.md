# Priority corrections and General Purpose Language

Updated 2026-11-18. Thirsty-Lang 0.9.0 was published and its artifact identity
verified. M3.1 sequence semantics has its own completed local verification in
[M3_SEQUENCE_VERIFICATION.md](operations/M3_SEQUENCE_VERIFICATION.md).
The recorded M3.2 Boolean/type-coherence increment built on then-uncommitted
work; it had no new package version or publication claim. Consult its separate
integration results in
[M3_TYPE_COHERENCE_VERIFICATION.md](operations/M3_TYPE_COHERENCE_VERIFICATION.md).
Earlier release or M3.1 totals do not validate M3.2.
M3.3 governance/security defaults follows those changes and has its own
[completed local integration record](operations/M3_SECURITY_DEFAULTS_VERIFICATION.md).
The M3.4 callable-consistency and iteration increment has a separate
[verification record](operations/M3_CALLABLE_ITERATION_VERIFICATION.md).
The current M3.5 value-identity candidate adds constructor/cascade type repairs
and bounded native governed-call contexts. Its
[verification record](operations/M3_VALUE_IDENTITY_VERIFICATION.md) reports
final integration evidence; focused implementation checks do not close that gate.
These implementations are not new releases, and earlier verification totals
do not validate later increments.

Cumulative M3.1-M3.5 was subsequently committed and pushed as
`e888a847b079048ba29b78a39b8e5ddfebed86ce`; its historical verification
records retain their original pre-delivery wording. The current M4.1 execution
control work follows that commit and remains unreleased. Its contract is
[EXECUTION_CONTROL.md](EXECUTION_CONTROL.md), with separate integration evidence
in [M4_EXECUTION_CONTROL_VERIFICATION.md](operations/M4_EXECUTION_CONTROL_VERIFICATION.md).

The November development candidate enforces typed mutable values across guest aliases,
adds the TSCG-B text-frame module, and includes the data-report application in the
wheel. The [qualification record](operations/LANGUAGE_DEVELOPMENT_QUALIFICATION_20261118.md)
tracks the installed checks and the next portable-backend acceptance cases.

## Authority, order, and completion evidence

The user authorized implementation after a read-only repository investigation
and full-suite baseline. The user then directed that robotics and swarm features
stay on the back-burner until priority fixes and the general-purpose language
are implemented. Implementation is local to this repository. In November the owner authorized a
wire-compatibility comparison with the ThirstForged Conclave. Its installed
codec and representation adapter supplied comparison results. Thirsty-Lang
continues to use its own codec.

The order is: correct unsound behavior, deliver a useful general-purpose
foundation, verify it, then expand language coverage. Robotics is deferred.
The governing product objective is a **Governance First Language, Security
Default**: ordinary computation must remain useful while mediated effects
require authority from the host's explicit policy. Source headers and imported
code must not silently remove that boundary. Legitimacy depends on executable
contracts, accurate limitations, reproducible evidence, and sustained language
usefulness; it cannot be established by feature labels or a rename.
Passing tests demonstrate the tested behavior; they do not establish a universal
security theorem, independent acceptance, deployment, or parity with Python.

Baseline evidence: 1497 passed, 1 Windows platform skip, 22 subtests passed,
90.30% coverage; Ruff, Black, mypy, and dependency consistency passed. These are
the baseline results, not the results of this implementation. Final verification
is recorded separately in `operations/IMPLEMENTATION_VERIFICATION.md`.

The completed 0.9.0 release is recorded in
`.tmp/release-0.9.0-20260906/published/release-receipt.json`, with verified commit
`b09bbfc3dda4654cca2e9872423460667eed9498`. The receipt records 1986 passed,
1 skipped, and 22 subtests passed locally with 91.86% coverage; Linux Python
3.11 and 3.12 each recorded 1986 passed, 1 skipped, and 22 subtests passed with
91.77% coverage. The public wheel and sdist hashes matched the workflow build,
and all 54 wheel Python files matched both repository and sdist source.
The recorded [release workflow](https://github.com/IAmSoThirsty/Thirsty-lang/actions/runs/34053055171)
and [CI run](https://github.com/IAmSoThirsty/Thirsty-lang/actions/runs/34053057407)
completed successfully. This is recorded release evidence, not a fresh online
check or validation of subsequent edits. The receipt's clean tree and zero
ahead/behind observations describe that release checkpoint.

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
| C18 | A source pass alone does not prove package or release identity. Verify full tests/quality gates, built artifacts, installed import provenance, and documented scope. | Never reuse baseline totals as new results; no remote release claim without remote evidence. | Completed for recorded 0.9.0 release and separate local M3.1 candidate; consult the separate M3.2 integration record |
| C19 | Runtime/CLI/scaffolds defaulted to Core and source headers could remove requested governance. Separate semantic mode from host posture; require governance by default; retain only explicit trusted-host compatibility opt-out. | Headerless/Core/strict/pure input, `--unsafe-core` conflicts, governed declaration floor, REPL reset, matching scaffold metadata, and Thirst of Gods delegation. `test_security_defaults.py`, `test_governance_entrypoint_defaults.py`. | Implemented; consult security-defaults integration record |
| C20 | Lexical/parser errors could lose failure provenance and formatting could rewrite recovered partial source. Preserve failure through token streams/ASTs and reject malformed programs at execution and formatting boundaries. | Unknown punctuation, invalid escapes, forged/copy-transformed failure markers, imports, explicit compatibility mode, and no write on format refusal. `test_source_failure_provenance.py`. | Implemented; consult security-defaults integration record |
| C21 | A newly exposed stdlib callable could receive no explicit effect classification. Require an exact effect/no-ambient-effect export inventory before guest exposure. | Missing/unknown exports, overlapping classifications, cached exports, no-ambient helpers with effectful callbacks. `test_stdlib_export_classification.py`. | Implemented; host-injected foreign callable provenance remains open |
| C22 | Callbacks and imported closures could retain only one side's restrictions. Carry caller and definer restrictions together through language calls, methods, aliases, callbacks, and cascades. | Multiple policy/authority bindings, revocation during compound authorization, active pure/strict restrictions, and caller/definer lock enforcement. `test_security_defaults.py`. | Implemented; consult security-defaults integration record |
| C23 | Callable parameter covariance and erased callable choices accepted invocations that a selected function could not support. Use contravariant parameters, covariant returns, and retained alternatives checked at every known call. | Nominal-aware exact deduplication, higher-order signatures, mixed arities, argument/result joins, and pipe/pipeline calls. `test_callable_type_conformance.py`. | Implemented in M3.4; consult its separate integration record |
| C24 | Foreach introduced its binding before resolving the iterable, erased known element types, and silently skipped dynamic noniterables. Resolve enclosing scope, retain element/key descriptors, and use native iteration with explicit errors. | Nested nominal records, shadowing, E025 spans, dynamic values, iterator sequencing, per-iteration closure scope, returns, cascades, and denials. `test_iteration_conformance.py`. | Implemented in M3.4; host iterators remain trusted |
| C25 | Constructor values shared instance descriptors, losing callable identity through aliases and selections. Introduce `ConstructorType` and validate every retained function/constructor signature at calls, `new`, and pipes. | Nominal annotations, alias/member resolution, nested collections, E031 noncallables, and callable choices. `test_constructor_type_conformance.py`. | Implemented M3.5 candidate; consult its integration record |
| C26 | Cascade returned its awaited value while the checker wrapped it in Task; a dynamic noncallable route evaluated operands twice. Infer the actual operand result and reject invalid calls after one evaluation. | Assignments, returns, callbacks, collections, pipes, worker errors, and governance denials. `test_cascade_type_conformance.py`. | Implemented M3.5 candidate; consult its integration record |
| C27 | Governed calls omitted or ambiguously rebound receivers, rejected native data, or admitted mutated/invalid values under an earlier snapshot. Project registered native values, reject duplicate/receiver-conflicting parameters, recheck live values at authorization checkpoints, and bind positive proofs to the submitted original context. | Receiver/result admission, duplicate-binding rejection before defaults/contracts/body, callback mutation, reserved result parameters, bounds, native identity, and no-hook rejection. `test_governed_value_integrity.py`, `test_parameter_binding_conformance.py`. | Implemented M3.5 candidate; consult its integration record; wider ownership and handoff contracts remain open |

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
| Accurate Float inference for division exposed operand-order-dependent numeric checks; valid `24 / (6 / 2)` was rejected | Fixed and verified in M3.1: accept mixed Int/Float arithmetic and comparisons symmetrically. Regressions cover nested division and both operand orders. |
| Formatter statement boundaries could merge array, parenthesized, or unary-minus expressions into preceding statements | Fixed and verified in M3.1: preserve statement separation with parse-format-execute regression tests. |
| Scalar Boolean arithmetic and comparison inherited numeric coercion | Fixed in current M3.2 implementation: reject Bool arithmetic, ordering, arithmetic negation, and mixed Bool/non-Bool equality; retain Boolean equality and logical operators. Native container/key equality remains unchanged. Consult the separate integration record. |
| Nested nominal annotations became Any, same-named declarations could compare structurally equal, and some generic wrappers ignored arguments | Fixed in current M3.2 implementation: recursive lexical resolution, declaration identity, and checks of every wrapper argument/base/arity. Malformed/excess arguments report errors; unknown annotations and omitted argument defaults remain gradual. Consult the separate integration record. |
| Resolving top-level function signatures before nominal declarations erased their parameter/return types | Fixed in current M3.2 implementation: prepare nominal descriptors and recursive struct placeholders before function signatures; preserve runtime declaration order. Resolve signatures before parameter bindings can shadow type names. |
| Known dictionary key annotations were ignored on indexed reads and writes | Fixed in current M3.2 implementation: compare known key types with the declared key annotation. Any keys remain dynamic and runtime hashing/equality is unchanged. Consult the separate integration record. |
| Struct/interface parser errors could repeat without consuming input; standalone cascade calls missed statement checking | Fixed in current M3.2 implementation: ensure parser progress on malformed declaration members and check cascade operands/arguments as statements. Regression tests cover diagnostics and valid execution. |
| A declaration without an initializer lost its annotation in the checker | Fixed in current M3.2 implementation: retain the declared static type. Core execution still initializes the value to none; definite-assignment analysis remains open. |
| Z3 could equate Boolean true with integer 1 and admit stale assurance | Fixed in current M3.2 implementation: preserve Boolean/numeric result distinctions and reject invalid Boolean operations in modeled paths. Advance Shadow engine to 0.4.0 and convergence methods v4; older engines require explicit historical integrity verification and reanalysis for current assurance. |
| Callable common-type joining could conceal different arities or erase a narrower known alternative through Any compatibility | Fixed in M3.4: flatten known alternatives and deduplicate exact descriptors; require every possible signature at direct and known pipe/pipeline calls. Keep mixed callable/noncallable heterogeneous joins explicitly gradual. |
| Runtime call binding used zip, silently dropping excess arguments or leaving missing parameters unbound | Fixed in M3.4: exact positional arity before parameter binding, body/contract evaluation, and fountain defaults. Caller argument expressions retain their existing evaluation order. `test_callable_arity.py` covers the repair; broader default/named argument design remains open. |
| TypeVariable descriptors with different names could assign or join as the same type | Fixed in M3.4: compare names consistently; different names do not assign and join to Any. This does not implement quantified generic functions. |
| Pipe fallback typing treated nominal constructors as noncallable, rejecting valid calls and accepting incorrect result annotations | Fixed in M3.4: direct struct/enum constructor names retain nominal return types; struct fields supply argument checks. Explicit instances keep fallback behavior. Ambiguous nominal aliases remain Any until constructor identity has its own descriptor. |

## General Purpose Language

### Execution corrections in M4.1

Deterministic review exposed shared-environment corruption in competing escaped
calls, starvation at five outstanding cascades on a four-worker pool, and caller
shadowing of governed preconditions through inconsistent lexical scoping. These
are priority security/correctness repairs, so M4 execution work starts alongside
the still-open M3 language features.

The interpreter now claims one logical execution across every joined caller and
definer domain, shares file-import ownership and its scheduler, and admits only
same-thread reentry or explicit cascade thread transfer. Nested awaited cascades
execute on the active worker. Governed functions, morphs, and methods retain
their defining environment. Caller restrictions remain conjunctive with definer
restrictions; lexical lookup does not select a weaker authority.

Finite step, cooperative deadline, and call-depth limits apply by default and
combine using the tightest joined host limits, including work already spent.
Cancellation and resource stops latch until the outer run unwinds; guest
handlers and finalizers cannot resume execution after that stop. Idle close
shuts down the import graph's scheduler; borrowed TARL runtimes remain host-owned.
CLI-created resources are released on setup failures and runtime exits.

The CLI review also revealed successful REPL input being replayed. Checked
history is now used for static context only; runtime receives each submission
once. Runtime failure requires `.clear` before continuing because partial state
and effects cannot be reconstructed as a successful static history.

These controls do not implement process isolation, allocation/output quotas,
frontend budgets, total adapter deadlines, or process-tree/stdlib-handle teardown.
Direct host `resolve_import` caching also lacks an explicit lifetime handle;
the next repair path is an owned module-loading API with cache eviction and
escaped-closure tests. Python embedding and its private APIs remain trusted.
M3-M7 and independent acceptance remain open; robotics remains deferred.

The executable API and migration reference is
[GENERAL_PURPOSE_LANGUAGE.md](GENERAL_PURPOSE_LANGUAGE.md).

The language deserves continued engineering only if it becomes useful and its
claims remain inspectable. The near-term product is a readable application
language with explicit effects and reliable ordinary data processing. Rivaling
Python means usefulness, libraries, tooling, portability, diagnostics, and
maintenance over time; syntax count alone cannot achieve that.

### Foundation released in 0.9.0

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

### Completed local increment: M3.1 sequence semantics

The M3.1 implementation adds one indexing/slicing contract across the
parser, formatter, checker, and reference interpreter. Exact native lists,
strings, tuples, and bytes support sequence reads with non-boolean `Int`
indices, negative offsets, and strict bounds errors. Slices retain container
type, clip bounds, accept omitted/`none` bounds and negative steps, and reject
zero steps. String positions are Unicode code points. List slices copy only
the outer structure. Dictionaries retain native key semantics and indexed
assignment. M3.1 left dictionary key annotation checks for the M3.2 increment
below.

The runtime evaluates a slice receiver and its start/stop/step once in source
order before validation. Indexed assignment evaluates the right-hand side,
receiver, and index in that order. Slice assignment is explicitly unsupported
before any target or right-hand-side effects. Pure/governed callback checks
remain active. Python sequence subclasses and implicit index coercion hooks
are rejected; dictionary key hashing/equality remains an embedding boundary.

Checker changes retain known slice element types, infer numeric division as
`Float`, accept mixed Int/Float arithmetic and comparisons in both operand
orders, and unify `and`/`or` operand types. Imported tuple/bytes values remain
static `Any`. Annotated reservoir checks inspect every source literal element
through a slice, even when its bounds appear to exclude an invalid element;
the checker does not execute bounds.

JS/LLVM builds reject slices before artifact emission. Pyodide uses the
interpreter semantics but still requires a distribution matching the current
source fingerprint; published 0.9.0 is not that post-release runtime. Shadow
structural/effect traversal includes every slice operand, while symbolic and
sampled semantic analysis abstain. Unknown AST subclasses cannot gain proof
or compiled output by inheriting from an accepted node.

The stored-record audit showed that engine/method identity, rather than AST
replay, determines whether proof evidence is current. This repair therefore
advanced Shadow admission to engine 0.3.0 and v3 convergence methods. Engines
0.1.0/0.2.0 remain readable for explicit historical integrity verification;
their claims require reanalysis. Unary bounds also now retain their actual
source spans instead of inheriting the beginning of the file.

Validation surfaces are `test_sequence_values.py`,
`test_sequence_conformance.py`, and `test_slice_boundaries.py`, covering bounded
sequence corpora, formatter round trips, runtime/checker agreement, operand
effects, and conservative proof/build behavior. The M3.1 verification record
reports 2,255 passed, 1 skipped, and 22 subtests passed with 91.98% statement
coverage. Those results describe its recorded source and artifacts. M3.2 now
supersedes its current proof engine; the historical record remains unchanged.

### Completed local increment: M3.2 Boolean and type coherence

The nominal predeclaration review also exposed callable/type name collisions
that could bypass duplicate checks. Failed function/class declarations now
retain the conflicting nominal binding and report E010 in either source order.

Scalar `Bool` values support `==`/`!=` with other `Bool` values, and retain
ordinary `and`/`or`/`not` behavior. Arithmetic, ordering, arithmetic negation,
and equality between a Bool and a non-Bool now fail instead of treating the
Boolean as a number. This contract applies to scalar operators. Native nested
container equality and dictionary key equality retain their existing behavior,
including the numeric collision between `true` and `1` as keys.

Type resolution now preserves declared enums and structs inside nested generic
arguments. A per-declaration `declaration_id` distinguishes same-named
declarations and avoids recursively comparing a struct's fields to establish
nominal identity. The checker prepares nominal descriptors before top-level
function signatures; runtime declaration order is unchanged. Nested lowercase
primitive aliases and explicitly shadowed nominal names resolve consistently,
including existing runtime struct-field checks.

Every existing generic descriptor checks its constructor, argument count, and
arguments during assignability/unification, including Task, Result, Governed,
and custom GenericType descriptors. Malformed syntax and excess known-wrapper
arguments report errors. Unknown leaf annotations retain static Any fallback,
and omitted type arguments retain compatibility defaults. This is gradual
typing, not a whole-program type-soundness claim.

Known dictionary key types are checked on reads and writes; Any keys remain a
dynamic boundary. Declared types survive declarations without initializers in
the checker, while Core runtime values still begin as none. The increment does
not provide definite-assignment analysis or add general runtime enforcement of
variable/function annotations. Existing struct construction and field-write
validation remains active; mutation through aliases can escape those checks.

Connected repairs ensure malformed struct/interface parsing makes progress and
standalone cascade statements check their operands. Shadow's Boolean/numeric
proof repair advances the admission engine to 0.4.0 and convergence methods to
v4. Engines 0.1.0, 0.2.0, and 0.3.0 remain readable only through explicit historical
integrity verification; their claims need reanalysis for current assurance.

Focused regression surfaces include `test_nominal_type_resolution.py` and
`test_type_coherence.py`, plus the scalar, compiler, and Shadow boundary tests.
Consult the current verification record for measured integration results and
limitations. M3's broader language/tooling work stays open, and robotics remains
deferred.

### Completed local increment: M3.3 governance and security defaults

The reference interpreter and CLI now require governance without an enabling
flag. Source `core`, `strict`, and `pure` headers retain their language semantics
without granting ungoverned execution. Pure computation remains usable without
policy; imports, input/output, and mapped sensitive operations require an
allowing decision. Standard-library exports must have an explicit classification.
New projects demonstrate pure calculation under governed metadata, returning a
value for trusted CLI presentation rather than silently granting output rights.

Compatibility execution is an explicit trusted-host decision through
`Interpreter(allow_ungoverned=True)` or disclosed `--unsafe-core`. CLI security
options cannot be combined with that opt-out. Explicit governed declarations,
active caller/definer policies, pure restrictions, and lock checks retain their
floor. Embedded foreign Python values remain trusted host inputs; their source
identity is not established merely because a lockfile exists.

Every public JS/LLVM/Pyodide build requires `--allow-governance-loss` and persists
a disclosure manifest before executable artifacts or toolchain execution.
Unsupported compiler input fails before either output. Pyodide retains the
interpreter and explicit governed declarations, while lacking host policy and
authority configuration; its effective enforcement and requested opt-out are
recorded separately. A manifest remaining after a later build failure does not
certify build success.

Connected corrections preserve lexical/parser failure provenance, refuse
malformed format inputs before writing, and use UTF-8 for source tooling.
Static proof-obligation reports describe declared semantics and effective
governance without inventing policy/authority requirements for pure computation.
They explicitly limit effect discovery through dynamic dispatch and imported
module bodies. M3 language/tooling, M4 portability/resource containment, and
M5-M7 library/ecosystem/usefulness requirements remain open. This increment
does not claim an OS sandbox, universal proof of safety, or robotics readiness.

### Prior increment: M3.4 callable consistency and iteration

Callable assignment now accepts replacements with contravariant parameters and
covariant returns, retaining exact arity. Known callable common types use an
internal `FunctionUnionType`: one selected function whose possible signatures
are retained, flattened at joins, and deduplicated by exact descriptor equivalence.
Nominal declarations and nested generic/callable arguments remain distinct;
gradual compatibility with `Any` is not evidence of an exact duplicate. Direct
calls and known `|`/`->` calls must satisfy every alternative's arity and parameter
types; their static result joins every alternative's return. No overload dispatch
or source callable-annotation syntax is added. `TypeVariable` name consistency
is repaired without claiming quantified generics.

Pipe review also exposed constructor/instance descriptor ambiguity. Direct
struct constructor names now validate their field signature, and direct enum
constructor names retain nominal results with runtime variant-value validation.
Explicit nominal instances kept the noncallable fallback. At that checkpoint,
ambiguous nominal aliases and Task/cascade operands remained `Any`; runtime
cascade awaited its result while the checker described `Task[T]`. M3.5 addresses
those recorded constructor and cascade gaps below.

The runtime requires exact positional arity for ordinary functions, lambdas,
morphs, governed functions, bound fountain methods, and fountain construction.
Struct construction retains its existing exact field count. The checks precede
callee parameter binding, body execution, contract predicates, and function-policy
evaluation; fountain construction checks before field defaults. Existing caller
argument expressions still evaluate before callable entry. A leading `self`
receiver is excluded from a bound method or initializer's explicit argument
count, and a fountain with no initializer accepts zero arguments.

Foreach checks its iterable in the enclosing scope before introducing the loop
binding. Known lists yield their element descriptor, dictionaries their key
descriptor, and strings `String`; nested nominal identity is retained. Unknown
`Any` stays dynamic. Known noniterables report E025 and dynamic noniterables now
raise `TypeError`. Native iteration evaluates its source once, acquires the
iterator once, and preserves sequencing, per-iteration scope, exceptions,
returns, cascades, and governance denials. Host `__getitem__` sequence objects
now iterate through the native protocol instead of being silently skipped.

This increment does not complete M3. Lambda signature inference, unresolved
annotation diagnostics, mutable alias validation, source generics, guest
iterators/generators/comprehensions, and broader tooling remain open. Mixed
callable/noncallable joins retain `Any`. Host iterator methods remain trusted
Python code; global resource limits and cancellation remain M4. Consult the
separate M3.4 verification record for current integration results, without
reusing M3.1-M3.3 totals. Robotics remains deferred.

### Current candidate: M3.5 value identity and governed native values

`ConstructorType` separates struct/enum constructor values from their instances.
Aliases, collection selections, and callable alternatives retain that identity;
nominal annotations still describe instances. Known calls, `new`, and pipes use
the same signature checks, including every possible function/constructor
alternative. Struct parameters follow declared fields; enum constructors take
one argument and validate the variant value at runtime. Known noncallable calls
and `new` report E031. Instance pipe fallbacks remain unchanged. Fountains and
unknown/foreign values retain their existing gradual typing; this is not a
complete object-type or source callable-annotation system.

`cascade expression` is checked as the awaited expression's result, including
known returned callbacks and nested collection types, rather than `Task[T]`.
The dynamic noncallable route raises after evaluating its callee and arguments
once. Thread-pool awaiting, source order, errors, and governance propagation
remain; no new async protocol is added. Explicit/host `Task` descriptors remain
gradual where no corresponding runtime task-value contract is defined.

Governed call entry and exit use independently owned JSON projections of exact
JSON values and registered native structs, fountains, and enums. The
`thirsty.native-value.v1` profile binds runtime scope/declaration tokens and
declared fields or an enum variant. Ordinary JSON parameter paths remain;
native fields use paths such as `row.fields.value`. Explicit `self` and implicit
`this` receivers participate. A governed/contract-bearing parameter named
`result` denies before entry callbacks or the body because exit reserves that
binding; uncontracted parameters and nested fields with that name remain valid.

Review also exposed a duplicate `self` parameter that could substitute an
argument for the receiver in policy context while the body used the actual
`this` object. Duplicate parameters now report E010 across functions, lambdas,
morphs, and methods; runtime binders reject them before parameter binding,
contracts, or bodies, and initializers before field defaults. A remaining
`this` parameter in a method AST reports E901 and fails runtime binding. Source
methods use explicit leading `self` or implicit `this`; explicit leading `this`
is a host-AST convention only because the parser reserves that keyword.
A nonleading `self` remains an ordinary parameter, with the actual receiver
separately included as `this`. Caller argument evaluation remains before entry.

Projection rejects unsupported foreign values, forged native markers, cycles,
invalid layouts, and exceeded depth/node/text/integer budgets without calling
object conversion or traversal hooks. Entry admits one snapshot; live values
must still match it after callback-capable checks and before handoff. Exit
admits a new snapshot after the body and validates the returned value even
without an explicit exit predicate. Positive policy proofs must bind the
original composed context hash captured before evaluation; permitted registered
source enrichment retains its separate evaluated-context checks. Exit contracts
and projection do not add a new TARL exit-policy decision.

The [native context contract](GOVERNED_VALUE_CONTEXT.md) defines the bounded
surface and remaining requirements. Checkpoints do not detect mutate-and-restore
between checks, guarantee atomicity against concurrent host mutation, or bind
dictionary insertion order and alias identity. Scope tokens are not portable
source provenance; arbitrary host code remains trusted. Global resource
containment, native external handoff validation, composite call receipts,
closure provenance, literal dictionary-key policy semantics, and rollback of
effects preceding exit denial require separate work. M3-M7 remain incomplete;
robotics remains deferred. Final candidate evidence belongs in the separate
[M3.5 record](operations/M3_VALUE_IDENTITY_VERIFICATION.md), not earlier totals.

### Milestones and dependency order

| Milestone | Work and prerequisites | Exit evidence |
|---|---|---|
| M1: trustworthy existing behavior | C01-C15, C17, C19-C27, authority lifetime, all newly revealed regressions | Full test suite with optional analysis/docs enabled, coverage floor, Ruff/Black/mypy, no unexplained failures, artifact verification |
| M2: usable data/application foundation | M1; collections, dictionary literals, enums/structs, binary/text conversion, real bounded network, practical application example | End-to-end .thirsty programs, malformed data controls, capability denial before effect, cleanup on failures |
| M3: language semantics and tooling | M2; separate M3.1-M3.4 integration records and M3.5 value-identity candidate; remaining numeric domains, broader Unicode/text tooling, default/named args, optional/result values, guest iterators/generators/comprehensions, protocols/generics, diagnostics and debugger | Executable language conformance corpus; formatter/parser round trips; error-span tests; supported-feature matrix |
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
| Guest writes through aliases of annotated native collections | Fixed for supported reference-interpreter writes in the November candidate | The runtime checks annotated elements, keys and values before mutation, including across guest calls and optional wrappers. Direct host mutation is a trusted embedding operation. Portable targets still need conformance tests. |
| General static typing is incomplete for dynamic Any and foreign values | Requires separate follow-up work | M3 inference and runtime boundary validation; no claim of whole-program type soundness. |
| Loop variables lost known element/key types and noniterables silently skipped execution | Fixed now in M3.4 | Known iterable descriptors retain element/key identity; E025 rejects known noniterables and native iteration raises for dynamic invalid values. Unknown Any and host iterators retain the documented dynamic/trusted boundary. |
| Unknown annotation names retain static Any fallback | Requires separate follow-up work | Define compatibility and diagnostics for unresolved names, forward declarations, and dynamic imports; do not silently treat the current fallback as checked type evidence. |
| Function parameter variance and callable common types erased incompatible possibilities | Fixed now in M3.4 | Contravariant parameters, covariant returns, exact retained alternatives, and checks against every known signature. Lambda inference, source callable annotations, mixed callable/noncallable joins, and quantified generics require separate follow-up. |
| Constructor aliases and nominal instances shared one descriptor | Fixed in M3.5 candidate; consult its integration record | ConstructorType retains struct/enum constructor identity through aliases, selections, and calls; known instances are not callable and constructor values cannot satisfy instance annotations. Fountain typing remains gradual. |
| Cascade returned an awaited value while the checker described Task[T] | Fixed in M3.5 candidate; consult its integration record | Actual result inference covers callbacks, aliases, collections, and pipes; noncallable operands evaluate once. A general runtime Task-value protocol remains separate work. |
| Governed native arguments/receivers/results and callback mutation could invalidate admission | Fixed in M3.5 candidate; consult its integration record | Bounded registered projection, receiver inclusion, reserved result binding, live snapshot checkpoints, and original policy-context proof binding; final evidence is recorded separately for M3.5. |
| Snapshot hashes omit order/alias identity and mutations hidden between checkpoints | Requires separate follow-up work | Specify an execution-sensitive witness or ownership/freeze model; test concurrent mutation, mutate/restore, insertion order, and shared aliases. No atomicity or immutability claim. |
| Native profile portability, complete call receipts, and policy namespace migration | Requires separate follow-up work | Define explicit external native adapters and authenticated declaration/code bindings, composite entry/exit receipts, and literal-key/argument/result namespace semantics; preserve current TARL paths meanwhile. |
| Core declarations without initializers retain a static annotation while the runtime value is none | Requires separate follow-up work | Add definite-assignment analysis with branch/loop controls; preserve the documented Core behavior until an intentional compatibility change. |
| PSIA / governance prototype services are excluded from the shipped `utf` package, require undeclared FastAPI/Pydantic/uvicorn, and contain simulated signatures/automatic or keyword-based decisions | Environment/dependency issue and separate follow-up | Keep outside the language authority path. Before activation, replace fake verdict/evidence paths, declare an optional dependency group, require authentication and broker integration, add service tests. No service was started in this task. |
| No complete TLS/DNS socket layer or remote package resolver | Requires separate follow-up work | M5/M6; numeric socket endpoints and local/stdlib package resolution fail explicitly outside supported scope. |
| Active imports honor caller/definer locks, but an already injected foreign callable has no proven defining-source identity | Requires separate follow-up work | M6 code-provenance binding for host adapters/callables, including source/runtime identity and active lock authorization. Keep Python embedding trusted until that boundary is specified and verified. |
| No complete compiled backend or Python ecosystem compatibility | Requires separate follow-up work | M3-M6 conformance and interoperability plan above. |
| Windows cannot exercise POSIX private-key permission enforcement | Environment/platform issue | Linux release CI is recorded for 0.9.0; repeat the relevant Linux validation for later changes and preserve each platform's skip separately from pass. |
| Independent Competence Register acceptance remains pending | Requires separate follow-up work | Submit current context-contract evidence for independent acceptance; do not rewrite historical FAIL entries into a new review outcome. |

## Change discipline

Before every semantic change: inspect callers, record the failing case, update
the implementation and affected tests/docs, and run focused validation. Then
run the integrated suite. Do not weaken checks to recover a green result.
Version changed artifact formats/methods, document migration, and preserve old
evidence. No new dependency, generated bundle, or declared capability may cross
another project's boundary without explicit source/destination authorization.
