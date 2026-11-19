# Governed Value Context

Thirsty-Lang 0.9.1 implements native-value projection and integrity checks at
governed call boundaries. This document explains the original defects, the
implemented contract and the remaining work on portable identity.
[M3.5 verification record](operations/M3_VALUE_IDENTITY_VERIFICATION.md)

## Problem and observed baseline

The interpreter binds language values to parameters and contracts. TARL
authorizes strict JSON snapshots. Those representations must describe the same
values when execution begins and when a governed result is returned.

The read-only probe recorded at `2026-09-09T02:46:24.599192+00:00` preserved
these observations in `.tmp/m3-governed-values-20260909-01/probe.json`:

| Probe | Observed before this repair | Classification and repair |
| --- | --- | --- |
| Explicit `self` receiver | `FountainInstance` rejected before policy evaluation | Blocks ordinary contracted methods; add bounded native receiver projection. |
| Implicit `this` receiver | Method returned `7`; policy context omitted receiver state | Blocks equivalent receiver semantics; include the bound receiver independently of parameter spelling. |
| Struct and enum arguments | `StructInstance` and native enum rejected | Blocks governed native data; project registered nominal values. |
| Struct result with `ensures true` | Returned a struct while the final proof said `ALLOW` with rejected/invalid context metadata | Blocks trustworthy result admission; validate before exit predicates and deny unsupported or invalid results before return. |
| Registered source callback mutating a list argument | Policy observed `[1]`; callback changed the live list to `[99]`; body returned `99` | Blocks snapshot integrity; recheck the exact admitted values after callback-capable checks and before execution. |

The baseline probe's interpreter SHA-256 was
`73627e5734115c67a80cb168bd66071325e3c6bbe1aaea0d83ad32681bbea2d6`.
Its JSON receipt records before/after hashes for the interpreter, context,
runtime, and verifier; those hashes were identical during the probe. This is
historical reproduction evidence, not validation of subsequent edits. A local
unsigned proof inspection in that receipt does not establish authenticated
authority, source provenance, or successful execution verification.

## Immediate integrity correction

The implementation establishes a representation check before entry and
exit predicates. It records one admitted snapshot for each boundary and checks
the live values against that same snapshot after predicates, schema preparation,
policy evaluation, and final credential callbacks. A representation failure or
change denies the boundary; it must not be silently accepted by authorizing a
new snapshot after an earlier policy evaluated different values.

Caller and defining-function policies remain a conjunction. Each receives the
same admitted call values, with its own authority and registered-source context.
A callback from a later policy cannot invalidate an earlier policy's input and
still permit execution. Policy context copies are isolated from live language
objects, and integrity checks concern the original live values as well as those
copies.

A positive policy proof must also bind the exact composed policy context hash
captured before the runtime callback. Rewriting only a copied context could
otherwise authorize values the body will never receive even when live arguments
remain unchanged. Compare `proof.original_context_hash` with that captured hash;
legitimate registered-source injection may change the evaluated canonical hash
and must retain its existing separate transformation checks.

The bound receiver participates whether source uses implicit `this` or an
explicit leading `self`. Native projection is the repair path for these methods;
permanently rejecting legitimate receivers is not the intended outcome.
Unsupported results deny before their return to the caller, including when no
exit predicate refers to the result. Body effects that already occurred cannot
be rolled back by an exit denial. `_make_decision_proof` must never emit an
`ALLOW` certificate over a rejected context representation.

The verification record determines which acceptance checks passed. These rules do not
authorize weakening existing TARL context validation or changing unsafe/core
execution into an implicit fallback.

## Projection contract

The selected helper is
`utf.thirsty_lang.governed_values.project_governed_context(context: dict) -> dict`.
It returns independently owned JSON data and raises `GovernedValueError`, a
`ValueError` subclass, on a projection violation. The interpreter uses it for
initial snapshots, live rechecks, the function-argument policy layer, and
contract proofs. Projection
failure produces a bounded diagnostic DENY, without hashing a `repr` of the raw
object or claiming that the invalid native input was successfully projected.

### Preserve JSON paths; tag only native values

Existing strict JSON arguments retain their current policy paths. There is no
full call-envelope migration in this increment. For example, the `values`
parameter remains available to `ANY(values, value -> value == 1)`.

A native record argument called `row` is projected as follows; the example
tokens are illustrative, not authentic registrations:

```json
{
  "row": {
    "__thirsty_native__": {
      "profile": "thirsty.native-value.v1",
      "scope_id": "runtime-issued-scope-token",
      "declaration_id": "runtime-issued-declaration-token",
      "kind": "struct",
      "name": "Row"
    },
    "fields": {
      "value": 7
    }
  }
}
```

