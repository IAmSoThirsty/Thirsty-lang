# General Purpose Language

Thirsty-Lang 0.9.0 was published and its artifact identity verified on
2026-09-06, as recorded in the local release receipt. Updated 2026-09-08, this
reference includes local M3.1 sequence, M3.2 Boolean/type-coherence, M3.3
governance/security-defaults, M3.4 callable/iteration work, and the M3.5
constructor/cascade and governed native-value candidate. These
post-release changes remain uncommitted and unreleased; they do not describe
the published 0.9.0 package.
See [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) for recorded release evidence,
correction dependencies, and remaining milestones. Python compatibility is not
claimed. Historical M3.1 results and limitations are recorded in
[M3_SEQUENCE_VERIFICATION.md](operations/M3_SEQUENCE_VERIFICATION.md).
Consult the separate M3.2 integration results in
[M3_TYPE_COHERENCE_VERIFICATION.md](operations/M3_TYPE_COHERENCE_VERIFICATION.md).
The later security-defaults work has a separate
[verification record](operations/M3_SECURITY_DEFAULTS_VERIFICATION.md); older
test totals do not validate newer changes. M3.4 has its own
[callable and iteration verification record](operations/M3_CALLABLE_ITERATION_VERIFICATION.md).
The M3.5 candidate's final integration evidence is reported separately in
[M3_VALUE_IDENTITY_VERIFICATION.md](operations/M3_VALUE_IDENTITY_VERIFICATION.md).

## Governance First Language, Security Default

The reference interpreter, `thirsty run`, and REPL require governance without
an enabling flag. Arithmetic, collections, and other computation without
mediated effects can run without a policy. Imports, `pour`/`print`, `sip`, and
sensitive library operations need an allowing policy decision. Even an import
of a computation-only standard library is an explicit import operation.
Allowing a namespace does not grant its file, network, process, or other effects.

Module headers specify semantics. `core` retains ordinary initialization,
`strict` rejects uninitialized declarations, and `pure` additionally refuses
mediated external effects. None grants permission to bypass host governance.
An explicit `governed` declaration retains its governance floor. Caller and
defining-function restrictions both apply through language calls, methods,
callbacks, imports, aliases, and cascades; selecting a weaker callee cannot
cancel a governed or pure caller's restrictions.

Trusted hosts can explicitly choose compatibility execution using
`Interpreter(allow_ungoverned=True)` or `thirsty run --unsafe-core file.thirsty`
and `thirsty repl --unsafe-core`. The CLI discloses the choice and rejects
combining it with policy/authority, locks, hardened mode, signing, required
audit, or an explicit governed request. Stronger source/caller restrictions
still apply. `--thirst-level core` by itself does not opt out.

`thirsty new project` creates governed source and matching project metadata.
Its example returns a computed value for trusted CLI presentation, without
granting guest output capability. This distinction also applies to REPL result
display. Policies, authenticated credentials, proof signers, and required audit
archives remain explicit host configuration, not silently provisioned privileges.

Lexical and parser failures retain failure provenance and cannot become a
successful partial program, including in explicit compatibility execution.
Formatting refuses malformed source before writing. Source tooling reads and
writes UTF-8 independently of the host's text locale.

These are language/runtime boundaries. They do not establish OS isolation,
global memory/time limits, whole-program type safety, or the provenance of
arbitrary Python values a trusted embedding host injects.

## Ordinary data and functions

```thirsty
module report: governed
import "thirst::collections" as c
import "thirst::json" as json

drink rows = [{"category": "books", "units": 2}, {"category": "books", "units": 3}]
glass units(row) { return row.units }
drink report = {"orders": length(rows), "units": c.sum(c.map(units, rows))}
pour json.stringify(report)
```

Save that program as `report.thirsty` and use an explicit `report.tarl` policy:

```tarl
policy report_example
when action == "import" and (target == "thirst::collections" or target == "thirst::json") => ALLOW
when action == "write" and target == "stdout" => ALLOW
when true => DENY
```

Run `thirsty run report.thirsty --policy report.tarl`. This policy allows only
the two named imports and console output. It does not require authenticated
identity; select hardened execution and supply verified credentials/signing
configuration when that is required. Collection callbacks retain their active
effect restrictions.

