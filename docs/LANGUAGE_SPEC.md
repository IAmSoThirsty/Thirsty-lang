# Thirsty-Lang Language Specification

**Version:** 0.8.6
**Copyright:** 2026 Thirsty's Projects LLC (Apache 2.0)

This is the concise normative family specification. For the integrated
tutorial, CLI encyclopedia, security contract, deployment guidance, and source
traceability, see [THIRSTY_LANG_101.md](THIRSTY_LANG_101.md).

---

## Overview

Thirsty-Lang (Universal Thirsty Family — UTF) is a 6-tier governance-first language stack. Each tier adds progressive capabilities while maintaining default-DENY governance at every gate.

---

## Tier 1 — Thirsty-Lang (Core)

The base language with water-metaphor syntax.

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
module hello: core

glass greet(name: String) -> String {
    return "hello, " + name + "!"
}

drink main = greet("thirsty world")
pour main
```

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

### CLI Commands

| Command | Description |
|---------|-------------|
| `thirsty run <file>` | Execute a .thirsty file |
| `thirsty repl` | Start interactive REPL |
| `thirsty build <file> --target js` | Build to JavaScript |
| `thirsty prove <file> --policy <policy>` | Emit static proof obligations without executing effects |
| `thirsty explain-denial <file> --policy <policy>` | Explain unmet static governance obligations |
| `thirsty fmt <files>` | Format .thirsty files |
| `thirsty new <name>` | Scaffold new project |
| `thirsty govern <file>` | Governance operations |
| `thirsty add <package>` | Add dependency |
| `thirsty audit` | Audit dependencies |
| `thirsty lock` | Generate lockfile |
| `thirsty doctor` | Project health check |
| `thirsty lsp` | Start the TARL language server |
| `thirsty docs` | Generate documentation |

---

## Tier 2 — Thirst of Gods

Applies a structural AST contract over the Tier 1 object-oriented, cascade, and
structured-error constructs before running the ordinary interpreter.

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

T.A.R.L. 0.8.6 has exactly one caller-context representation:
`tarl.context.nested-json.v1`. Dotted identifiers traverse nested JSON objects:

```json
{"user": {"role": "admin"}}
```

A flat key such as `{"user.role": "admin"}` is not normalized. Flat dotted
keys, duplicate JSON keys, mixed flat/nested forms (even when their values are
equal), non-string object keys, non-finite numbers, cycles, and values outside
the finite JSON domain fail closed.

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

- Magic bytes: `TSGB` (4 bytes)
- CRC32 integrity check (4 bytes)
- SHA-256 payload verification (32 bytes)
- Automatic resynchronization for multi-frame transport

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
