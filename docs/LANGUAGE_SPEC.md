# Thirsty-Lang Language Specification

**Version:** Thirsty-Lang 0.9.1
**Copyright:** 2026 Thirsty's Projects LLC (Apache 2.0)

This is the concise normative family specification. For the integrated
tutorial, CLI encyclopedia, security contract, deployment guidance, and source
traceability, see [THIRSTY_LANG_UTF_101.md](THIRSTY_LANG_UTF_101.md).

---

## Overview

Thirsty-Lang (Universal Thirsty Family — UTF) is a six-tier governance-first
language family. The reference interpreter requires governance by default.
The tier labels identify implemented components and their specific contracts;
they do not establish general program correctness or a complete portable runtime.

---

## Tier 1 — Thirsty-Lang (Core)

The base language with water-metaphor syntax.

### Execution posture and semantic modes

The reference API `Interpreter()`, `thirsty run`, and `thirsty repl` require
governance unless a trusted host explicitly opts out. No module header grants
host authority. Headerless programs use governed semantics by default;
`core` retains ordinary semantics, `strict` requires initializers, and `pure`
additionally refuses mediated external effects. These modes do not remove the
default governance requirement. A `governed` declaration explicitly retains it.

The Python option `Interpreter(allow_ungoverned=True)` and CLI `--unsafe-core`
request compatibility execution. `--thirst-level core` alone does not. The CLI
discloses the opt-out and rejects conflicting policy/authority, lock, signing,
hardened, audit, and explicitly governed options. An explicit governed
declaration, configured runtime governance, or active governed caller retains
its floor. Language callables carry both defining and calling restrictions;
callbacks, aliases, imported closures, methods, and cascades cannot select only
the weaker side. Active pure/strict and caller/definer lock restrictions remain
applicable.

Pure computation does not need a policy. Mediated operations require an
allowing policy decision, including import, `write` to `stdout` for
`pour`/`print`, `read` from `stdin` for `sip`, and mapped sensitive stdlib
operations. Import permission does not grant operation permission. Stdlib
exports require an explicit effect or no-ambient-effect classification before
guest exposure. Trusted CLI result display is host presentation, not guest
output authorization. Authenticated authority, signed proofs, and durable
required auditing remain explicit host configurations with their own gates.

Input with lexer/parser failures must not execute as a recovered partial
program, including under compatibility opt-out. Failure provenance is retained
through the token/AST path. Formatting must reject malformed input before
writing; source tools use UTF-8 independently of host text locale.

These contracts mediate language execution. They do not confine arbitrary host
Python code, establish foreign-callable defining-source identity, or provide OS
memory/process isolation. Full static effect discovery, resource accounting,
and portable enforcement remain open requirements in the development plan.

### Keywords

| Keyword | Token | Purpose |
|---------|-------|---------|
| `drink` | DRINK | Variable declaration |
| `mut` | MUT | Mutable modifier |
| `pour` | POUR | Print/emit value |
| `sip` | SIP | Read input |
| `glass` | GLASS | Function declaration |
| `return` | RETURN | Return from function |
| `thirsty` | THIRSTY | If (conditional) |
| `hydrated` | HYDRATED | Else (conditional) |
| `thirst` | THIRST | Guard/when expression |
| `quench` | QUENCH | Default in guard |
| `refill` | REFILL | Loop (while/for) |
| `times` | TIMES | Repeat n times |
| `module` | MODULE | Module declaration |
| `import` | IMPORT | Import module |
| `as` | AS | Import alias |
| `and` | AND | Logical AND |
| `or` | OR | Logical OR |
| `not` | NOT | Logical NOT |
| `true` | BOOL_TRUE | Boolean true |
| `false` | BOOL_FALSE | Boolean false |
| `none` | NONE | Null value |

### Operators

| Operator | Token | Purpose |
|----------|-------|---------|
| `+` | PLUS | Addition / string concat |
| `-` | MINUS | Subtraction |
| `*` | STAR | Multiplication |
| `/` | SLASH | Division |
| `%` | PERCENT | Modulo |
| `==` | EQEQ | Equality |
| `!=` | NE | Not equal |
| `<` | LT | Less than |
| `>` | GT | Greater than |
| `<=` | LE | Less or equal |
| `>=` | GE | Greater or equal |
| `=` | ASSIGN | Assignment |
| `\|>` | PIPE | Pipe operator |
| `->` | ARROW | Return type arrow |
| `(` `)` | LPAREN/RPAREN | Grouping / calls |
| `{` `}` | LBRACE/RBRACE | Blocks |
| `[` `]` | LBRACKET/RBRACKET | Reservoir literals and indexing (`xs[i]`) |
| `:` | COLON | Type annotation |
| `,` | COMMA | Separator |