Dictionary entries evaluate in source order. Keys must be hashable guest
values. Repeated keys raise; a literal never silently overwrites an earlier
entry. Keys following Python numeric equality, such as `1` and `true`, collide.
Use explicit subscript assignment or `with_item` when replacement is intended.
Iteration visits insertion-ordered keys. JSON objects require string keys.

```thirsty
enum Status { Pending, Complete }
struct Record { name: String
                status: Status }
drink item = new Record("report", Status.Pending)
item.status = Status.Complete
```

Enum values retain their enum identity. Struct construction checks arity and
field types; later field writes are checked too. These are nominal runtime
types. Struct validation occurs at construction and field replacement; mutation
through an alias to a nested container can still escape those checks.
Nested collection annotations such as `Dict[String, Reservoir[Int]]`
are parsed and literal elements are checked, including function arguments and
returns. Interfaces/protocol conformance and polymorphic generic functions
remain planned.

Ordinary `and`/`or` short-circuit and return the selected operand. TARL retains
its stricter eager validation rules for policy expressions. An uncaught language
`throw` is an error with a failing CLI exit; handled `spillage` remains usable.

## Indexing and slicing: M3.1

```thirsty
drink values = [0, 1, 2, 3, 4]
drink last = values[-1]
drink alternating = values[1:5:2]
drink reversed = values[::-1]
values[-1] = 9
```

Indexed reads accept exact native lists, strings, tuples, bytes, and
dictionaries. Sequence indices must be `Int`; `Bool`, floats, and implicit
integer conversions are rejected. Negative indices count from the end.
An out-of-range index raises `IndexError`, including on an empty sequence.
Bytes indexing returns an integer from 0 through 255. String indices count
Unicode code points: combining characters remain separate, and no grapheme
segmentation or normalization occurs.

Dictionary indices retain native hashable-key semantics, including enum and
tuple keys, numeric/boolean key equality, and `KeyError` for missing keys.
Keys are not implicitly converted. Only lists and dictionaries support indexed
assignment. A list assignment replaces an existing element and cannot grow the
list; strings, tuples, and bytes reject assignment.

`value[start:stop:step]` accepts lists, strings, tuples, and bytes. Bounds may be
omitted or `none`; supplied bounds must be `Int`, excluding `Bool`. The stop is
exclusive, negative bounds count from the end, outlying bounds are clipped,
and negative steps traverse backwards. A zero step raises `ValueError`, even
for an empty sequence. Very large integer bounds are clipped without
integer-overflow errors. The result preserves the
container type. A list slice creates a new outer list with shared element
references; it does not deep-copy nested mutable values. Immutable full slices
may reuse the original object.

A read evaluates its receiver, then index, once each. A slice evaluates its
receiver, start, stop, and step once each in that order, then validates the
container and bounds. An exception during evaluation stops later operands;
an invalid value that evaluates normally is checked after the remaining bounds
have evaluated. Indexed assignment preserves the existing order: right-hand
side, receiver, index, then validation and mutation. Slice assignment is
unsupported and is rejected before evaluating its right-hand side or target.
Pure and governed restrictions continue to apply to callbacks in every operand.

Sequence containers must be exact native values, not Python subclasses or
objects providing indexing hooks. Sequence indices and slice bounds do not
invoke host `__index__` conversions. Dictionary keys can still invoke their
Python `__hash__`/`__eq__` methods through trusted embedding; this is a separate
boundary, not a claim that all host callbacks are blocked.

The checker preserves known `Reservoir[T]` and `String` slice types and checks
known index/bound types. Imported tuple and bytes constructors currently return
static `Any`; their runtime checks still apply. Numeric `/`, including
`Int / Int`, has static type `Float`. Mixed `Int`/`Float` arithmetic and
comparison checks accept both operand orders. `and`/`or` unify the possible
operand types instead of assuming a `Bool` result; incompatible alternatives
become `Any`. When an annotated `Reservoir[T]` receives a slice of a source
literal, all source elements are checked conservatively. For example,
`drink values: Reservoir[Int] = [1, "wrong"][:1]` is rejected: the checker
does not execute bounds to prove that the incompatible element is excluded.