The trusted projector creates the `__thirsty_native__` marker. A raw context or
guest dictionary key containing that exact marker as any dotted path segment
is rejected, including equal-looking mixed/nested forms. Guest dictionaries
cannot forge native metadata by submitting a prebuilt envelope. Reproject the
original live values at integrity checkpoints; do not feed already projected
native envelopes back through the raw-input projector.

The receiver is included under the existing explicit receiver name or implicit
`this` binding. The existing exit context binds the actual returned value to
`result`. A parameter literally named `result` in a governed/contract-bearing
signature denies at entry before predicates, policies, or body execution, with
a denial certificate. Ordinary uncontracted functions and nested fields named
`result` are unaffected. This prevents silently replacing an argument in the
exit context. Exit captures current argument/receiver state after the body, so
deliberate body mutation need not equal entry state. A mutation during exit
authorization still denies. Distinct entry/exit call metadata and a dedicated
namespace for original arguments are future migration work; this profile does
not replace current call-context naming conventions.

Parameter bindings must be unambiguous before constructing that context.
Duplicate names, including a repeated `self`, report E010 in functions,
lambdas, morphs, and methods; runtime binders raise `TypeError` before binding,
contracts, or body execution, and initializers before field defaults. This
closes the case where policy inspected a supplied argument under `self` while
the body used a different actual receiver through `this`. Source methods use
explicit leading `self` or implicit `this`. Explicit leading `this` is a
host-AST convention only; the parser reserves that keyword. Any remaining
method parameter named `this` reports E901 and fails runtime binding. A
nonleading `self` remains an ordinary parameter, with the actual receiver
separately included as `this`. Caller argument expressions retain their
evaluation before callable entry; these guards do not undo their effects.

### Accepted values and native layouts

| Runtime value | Projected node and admission rule |
| --- | --- |
| Null, exact `bool`, exact `int`, exact `str` | Preserve the JSON primitive without coercion, within the integer/text budgets. Boolean remains distinct from integer. |
| Exact finite `float` | Preserve the JSON number; reject NaN and infinities. |
| Exact native `list` | Ordered array of recursively projected nodes. |
| Exact native `dict` with string keys | Preserve the JSON dictionary, recursively project values, and reject reserved native-marker key segments. Existing TARL dotted-path rules still apply. |
| Registered `StructInstance` | Native metadata with `kind: "struct"` and a `fields` object containing every declared field. |
| Registered `FountainInstance` | Same fields-only form with `kind: "fountain"`; include every declared field. |
| Registered native enum member | Native metadata with `kind: "enum"` and a literal `variant` member instead of `fields`. |
| Everything else | Deny this profile; no stringification, duck typing, coercion, or best-effort fallback. |

The metadata profile, scope/declaration identities, kind, and name are included
in canonical JSON hashes. Native metadata has one exact shape; record/fountain
nodes have `fields`, and enum nodes have `variant`. Name is descriptive and
cannot substitute for nominal identity.

This preserves TARL's JSON contract: dotted keys normalize into nested paths;
ambiguous forms, malformed/empty paths, reserved `__tarl_` path segments, and
non-string object keys still deny. It does not give general-purpose dictionaries
literal-key semantics at policy boundaries. Tuples, bytes, sets, exceptions,
callable values, and foreign objects are outside this profile; extending them
requires explicit representation and conformance tests.

Read native fields from the interpreter's declared storage layout in declaration
order. Reject missing, extra, duplicate, or malformed fields rather than
silently omitting them. Do not evaluate properties, methods, field defaults,
`__iter__`, `__getattr__`, `__str__`, `__repr__`, `__deepcopy__`, or user equality
hooks during projection or denial diagnostics. Exact built-in type checks
exclude subclasses that can redefine traversal or conversion behavior.

`FountainInstance.methods`, its interpreter and execution frames, and
`StructInstance.type_environment` are implementation state, not value fields.
Do not traverse them. Fields containing unsupported values deny the entire
projection. A bounded diagnostic identifies the failure category without
evaluating or exposing arbitrary object contents; structural paths are not
currently included.

### Nominal identity and registration

Type names are display information, not identity. A registry for an interpreter
session, shared with its imports, assigns an opaque declaration token to each
distinct runtime nominal identity. The wire identity is the pair of scope token
and declaration token. Repeated values of
the same declaration use the same token; different declarations with the same
name must remain distinct.

