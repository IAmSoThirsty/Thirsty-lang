# Thirsty-Lang UTF 101 (Universal Thirsty Family)

- **Canonical bridge manual for Thirsty-Lang 0.8.6**
- **Python:** 3.11 or later
- **Package:** `thirsty-lang`
- **License:** Apache-2.0
**Release date:** 2026-08-02

Thirsty-Lang is a governance-first programming language family. Its central
execution question is not only "can this code run?" but also "should this action
run under this policy, authority, context, and proof?"

This manual is the end-to-end bridge between a first successful program and the
maintained language, policy, security, and operations references. It deliberately
does not copy every grammar production or API member. The generated single-file
PDF appends the detailed specifications and reference material behind this
bridge.

Use this document to learn the system, select the correct execution path, and
find the authoritative source or test for a claim.

## 1. Document authority and scope

### 1.1 Authority legend

| Label | Meaning |
|---|---|
| **Contract** | Behavior implemented by active source and protected by deterministic tests. |
| **Security contract** | Fail-closed behavior whose test or threat-model evidence is part of the security boundary. |
| **Published surface** | Code, metadata, or commands included in the `thirsty-lang` 0.8.6 package. |
| **Operational requirement** | A control that an embedding or deployment must configure; installing the package alone does not satisfy it. |
| **Repository-local** | Material present in the repository but not included in the published package. |
| **Historical** | Evidence or behavior retained to explain a previous release. It does not override the current contract. |
| **Pending acceptance** | Implemented and released behavior whose independent constitutional acceptance is still open in the Competence Register. |

### 1.2 Source hierarchy

When two descriptions differ, use this order:

1. The exact published artifact decides what a user of that artifact received.
2. Active source plus deterministic tests decides current implemented behavior.
3. `pyproject.toml`, package contents, and release workflows decide the shipped
   interface and provenance.
4. Maintained specifications and security documents explain that behavior.
5. Examples and tutorials demonstrate selected paths but do not expand the
   language or security contract.
6. Generated API pages are navigation aids. They do not override source or
   tests.

The primary maintained references are:

- [Language specification](LANGUAGE_SPEC.md)
- [Exact grammar](GRAMMAR.md)
- [Feature and capability matrix](FEATURES.md)
- [Governance runtime model](governance_model.md)
- [Feature status and Competence Register](STATUS.md)
- [Offensive threat model](THREAT_MODEL.md)
- [Production deployment requirement](PRODUCTION_DEPLOYMENT.md)
- [Whitepaper](WHITEPAPER.md)
- [Signing and publication model](SIGNING.md)
- [Release and shipping guide](../SHIPPING.md)
- [Security policy](../SECURITY.md)
- [Operational continuity map](operations/CONTINUITY_MAP.md)

### 1.3 Published boundary

The 0.8.6 wheel packages these namespaces:

```text
utf
utf.*
thirsty_lang
```

The canonical import is:

```python
from utf import thirsty_lang
```

`import thirsty_lang` is a compatibility shim to the same implementation.

The top-level `governance/` tree and `src/psia` are **repository-local**. They
are not included in the published 0.8.6 Python package and are not part of its
installed runtime or security boundary. Their presence in a checkout must not
be presented as a capability of a clean PyPI installation.

## 2. The mental model

The shortest accurate model is:

```text
source
  -> lex, parse, and check
  -> core or governed runtime
  -> contracts and capability request
  -> TARL policy evaluation
  -> ALLOW, DENY, or ESCALATE
  -> proof record
  -> optional required durable audit
  -> governed effect only after admission
```

The terms are intentionally separate:

- A **policy** states the decision rules.
- A **context** is the finite JSON input evaluated by those rules.
- A **schema** establishes that the evaluated context has the required shape
  and types.
- A **verdict** is `ALLOW`, `DENY`, or `ESCALATE`.
- A **proof** binds the decision to policy, context, schema, rule, time, and
  optional cryptographic identity.
- An **audit archive** durably persists proof records in a hash-linked chain.
- An **authority** identifies and, in hardened mode, cryptographically
  authenticates who may request the action.
- A **broker** is the single admission point for governed effects and external
  adapters.

These objects are related, but none substitutes for another. In particular, a
proof object is not automatically a signed proof, and a proof is not durable
audit evidence until an attached archive successfully stores it.

## 3. Install and prove provenance

### 3.1 Isolated installation on PowerShell

```powershell
$ErrorActionPreference = "Stop"

py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install --no-cache-dir thirsty-lang==0.8.6
```

On POSIX shells:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --no-cache-dir thirsty-lang==0.8.6
```

Development and analysis extras are explicit:

```bash
python -m pip install -e ".[dev,analysis]"
```

`analysis` adds Z3. It is not required for ordinary parsing, execution, or
policy evaluation.

### 3.2 Verify the installed artifact

```powershell
python -m pip show thirsty-lang
python -c "import importlib.metadata as m; print(m.version('thirsty-lang'))"
Get-Command thirsty,tarl,tarl-lsp,shadow-thirst,tscg,tscg-b,thirst-of-gods |
    Format-Table Name,Source
thirsty --version
tarl --help
```

If a console script is not on `PATH`, invoke the virtual-environment executable
directly, for example:

```powershell
.\.venv\Scripts\tarl.exe --help
```

For a source checkout:

```bash
git clone https://github.com/IAmSoThirsty/Thirsty-lang.git
cd Thirsty-lang
python -m pip install -e ".[dev,analysis]"
```

Do not treat an editable checkout as proof of what the PyPI artifact contains.
Release verification uses a clean environment and the pinned published version.

## 4. Fifteen-minute core path

This path executes ordinary Tier 1 code. No policy or authority is required
because the module is explicitly `core`.

### Step 1: create `hello.thirsty`

```thirsty
module hello: core

glass greet(name) -> String {
    return "hello, " + name + "!"
}

drink message = greet("Thirsty-Lang")
pour message
```

### Step 2: run it

```bash
thirsty run hello.thirsty
```

Expected output:

```text
hello, Thirsty-Lang!
```

### Step 3: add state and repetition

```thirsty
module counter_demo: core

fountain Counter {
    drink count: Int = 0

    glass init(self) {
        self.count = 0
    }

    glass increment(self) -> Int {
        self.count = self.count + 1
        return self.count
    }
}