M3.1's recorded proof-boundary repair advanced Shadow admission to engine
`0.3.0` and convergence methods `v3`. The current M3.2 repair below supersedes
that engine. Historical verification preserves integrity evidence; it does not
independently replay the stored proof.

## Boolean and type coherence: local M3.2 increment

Scalar Boolean values no longer act as numbers in language operators.
Arithmetic, ordering, and arithmetic negation with a `Bool` raise a type error.
`Bool == Bool` and `Bool != Bool` are valid; equality or inequality between a
Bool and any non-Bool is rejected, including `true == 1`. Known invalid operands
are diagnosed by the checker; runtime checks cover values whose static type is
`Any`. Ordinary `and`/`or` retain short-circuit operand selection, and `not`
retains its existing truthiness behavior.

This scalar contract does not recursively change container equality or
dictionary hashing/equality. Native nested values keep their prior comparisons;
dictionary keys such as `true` and `1` still collide. A known `Dict[Int, T]`
annotation rejects a Boolean index statically, while `Dict[Any, T]` keeps the
dynamic native-key behavior.

```thirsty
enum State { Queued, Done }
struct Row { state: State }
drink groups: Dict[string, Reservoir[Row]] = {"pending": [new Row(State.Queued)]}
drink first: Row = groups["pending"][0]
first.state
```

Nested generic annotations preserve declared enum and struct types. The checker
uses per-declaration identity, so separate declarations with the same name and
fields are distinct types. It prepares nominal descriptors before top-level
function signatures, including recursive struct placeholders. Each full function
signature resolves in its declaration scope before parameter value bindings can
shadow type names. Runtime declarations still execute in source order. Lowercase
primitive aliases work inside nested annotations. An explicitly shadowing nominal
declaration resolves in its lexical scope, including existing runtime struct-field
checks.

All existing generic descriptors check their constructor, argument count, and
each argument during assignability and unification. This includes `Task`,
`Result`, `Governed`, and custom generic descriptors. Malformed annotations and
excess arguments report errors instead of discarding information. Unknown leaf
names retain static `Any` fallback; omitted arguments retain compatibility
defaults, such as `Result[Int]` resolving to `Result[Int, Any]`. This does not
add runtime implementations for previously unsupported generic forms.

Known dictionary index types are checked against the declared key type on both
reads and writes. `Any` remains dynamic. An annotation is also retained
statically when its declaration has no initializer; Core execution still binds
`none` in that case. No definite-assignment guarantee or general runtime
enforcement of variable/function annotations is implied. Struct construction
and field writes keep their existing runtime checks; shared nested aliases can
still escape later validation.

Malformed struct/interface members now produce a progressing parser diagnostic
instead of repeating on the same token. Standalone cascade statements check
their operands and arguments. The accompanying Shadow correction prevents a
symbolic proof from equating Boolean `true` with integer `1` and advances the admission engine
to `0.4.0`, with `alpha-renamed-ast-equivalence/v4` and
`z3-symbolic-equivalence/v4`. Engines `0.1.0`, `0.2.0`, and `0.3.0` require
explicit historical integrity verification; current assurance requires
reanalysis.

Unknown annotation diagnostics and mutation through annotated aliases remain
separate follow-ups in the development plan. The next increment below addresses
known callable signatures and loop element inference. Broader M3 tooling and
robotics remain open and deferred respectively.

## Callable consistency and iteration: local M3.4 increment

The checker retains the possible signatures when a value is selected from known
functions, including a collection of functions. Internally, `FunctionUnionType`
represents one selected callable with several possible signatures. Calls must
satisfy the argument count and parameter types of every alternative; the checker
joins their return types. This does not perform overload dispatch or choose a
different function based on argument types.

```thirsty
glass increment(value: Int) -> Int { return value + 1 }
glass half(value: Float) -> Float { return value / 2 }

drink operations = [increment, half]
drink mut total: Float = 0.0
refill (operation in operations) {
    total = total + operation(4)
}
total
```