### Syntax Examples

```thirsty
module hello: governed

glass greet(name: String) -> String {
    return "hello, " + name + "!"
}

drink main = greet("thirsty world")
main
```

The remaining output examples require an explicit policy allowing
`action == "write" and target == "stdout"`, supplied through `--policy`.
Their Core headers do not waive that requirement.

```thirsty
module loop: core

// while form
drink mut i = 0
refill (i < 3) { pour i  i = i + 1 }

// for-each form
refill (x in [1, 2, 3]) { pour x }

// C-style form — the loop counter is implicitly mutable
refill (drink x = 0; x < 10; x = x + 1) {
    pour x
}

// repeat N times
times 3 {
    pour "hydrate"
}
```

Anonymous functions (lambdas) are first-class values:

```thirsty
module lambda: core

drink add = glass(a, b) { return a + b }
pour add(2, 3)
```

```thirsty
module branches: core

drink x = 1
thirsty (x > 0) {
    pour "positive"
} hydrated thirsty (x < 0) {
    pour "negative"
} hydrated {
    pour "zero"
}
```

### Types

- `Int` — Integer values
- `Float` — Floating-point values
- `String` — String values
- `Bool` — Boolean values
- `NoneType` — Null type

### Writable collections and value choices

A new list or dictionary literal takes its type from its destination when all
elements fit. For example, `drink xs: Reservoir[Float] = [1]` accepts an
integer through scalar widening. Once a writable collection has a known type,
assignment, argument passing, returns and field defaults preserve its key and
element types. A `Reservoir[Int]` alias cannot be passed to a parameter of
type `Reservoir[Float]` because that function could write a fractional value.
A slice copies the outer list. Its nested lists and dictionaries remain shared.

When an expression can select among known types, a read, write, call or
iteration must support every possible value. Straight-line reads of a fresh, fully literal
collection retain the type at a constant key or index. Calls, control flow, and
writes that can change the slot type discard that information. For example, assigning a loop element
of `[1, "two"]` to `Int` produces diagnostic `E021`. An incompatible return
produces `E023`. An explicit `Any` permits a dynamic boundary.

At runtime, binding a native list or dictionary to an explicit collection
annotation checks its current contents. The interpreter records the contract
on the object, so subsequent guest writes through an alias, including `Any`,
must satisfy it. A collection with only an inferred type receives static checking
until it crosses an explicit runtime collection boundary. A failed write leaves
the target intact. A typed shallow copy shares the contracts of its children.
A collection containing `Quenched[T]` preserves the optional wrapper. Its
payload may be absent (`none`). A present payload must satisfy `T`.

Validation supports nesting to depth 64 and at most 100,000 visited values per
operation. An interpreter and its guest imports retain up to 65,536 constrained
objects. A guest call between two interpreters joins their object contracts after
checking overlapping values. Closing the last connected interpreter releases
the retained objects. Direct Python mutation and host injection of the same
object into independent interpreters before their first guest call are trusted
embedding operations. Each independent interpreter can enforce only the
contracts it has observed. `Task`, `Result` and `Governed` lack a general guest value
representation for validating collection elements.

### Sequence operations (M3.1)

`value[index]` reads a native list, string, tuple, or bytes value using an
exact `Int`; booleans and coercible host objects are rejected. Negative
indices count from the end; an out-of-range scalar index raises `IndexError`.
String indices address Unicode code points and return `String`, without
normalization or grapheme segmentation. Bytes indices return `Int`.
Dictionary indexing retains native key lookup and missing-key errors.

`value[start:stop:step]` returns the same sequence type, with exclusive stop,
clipped bounds, and a nonzero step. Omitted or `none` bounds use sequence
defaults; negative steps reverse traversal. List slices are shallow copies.
The receiver, start, stop, and step evaluate once in that order before value
validation. Exceptions and governance denials stop evaluation immediately.
Indexed assignment supports lists and dictionaries; slice assignment is
unsupported and is rejected before operand effects.

