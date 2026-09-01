# Thirsty-Lang — Feature Reference

> Feature-oriented reference for Thirsty-Lang `0.8.6`. See
> [STATUS.md](STATUS.md) for the authoritative capability-to-test map and
> [THREAT_MODEL.md](THREAT_MODEL.md) for security acceptance status. The
> [canonical Thirsty-Lang UTF 101 manual](THIRSTY_LANG_UTF_101.md) is the integrated
> tutorial, specification, operations, and traceability reference.

Thirsty-Lang is a **governance-first language family**. It is not one language
but a layered stack: a small imperative core whose execution is *governed*, a
policy engine that decides what code may do, and a set of semantic verifiers
that *prove* properties of code rather than pattern-matching its text.

---

## 1. Language Core (`thirsty`, `.thirsty`)

A tree-walking interpreter with a recursive-descent + Pratt parser, a static
checker, a type system, and a formatter.

### 1.1 Declarations

| Form | Meaning |
|---|---|
| `drink x = expr` | immutable binding |
| `drink mut x = expr` | mutable binding (reassignable via `x = …`) |
| `drink x: Int = 5` | binding with a type annotation |
| `glass f(a, b) -> Ret { … }` | function (first-class, TCO-eligible) |
| `glass f(x) requires P ensures Q invariant I { … }` | governed function (§2) |
| `fountain C { field: T  glass init(self){…}  glass m(self,…){…} }` | class with fields, constructor, methods |
| `enum`, `struct`, `interface`, `symbol`, `morph`, `defend` | additional type / transform / strategy declarations |

### 1.2 Statements

- **Conditionals:** `thirsty (c) { … } hydrated thirsty (c) { … } hydrated { … }`
  (if / else-if / else).
- **Loops:** `refill (item in iterable) { … }` (for-each),
  `refill (cond) { … }` (while). Loop bodies accumulate into mutable bindings.
- **I/O:** `pour expr` (output), `sip target` (input).
- **Imports:** `import "path" as alias`.
- **Errors:** `spillage { … } error { … }` (try/catch),
  `cleanup { … } finally { … }`, `throw expr`.
- **Async:** `cascade expr` — schedules on a thread pool and **awaits**, yielding
  the value (not a future).
- **Security blocks:** `shield` / `sanitize` / `armor` / `morph` / `detect` /
  `defend`.

### 1.3 Expressions & operators

- Literals: int, float, string, bool, `none`, error, `quenched` (optional),
  and **array/reservoir literals** `[1, 2, 3]` (real Python `list`).
- Arithmetic `+ - * / %`; comparison `== != < > <= >=`; logical `and or not`;
  unary `-` and keyword negation `not` (a bare `!` is invalid).
- **OOP:** member read `obj.field`, member write `obj.field = v`, method dispatch
  `obj.method(args)`.
- `new Class(args)`, function calls, pipe `|`, guard `thirst(e) quench(c)`,
  and the TSCG pipeline/combine operators.

### 1.4 Built-in functions

`length`, `size`, `contains`, `get`, `split`, `abs`, `min`, `max`, `push`,
`pop`, `flood`, `condense`, `evaporate`, `strain`, `transmute`, `distill`,
`print`, `pour`.

### 1.5 Modes

A module header declares the enforcement mode:

```
module myapp: core       // ordinary execution
module myapp: governed   // governance enforcement active
```

---

## 2. Governance (the differentiator)

Governance is **runtime-enforced, deny-by-default, and a hard floor**: a
`GovernanceViolation` is *not* catchable by `spillage`. This is what separates
Thirsty-Lang from “contracts as assertions” — a governed program cannot talk its
way out of its own rules.

### 2.1 Design-by-contract

| Clause | When checked |
|---|---|
| `requires P` | at call **entry** |
| `ensures Q` | at call **exit**, with `result` bound to the return value |
| `invariant I` | at **both** entry and exit |

Contracts apply to **free functions and methods** alike.

```
module bank: governed

glass withdraw(balance, amount)
    requires amount > 0
    requires amount <= balance
    ensures result == balance - amount
{
    return balance - amount
}
```

### 2.2 Capability gates