drink counter = new Counter()
times 3 {
    pour counter.increment()
}
```

Run and format it:

```bash
thirsty run counter.thirsty
thirsty fmt --check counter.thirsty
thirsty fmt counter.thirsty
```

### Step 4: inspect other core entry points

```bash
thirsty repl
thirsty new sample-project --mode core
thirsty doctor
```

The core path demonstrates syntax and runtime behavior. It does not create a
governed-execution claim.

## 5. Fifteen-minute governed path

This first governed example uses a plain local authority string so the policy
flow is visible without provisioning keys. It is a tutorial path, not the
production hardened profile.

### Step 1: create `governed_hello.thirsty`

```thirsty
module governed_hello: governed

glass greet(name) -> String
    requires length(name) > 0
    ensures length(result) > 0
{
    return "governed hello, " + name + "!"
}

drink message = greet("operator")
pour message
```

The function contract makes `greet` a governed function entry. `pour` also
requests the `write` capability for standard output.

### Step 2: create `tutorial.tarl`

```tarl
policy governed_tutorial

when action == "greet" => ALLOW
when action == "write" => ALLOW
when true => DENY
```

Rules are first-match-wins. The final rule is an explicit default-deny control.

### Step 3: run under the policy

```bash
thirsty run governed_hello.thirsty \
    --thirst-level governed \
    --policy tutorial.tarl \
    --authority local-tutorial
```

On PowerShell, backticks may replace the backslashes or the command can be
entered on one line.

### Step 4: prove the denial path

Copy the policy, remove the `write` grant, and run with the restrictive copy.
The governed `pour` must fail closed with exit code 2. A denial is evidence that
the gate executed; it is not a runtime crash.

### Step 5: inspect static obligations without executing effects

```bash
thirsty prove governed_hello.thirsty \
    --policy tutorial.tarl \
    --emit-manifest

thirsty explain-denial governed_hello.thirsty \
    --policy tutorial.tarl
```

`thirsty prove` parses and checks the program and emits obligations. It does not
run program side effects. Its report includes governed calls, sensitive
standard-library calls, required actions and capabilities, contracts, context
schema status, authority and proof requirements, policy/source hashes, audit
requirements, and unresolved gaps.

### Step 6: understand the production difference

The hardened path adds:

- a signed authority claim verified against an authority-issuer public key;
- Ed25519-signed decision proofs;
- an explicit context schema or a complete derived schema;
- a trusted clock for temporal authority;
- durable replay and revocation stores for independent verification;
- an explicitly attached audit archive when durable audit is required;
- a capability broker and path guard for all external effects.

Follow [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) for the complete
operator checklist. `--hardened` alone does not create an audit database.

## 6. The exact six-tier family

The Universal Thirsty Family has six implemented tiers.

| Tier | Name | Current role | Primary source |
|---:|---|---|---|
| 1 | Thirsty-Lang | Lexer, parser, checker, interpreter, formatter, modules, package tools, contracts, builds, and primary CLI | `src/utf/thirsty_lang` |
| 2 | Thirst of Gods | Structural deity-contract validation over the real Tier 1 AST, then interpretation or transpilation | `src/utf/thirst_of_gods` |
| 3 | T.A.R.L. | Policy parsing, safe evaluation, schema admission, proof generation/verification, time, audit, broker, and escalation | `src/utf/tarl` |
| 4 | Shadow Thirst | Mutation analysis and `PROMOTE`, `FLAGGED`, or `REJECT` decisions | `src/utf/shadow_thirst` |
| 5 | TSCG | Symbolic constitutional grammar, parsing, canonical spacing, validation, and checksum | `src/utf/tscg` |
| 6 | TSCG-B | Binary frames for UTF-8 TSCG text with CRC32 and SHA-256 integrity | `src/utf/tscg_b` |

The tiers form a family, not six interchangeable authorization gates. TARL and
the capability broker perform policy admission. Shadow Thirst, TSCG, and
TSCG-B contribute analysis or integrity services; they do not independently
authorize a governed effect.

## 7. Tier 1 language bridge

The complete syntax belongs in [GRAMMAR.md](GRAMMAR.md) and
[LANGUAGE_SPEC.md](LANGUAGE_SPEC.md). This section supplies the working mental
map.

### 7.1 Modules and modes

```thirsty
module name: core
module name: governed
module name: strict
module name: pure
```

- `core` is ordinary execution.
- `governed` routes governed calls and capability-bearing effects through the
  configured governance path.
- `strict` rejects uninitialized bindings.
- `pure` rejects `pour` and `sip` I/O.

A governed parse error fails closed. Recovered statements are discarded rather
than partially executed.

### 7.2 Bindings and mutation

```thirsty
drink value = 1
drink mut counter = 0
let stable = "fixed"
next_value := 2
counter = counter + 1
```

`let` is immutable. `drink mut` and `:=` establish mutable bindings. Assignment
mutates an existing mutable binding or supported member/subscript target.

### 7.3 Functions, lambdas, and contracts

```thirsty
glass add(a, b) -> Int {
    return a + b
}

drink double = glass(x) -> Int {
    return x * 2
}
```

Contracts are executable checks:

```thirsty
glass withdraw(amount) -> Int
    requires amount > 0
    ensures result >= 0
    invariant amount < 10000
{
    return amount
}
```

`requires` is checked before the body. `ensures` is checked after the body with
`result` bound. `invariant` is checked at entry and exit. Method contracts are
design-by-contract even in core mode; governed top-level calls additionally
require policy and authority admission.

### 7.4 Control flow

Implemented control-flow families include:

```thirsty
thirsty condition {
    pour "yes"
} hydrated {
    pour "no"
}

for item in items {
    pour item
}

refill condition {
    // while-like loop
}

refill (item in items) {
    // for-each form
}

refill (drink i = 0; i < 10; i = i + 1) {
    // C-style form
}

times 3 {
    pour "again"
}
```

The C-style `refill` form desugars to initialization plus a while-like loop;
a declaration used as its counter is made mutable by the parser.

### 7.5 Fountains, members, and subscripts

```thirsty
fountain Account {
    drink balance: Int = 0

    glass init(self) {
        self.balance = 0
    }

    glass credit(self, amount) {
        this.balance = this.balance + amount
        return this.balance
    }
}