The checker retains known list element and string types through these
operations. Known numeric division returns `Float`, and mixed `Int`/`Float`
arithmetic and comparisons accept either operand order. Dynamic `Any` remains
a runtime validation boundary. These changes do not establish complete static
typing or compiler parity; see the
[general-purpose reference](GENERAL_PURPOSE_LANGUAGE.md).

### Scalar Boolean and annotation contracts (M3.2)

`Bool` is separate from numeric arithmetic. The scalar operators `+`, `-`,
`*`, `/`, `%`, unary `-`, and ordering comparisons reject Boolean operands.
Scalar `==` and `!=` accept Bool/Bool and reject Bool/non-Bool pairs.
Binary operands evaluate once, left to right, before validation. Short-circuit
`and`/`or` still return an operand; `not` still uses truthiness. Native container
comparisons and dictionary hashing/equality retain their existing semantics;
this is not a recursive change to every value comparison.

Declared enum/struct identity is preserved through nested generic arguments,
including forward function signatures and recursive struct fields. A same-named
declaration in another scope is a different type. Known dictionary index types
must match their key annotation for reads and writes, with existing Int-to-Float
widening. Dynamic `Any` retains runtime/native-key behavior. An annotation is
retained for later assignment checks even without an initializer; core-mode
initialization still produces `none`, with no definite-assignment guarantee.
Unknown annotation names remain a gradual limitation.

### Execution ownership and limits (M4.1)

The [execution-control contract](EXECUTION_CONTROL.md) defines shared logical
ownership, finite host limits, explicit cascade thread transfer, cancellation,
and idle close. Default limits are 1,000,000 steps, a cooperative 30 seconds,
and 64 bound callable entries. A resource stop is outside guest exception
handling and prevents further guest cleanup. Previously completed mutations and
effects are not rolled back. Governed functions, morphs, and fountain methods
capture their lexical declaration environment; caller policy restrictions
remain active even though caller local variables do not replace free names.

### Callable and iteration contracts (M3.4)

Known callable assignment requires equal arity, contravariant parameters, and
covariant returns. A replacement accepts the inputs promised by its destination
and returns a compatible value. Common-type joins of known functions retain
their possible signatures in the internal `FunctionUnionType` descriptor.
These joins flatten existing alternatives and deduplicate exact descriptors
using nominal declaration identity; gradual compatibility with `Any` is not
exact equality. The descriptor represents one selected function. Calling it
must satisfy every alternative's arity and parameter types; the result type
joins the alternatives' returns. There is no overload dispatch. Arity and
argument mismatches report E030 and E021 respectively.

Runtime calls require exact positional arity for ordinary functions, lambdas,
morphs, governed functions, bound fountain methods, and fountain constructors.
Argument expressions retain their source evaluation order before callable entry.
The arity check then precedes parameter binding, body/contract execution, and
function-policy evaluation. Fountain construction checks before field defaults;
a leading `self` receiver is implicit in the caller's argument count, and no
initializer means zero arguments. Missing or excess arguments raise `TypeError`.
Struct construction keeps its existing exact field-count contract. These rules
do not add default/named arguments or a foreign-callable signature guarantee.

M3.5 rejects duplicate parameters in functions, lambdas, morphs, and methods
with E010. Runtime binders raise `TypeError` before binding, contracts, or body
execution; initializer validation also precedes field defaults. This prevents
duplicate receiver names from giving policy and body different receiver values.
Source methods accept explicit leading `self` or implicit `this`. Explicit
leading `this` is a host-AST convention only; the parser reserves that keyword
and rejects it as a source parameter. Any remaining method parameter named
`this` reports E901 and is rejected by runtime binding. A nonleading `self`
remains an ordinary parameter; the actual receiver is separately included as
`this`. Caller argument expressions still evaluate before callable entry.

With a known function or callable choice on the right, both `left | right` and
`left -> right` are checked as calls with one argument and use the callable's
result type. Both operands evaluate once, left to right. Their noncallable
fallbacks remain distinct: `|` returns the left value and `->` the right value.
Unknown callables remain dynamic. `TypeVariable` descriptors match by name;
different names do not assign and join to `Any`. Callable annotation syntax,
lambda signature inference, and quantified generics are not introduced.
Mixed callable/noncallable common types still fall back to `Any`.