This computation returns `7.0` without a policy. The loop retains both known
signatures; `4` is valid for each, and the call's static result is `Float`.
Changing the argument to `4.5` is a static error because `increment` requires
`Int`. Selecting `operations[0]` still retains the collection's possible
signatures; constant-index narrowing is not implemented.

Callable common-type joins flatten existing alternatives and deduplicate only
exact descriptors, including nominal declaration identity and nested arguments.
`Any` parameters and broader/narrower signatures are not considered exact
duplicates. Different arities remain visible and an invocation that cannot
satisfy every alternative reports E030. Parameter incompatibility reports E021.
Callable assignment uses contravariant parameters and covariant returns: a
replacement must accept the inputs promised by the destination and return a
compatible result. For example, accepting `Float` can replace accepting `Int`
under numeric widening, provided the result contract also fits; the reverse
would accept calls the replacement cannot support.

For a known callable on the right, `value | function` and `value -> function`
check one argument and retain the joined result type. Existing noncallable
fallback behavior remains: `|` returns its left value and `->` returns its
right value after evaluating both operands. An unknown callable remains dynamic.

M3.4 initially checked direct nominal constructor names and kept ambiguous
constructor aliases and Task/cascade operands gradual. The M3.5 candidate below
replaces those constructor and awaited-result limitations with explicit types.

The descriptor API also compares `TypeVariable` names consistently: equal
names match, different names do not assign and join to `Any`. This is descriptor
consistency, not quantified generic functions. No callable annotation syntax,
lambda signature inference, or whole-program type-soundness guarantee is added.
Mixed callable/noncallable heterogeneous joins and unknown values still become
`Any`; container mutation through aliases can still escape annotation checks.

Runtime positional arity is exact for ordinary functions, lambdas, morphs,
governed functions, bound fountain methods, and fountain constructors. Missing
or excess arguments raise `TypeError` before parameter binding, body execution,
contract predicates, or function-policy evaluation. Caller expressions still
evaluate once in their existing order before entering the callable; an arity
error does not undo argument effects. Fountain initialization checks the explicit
argument count before field defaults, excludes a leading `self` receiver, and
requires zero arguments when no initializer exists. The implicit `this` receiver
continues to work. Struct construction retains its exact field-count check.
This does not add default or named arguments or validate foreign Python callable
signatures on behalf of the host.

M3.5 also rejects duplicate parameter names: the checker reports E010 for
functions, lambdas, morphs, and methods; runtime binders raise `TypeError`
before binding, contracts, or bodies, and initializers before field defaults.
This prevents a duplicate `self` from making policy and body use different
receivers. Source methods support leading `self` or implicit `this`; leading
`this` is accepted only in host-created ASTs, since it is a reserved source
keyword. A remaining `this` parameter conflicts with the bound receiver and
reports E901 in method AST checking, with runtime rejection as well. A
nonleading `self` is still an ordinary parameter; the actual receiver remains
separately bound and included as `this`. Caller argument effects are not undone.

For `refill (item in iterable)`, the checker resolves `iterable` in the enclosing
scope before introducing `item`. Known `Reservoir[T]` elements have type `T`,
`Dict[K, V]` elements are keys of type `K`, and string elements have type
`String`. Nested and same-named nominal declarations retain their identity.
The loop binding is immutable and local to each iteration. Unknown iterable or
element types remain dynamic. A known noniterable reports E025 at its expression;
an unresolved name keeps its original diagnostic without an extra E025.

Runtime iteration evaluates the source once and uses its native iterator
protocol without materializing it first. Lists, dictionary keys, strings,
tuples, bytes, generators, and valid host `__getitem__` sequence objects follow
that protocol. Invalid dynamic values now raise `TypeError` instead of silently
skipping the body. Iteration order, per-iteration closure scope, early returns,
thrown values, iterator exceptions, cascades, and governance denials retain
their execution behavior. Ordinary errors remain catchable by `spillage`;
governance denials propagate.

Host-provided iterators remain trusted Python inputs, including code inside
`__iter__`, `__next__`, or `__getitem__`. This increment adds neither guest
generator syntax nor iteration budgets. Global resource accounting, cancellation,
and hostile-host isolation remain M4 work.

## Value identity: local M3.5 candidate