drink account = new Account()
drink values = [10, 20, 30]
values[1] = account.credit(values[1])
```

Both `self` and `this` receiver conventions are supported. Lists, dictionaries,
and strings support indexed reads; lists and dictionaries support assignment
where appropriate. Bounds and invalid index types are checked.

### 7.6 Error and asynchronous structure

```thirsty
spillage {
    drink result = cascade perform_work()
    return result
} error (problem) {
    pour problem
} cleanup {
    pour "cleanup"
} finally {
    pour "finished"
}
```

`spillage`, `error`, `cleanup`, `finally`, `throw`, and `cascade` provide the
structured error and asynchronous vocabulary used by Tier 1 and validated more
strictly by Thirst of Gods.

### 7.7 Types and implementation limits

Runtime/checker types include `Int`, `Float`, `Bool`, `String`, `Void`, `Any`,
`Error`, `Quenched`, `Reservoir`, `Task`, `Result`, `Governed`, function types,
and internal enum/struct/interface/generic forms.

Important 0.8.6 limits:

- An unannotated function return type is `Any`.
- A source type annotation currently consumes a single identifier; generic
  type strings accepted by the Python type API are not a general source syntax.
- Fountain inheritance or mixin syntax is not implemented.
- Enum variants do not carry parsed payload types.
- Interface parsing does not implement complete typed parameter signatures.
- `morph` does not parse a return annotation.
- Bare `!` is invalid; use `not`.
- Semicolons are generally optional, except where the grammar uses them as
  structural separators such as a C-style `refill` header.

### 7.8 Expression behavior

The implementation precedence, lowest to highest, is:

1. assignment
2. pipe and thirst
3. `or`
4. `and`
5. comparisons
6. `+` and `-`
7. `*`, `/`, `%`
8. arrow, `||`, and `^`
9. member access, calls, and subscripts

In Tier 1, `^` and `||` require Boolean operands. The pipe tokens `|>` and bare
`|` are both recognized. Consult the grammar for the exact parse forms.

## 8. Modules, standard library, and project files

### 8.1 Imports

```thirsty
import "thirst::json" as json
import "thirst::fs" as fs
```

The standard library currently registers 16 namespaces:

```text
thirst::time          thirst::crypto       thirst::reservoir
thirst::fs            thirst::path         thirst::json
thirst::http          thirst::env          thirst::process
thirst::log           thirst::test         thirst::collections
thirst::net           thirst::sqlite       thirst::yaml
thirst::toml
```

Global built-ins are:

```text
length     contains    split       abs
min        max         push        pop
size       get         flood       condense
evaporate  strain      transmute   distill
```

### 8.2 Sensitive capability map

Governed mode wraps the functions currently declared in
`SENSITIVE_STDLIB_CAPABILITIES`:

| Namespace | Mapped actions |
|---|---|
| `thirst::fs` | `read_file`, `exists`, `list_dir` as `read`; `write_file`, `mkdir`, `remove` as `write` |
| `thirst::http` | `get`, `post`, `put`, `delete` as `network` |
| `thirst::net` | `tcp_connect`, `tcp_listen`, `udp_send` as `network` |
| `thirst::env` | `get`, `all` as `read`; `set` as `write` |
| `thirst::process` | `run`, `exit` as `execute`; `args`, `pid` as `read` |
| `thirst::log` | `info`, `warn`, `error`, `debug` as `write` |
| `thirst::test` | `describe`, `it` as `write` |
| `thirst::sqlite` | `connect`, `execute`, `close` as `write`; `query` as `read` |

This table is a boundary, not a claim that every callable in all 16 namespaces
is mediated. For example, current `time` and `crypto` functions are not listed
in this map. A production embedding must inspect or extend the map when its
threat model treats additional functions as sensitive.

### 8.3 Package manager scope

`thirsty add`, `thirsty lock`, and `thirsty audit` manage local manifest and
lock integrity. Version 0.8.6 records `thirsty-registry://`-style resolution
identities and deterministic hashes; it does not download packages from a live
remote dependency registry. Do not treat a generated lockfile as supply-chain
verification of externally fetched code.

`thirsty run --locked` requires the local lock integrity check to pass.

## 9. All seven installed CLIs

The following is the exact 0.8.6 command family. Use each command's `--help` for
all flags and positional arguments.

### 9.1 `thirsty`

Subcommands:

```text
run
repl
fmt
new
build
prove
explain-denial
govern
add
audit
lock
doctor
lsp
docs
```

Notes:

- `audit` here audits dependency-lock integrity. TARL archive audit is under
  `tarl audit`.
- `lsp` launches the TARL policy language server over stdio or TCP. It is not a
  separate Thirsty source-language LSP.
- `prove` and `explain-denial` are static and do not execute effects.
- `docs` generates the repository documentation site surface; this maintained
  manual and its manifest-driven PDF remain the canonical integrated guide.

### 9.2 `tarl`

Subcommands:

```text
eval
parse
verify
lint
audit
keygen
revoke
explain
test
analyze
```

`tarl audit` has three subcommands:

```text
verify-chain
checkpoint
query
```

`tarl analyze` modes are exactly:

```text
coverage
shadows
conflicts
equiv
refines
```

`tarl keygen` roles are exactly:

```text
authority-issuer
proof-signer
time-authority
```

### 9.3 `tarl-lsp`

`tarl-lsp` has no subcommands. It runs the TARL JSON-RPC language server over
standard input/output. Its command-line options are `--help` and `--version`.

### 9.4 `shadow-thirst`

Subcommands:

```text
check
visualize
```

### 9.5 `tscg`

Subcommands:

```text
parse
canonical
checksum
validate
list
```

### 9.6 `tscg-b`

Subcommands:

```text
encode
decode
stream
```

`encode` writes a binary frame. `decode` accepts a hexadecimal frame argument
or binary standard input. `stream` decodes concatenated frames from hexadecimal
input or standard input.

### 9.7 `thirst-of-gods`

Subcommands:

```text
run
check
transpile
```

`transpile --target` accepts exactly `thirsty` or `js`.

## 10. TARL policy fundamentals

TARL is Thirsty's Active Resistance Language. It evaluates explicit rules and
produces one of three verdicts:

```text
DENY < ESCALATE < ALLOW
```

`DENY` is the default. `ESCALATE` is not an implicit ALLOW; promotion requires
the separately configured quorum path.

### 10.1 Basic policy

```tarl
policy access_control v1

when user.role == "admin" => ALLOW
when action == "delete" and resource == "critical" => ESCALATE
when true => DENY
```

Rule syntax is:

```text
when <condition> => ALLOW|DENY|ESCALATE [for: <duration>]
```

Policy support also includes:

- `EXTENDS` and `RESTRICTS` relationships;
- `INCLUDE` by name or file with optional alias;
- `STOP`;
- `valid_from`, `valid_until`, `supersedes`, and `on_expiry` metadata;
- succession with `if_unresolved_after` and `revert_to`;
- policy sets using `UNION`, `INTERSECT`, or `MAJORITY` plus a default verdict.

Malformed rules, dates, and durations are rejected. `on_expiry` cannot grant
`ALLOW`.

### 10.2 Safe expressions

TARL expressions support:

- `and`, `or`, and `not`;
- comparisons and strict membership;
- arithmetic and unary minus;
- nested dotted paths;
- list/set-like literals;
- registered sources;
- safe functions and quantifiers;
- explicit temporal built-ins.