The initial M3.4 constructor and cascade pipe fallbacks are superseded by the
M3.5's value-identity rules below. Historical M3.4 evidence remains
scoped to its recorded source.

For-each checks the iterable expression in the enclosing scope before binding
the loop variable. `Reservoir[T]` yields `T`, `Dict[K, V]` yields `K`, and
`String` yields `String`, preserving nested nominal identity. The variable is
immutable and local to each iteration. Known noniterables produce E025;
unknown `Any` stays dynamic. Runtime evaluation acquires the native iterator
once after evaluating the iterable once; it does not eagerly consume it.
Dynamic noniterables raise `TypeError`. Iterator exceptions, returns, thrown
values, scope restoration, and governance denials propagate through the existing
execution boundaries, including cascades. Valid host sequence iteration through
`__getitem__` is supported along with `__iter__`/`__next__`.

Host iterator methods remain trusted Python code. These contracts provide no
global iteration budget, guest generator syntax, or complete static type
soundness. See the
[M3.4 verification record](operations/M3_CALLABLE_ITERATION_VERIFICATION.md)
for the increment's evidence and limitations.

### Constructor and awaited-result types (M3.5)

Struct and enum declaration expressions produce an internal `ConstructorType`;
their nominal annotations describe instances. Constructor aliases retain both
callability and declaration identity, including through collections and callable
choices. A known constructor alias can resolve an instance annotation. An
instance value cannot stand in for that type binding, and a constructor value
cannot satisfy an instance annotation. Struct fields require an instance;
enum variant access requires its constructor or a known constructor alias.

Struct signatures follow declared field order/types and return their nominal
instance type. Enum signatures take one argument and return their enum type;
variant-value validity is checked at runtime. The existing `new name(args)`
form and ordinary calls use the same known-signature rules. Known noncallables
report E031; dynamic invalid calls raise `TypeError`. Fountains and unresolved
foreign values retain their existing gradual typing.

`FunctionUnionType` alternatives may be functions or constructors. Calls and
known `|`/`|>`/`->` invocations must satisfy every possible signature and join
their returns. Exact nominal-aware deduplication and callable variance still
apply. A constructor is callable without becoming interchangeable with an
instance. Noncallable pipe fallbacks remain: `|`/`|>` returns the left operand,
`->` the right operand. Mixed callable/noncallable joins remain `Any`.

`cascade expression` has the type of its awaited expression, including nested
collections and known returned callable choices; it does not wrap that type in
`Task`. Statement operands are still checked. Runtime cascade awaits completion,
propagates errors and governance restrictions, and evaluates callee/argument
expressions once even when the callee is noncallable. Explicit/host `Task`
descriptors remain gradual in call/member/pipe contexts pending a runtime
task-value contract. No new asynchronous language protocol is introduced.

### Governed native call contexts (M3.5)

The interpreter projects governed call values into independently owned JSON
before entry or exit predicates. Exact JSON primitives, finite floats, lists,
and string-key dictionaries remain accepted subject to bounds and TARL path
validation. Registered structs, fountains, and enums use the
`thirsty.native-value.v1` profile with runtime scope/declaration identity and
declared fields or a literal enum variant. Ordinary JSON parameter paths remain;
native fields are addressed through `parameter.fields.field`. Raw dictionary
keys containing the `__thirsty_native__` marker as a dotted segment are rejected.
Unsupported foreign values, cycles, malformed native layouts, and exceeded
budgets deny without invoking conversion or traversal hooks.

The profile limits depth to 32, nodes to 10,000, aggregate UTF-8 string/key bytes
to 1,048,576, and integer magnitude to 4,096 bits. Generated metadata and repeated
alias expansions count. These are projection limits, not a bound on complete
encoded JSON, source providers, body execution, or the embedding process.

Explicit `self` and implicit `this` receivers participate in call contexts.
Governed/contract-bearing parameters named `result` deny before entry callbacks
and body execution; exit reserves that binding for the returned value. Ordinary
uncontracted parameters and nested fields named `result` remain valid. Exit
projects current arguments/receiver and the result after the body, even if no
exit predicate mentions it. A representation failure prevents the return.