Struct and enum constructor values now have an internal `ConstructorType`,
distinct from the nominal instance descriptor. The distinction survives aliases,
collection selections, and known callable choices. Nominal annotations denote
instances, including annotations resolved through a known constructor alias:

```thirsty
struct Row { value: Int }
drink build = Row
drink row: build = new build(7)
drink answer: Int = row.value
answer
```

The alias keeps the field signature and constructed `Row` identity. A constructor
value cannot satisfy an instance annotation. Calling a known instance, or using
it as `new value(...)`, reports E031; a dynamic noncallable raises `TypeError`.
Struct fields require an instance, while enum variants are accessed through
their constructor, including an alias. Enum construction takes one argument;
valid variant strings or members are checked at runtime.

Known ordinary calls, `new`, `|`/`|>`, and `->` check the same signatures.
`FunctionUnionType` may retain function and constructor alternatives; every
alternative must accept the argument count and types, and returns are joined.
This remains one selected callable, without overload dispatch. Instance pipe
fallbacks remain unchanged. Fountain types, explicit `Any`, foreign values, and
mixed callable/noncallable joins retain their documented gradual limits.

The type of `cascade expression` is now the expression's awaited result. For
example, cascading a known `Int`-returning function yields `Int`; a known
returned callable retains its signature for later calls and pipes. Nested
collections, assignments, and return checks use that result directly. Declaring
such an `Int` result as `Task[Int]` is a mismatch. Explicit/host `Task`
descriptors remain gradual until a runtime task-value contract exists. The
runtime still awaits work and preserves errors and governance restrictions;
this adds no async syntax or scheduler guarantees. A noncallable cascade call
now rejects after evaluating its callee and arguments once, without repeating
their effects.

### Governed native values and live snapshots

Governed function and contract-bearing method contexts can contain registered
native structs, fountains, and enum members, including nested fields and results.
The bounded projector copies exact JSON values and emits native envelopes under
`thirsty.native-value.v1`. Each native value carries runtime scope/declaration
tokens plus declared fields or an enum variant. Existing JSON parameter paths
remain unchanged; native fields use paths such as `row.fields.value`.
The detailed [governed value context contract](GOVERNED_VALUE_CONTEXT.md) defines
the layouts, registration, policy paths, proof boundary, and outstanding work.

Both explicit `self` and implicit `this` receivers enter the context. Exit adds
the actual returned value as `result` and validates it even without an explicit
exit predicate. A governed/contract-bearing parameter named `result` denies
before entry callbacks or the body to prevent an exit-binding collision.
Ordinary uncontracted parameters and nested fields named `result` remain valid.

One entry snapshot is compared with the live values after callback-capable
checks and before execution. Exit captures a new snapshot after the body, so
intentional body mutation is allowed; mutation during exit checks denies the
return. Each active policy must admit the same call values. A positive proof's
`original_context_hash` must match the composed context captured before policy
evaluation. Registered-source enrichment keeps its separate evaluated-context
checks. Exit projection and contracts do not introduce a TARL exit-policy gate.

Projection rejects cycles, forged `__thirsty_native__` key segments, invalid
native layouts, unsupported foreign values, and exceeded limits without calling
their conversion or traversal hooks. Limits are depth 32, 10,000 nodes,
1,048,576 aggregate UTF-8 string/key bytes, and 4,096-bit integer magnitude.
Generated metadata and repeated alias expansions count toward the budgets;
the byte limit is not a complete encoded-JSON or whole-runtime memory limit.

Snapshot checks do not establish atomic traversal, detect mutations restored
between checkpoints, or bind dictionary insertion order and alias identity.
Native tokens are local identity, not portable source provenance. External
native adapters, composite call receipts, closure provenance, a full policy
namespace, ownership controls, and global execution budgets remain open. Exit
denial cannot undo earlier body effects. The Python embedding host remains
trusted; neither OS sandboxing nor whole-program verification is claimed.
M3-M7 remain incomplete and robotics stays deferred. Consult the separate
[M3.5 verification record](operations/M3_VALUE_IDENTITY_VERIFICATION.md) for the
candidate's integration outcome; earlier totals do not verify it.

## Collection library