Safe functions include `MATCHES`, `STARTS_WITH`, `ENDS_WITH`, `CONTAINS`,
`ELAPSED_SINCE`, `LEN`, `LOWER`, and `UPPER`.

TARL's expression algebra is deliberately stricter than Tier 1 runtime
truthiness:

- Boolean operators require resolved Boolean operands.
- Both Boolean operands are validated even when one would decide the result.
- Every supplied `ALL` or `ANY` element is validated.
- Empty quantifier collections provide no authorization evidence and fail
  closed.
- Integers and floats may compare numerically; strings never coerce to numbers.
- Non-finite numeric operands or results fail closed.
- Missing or malformed paths cannot enter comparisons, membership, functions,
  or ordinary Boolean algebra.

## 11. The authoritative context contract

### 11.1 One representation

TARL policy expressions use dotted **paths**. Caller context uses nested JSON.

Policy:

```tarl
when user.role == "admin" => ALLOW
```

Authoritative context:

```json
{
  "user": {
    "role": "admin"
  }
}
```

Representation identity:

```text
tarl.context.nested-json.v1
```

Normalization:

```text
algorithm: identity
version: 1
path model: nested objects
silent conversion: none
```

A flat dotted key is rejected:

```json
{
  "user.role": "admin"
}
```

A mixed representation is also rejected, even if both values are equal:

```json
{
  "user.role": "admin",
  "user": {
    "role": "admin"
  }
}
```

A contradictory mixed representation is a representation conflict, never a
choice between competing values:

```json
{
  "user.role": "guest",
  "user": {
    "role": "admin"
  }
}
```

### 11.2 Resolution is typed

Every path lookup has one of four states:

```text
RESOLVED(value)
MISSING
TYPE_ERROR
REPRESENTATION_CONFLICT
```

Only `RESOLVED` carries an ordinary expression value. The other states
short-circuit policy evaluation to a fail-closed decision with an explicit
reason.

This distinction is constitutional:

```text
missing is not false
invalid is not false
unresolved is not evidence
```

A resolved Boolean false remains valid and distinguishable:

```json
{
  "feature": {
    "enabled": false
  }
}
```

### 11.3 Accepted value domain

Caller contexts and registered-source values must be finite JSON values:

- objects with string keys;
- arrays;
- strings;
- Booleans;
- integers and finite floating-point values;
- null.

Duplicate object keys, NaN, infinity, cycles, tuples, sets, and arbitrary
Python objects are rejected. Callers cannot provide reserved temporal,
internal, or `source:*` fields.

### 11.4 Command-line evaluation

```bash
tarl parse access.tarl

tarl eval access.tarl \
    --context '{"user":{"role":"admin"}}' \
    --json
```

The following must deny because the representation is invalid:

```bash
tarl eval access.tarl \
    --context '{"user.role":"admin"}' \
    --json
```

## 12. Schema, verdict, proof, and audit

These four layers are intentionally independent.

| Layer | Question answered | Failure meaning |
|---|---|---|
| Context schema | Did the exact evaluated representation contain the required fields and types? | Policy rules do not run; fail closed with `DENY` or configured `ESCALATE`. |
| Verdict | Which rule decided this request? | No matching authoritative grant means no effect. |
| Proof | Can the decision be bound to policy, context, schema, rule, time, and signer? | The verdict may be diagnostic but is inadmissible for a consumer requiring those bindings. |
| Audit archive | Was the proof durably appended to a hash-linked history? | If persistence is configured as required, failure downgrades the decision to `DENY`. |

### 12.1 Context schemas

Schema kinds are exactly:

```text
string
int
float
number
bool
list
dict
```

Boolean is not accepted as `int` or `number`, despite Python's internal type
relationship.

An explicit schema may use the full canonical form:

```json
{
  "status": "explicit",
  "representation": {
    "id": "tarl.context.nested-json.v1",
    "path_model": "nested-objects",
    "normalization": "none"
  },
  "on_violation": "DENY",
  "fields": [
    {
      "name": "user.role",
      "kinds": ["string"],
      "required": true
    },
    {
      "name": "risk",
      "kinds": ["number"],
      "required": false
    }
  ]
}
```

`on_violation` cannot be `ALLOW`. Unknown kinds, duplicate fields, unknown
metadata, representation mismatch, or requested normalization are rejected.

The proof-obligation loader also accepts the documented compact field mapping,
then normalizes it into the canonical schema model:

```json
{
  "fields": {
    "user.role": "string",
    "risk": {
      "kind": "number",
      "required": false
    }
  }
}
```

When static schema derivation is incomplete, provide an explicit schema rather
than loosening the evaluator. A differing policy-text override receives its own
derived schema; the runtime does not silently reuse the base policy's derived
schema.

### 12.2 Positive verdict admissibility

`tarl eval` can return a raw `ALLOW` for diagnostic use. A load-bearing broker
or governed runtime accepts positive authority only when the explicit or
complete derived schema passed and that result is bound into the proof for the
exact representation evaluated.

This is the governing rule:

> A positive policy verdict is inadmissible as advancement authority unless the
> exact context representation used for schema validation is the same
> representation evaluated by the policy engine and bound into the proof.

No conversion may occur silently.

### 12.3 Proof binding

A TARL proof records or binds, as applicable:

- policy hash;
- original and canonical/evaluated context hashes;
- context representation identity;
- normalization algorithm and version;
- conflict status;
- schema fingerprint, representation, and validation status;
- matched rule and condition;
- verdict and evaluation trace;
- evaluation time and expiry;
- signing algorithm, key ID, and signature.

HMAC is a symmetric compatibility mechanism. Ed25519 is the asymmetric
attribution path and is required by hardened execution.

Proof verification requires signatures by default. `--allow-unsigned` is an
explicit local-inspection option, not a production authorization mode.

### 12.4 Registered sources

Registered sources are the one explicit context transformation. Their values
are injected under trusted top-level `source:<name>` fields. Callers may not
submit those fields themselves.

A source-injected proof preserves both original and evaluated context hashes.
Verification requires the exact original context and the exact evaluated
context. Removing only valid top-level source additions must reproduce the
original request.

### 12.5 Durable audit

`TarlAuditArchive` is SQLite-backed and hash-links records. It is not
automatically created by `--hardened`.

A production embedding that requires durable audit must attach the archive to
the same runtime and enable required persistence:

```python
from utf.tarl.archive import TarlAuditArchive

with TarlAuditArchive("audit.db") as archive:
    runtime.set_archive(archive).set_require_audit(True)
    interpreter.attach_tarl(runtime)
    # Evaluate governed work while the archive remains open.
```

