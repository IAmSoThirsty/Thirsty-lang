# General Purpose Language

Foundation prepared for Thirsty-Lang 0.9.0, 2026-09-06. See
[DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) for correction dependencies and the
remaining milestones. Python compatibility is not claimed. Publication and
remote artifact identity require separate release verification.

## Ordinary data and functions

```thirsty
module report: core
import "thirst::collections" as c
import "thirst::json" as json

drink rows = [{"category": "books", "units": 2}, {"category": "books", "units": 3}]
glass units(row) { return row.units }
drink report = {"orders": length(rows), "units": c.sum(c.map(units, rows))}
pour json.stringify(report)
```

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
Collections are not globally resource-bounded. Iterators/generators, slicing,
comprehensions, named/default parameters, and complete static container typing
remain language milestones.

## A complete report application

From the repository root:

```powershell
.venv\Scripts\python.exe -m utf.thirsty_lang.cli run src/utf/examples/data_report/main.thirsty
```

The checked-in `orders.json` is synthetic example data. The program caps its file
read at 1 MiB before parsing JSON,
requires a list of uniquely identified orders, validates exact fields and numeric
ranges, groups by category, and emits sorted category totals as JSON. Monetary
amounts use integer cents. Set `THIRSTY_REPORT_INPUT` to select another local
input. Invalid data fails instead of printing an error as a successful report.

The example is an ordinary core-mode application. A governed deployment must
also configure a policy and mediate its imports, file reads, environment reads,
and output. Its validation limits are not an OS memory sandbox.

## Network operations

Import `thirst::net`. All operations require their own `network` capability in
governed mode; allowing the import alone is insufficient.

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
and cascades. Governed mode applies policy to sensitive operations. Hardened
mode additionally requires governed execution, authenticated authority, and
Ed25519-signed proofs. Bound signed credentials are revalidated for time and
issuer revocation before effects. Direct construction of `VerifiedAuthority`
remains a trusted Python embedding API, not an untrusted credential parser.

Use `--policy`, `--audit-db`, and `--require-audit` together on a governed module
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
The supported build example is `src/utf/examples/compiler_scalar.thirsty`.
JS sequence repetition is capped at 1,000,000 elements or UTF-16 code units;
its generated `main` display is not a complete Python formatting contract.
Pyodide pins the package version and checks all bundled `utf` Python source
files before importing the language. This fingerprint excludes the Python ABI,
native libraries, and downloaded dependencies. A wheel with different source is
refused even if its version matches; the prepared 0.9.0 release requires separate
publication verification. Browser dependency download/installation remains an
external boundary and was not verified by the local bootstrap and generated-
JavaScript tests.

OS isolation, complete runtime resource limits, descriptor-relative file I/O,
full static effect typing, and a constrained Python bridge remain planned.
Robotics and swarm work is deferred until priority fixes and the general-purpose
language milestones are implemented and verified.