Import with `import "thirst::collections" as c`. Arguments are positional.

| API | Behavior |
|---|---|
| `map(fn, values)`, `filter(fn, values)` | Return new lists; callbacks execute in the caller's effect context |
| `reduce(fn, values[, initial])` | Fold values; omitting initial on empty input is an error |
| `sort(values[, reverse[, key]])` | New sorted list; reverse must be Bool |
| `unique(values)`, `flatten(values)`, `zip(a, b, ...)` | Ordered uniqueness, recursive list/tuple flattening, shortest-input zip |
| `dict(pairs)` | Construct from two-element key/value pairs; duplicate keys error |
| `keys(d)`, `values(d)`, `items(d)`, `has(d, key)` | Dictionary inspection in insertion order |
| `with_item(d, key, value)` | Shallow dictionary copy with an explicit replacement |
| `merge(a, b[, overwrite])` | Shallow merge; duplicate keys error unless overwrite is true |
| `tuple(values)`, `bytes(values)` | Immutable sequence / byte representation; bytes require integer 0-255 |
| `encode_utf8(text)`, `decode_utf8(data)` | Explicit strict UTF-8 conversion; malformed byte sequences error |
| `set(values)` | Immutable ordered set of hashable guest values |
| `set_union(a,b)`, `set_intersection(a,b)`, `set_difference(a,b)` | New ordered sets; both inputs must be set values |
| `to_list(values)` | Explicit list conversion |
| `kind(value)` | Tag: none, bool, int, float, string, list, dict, tuple, bytes, set, function, or object |
| `group_by(fn, values)` | Ordered dictionary of lists keyed by a callback result |
| `sum(values)` | Sum finite Int/Float values; bool and non-finite results are rejected |

Tuple, bytes, and ordered-set construction prevents structural mutation of that
container. Copying is shallow: a tuple can still refer to a mutable list.
Collections are not globally resource-bounded. Slicing was added in the M3.1
increment above. Iterators/generators, comprehensions, named/default
parameters, and complete static container typing remain language milestones.

## A complete report application

From the repository root:

Save this explicit demonstration policy as `report-example.tarl`:

```tarl
policy data_report_example
when authority == "report-reader" and action == "import" and target == "thirst::collections" => ALLOW
when authority == "report-reader" and action == "import" and target == "thirst::json" => ALLOW
when authority == "report-reader" and action == "import" and target == "thirst::fs" => ALLOW
when authority == "report-reader" and action == "import" and target == "thirst::env" => ALLOW
when authority == "report-reader" and action == "read" and target == "thirst::env.get:THIRSTY_REPORT_INPUT" => ALLOW
when authority == "report-reader" and action == "read" and target == "thirst::fs.read_file:src/utf/examples/data_report/orders.json" => ALLOW
when authority == "report-reader" and action == "write" and target == "stdout" => ALLOW
when true => DENY
```

```powershell
.venv\Scripts\python.exe -m utf.thirsty_lang.cli run src/utf/examples/data_report/main.thirsty --policy report-example.tarl --authority report-reader
```

The checked-in `orders.json` is synthetic example data. The program caps its file
read at 1 MiB before parsing JSON,
requires a list of uniquely identified orders, validates exact fields and numeric
ranges, groups by category, and emits sorted category totals as JSON. Monetary
amounts use integer cents. Set `THIRSTY_REPORT_INPUT` to select another local
input. Invalid data fails instead of printing an error as a successful report.

Omitting the policy denies the first import under the default posture, despite
the example's Core semantic header. The policy permits the listed operations
only. Changing `THIRSTY_REPORT_INPUT` requires an intentional update to the
permitted read target. `--authority report-reader` is a self-asserted tag for
this local demonstration; authenticated identity requires signed credentials
and hardened configuration. The example's data-validation and policy limits
are not an OS memory sandbox.

## Network operations

Import `thirst::net` with explicit import permission. All operations require
their own `network` capability under the default governance posture; allowing
the import alone is insufficient.