The registration key must preserve the runtime's existing identity semantics:
the actual declaration object for records and fountains, and the exact generated
enum class for enum values. This work must not silently change type equality.
Do not use a name, source line, `repr`, source hash, or exported Python memory
address as a replacement identity. The registry uses weak declaration references
and monotonically increasing, nonreused declaration IDs, so object-address reuse
cannot reuse an old token.

The trusted interpreter registers declarations and their declared native
layouts, and records the exact allowed enum members. Exact Python class matches
alone do not prove that a host-constructed value belongs to a language
declaration. Untagged or unregistered values fail closed. This is declaration
registration, not unforgeable per-instance provenance: the trusted Python host
can construct or alter native objects and copy valid metadata. Host mutation of
declaration
metadata must not silently update a previously admitted layout; check the
registered layout or reject the binding.

Importing modules must preserve the registration needed by escaped values and
callbacks, including their original scope token. The implementation must define
and test that registry lifetime; an interpreter-created value is not made
portable merely because another interpreter can read its tag. Portable
identities across runs, persisted caches, and remote workers require a separate
versioned identity and trust contract. A scope token is neither a source
signature nor proof that an object is trustworthy. The embedding Python process
remains trusted.

### Aliasing, admission timing, and limits

Projection describes values, not object identity. Repeated aliases expand to
their values; distinct equal objects may project identically. Cycles deny. A
path-local active-object set distinguishes a cycle from harmless repeated
references. Every expansion counts against the budget so shared subgraphs
cannot create unbounded output.

The selected first-profile limits are:

| Budget | Definition |
| --- | --- |
| Maximum depth: 32 | The root context is depth 0; each nested value increases depth by one, including generated native envelopes. |
| Maximum nodes: 10,000 | Count every value/container and every object key, including generated native metadata and each repeated alias expansion. |
| Maximum aggregate UTF-8: 1,048,576 bytes | Count the UTF-8 bytes of every string value and object key, including generated metadata. Excludes JSON syntax and integer decimal text; the encoded JSON can exceed 1 MiB. |
| Maximum integer magnitude: 4,096 bits | Reject integers whose magnitude needs more than 4,096 bits before converting them to text. |

Enforce the limits while traversing/encoding, before an unbounded intermediate
copy. Check integer/string encoding sizes as well as containers. Deny one unit
over a limit; never truncate, replace a field with null, skip a repeated alias,
or emit an otherwise positive proof for a partial snapshot. These are native
call-context projection bounds. They do not bound registered providers, the
complete authority/source evaluation context, body execution, or arbitrary
host allocation. Extending bounded validation to those paths is separate work.

The admitted entry snapshot is taken after callee/argument evaluation and exact
arity validation, before callback-capable contracts and authorization. Preserve
existing once-only argument evaluation and constructor ordering. Reprojection
after each callback compares with the original admitted snapshot, not the most
recent observed state. Entry handoff occurs only after all active owners still
authorize that snapshot. Exit uses a new snapshot and the same integrity rule
before returning the result.

Hash rechecks detect changes visible at checkpoints. They do not prove absence
of a mutate-and-restore event between checks, atomic traversal under concurrent
host mutation, or immutability after handoff. Closing those gaps requires an
explicit ownership/freeze, versioned mutation, or isolation mechanism spanning
traversal and execution. A lock around the interpreter alone cannot constrain
arbitrary Python aliases held by the host. These limitations must remain stated
until such a mechanism is implemented and tested.

TARL's canonical JSON encoder sorts object keys. Equality under that hash does
not establish unchanged dictionary insertion order, even though language
dictionary iteration observes insertion order. Container identity and alias
relationships are also outside a value-only hash. Order-sensitive execution
binding needs a separate representation or integrity witness and focused tests;
do not claim that the current JSON hash captures those properties.

## Policy paths and schema

Policies retain ordinary JSON paths and read projected native data at explicit
paths, such as `row.fields.value`. Native metadata is available through
`row.__thirsty_native__`; only the projector can produce that marker from native
input. A value policy for the illustrative record is:

```tarl
when row.__thirsty_native__.profile == "thirsty.native-value.v1" and row.__thirsty_native__.kind == "struct" and row.fields.value <= 10 => ALLOW
when true => DENY
```

The implemented projector checks raw native layout, limits, registrations, and
primitive/node types before policy evaluation, then constructs the exact
versioned profile. Raw native-looking JSON envelopes are rejected at the
reserved marker. There is no external native-envelope handoff API in this
increment. A future such API must validate the corresponding profile grammar;
ordinary policy comparisons would not substitute for those checks.
A `name == "Row"` or `kind == "struct"` condition
does not select one particular declaration; a nominally restrictive policy must
also bind the expected scope and declaration identities through trusted setup.