Live values are compared with the same admitted snapshot after callback-capable
checks and before handoff. Every active caller/definer policy must admit that
snapshot. Positive policy proofs must bind the original composed context hash
captured before evaluation; registered-source enrichment retains separate
evaluated-context checks. Projection and contracts at exit do not add a TARL
exit-policy decision. An intermediate ALLOW does not certify final handoff.

The [governed value context contract](GOVERNED_VALUE_CONTEXT.md) defines exact
layouts and limitations. Checkpoints do not ensure atomicity, capture mutations
restored between checks, or bind dictionary insertion order and alias identity.
Native identities are runtime-local; external native handoff verification,
portable code/closure provenance, composite receipts, and a full argument/result
namespace remain separate work. Prior body effects cannot be rolled back by
exit denial. Host embedding remains trusted. The M3.5
[verification record](operations/M3_VALUE_IDENTITY_VERIFICATION.md) reports
integration evidence for this implementation.
Broader M3-M7 implementation remains open and ecological robotics is deferred.

### CLI Commands

| Command | Description |
|---------|-------------|
| `thirsty run <file>` | Execute with governance required by default |
| `thirsty run <file> --unsafe-core` | Explicit, disclosed trusted-host compatibility opt-out; stronger restrictions remain active |
| `thirsty repl` | Start REPL with governance required by default |
| `thirsty build <file> --target js --policy <policy>` | Compile the supported governed Node subset with a bound TARL policy |
| `thirsty run-js <file.js> --policy <policy> --authority <subject>` | Verify the compiled artifact and run it through the installed Node host |
| `thirsty build <file> --target js --allow-governance-loss` | Build the supported JS subset with mandatory loss disclosure |
| `thirsty prove <file> --policy <policy>` | Emit static proof obligations without executing effects |
| `thirsty explain-denial <file> --policy <policy>` | Explain unmet static governance obligations |
| `thirsty fmt <files>` | Format valid UTF-8 source; refuse malformed input before writing |
| `thirsty new <name>` | Scaffold governed source/metadata with a computation-only example |
| `thirsty govern <file>` | Governance operations |
| `thirsty add <package>` | Add dependency |
| `thirsty audit` | Audit dependencies |
| `thirsty lock` | Generate lockfile |
| `thirsty doctor` | Project health check |
| `thirsty lsp` | Start the TARL language server |
| `thirsty docs` | Generate documentation |