| API | Result / contract |
|---|---|
| `tcp_connect(host, port[, timeout])` | Opens a real connection; returns connected/host/port/handle fields |
| `tcp_listen(port[, host[, backlog[, timeout]]])` | Binds/listens; returns listening/port/handle fields; port 0 selects an available local port |
| `tcp_accept(handle)` | Accepts a peer and returns a distinct connected handle |
| `tcp_send(handle, data)` | Sends text, bytes, or byte integers; returns locally accepted byte count |
| `tcp_receive(handle[, max_bytes])` | Returns data as byte integers, received count, and EOF flag; a read may be shorter than requested |
| `udp_bind(port[, host[, timeout]])` | Binds a datagram receive handle |
| `udp_send(host, port, data[, timeout])` | Sends one datagram; count means local transport acceptance |
| `udp_receive(handle[, max_bytes])` | Receives one datagram with sender address; truncation errors explicitly |
| `close(handle)` | Closes owned resources; false for an already closed/unknown handle |

Numeric IPv4/IPv6 addresses are required. DNS and TLS are not implemented in
this socket namespace. Default bind host is loopback. Default timeout is 10
seconds, configurable above zero through 60 seconds. TCP transfers are limited
to 1 MiB per call; UDP to 65,507 bytes. The module instance permits at most 256
open handles. Close handles explicitly, including failure paths. Per-call
deadlines cover waiting for the handle lock and socket operation; they are not
a total program execution deadline.

TCP is a stream: accumulate complete application frames before decoding UTF-8.
A send receipt does not establish delivery, authorization, or successful
processing by the peer. Loopback tests exercise OS behavior; public network
services were not contacted to establish these results.

## Serialization, SQL, crypto, and locks

- `fs.read_file(path[, max_bytes])` optionally bounds the bytes read before
  strict UTF-8 decoding. Existing unbounded calls retain their contract.
- HTTP `get`/`delete` accept `(url[, timeout[, max_bytes]])`; `post`/`put` accept
  `(url[, data[, timeout[, max_bytes]]])`. Only HTTP(S) is accepted. Embedded
  credentials and automatic redirects are rejected; a redirect destination needs
  its own brokered request. Default timeout is 10 seconds and body limit 1 MiB.
  The timeout is socket inactivity, not a guaranteed DNS or total-request deadline.
  Failures raise rather than returning error strings as successful responses.
- `process.run(argv[, timeout[, max_output_bytes]])` requires a list/tuple of
  argument strings, defaults to 30 seconds/1 MiB, and invokes no implicit shell.
  Windows batch files are rejected because the OS can invoke a shell for them.
  Successful output is UTF-8 text with stderr merged into stdout; nonzero status,
  timeout, or overflow raises. The direct child is killed/reaped on failure;
  descendant/process-tree containment remains an OS isolation requirement.
- JSON parsing rejects duplicate object keys and non-finite numbers; JSON output
  requires string object keys and finite numbers. TOML parsing uses `tomllib`;
  the validated serializer rejects unsupported values such as null.
- YAML supports an explicit YAML 1.2 subset: JSON documents or flat scalar
  mappings. Nested YAML, anchors, tags, and ambiguous plain scalars fail rather
  than silently changing meaning. YAML output is JSON, a compatible subset.
- SQLite `query(handle, sql[, params])` is read-only under a deny-by-default
  authorizer. `execute(handle, sql[, params])` is a separate write action.
  Neither permits ATTACH/DETACH or extension loading; query also denies PRAGMAs
  and unknown SQL functions. Parameter arrays/dictionaries avoid SQL assembly.
- `crypto.hmac(key, data)` / `hmac_sha256` use HMAC-SHA256. `verify_hmac` uses
  constant-time comparison. `sign(data, private_seed_hex)` requires an explicit
  32-byte Ed25519 seed. `public_key(seed)` derives the public key;
  `verify(data, signature, public_key_hex)` verifies the `ed25519:` signature.
  Old concatenation hashes/default-key signatures are not accepted.
- Lock v2 hashes manifest, actual local source, bundled runtime source, and
  Python version. Run `thirsty lock` explicitly after intended changes and use
  `thirsty run --locked source.thirsty`. Legacy locks fail verification. Local
  source and bundled stdlib resolve; a remote registry does not yet exist.
  A lock is integrity evidence relative to its trusted baseline, not proof that
  an attacker-controlled replacement lock or runtime should be trusted.