In `governed` mode, governed function calls and the explicitly mapped sensitive
operations - including import, I/O, filesystem, HTTP/network, environment,
process, logging, testing, and SQLite operations - are routed through an
attached **T.A.R.L. policy runtime** (`evaluate_with_proof`). A non-`ALLOW`
verdict denies the operation before it takes effect. Do not infer that every
standard-library function is sensitive: `module_system.py` is the authority for
the current capability map.

### 2.3 Cryptographic proofs

Every gated decision produces a `TarlProof` record. It is unsigned unless a
runtime signing key is configured. HMAC-SHA256 provides symmetric integrity;
Ed25519 provides asymmetric signer attribution and is required by hardened
mode. Independent verification rejects unsigned proofs by default. A denial
proof is attached to `GovernanceViolation`; durable audit storage additionally
requires an attached archive.

### 2.4 Temporal governance

T.A.R.L. evaluates **time-windowed policies** (`valid_from` / `valid_until`,
durations). Production callers must supply a verified, timezone-aware trusted
clock; an explicitly configured clock that is missing, malformed, or fails
verification denies without falling back to host time. The CLI requires a
zoned `--now` for temporal evaluation.

### 2.5 Static parity (checker)

- **E053** — calling a governed function from a `core` module.
- **Hoisting** — top-level function/class names are pre-declared, so forward
  references and mutual recursion resolve.
- Contract predicates are checked for resolvable names.

---

## 3. Semantic Verifiers

### 3.1 Shadow Thirst (`shadow-thirst`) — safe mutation and governed admission

Parses a `mutation { validated_canonical { shadow{…} invariant{…} canonical{…} } }`
and runs **six AST-based analyzers** to a **PROMOTE / FLAGGED / REJECT** verdict:

1. **PlaneIsolation** — the shadow plane never writes canonical state.
2. **Determinism** — a taint dataflow (`EffectAnalysis`) that follows
   non-determinism (`now`, `rand`, `uuid`, …) **through aliases to a fixpoint**,
   so aliasing `now` into a variable and calling it is still caught.
3. **ResourceEstimator** — CPU cost estimated from AST structure.
4. **PuritySpring** — the invariant block is side-effect free.
5. **MemoryEvaporation** — peak memory from allocation-producing nodes.
6. **CanonicalConvergence** — three layers (see below).

**Layered convergence** answers “does the shadow compute the same thing as the
validated canonical?”:

| Layer | Mechanism | Guarantee |
|---|---|---|
| Structural | alpha-renamed AST equality | sufficient proof of equivalence |
| Z3 symbolic *(opt)* | translate return values to Z3 over shared inputs | proof for **all** inputs, or a **counterexample** |
| Execute-and-compare | run both over seeded inputs in a sandbox | observed equivalence, or the **diverging input** |

Equal-but-differently-shaped blocks (`x + x` is equivalent to `x * 2`) now
**promote**; subtly
different ones (`x + 1` vs `x + 2`) **reject with a witness**. The sampling layer
abstains on blocks with observable effects (return-value equality is unsound
there). Z3 requires `pip install thirsty-lang[analysis]`.

The separate governed-admission layer evaluates technical eligibility without
mutating canonical state or granting execution authority. It adds
security-effect, governance-surface, complexity, and explainability-proxy
regression checks; classifies evidence as **PROVEN**, **OBSERVED**,
**VIOLATED**, **UNKNOWN**, or **INAPPLICABLE**; and emits an **ELIGIBLE**,
**FLAGGED**, or **REJECTED** Change Admission Record. Records bind exact input,
policy, analysis, and artifact hashes and may be signed with an Ed25519
`proof-signer` key. Strict record verification rejects malformed or unknown
fields. Every record keeps `execution_authorized=false` and
`authorization_state=NOT_EVALUATED`; TARL policy, authority, quorum, replay
protection, and governed execution remain separate later boundaries.

CLI: `shadow-thirst check <file>`, `shadow-thirst visualize <file>` (Mermaid),
`shadow-thirst admit <file> --record <record.json>`, and
`shadow-thirst verify-admission <record.json>`.

### 3.2 Thirst of Gods (`thirst-of-gods`) — deity contracts