Governed Node execution requires the adjacent `.thirsty` source, the installed language
package, Node.js, the host-selected policy and a host-asserted subject. The launcher
recompiles with that policy, compares the complete artifact and passes the verified
bytes to Node. The canonical TARL broker authorizes source `pour` and the CLI display
of `main` as `write` to `stdout`. Only an explicit ALLOW permits output. A policy can
restrict `authority` or `authority_subject`; these bare subjects are unauthenticated.
The host accepts scalar and flat typed reservoir annotations, including indexed reads
and checked writes through aliases. Unsupported effects, source constructs and policy
features fail closed. The policy profile accepts one optional `policy NAME` header and
ordered `when ... => ALLOW|DENY|ESCALATE` rules with a complete derived TARL schema.
It exposes `action`, `target`, `authority`, `authority_subject`,
`authority_authenticated` and `authority_grants`. The asserted subject has
`authority_authenticated = false` and an empty grants list. Build diagnostics reject
composition, time windows, external sources, duplicate conditions and unknown fields.
The separate [stdout shield profile](DEFENSIVE_COMPARTMENTS.md#running-the-first-milestone)
accepts a verified expiring subject and a source/site/record grant. All
handles for a run share one publication. Only a policy-bound JS build may
emit a shield artifact. Compatibility builds for other programs on JS, LLVM and Pyodide require
`--allow-governance-loss` and persist the disclosure before executable output.
Manifests distinguish requested
opt-out and effective artifact governance. A manifest alone does not prove
successful artifact production.

Static reports identify declared semantic mode, effective governance, and
concrete discovered obligations. Computation without known gated operations
does not require policy/authority/audit merely because governance is enabled.
Reports remain syntactic and explicitly incomplete for dynamic dispatch,
callable aliases, and effects inside imported-module bodies.

---

## Tier 2 — Thirst of Gods

Applies a structural AST contract over the Tier 1 object-oriented, cascade, and
structured-error constructs before running the ordinary interpreter.
Structural compliance does not grant capabilities: execution retains the
reference interpreter's default governance requirement. Restricted delegation
from `thirsty run` is refused when options cannot be preserved; convert to
Tier 1 source and supply the required host configuration. Direct JavaScript
transpilation requires the same explicit loss consent and mandatory disclosure
as `thirsty build`.

### Keywords

| Keyword | Token | Purpose |
|---------|-------|---------|
| `fountain` | FOUNTAIN | Class declaration |
| `cascade` | CASCADE | Async function |
| `spillage` | SPILLAGE | Try block |
| `cleanup` | CLEANUP | Resource cleanup |
| `finally` | FINALLY | Finalizer |
| `error` | ERROR | Error handler |
| `throw` | THROW | Throw error |
| `this` | THIS | Self reference |
| `new` | NEW | Instantiate class |

### Syntax Examples

```thirsty
fountain Counter {
    drink count: Int = 0

    glass increment() {
        this.count = this.count + 1
        return this.count
    }
}

drink c = new Counter()
c.increment()
```

```thirsty
spillage {
    drink result = risky_operation()
} error (e) {
    pour "Error: " + e
}
```

---

## Tier 3 — T.A.R.L. (Thirsty's Active Resistance Language)

A policy-as-code engine with default-DENY governance.

### Keywords

| Keyword | Token | Purpose |
|---------|-------|---------|
| `policy` | POLICY | Policy declaration |
| `when` | WHEN | Policy condition |
| `ALLOW` | ALLOW | Allow verdict |
| `DENY` | DENY | Deny verdict |
| `ESCALATE` | ESCALATE | Escalate verdict |

### Syntax

```tarl
policy example:
    when user.role == "admin" => ALLOW
    when user.ip in blacklist => DENY
    when true => ESCALATE
```

TarlVerdict values: ALLOW, DENY, ESCALATE. Default-DENY applies when no rule matches.

### Authoritative context contract

T.A.R.L. evaluates one canonical context representation:
`tarl.context.nested-json.v1`. `prepare_context()` normalizes dotted, nested, and
equivalent mixed caller inputs using `tarl.context.dotted-path-expansion`,
version `1`. Dotted identifiers then traverse nested JSON objects:

```json
{"user": {"role": "admin"}}
```

A flat key such as `{"user.role": "admin"}` normalizes to the object above.
Equal mixed forms converge; contradictory values, malformed dotted paths,
duplicate JSON keys, non-string object keys, non-finite numbers, cycles, and
values outside the finite JSON domain fail closed.

Path resolution preserves four distinct states: `RESOLVED(value)`, `MISSING`,
`TYPE_ERROR`, and `REPRESENTATION_CONFLICT`. Only `RESOLVED(value)` may enter
ordinary comparison, membership, negation, safe functions, or boolean algebra.
Missing is not false; invalid is not false; unresolved is not evidence.

A raw evaluator may report `ALLOW` for diagnostic use. Load-bearing positive
authority additionally requires a complete context schema that passed against
the exact evaluated nested representation and is bound into the proof. The
proof records the original and canonical/evaluated context hashes,
representation identifier, normalization algorithm identifier and version,
conflict status, schema fingerprint/representation/result, policy hash,
matched rule and condition, verdict, trace, evaluation time, and applicable
expiry.

Registered sources are the only supported context transformation. The proof
binds both the original request and exact source-enriched evaluated context;
verification requires both, and removing only permitted top-level
`source:<name>` additions must reproduce the original request.

T.A.R.L. condition validation is eager and fail-closed. Both operands of
`and`/`or` are evaluated, and `ALL(collection, item -> predicate)` and
`ANY(collection, item -> predicate)` validate every collection element before
accepting the aggregate result. Missing paths, wrong intermediate types, or incompatible
predicate values therefore cannot be hidden by boolean or iteration order.
An empty quantifier collection fails closed; it is not authorization evidence.

Comparisons are type-strict. Integers and floats interoperate as numbers;
strings never coerce to numbers, including in ordering and equality. Numeric
operands and every arithmetic result must be finite. `NaN`, infinities, and
overflow to infinity are evaluation errors that deny the affected policy
decision. Quantifier binder names beginning with `__tarl_` are reserved for
trusted runtime state and are rejected during parse and evaluation.

Temporal metadata is strict. Invalid `valid_from`/`valid_until` timestamps,
`for:` or `if_unresolved_after` durations, and expiry verdicts reject the
policy. `on_expiry: ALLOW` is forbidden. `valid_until` is an exclusive cutoff,
and a matched verdict expires at the earlier of that effective policy cutoff or
its rule-level `for:` duration.

Independent verification rejects unsigned proofs by default and can enforce
exact policy/context/schema bindings, Ed25519-only attribution, freshness,
expiry, revocation, and durable replay prevention. A configured trusted clock
must return a timezone-aware verified value; it never silently falls back to
host time after failure. Quorum promotion requires an independently verified,
schema-passed, signed `ESCALATE` proof plus distinct Ed25519 approvals over the
complete proof digest and explicit request/time/freshness/replay bindings.

---

## Tier 4 — Shadow Thirst

Mutation analysis and invariant verification.

### Keywords

| Keyword | Token | Purpose |
|---------|-------|---------|
| `shadow` | SHADOW | Shadow block |
| `invariant` | INVARIANT | Invariant declaration |
| `canonical` | CANONICAL | Canonical form |
| `promote` | PROMOTE | Promote block |
| `reject` | REJECT | Reject block |

### Built-in Analyzers

The analyzers parse each `shadow` / `invariant` / `canonical` block with
Thirsty-Lang's own lexer + parser and reason over the resulting **AST** (with a
lexical fallback when a block does not parse):