TARL's current `ContextSchema` describes required dotted fields and accepted
primitive/container kinds. It does not by itself validate every element of a
recursive tagged-node grammar or native registration. Current calls obtain
those checks from the raw-input projector and its exact profile construction,
while retaining the policy's existing schema check. A future external native
adapter needs a separate profile validator and version binding. Incomplete
schema derivation must continue to fail closed at an
authority consumer. Do not label a broad `dict`/`list` field declaration as full
native-profile validation.

Reserve native markers on the interpreter's raw-input path, without changing
plain TARL JSON semantics. Caller-controlled data cannot replace generated
metadata, add trusted registrations, or select a weaker projection. Registered
sources remain separate top-level additions under the existing TARL source
contract; a native-looking source value does not acquire interpreter origin.
Every active entry policy gets identical projected call values and separate
authority/source layers with existing collision rejection. Current TARL routing
authorizes entry; introducing a new TARL decision at exit requires an explicit
policy migration. Exit projection and contracts are not an exit-policy gate.

A future full call profile could put arguments, receiver, result, phase, and
profile metadata under a trusted `thirsty_call` namespace. Tagged literal-key
dictionary entry lists would distinguish guest `a.b` from nested policy paths
and permit dictionary keys that the current TARL representation rejects. That
would change policy paths and requires an explicit migration, not a silent
fallback in this repair. That future namespace is not implemented by
`thirsty.native-value.v1`; the current reserved `result` parameter rule handles
the immediate exit-binding collision.

## Proof, replay, and handoff compatibility

The native profile produces strict JSON. Reuse `prepare_context()` and TARL's
canonical encoder; do not introduce an independent hash implementation or
rename TARL's existing JSON representation/normalization identifiers. The
versioned profile and scope/declaration tokens are data inside the original
and canonical context hashes.

An existing TARL proof can bind that JSON snapshot, the policy, schema, and
registered-source transformation. It cannot alone establish that a live native
receiver was projected faithfully. Current calls use the trusted projector and
live integrity checks. A future external native handoff adapter must require
the expected supported profile, validate its node grammar and registration, and
compare the live call snapshot before relying on a positive verdict. Passing a
hand-crafted JSON native envelope to plain TARL never establishes native value
origin.

Verify policy source and expected original context explicitly. Source-injected
proofs also require the expected evaluated context and the permitted
top-level-source-addition relationship. Preserve configured signature,
authority-validity, expiry, freshness, revocation, replay, and required-audit
checks. A snapshot hash or scope token is not a replay guard.
Unknown profiles and unsupported versions cannot silently fall back to generic
JSON admission for native execution.

Composite call receipts are separate follow-up work: bind entry and exit
snapshots, all caller/definer policy decisions, contracts, final handoff or
denial, and relevant audit identifiers in one versioned record. The current
single `_last_proof` is not such a receipt. An archived intermediate `ALLOW`
does not establish that subsequent mutation checks allowed the body or return.
Record a later denial as a distinct event; never rewrite historical evidence.

Portable declaration identity, closure/free-variable provenance, code and
dependency-lock binding, and independent execution reproduction remain outside
this projection profile. Capturing receiver fields does not capture everything
a method may read. Do not claim whole-program verification, arbitrary foreign
object provenance, OS sandboxing, transactional rollback, or complete resource
containment from this work.

## Implementation order and required verification

| Order | Work surface | Required evidence |
| --- | --- | --- |
| 1 | Interpreter boundary integrity and proof construction | Original list-mutation and invalid-result probes become denials at the proper boundary; valid JSON calls remain usable. |
| 2 | Bounded projection helper and nominal registration | Deterministic projection within registered scope, no-hook rejection, reserved-marker rejection, exact boundary budgets, and native identity tests. |
| 3 | All governed function/method entry and exit routes | Equivalent implicit/explicit receivers; imports, aliases, callbacks, cascades, and host calls retain values and policy conjunction. |
| 4 | Current raw-input projection and policy schemas; future external native handoff API | Current calls reject reserved-marker raw envelopes, invalid registration, incomplete policy schemas, and stale live snapshots. A future external adapter needs separate profile/token validation and replay tests; no such API is exposed by this increment. |
| 5 | Documentation, artifacts, and full integration | Full suite and repository release-equivalent checks after final source changes; source-bound manual rebuilt and verified where updated. |

The minimum focused matrix must cover:

- Native records, fountains, and enums as arguments, receiver fields, nested
  list/dictionary members, and results at optimization levels 0 through 3.
- Same-named declarations in different scopes/modules remain distinct;
  same-declaration aliases retain identity; unknown scope/declaration/member
  combinations and foreign enum classes deny.