## Security posture and execution targets

Pure mode blocks mediated external effects through imports, aliases, callbacks,
and cascades. The default governance posture applies policy to mediated effects
regardless of a Core semantic header. Standard-library exports must match an
explicit effect or no-ambient-effect classification; unknown or missing exports
are refused before guest exposure. A computation-only collection helper can
still invoke a callback, whose restrictions remain active. Hardened
mode additionally requires governed execution, authenticated authority, and
Ed25519-signed proofs. Bound signed credentials are revalidated for time and
issuer revocation before effects. Direct construction of `VerifiedAuthority`
remains a trusted Python embedding API, not an untrusted credential parser.

Use `--policy`, `--audit-db`, and `--require-audit` together
when an effect must not occur unless its decision proof was persisted. Failure
to attach/open/write the required archive denies execution. Audits record
authorization decisions, not external-world completion. Retain a trusted
external chain checkpoint to detect historical truncation/rewrite.

`shield`, `detect`, `defend`, `sanitize`, `armor`, and `interface` are rejected
until their actual semantics exist. Their names do not provide protection.

The interpreter is the reference target. JS supports checked scalar/array
expressions, simple declarations/assignments/returns and directly declared
functions; unsupported statements, host calls, and new container/type forms
are rejected. LLVM's `closed-scalar-i32/v1` profile evaluates bounded closed
expressions/local functions at build time, requires signed-i32 intermediates,
and emits the verified constant entry result. The Int `main` binding becomes
the process return value, subject to OS exit-code conventions; it does not
export callable language functions. It is not a general LLVM backend. All
targets reject uninitialized strict-mode declarations before artifact emission.
JS and LLVM explicitly reject slice expressions before emitting an artifact
or manifest. The interpreter and its Pyodide execution path support slices;
the browser must load the matching source described below.
The supported build example is `src/utf/examples/compiler_scalar.thirsty`.
Every public JS/LLVM/Pyodide build requires `--allow-governance-loss`, even for
headerless or Core source, and automatically writes a disclosure manifest before
executable output or toolchain launch. Unsupported source is rejected before
those writes. Binding a policy hash in a manifest does not install that policy
into the artifact. Private subset emitters are internal rendering APIs, not a
public execution-authorization boundary.

Pyodide retains the reference interpreter but has no configured host policy or
authority. Its explicit build opt-out can permit compatibility execution for
headerless/Core input; a governed declaration still requires governance and
denies effects without policy. The manifest records the opt-out request and
the artifact's effective governance separately. A manifest may remain after a
later build failure; it does not certify successful artifact production.
JS sequence repetition is capped at 1,000,000 elements or UTF-16 code units;
its generated `main` display is not a complete Python formatting contract.
Pyodide pins the package version and checks all bundled `utf` Python source
files before importing the language. This fingerprint excludes the Python ABI,
native libraries, and downloaded dependencies. A wheel with different source is
refused even if its version matches. The published 0.9.0 artifacts were verified
against the recorded release source. A Pyodide page generated from changed
post-release source cannot silently use the older published wheel; it needs
a matching runtime distribution. Browser dependency download/installation
remains an external boundary and was not verified by the local bootstrap and
generated-JavaScript tests.

Shadow structural signatures include the slice receiver and every bound, and
effect analysis visits those expressions. Symbolic and sampled convergence
analysis explicitly abstain on slice semantics. Unknown AST subclasses are
rejected by structural proof and compiler gates and remain unsupported by
symbolic/sampled analysis; inheritance from a known node is not proof that its
additional behavior is safe to ignore.

OS isolation, complete runtime resource limits, descriptor-relative file I/O,
full static effect typing, and a constrained Python bridge remain planned.
Imports are checked by all active caller/definer lock restrictions. A lockfile
does not yet prove the defining-source identity of a foreign callable already
injected by the embedding host; that M6 provenance boundary remains open, and
Python embedding remains trusted. Static obligation reports are syntactic and
do not claim complete discovery through dynamic calls or imported-module bodies.
Robotics and swarm work is deferred until priority fixes and the general-purpose
language milestones are implemented and verified.