1. **Plane Isolation** — Walks the shadow block for writes into `canonical_*`
   bindings or calls into the canonical plane
2. **Determinism** — Flags *calls* to non-deterministic functions (`now()`,
   `rand()`, `uuid()`, …), not like-named variables
3. **Resource Estimation** — Estimates CPU/memory from loop, call, and
   allocation nodes
4. **Purity Spring** — Checks the invariant block for impure calls / output
   statements
5. **Memory Evaporation** — Counts allocation nodes (`new`, reservoir literals,
   floods)
6. **Canonical Convergence** — Compares shadow and canonical via structural AST
   equivalence (alpha-renamed shape + return arity)

---

## Tier 5 — TSCG (Thirsty Symbolic Constraint Grammar)

Symbolic security expressions with 9 core symbols.

### Symbols

| Symbol | Name | Purpose |
|--------|------|---------|
| COG | Cognition | Cognitive capability |
| DNT | Do Not Track | Privacy constraint |
| SHD | Shield | Protection boundary |
| INV | Invariant | Invariant condition |
| CAP | Capability | Capability grant |
| QRM | Quorum | Consensus requirement |
| COM | Communication | Communication channel |
| ANC | Anchor | Trust anchor |
| RFX | Reflexive | Self-reference |

### Operators

- Pipeline: `->`
- AND-combine: `^`
- OR-combine: `||`

For boolean operands, `^` evaluates as logical **AND** (conjunction — *not*
XOR, despite the glyph) and `||` evaluates as logical OR. Both operands must be
bool: a mixed `bool`/non-`bool` combine is a type error (rejected statically and
refused at runtime) so a malformed predicate fails closed rather than coercing.
For structured operands, `^`/`||` keep their runtime composition behavior:
dictionaries merge and reservoirs concatenate.

All expressions are SHA-256 canonicalized.

---

## Tier 6 — TSCG-B (Thirsty Symbolic Constraint Grammar — Binary)

Binary frame protocol for TSCG expressions.

### Frame Format

A version 1 frame starts with `TSGB`, followed by a one-byte version, one-byte
flags and a two-byte big-endian payload length. The trailer contains CRC32 of
the header and payload, then SHA-256 of those bytes and the stored CRC32.

The 0.9.1 standard library exposes the single-frame UTF-8 text profile:

```thirsty
import "thirst::tscgb" as frames
drink wire = frames.encode("hello")
drink text = frames.decode(wire)
```

Encoding preserves whitespace and accepts at most 65,535 UTF-8 bytes.
Decoding requires exactly one frame, zero flags, valid checksums and strict
UTF-8. It accepts native bytes or a list of integer octets such as the
`data` field returned by `thirst::net`. A stream reader must assemble a
complete frame before calling `decode`. The import uses the ordinary import policy. Both operations run in
memory. The Python frame API also supports flagged frames and the stream
decoder accepts concatenated frames.


---

## License

Copyright 2026 Thirsty's Projects LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