- Existing JSON paths, dotted/nested coherence, Unicode keys, malformed paths,
  and authority/action collisions retain their TARL behavior. A reserved native
  marker at any raw dotted/nested path segment denies; non-string keys deny
  without coercion. Forged JSON envelopes never become native values.
- Missing/extra native fields, tampered declaration layouts, hostile subclasses,
  and objects with raising or side-effecting conversion/traversal/repr hooks
  deny without invoking those hooks, including the denial diagnostic path.
- Depth 31/32/33, node counts 9,999/10,000/10,001, aggregate text byte sizes
  1,048,575/1,048,576/1,048,577, integer magnitudes of 4,095/4,096/4,097 bits,
  escaped Unicode, direct/indirect cycles, and repeated shared subgraphs. Use
  the helper's documented counting rule and account for context metadata.
- Mutation from each entry/exit predicate, schema callback, registered source,
  policy evaluation, archive callback, and final credential callback. Assert
  denied-entry bodies do not execute and denied-exit values are not returned;
  preserve evidence that earlier body effects cannot be undone.
- Multiple policies see the same projected input; a later callback cannot
  invalidate an earlier decision. DENY/ESCALATE, expired/revoked authority,
  required-audit failure, and policy replacement remain fail closed.
- Explicit/implicit receiver context paths, metadata-like argument names, and
  `result` parameter denial before all entry callbacks/body, including contracted
  methods. Ordinary uncontracted parameters and nested fields named `result`
  remain usable. Result-only and no-explicit-exit-predicate cases are validated
  without claiming a full call namespace.
- Canonical determinism within one scope, profile/token/field tampering,
  original/evaluated proof binding, source transformation, signing and replay.
  Generic JSON verification must not be reported as native-adapter verification.

Focused success does not replace the full suite. Keep the baseline probe,
focused output, complete-suite output, and final source/artifact hashes as
separate receipts.

The implemented boundary regressions are in
`tests/test_governed_value_integrity.py`. The following focused commands were
run after native projection integration; the final integration record remains
the authority for complete-suite results:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_governed_value_integrity.py tests/test_governance_maximal.py tests/test_callable_arity.py -q --tb=short
.venv\Scripts\python.exe -m pytest tests/test_security_defaults.py tests/test_tarl_context_resolution_integrity.py tests/test_tarl_context_security_boundaries.py -q --tb=short
```

## Remaining work classifications

| Issue | Classification | Next executable repair path |
| --- | --- | --- |
| Governed JSON snapshot mutation and invalid positive result proof | Blocking current increment until fixed and verified | Complete interpreter boundary checks and focused regressions, then full suite. |
| Native receiver/record/enum projection | Blocking requested native governed use until implemented and verified | Land the bounded helper, registration, interpreter routing, and profile tests above. |
| Native profile verification at an external handoff | Requires separate follow-up work; generic JSON verification is insufficient | Add exact profile/registration checks to an explicit native adapter; retain existing TARL schema and expected-context checks. |
| Concurrent host mutation and mutate/restore between checkpoints | Requires separate follow-up work | Select ownership/freeze or versioned mutation semantics and test controlled interleavings. |
| Dictionary insertion order and alias identity are not bound by the canonical JSON hash | Requires separate follow-up work | Add an execution-sensitive integrity witness or explicitly limited ownership/representation contract; test order-only mutation and shared aliases. |
| Resources outside native call-context projection | Requires separate follow-up work | Bound registered-source/context preparation and execution separately, with adversarial size/time tests. |
| Composite receipts and durable final handoff evidence | Requires separate follow-up work | Design a versioned call record referencing every relevant decision and final outcome. |
| Portable identity and closure/code provenance | Requires separate follow-up work | Define authenticated declaration/source/runtime bindings and explicit cross-session adapters. |
| Literal dictionary keys and a distinct argument/receiver/result namespace | Requires separate follow-up work | Introduce a versioned full call profile with explicit policy-path migration and collision tests. |
| Body effects preceding exit rejection | Not blocking this bounded repair; rollback is not supplied | Keep the limitation explicit; mediate each external effect and design transactions separately if required. |

Source surfaces inspected for this design: `src/utf/thirsty_lang/interpreter.py`
(`_run_governed`, `_enforce_governance`, `_call_user_fn`, native constructors),
`src/utf/tarl/context.py`, `src/utf/tarl/runtime.py`,
`src/utf/tarl/schema.py`, `src/utf/tarl/verifier.py`, and
`src/utf/thirsty_lang/proof_obligations.py`. No other project's implementation
or evidence is imported by this specification.