Checkpoint and verify the chain head:

```bash
tarl audit checkpoint --db audit.db --out audit-head.txt
tarl audit verify-chain --db audit.db --checkpoint audit-head.txt
tarl audit query --db audit.db --verdict DENY --json
```

Store the checkpoint outside the runtime host's silent rewrite authority. A
locally re-linked truncated database cannot be detected without a trusted
external head.

## 13. Hardened policy operation

### 13.1 Trust roots

Three Ed25519 roles are defined:

```bash
tarl keygen authority-issuer --key-id issuer-1 --out issuer.key
tarl keygen proof-signer --key-id signer-1 --out signer.key
tarl keygen time-authority --key-id time-1 --out time.key
```

Private files are written with restrictive permissions where the platform
supports them. Prefer file flags over legacy hexadecimal key material on argv:

```text
--authority-key-file
--sign-proofs-file
--ed25519-key-file
```

### 13.2 Hardened CLI shape

After an authority issuer has minted a signed claim, the execution shape is:

```bash
thirsty run app.thirsty \
    --thirst-level governed \
    --hardened \
    --policy policy.tarl \
    --context-schema context-schema.json \
    --authority-token authority-token.json \
    --authority-key-file issuer.key.pub \
    --sign-proofs-file signer.key
```

Hardened mode fails closed unless the authority claim authenticates and every
governed gate can create an Ed25519-signed proof.

### 13.3 Independent proof verification

```bash
tarl verify proof.json \
    --policy policy.tarl \
    --ed25519-key-file signer.key.pub \
    --ed25519-only \
    --context-file context.json \
    --max-age 300 \
    --now 2026-08-02T12:00:00Z \
    --replay-db replay.db \
    --revocation-store revocations.db \
    --json
```

For a registered-source proof, also provide:

```text
--evaluated-context-file evaluated-context.json
```

Verification checks proof structure, signature, policy identity, trace,
context and schema coherence, temporal bounds, freshness, revocation, and
replay according to the configured controls. A second verification against the
same replay database is expected to fail as reuse.

### 13.4 Time and expiry

Temporal authority is explicit:

- CLI evaluation requires a timezone-aware `--now` for policy windows,
  time-bound verdicts, `CURRENT_*`, or `ELAPSED_SINCE`.
- A configured runtime clock that is missing, malformed, naive, or fails
  verification produces a denial. It does not fall back to host time.
- `valid_until` is an exclusive cutoff.
- A proof expires at the earlier of the effective policy cutoff or matched-rule
  duration.
- `on_expiry` cannot grant `ALLOW`.

Example:

```bash
tarl eval temporal.tarl \
    --context '{"user":{"role":"admin"}}' \
    --now 2026-08-02T12:00:00Z \
    --json
```

### 13.5 Revocation and replay

```bash
tarl revoke sha256:<policy-hash> \
    --store revocations.db \
    --reason "policy retired"

tarl revoke --store revocations.db --list --json
```

In-memory replay or revocation state is process-local and disappears on
restart. Production verification uses durable stores shared by all relevant
workers.

### 13.6 Broker and path guard

The `CapabilityBroker` is the single intended admission surface for
in-language sensitive calls and out-of-language FFI, subprocess, MCP, agent,
and tool adapters. An adapter that performs the effect without
`broker.require(...)` is outside the governed boundary.

Filesystem operations should also use a `PathGuard` configured with allowed
roots. It resolves canonical paths before the effect so traversal and symlink
escapes fail closed.

### 13.7 ESCALATE and quorum

`ESCALATE` remains non-authorizing until `QuorumResolver` validates:

- the signed proof and exact policy/rule;
- the exact original request context;
- the exact evaluated context for registered-source proofs;
- passed authoritative schema binding;
- timezone-aware trusted time and signed expiry;
- maximum age and replay enforcement;
- distinct approver identities and key material;
- Ed25519 approvals over the digest of the complete proof artifact.

Approval count alone does not repair an invalid or stale proof.

## 14. Builds and governance loss

`thirsty build` targets are exactly:

```text
llvm-ir
llvm-obj
llvm-exe
llvm-asm
llvm-jit
js
wasm-pyodide
```

Version 0.8.6 build targets do not carry the governed Python runtime into the
output. A governed module therefore refuses to build to these targets unless
the user explicitly acknowledges the loss:

```bash
thirsty build governed_app.thirsty \
    --target js \
    --allow-governance-loss \
    --policy policy.tarl \
    --context-schema context-schema.json \
    --emit-manifest
```

The manifest records the disclosure. `--allow-governance-loss` is not a
production-preservation feature; it is an explicit statement that the target
does not provide the source runtime's governed-execution guarantee.

Additional target limits:

- `llvm-ir` is emitted directly.
- `llvm-obj`, `llvm-exe`, `llvm-asm`, and `llvm-jit` require appropriate LLVM
  or Clang tools such as `llc`, `clang`, or `lli`.
- JavaScript emission covers a practical subset rather than every interpreter
  behavior.
- wasm-pyodide emits an HTML/Pyodide wrapper that retrieves its runtime and
  package from external distribution sources.

Never infer policy enforcement from a build manifest that explicitly records
governance loss.

## 15. Higher tiers

### 15.1 Thirst of Gods

Thirst of Gods validates a Tier 1 AST for four structural signals:

1. At least one fountain with an `init` method.
2. At least one cascade, with every cascade inside a spillage body that has a
   handler.
3. At least one spillage handler.
4. At least one cleanup block.

Diagnostics are `G001` through `G004`. A program that does not satisfy the
complete deity contract is not executed by the Gods runtime path.

```bash
thirst-of-gods check program.thirstofgods
thirst-of-gods run program.thirstofgods
thirst-of-gods transpile program.thirstofgods --target thirsty
```

### 15.2 Shadow Thirst

Shadow Thirst evaluates mutations with six analyzers:

1. Plane isolation
2. Determinism
3. Resource estimation
4. Purity spring
5. Memory evaporation
6. Canonical convergence

A critical analyzer failure yields `REJECT`. Only noncritical failures yield
`FLAGGED`. A clean analysis yields `PROMOTE`.

Canonical convergence uses structural AST comparison, optional Z3 reasoning,
and seeded execute-and-compare where the program surface is safe to evaluate.
It abstains conservatively when effects prevent sound comparison.

```bash
shadow-thirst check mutation.thirsty
shadow-thirst visualize mutation.thirsty
```

### 15.3 TSCG

TSCG has nine core symbols:

| Symbol | Source meaning |
|---|---|
| `COG` | cognition or reflection |
| `DNT` | prohibition or restriction |
| `SHD` | recommendation or guidance |
| `INV` | invariant or constant |
| `CAP` | capacity or boundary |
| `QRM` | quorum or consensus |
| `COM` | command or directive |
| `ANC` | anchor or foundation |
| `RFX` | reflex or self-reference |

Extended symbols are `SAFE`, `ING`, `LED`, `MUT`, `SEL`, `QRM_LINEAR`, and
`QRM_STATIC`.

Expressions use `$SYMBOL`, parentheses, pipeline `->`, conjunction `^`, and
disjunction `||`. Pipeline has lower precedence than the combine operators.

```bash
tscg parse '$COG ^ $SAFE -> $LED'
tscg canonical '$COG^$SAFE->$LED'
tscg validate '$COG ^ $SAFE'
tscg checksum '$COG ^ $SAFE'
tscg list
```

Canonicalization currently normalizes the parsed spacing and structure.
`checksum` hashes the exact input text, not the canonicalized text.

### 15.4 TSCG-B

TSCG-B frames raw UTF-8 text:

```text
magic "TSGB"       4 bytes
version            1 byte
flags              1 byte
payload length     2 bytes, big endian
payload            N bytes, UTF-8
CRC32              4 bytes
SHA-256             32 bytes
```

The minimum frame is 44 bytes. The decoder verifies magic, version, declared
length, CRC32, and SHA-256. `StreamDecoder` buffers partial input and can
resynchronize on frame magic.

The module also exposes opcode helper functions, but `pack_text` and the CLI
frame raw UTF-8 payload bytes. Do not describe CLI frames as base-23 opcode
payloads.

## 16. Production, security, and release receipts

### 16.1 What the release evidence proves

The v0.8.6 release is anchored by:

| Receipt | Recorded value |
|---|---|
| Release commit | `60f226a69059b5803b0035f037d09e6f7f9c45a2` |
| Annotated tag | `v0.8.6` |
| Tag object | `d89bbbc80a165ab6340cbe7855dfd6af2b086d1a` |
| Branch CI | run `30756636768`, success |
| Tagged validation and PyPI | run `30756676570`, success |
| Multi-architecture container | run `30756676576`, success |
| Local release gate | 1,463 passed, 1 skipped, 22 subtests |
| Local line coverage | 90.60 percent, with a 90 percent CI floor |
| Published Python artifact | clean environment installed `thirsty-lang==0.8.6` and reproduced the context matrix |
| Authoritative image | `ghcr.io/iamsothirsty/thirsty-lang:0.8.6` |
| Image platforms | `linux/amd64`, `linux/arm64` |
| GHCR manifest digest | `sha256:6f3f516b8e979437dd414373afe581716b8c890dc4758b8675cbbcad9b94b13c` |
| Preserved 0.8.5 evidence manifest | `4DD3E6A4CF017E3E34A25C62A398D29A6F93D279890C4CCDF2A4528C6333F8D5` |

Docker Hub remains stale at 0.8.1 and is not an authoritative 0.8.6 source.

### 16.2 What the release evidence does not prove

The receipts establish the tested and published release state. They do not:

- make an arbitrary embedding production-ready;
- provision deployment keys, durable stores, a path guard, or an audit sink;
- prove that a governance-losing build target preserves the runtime;
- satisfy independent constitutional acceptance by themselves.

The Competence Register keeps `CR-TARL-ALLOW` and `CR-TARL-DENY` at PASS. The
released repair does not by itself change `CR-CONTEXT-COHERENCE` or
`CR-CONTEXT-RESOLUTION-INTEGRITY`; both remain critical FAIL pending independent
acceptance and continue to block the register's listed load-bearing authority.

### 16.3 Continuous and release gates

The maintained workflows cover:

- Python 3.11 and 3.12;
- Ruff;
- mypy over `utf`;
- pytest with at least 90 percent coverage;
- executable shipped examples;
- production acceptance;
- wheel installation and all seven console entry points;
- tag-to-package version agreement;
- distribution build and metadata validation;
- PyPI upload;
- multi-architecture GHCR build, pull, version, and demo smoke tests.

Publication uses the GitHub `release` environment and a scoped PyPI API token
for 0.8.6. PyPI Trusted Publishing and publish attestations were not active for
this release. Optional OpenPGP artifact signing is separate from TARL Ed25519
proof signing. See [SIGNING.md](SIGNING.md).

## 17. Migration from 0.8.5 to 0.8.6

Versions through 0.8.5 must not be used for load-bearing authorization with
dotted context paths. In 0.8.5, an unresolved path could collapse to ordinary
Boolean false. Negation or inequality could then turn resolution failure into
an illegitimate `ALLOW`.

### 17.1 Upgrade the artifact

```bash
python -m pip install --upgrade --no-cache-dir thirsty-lang==0.8.6
python -c "import importlib.metadata as m; print(m.version('thirsty-lang'))"
```

### 17.2 Convert caller data to the one accepted representation

Before:

```json
{"user.role":"admin"}
```

After:

```json
{"user":{"role":"admin"}}
```

Do not implement silent flat-to-nested conversion. Reject mixed forms. If an
external boundary performs an explicit migration, record the original and
canonical hashes, algorithm ID, version, and conflict status before using its
output as authority.

### 17.3 Revalidate every policy family

Permanent coverage should include:

- flat dotted key only;
- nested object only;
- simple identifier ALLOW;
- simple identifier DENY;
- flat and nested values equal;
- flat and nested values conflicting;
- missing intermediate object;
- intermediate value of the wrong type;
- missing-path equality, inequality, negation, membership, safe-function, and
  Boolean comparisons;
- a real resolved Boolean false;
- schema result compared with evaluator result;
- proof hash checked against the representation actually evaluated.

Exercise the matrix through direct `SafeExpr`, policy evaluation, `TarlRuntime`,
`tarl eval`, context schema validation, proof obligations, proof creation and
verification, broker/governed runtime, and any embedding-specific adapter.

### 17.4 Reissue proof and verification expectations

0.8.6 positive proofs bind the original/canonical context, representation,
normalization, conflict, and schema-validation metadata. Treat positive legacy
proofs lacking coherent metadata as inadmissible for load-bearing authority.

Also account for the 0.8.6 strictness changes:

- eager validation of both Boolean operands and every quantifier element;
- rejection of empty quantifier collections as authorization evidence;
- strict finite JSON and strict expression type algebra;
- per-policy derived schemas for policy overrides;
- canonical lowercase signature encoding and complete replay identity;
- explicit original/evaluated contexts for registered sources;
- timezone-aware trusted time with no configured-clock fallback;
- proof-bound quorum promotion with freshness and replay controls;
- strict temporal cutoffs and expiry.