Structural AST validation of four signals, emitting diagnostics `G001–G004`:

- a fountain with an `init` method,
- **every `cascade` lexically inside a `spillage` handler** (a real error
  consumer — not mere co-presence),
- spillage blocks with handlers,
- cleanup blocks.

CLI: `thirst-of-gods run | check | transpile`.

---

## 4. T.A.R.L. — Policy Engine (`tarl`)

A standalone, first-match-wins policy language.

- **Verdicts:** `ALLOW` / `DENY` / `ESCALATE`, default-deny.
- **Conditions:** comparisons, set membership (`in`), arithmetic, attribute
  access, and temporal builtins (`CURRENT_HOUR`, `CURRENT_WEEKDAY`, …).
- **Authoritative context:** dotted identifiers traverse nested JSON only.
  Flat dotted keys, duplicate keys, mixed representations, missing paths, and
  wrong intermediate types fail closed as distinct resolution states.
- **Schema-bound positive authority:** an evaluator ALLOW is diagnostic until
  a complete schema validated the exact evaluated representation and that
  binding appears in the proof.
- **Proof binding:** original and evaluated context hashes, representation,
  normalization identity/version, conflict status, schema result, policy hash,
  rule, verdict, trace, evaluation time, and expiry.
- **Temporal windows & durations**, with an optional hash-linked audit archive.
- **HMAC and Ed25519 proof signing**; secure-default verification rejects
  unsigned, stale, replayed, revoked, or context-mismatched proofs.
- **Registered sources and quorum:** the exact source-enriched context and
  proof-bound distinct Ed25519 approvals are required for their positive paths.
- **Policy composition.**
- **Z3 static analysis** (`analyze`, `[analysis]` extra): coverage gaps,
  shadowed/dead rules, conflicts, and **equivalence / refinement** proofs
  between two policies.

CLI: `tarl eval | parse | verify | audit | explain | test | analyze`, plus a
`tarl-lsp` language server.

---

## 5. TSCG / TSCG-B — symbolic & binary tiers

- **TSCG (`tscg`):** Thirst’s Symbolic Constitutional Grammar — `parse`,
  `canonical` (normalized form), `checksum` (SHA-256), `validate`, `list`.
  Canonicalization + hashing for tamper-evident symbolic expressions.
- **TSCG-B (`tscg-b`):** binary framing — `encode` / `decode` / `stream`, with
  CRC32 + SHA-256 integrity over each frame.

---

## 6. Tooling & Workflow

- **`thirsty` CLI:** `run`, `repl`, `fmt`, `new` (scaffold), `build`, `govern`,
  `add` / `audit` / `lock` (dependency integrity), `doctor`, `lsp`, `docs`.
- **Console scripts:** `thirsty`, `thirst-of-gods`, `tarl`, `tarl-lsp`, `tscg`,
  `tscg-b`, `shadow-thirst`.
- **UTF-8-safe** CLI output on Windows.
- **CI gate:** Ruff, mypy, full suite on Python 3.11/3.12 with a 90 percent
  coverage floor, production acceptance, every shipped example, and a separate
  wheel-install/all-seven-entry-points smoke job.

---

## 7. Representative use cases

1. **Governed agent/tool runner** — an agent emits `.thirsty`; in `governed`
   mode with a T.A.R.L. policy it may only import/IO what policy allows, every
   action yields a proof, and contracts bound its behavior.
2. **Provably-safe code migration** — propose a refactor as a Shadow Thirst
   `mutation`; promote only if Z3 proves (or sampling shows) equivalence to the
   validated original, else receive the diverging input.
3. **Time-boxed / conditional permissions** — temporal T.A.R.L. policies enforce
   windowed access, provable via the analyzer and auditable via the archive.
4. **Tamper-evident symbolic artifacts** — TSCG canonical form + checksum;
   TSCG-B integrity-framed binary streams.
5. **Contract-checked libraries** — `requires` / `ensures` / `invariant` on
   methods give runtime design-by-contract that `spillage` cannot bypass.

---

See the [whitepaper](WHITEPAPER.md) for the formal model, architecture, and the
soundness arguments behind the verifier layers.