### 17.5 Preserve historical evidence

The 0.8.5 reproduction files and manifest are historical security evidence.
Do not rewrite them to match 0.8.6. Add new release evidence separately.

## 18. Troubleshooting

### `tarl` or another CLI is not found

Activate the correct virtual environment. On Windows, try the direct path:

```powershell
.\.venv\Scripts\tarl.exe --help
```

Confirm package identity with `python -m pip show thirsty-lang` and
`Get-Command tarl`.

### `user.role` denies even though the JSON contains an admin

Use nested JSON:

```json
{"user":{"role":"admin"}}
```

A flat key named `user.role` is a representation error, not an alternate
spelling.

### Missing data makes an inequality or `not` expression deny

This is expected. Missing, wrong-type, and conflicting values do not become
false. Supply valid context or redesign the policy to require explicit
presence; do not weaken the evaluator.

### The schema is incomplete

Static derivation cannot infer every safe-function or collection element type.
Provide an explicit `--context-schema` whose paths, types, representation, and
normalization match the actual evaluated context.

### `tarl eval` requests `--now`

The policy uses a temporal window, time-bound verdict, `CURRENT_*`, or
`ELAPSED_SINCE`. Supply a timezone-aware ISO-8601 value such as:

```text
2026-08-02T12:00:00Z
```

### An unsigned proof does not verify

Signature verification is secure by default. Register the correct signer key.
Use `--allow-unsigned` only for deliberate local inspection, never to promote a
positive verdict to production authority.

### A registered-source proof asks for two contexts

Supply the exact original request context and exact post-injection evaluated
context. This proves that only registered source fields transformed the
request.

### A proof verifies once and fails the second time

If a replay guard or `--replay-db` is configured, the second presentation is a
replay and should fail.

### Hardened execution denies despite an ALLOW rule

Check all independent requirements:

- authenticated authority token;
- trusted issuer public key;
- authority grant for the capability;
- Ed25519 proof-signer private key;
- policy and admissible schema-bound context;
- trusted time for temporal use;
- broker/path guard configuration where required;
- required audit persistence if enabled.

A raw policy `ALLOW` cannot compensate for a missing authority or proof.

### No audit rows appear in hardened mode

This is expected unless the embedding attached `TarlAuditArchive` to the exact
runtime. Add `set_archive(...)`; if persistence is mandatory, also add
`set_require_audit(True)`.

### A governed build refuses

The selected target drops the governed runtime. Keep execution under the
interpreter or, only when deliberate, add `--allow-governance-loss` and inspect
the emitted manifest.

### TARL analysis reports that Z3 is unavailable

Install the analysis extra:

```bash
python -m pip install "thirsty-lang[analysis]==0.8.6"
```

### LLVM object, executable, assembly, or JIT build fails

Install the required `llc`, `clang`, or `lli` tools and confirm they are on
`PATH`. The emitted `.ll` file can still be inspected independently.

### `--locked` refuses to run

Generate or update the project lockfile with `thirsty lock`, then run
`thirsty audit`. Remember that 0.8.6 implements local manifest/lock integrity,
not remote package retrieval.

### Strict or pure mode rejects an otherwise valid program

Strict mode requires initialized bindings. Pure mode rejects `pour` and `sip`.
Select the module mode that matches the intended contract.

### A governed imported file behaves differently from a core import

Governed file imports inherit the caller's governance configuration so imported
top-level effects and returned functions remain gated. Do not expect the core
module cache path to detach governed imports from the caller.

### Docker behavior does not match the published package

Verify the exact versioned GHCR image and digest. Do not use the stale Docker
Hub 0.8.1 image as evidence for 0.8.6.

## 19. Glossary

| Term | Meaning in Thirsty-Lang 0.8.6 |
|---|---|
| Authority | Identity requesting governed action; hardened authority is a verified signed claim, not a raw string. |
| Broker | Central admission point for governed effects and external adapters. |
| Canonical context | Deterministic nested finite-JSON snapshot used for evaluation and hashing. |
| Capability | Named action such as `read`, `write`, `network`, `execute`, import, or governed function entry. |
| Conflict | Ambiguous or contradictory context representation; never resolved by choosing a value. |
| Context | Request data evaluated by TARL. Caller context uses nested JSON only. |
| Context schema | Required path/type contract checked before policy evaluation and bound into positive proofs. |
| Core mode | Ordinary Tier 1 execution without governed policy admission. |
| DENY | Fail-closed verdict; the default. |
| ESCALATE | Non-authorizing verdict requiring a separately verified quorum path. |
| Governed mode | Runtime mode in which governed calls and mapped effects require policy and authority. |
| Governance loss | Build output cannot preserve governed runtime semantics; must be disclosed explicitly. |
| Hardened mode | Posture requiring authenticated authority and Ed25519-signed proofs at every governed gate. |
| MISSING | Typed resolution state indicating that a path is absent; not Boolean false. |
| Path guard | Canonical filesystem-root confinement used before governed file effects. |
| Policy | TARL source containing ordered rules and metadata. |
| Proof | Decision artifact binding policy, context, schema, rule, verdict, time, and optional signature. |
| Proof obligation | Static report of the authority, policy, schema, capability, and contract evidence a program will require. |
| REPRESENTATION_CONFLICT | Typed resolution state for incompatible context shapes or values. |
| RESOLVED | The only context lookup state that carries an expression value. |
| Replay guard | State that makes configured proof presentations single-use. |
| Registered source | Trusted explicit addition under `source:<name>` whose transformation is proof-bound. |
| Schema fingerprint | Deterministic hash of the canonical context schema. |
| TARL | Thirsty's Active Resistance Language, Tier 3. |
| TSCG | Symbolic Constitutional Grammar, Tier 5. |
| TSCG-B | Integrity-checked binary TSCG text frame, Tier 6. |
| TYPE_ERROR | Typed resolution state indicating a path crossed an invalid intermediate value. |
| Trusted clock | Verified timezone-aware time provider used for temporal authority. |
| Verdict | TARL result: `ALLOW`, `DENY`, or `ESCALATE`. |

## 20. Source and test traceability

This table points from the major manual claims to the active implementation and
regression surfaces. Paths are relative to the repository root.

| Area | Source authority | Test or operational evidence |
|---|---|---|
| Package version, extras, scripts, included namespaces | `pyproject.toml`; `src/thirsty_lang/__init__.py` | package smoke tests; release workflow package-smoke job |
| Lexer and keywords | `src/utf/thirsty_lang/token.py`; `lexer.py` | `tests/test_thirsty_lang.py`; `tests/test_language_features.py`; `tests/test_language_fixes.py` |
| Parser, modes, precedence, fail-closed governed parsing | `src/utf/thirsty_lang/parser.py` | `tests/test_threat_model_parser_fail_closed.py`; language regression suites |
| Checker, contracts, core/governed call boundary | `src/utf/thirsty_lang/checker.py` | `tests/test_governance_maximal.py` |
| Interpreter, capability gates, imports, runtime values | `src/utf/thirsty_lang/interpreter.py` | `tests/test_gate_fail_closed.py`; `tests/test_threat_model_file_imports.py`; `tests/test_review_0_8_1.py` |
| Standard library and sensitive map | `src/utf/thirsty_lang/module_system.py` | `tests/test_gate_fail_closed.py`; `tests/test_threat_model_capability_broker.py`; `tests/test_proof_obligations.py` |
| Static proof obligations and manifests | `src/utf/thirsty_lang/proof_obligations.py` | `tests/test_proof_obligations.py`; `tests/test_threat_model_build_outputs.py` |
| Main CLI and build targets | `src/utf/thirsty_lang/cli.py` | `tests/test_cli.py`; `tests/test_cli_build.py`; `tests/test_threat_model_build_outputs.py` |
| TARL parser and SafeExpr | `src/utf/tarl/core.py` | `tests/test_tarl.py`; `tests/test_peer_review_0_8_1_tarl_regressions.py` |
| Context representation and typed resolution | `src/utf/tarl/context.py` | `tests/test_tarl_context_resolution_integrity.py`; `tests/fixtures/tarl_context_coherence/` |
| Schema parsing and validation | `src/utf/tarl/schema.py` | `tests/test_tarl_context_security_boundaries.py`; `tests/test_threat_model_context_schema.py` |
| TARL runtime, cache, sources, proof creation | `src/utf/tarl/runtime.py` | `tests/test_tarl_context_security_boundaries.py`; `tests/test_tarl_proof.py`; `tests/test_threat_model_failclosed.py` |
| Proof structure and verdict lattice | `src/utf/tarl/spec.py` | `tests/test_tarl_proof.py`; `tests/test_tarl_temporal.py` |
| Proof verification | `src/utf/tarl/verifier.py` | `tests/test_tarl_proof.py`; `tests/test_threat_model_proof_strictness.py`; `tests/test_threat_model_replay.py` |
| Durable replay and revocation | `src/utf/tarl/durable.py` | `tests/test_durable_state.py` |
| Audit archive | `src/utf/tarl/archive.py` | `tests/test_threat_model_audit_chain.py`; `tests/test_production_acceptance.py` |
| Authority and deployment keys | `src/utf/tarl/authority.py`; `keystore.py` | `tests/test_threat_model_authority.py`; `tests/test_production_acceptance.py` |
| Trusted time | `src/utf/tarl/clock.py`; temporal logic in `runtime.py` and `verifier.py` | `tests/test_threat_model_clock.py`; `tests/test_tarl_temporal.py` |
| Broker and path confinement | `src/utf/tarl/broker.py`; `pathguard.py` | `tests/test_threat_model_broker.py`; `tests/test_broker_unified_gate.py`; `tests/test_threat_model_pathguard.py` |
| ESCALATE and quorum | `src/utf/tarl/escalation.py` | `tests/test_threat_model_lint_quorum.py` |
| TARL CLI and LSP | `src/utf/tarl/cli.py`; `lsp.py` | `tests/test_cli_tarl_hardening.py`; TARL LSP tests |
| Thirst of Gods | `src/utf/thirst_of_gods/core.py`; `cli.py` | `tests/test_thirst_of_gods.py`; `tests/test_verifiers.py` |
| Shadow Thirst | `src/utf/shadow_thirst/core.py`; `cli.py` | `tests/test_shadow_thirst.py`; `tests/test_verifiers.py` |
| TSCG | `src/utf/tscg/core.py`; `cli.py` | `tests/test_tscg.py` |
| TSCG-B | `src/utf/tscg_b/core.py`; `cli.py` | `tests/test_tscg_b.py` |
| Production acceptance | Runtime sources above | `tests/test_production_acceptance.py`; `.github/workflows/smoke.yml` |
| Python publication | `pyproject.toml`; `.github/workflows/release.yml` | run `30756676570`; clean PyPI install receipt |
| Container publication | `Dockerfile`; `.github/workflows/docker.yml` | run `30756676576`; GHCR digest receipt |
| Security register and adversary model | `docs/STATUS.md`; `docs/THREAT_MODEL.md` | C001-C073 test references and preserved 0.8.5 evidence manifest |

## 21. Validation commands

For a source checkout with development extras installed:

```bash
ruff check src tests
mypy -p utf
python -m pytest tests/ -q --cov=utf --cov-report=term-missing --cov-fail-under=90
python -m build
python -m twine check dist/*
```

Run narrow security matrices during TARL work:

```bash
python -m pytest tests/test_tarl_context_resolution_integrity.py -q
python -m pytest tests/test_tarl_context_security_boundaries.py -q
python -m pytest tests/test_tarl_proof.py -q
python -m pytest tests/test_threat_model_lint_quorum.py -q
python -m pytest tests/test_production_acceptance.py -q
```

Passing repository tests is necessary release evidence, but published-artifact
acceptance still requires a clean install of the exact version and execution of
the release-specific matrix.

## 22. Where to continue

- Learn exact syntax in [GRAMMAR.md](GRAMMAR.md).
- Read semantic contracts in [LANGUAGE_SPEC.md](LANGUAGE_SPEC.md).
- Check whether a claim is implemented in [STATUS.md](STATUS.md).
- Review attacker paths in [THREAT_MODEL.md](THREAT_MODEL.md).
- Understand the broker and authority flow in
  [governance_model.md](governance_model.md).
- Prepare an embedding with
  [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md).
- Verify release provenance with [SHIPPING.md](../SHIPPING.md) and
  [SIGNING.md](SIGNING.md).
- Review release history in [CHANGELOG.md](../CHANGELOG.md) and
  [CONTINUITY_MAP.md](operations/CONTINUITY_MAP.md).

Security reports should be sent privately to
`FounderOfTP@thirstysprojects.com` as described in
[SECURITY.md](../SECURITY.md).

---

- **Document identity:** Thirsty-Lang UTF 101 (Universal Thirsty Family) for release 0.8.6
- **Canonical context representation:** `tarl.context.nested-json.v1`
- **Default governed verdict:** `DENY`
**Published package boundary:** `utf`, `utf.*`, and compatibility package
`thirsty_lang`
