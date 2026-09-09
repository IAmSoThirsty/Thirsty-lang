# Governance Model

Edition: unreleased development after Thirsty-Lang 0.9.0. See the
[canonical Thirsty-Lang UTF 101 manual](THIRSTY_LANG_UTF_101.md) for the complete
end-to-end reference and deployment recipes.

## Overview

Thirsty-Lang implements a **deny-by-default governance model** via T.A.R.L.
(Thirsty's Active Resistance Language). Governed calls and operations in the
explicit sensitive-capability map require authorization before execution.
This posture is the default for the CLI, REPL, embedding interpreter, and
Thirst of Gods execution entrypoints. Deterministic calculations do not need an
I/O policy simply to execute.

## Core Principles

1. **Deny by Default**: Governed calls, imports, and mediated effects require an
   explicit authorization; a missing policy or authority denies the gate.
2. **Policy-Driven**: Authorization rules are expressed as declarative policies, not imperative code.
3. **Staged Evaluation**: Policies support three verdicts:
   - **ALLOW** — Operation proceeds
   - **DENY** — Operation is blocked
   - **ESCALATE** — Operation requires manual review or higher-tier approval

4. **Composable Tiers**: Governance tiers stack (Tier 1 through Tier 6), with higher tiers enforcing stricter policies.

## T.A.R.L. Policy Language

### Syntax

```
policy <policy_name>

when <condition> => ALLOW|DENY|ESCALATE
when <condition> => ALLOW|DENY|ESCALATE
...
```

### Example Policy

```
policy resource_access

when role == "admin" => ALLOW
when role == "user" and level >= 3 => ALLOW
when action == "delete" and resource == "critical" => ESCALATE
when action == "read" and resource == "public" => ALLOW
when action == "write" and resource == "system" => DENY
when source == "external" and port > 1024 => DENY
```

### Conditions

Conditions are evaluated as restricted expressions supporting:

- **Comparisons**: `==`, `!=`, `<`, `>`, `<=`, `>=`
- **Logical operators**: `and`, `or`, `not`
- **Literals**: strings (`"value"`), integers (`42`), floats (`3.14`), booleans (`true`/`false`)
- **Context variables**: top-level identifiers and dotted paths into nested
  objects (`user.role` resolves `{"user":{"role":"admin"}}`)
- **Arithmetic**: Addition (`+`) within comparisons

### Safe Evaluation

T.A.R.L. expressions use a restricted AST evaluator:

- Missing identifiers and paths are a distinct `MISSING` state and terminate
  evaluation with a fail-closed verdict; they never become boolean `false`
- Wrong intermediate types are `TYPE_ERROR`; dotted flat/nested ambiguity is
  `REPRESENTATION_CONFLICT`; neither state participates in ordinary operators
- Only literal values and safe operators allowed
- Only the documented safe functions are callable; imports and mutation are
  unavailable
- Deterministic first-match rule evaluation in source order

This evaluator is not an operating-system sandbox or a general resource limit
for host processes.

### Authoritative context representation

T.A.R.L. evaluates canonical nested objects after `prepare_context()` normalizes
dotted, nested, or equivalent mixed input. For example, this policy:

```tarl
when user.role == "admin" => ALLOW
```

is evaluated with:

```json
{"user":{"role":"admin"}}
```

`{"user.role":"admin"}` normalizes to the same nested path. Supplying both
forms is accepted only when values agree. Contradictory values, malformed paths,
JSON duplicate keys, and conflicting caller/authority/source/action layers are
rejected. Proofs record original and canonical context hashes and the
`tarl.context.dotted-path-expansion` algorithm, version `1`.

Missing is not false. Invalid is not false. Unresolved is not evidence. A real
resolved value such as `{"feature":{"enabled":false}}` remains an ordinary
boolean and can be compared to `false`.

## Integration with Thirsty-Lang

### Runtime Enforcement (the interpreter, today)

The source headers `core`, `strict`, and `pure` select language semantics; they
cannot disable governance. `pure` also refuses ambient effects, including through
aliases and cascade callbacks. Deterministic imports in a pure module still
require import authorization. `strict` retains initialization requirements.
Definitions preserve these restrictions when their interpreter later runs a
less restrictive module.

Ungoverned core compatibility requires the trusted host to opt in with
`thirsty run --unsafe-core`, `thirsty repl --unsafe-core`, or
`Interpreter(allow_ungoverned=True)`. An explicit governed declaration or request
still requires governance. Attached policy, hardened posture, and required-audit
controls retain their gates; the CLI rejects combining its unsafe opt-out with
security controls.

Governance is enforced at runtime for **governed functions** — functions that
declare a precondition with `requires`:

```thirsty
module bank: governed
glass withdraw(amt) requires amt > 0 {
    return amt * 2
}
```

On **every call** to a governed function, the interpreter applies a layered,
default-deny decision (`Interpreter._enforce_governance`):

1. **In-language contract predicates** — `requires`, `ensures`, and `invariant`
   expressions are evaluated in the call scope. A falsy result denies the call
   and raises `GovernanceViolation`.
2. **Execution posture** — the default governance requirement survives semantic
   mode changes. Checker error `E053` applies to governed calls in an explicitly
   ungoverned compatibility context, rather than to a `core` header alone.
3. **T.A.R.L. routing** — attach a `TarlRuntime`
   (`interpreter.attach_tarl(runtime)`) and set an authority context to route
   the call through the policy engine. A non-`ALLOW` verdict denies. An
   `ALLOW` advances only when an explicit or completely derived schema passed
   against the evaluated representation and that result is proof-bound; an
   unbound or incomplete-schema `ALLOW` is replaced with a fail-closed denial.
   Each distinct active defining and calling policy must allow the action;
   a foreign closure cannot borrow its defining interpreter's ALLOW to bypass
   its caller's DENY. The same conjunction applies to mediated capabilities.
   Identical runtime, authority, credential, and guard bindings share one
   decision instead of duplicating its audit record. Distinct authorities or
   path guards retain their independent checks. A final pass checks every
   binding after callback-capable credential validation, before releasing the
   call or effect.
   The same positive-authority gate applies to `CapabilityBroker`. A `TarlProof`
   certificate is recorded on `interpreter._last_proof`.

   The proof binds the policy hash; original and canonical/evaluated context
   hashes; context representation ID; normalization algorithm ID and version;
   conflict status; schema fingerprint, representation, and validation result;
   matched rule and condition; verdict; evaluation trace/time; and applicable
   expiry. An identity evaluation has equal
   original and canonical hashes. A rejected context can produce a DENY proof
   but never an admissible positive proof. It is **unsigned by default**.
   Two signing modes exist: legacy **HMAC-SHA256**, a *symmetric* MAC that is
   forgeable by anyone holding the shared key, and **Ed25519**, an asymmetric
   signature whose verifier needs only the public key. Use Ed25519 when a proof
   must attest to the signer rather than merely detect tampering by parties
   without the shared HMAC key. The `thirsty run` path emits unsigned proofs
   unless CLI signing options or the embedding runtime configure a signing key.

   Rule evaluation validates the whole expression surface before accepting its
   boolean result. Both operands of `and`/`or` and every predicate application
   in `ALL`/`ANY` are evaluated, so a missing or malformed value cannot be
   hidden behind a decisive earlier result. Comparisons are type-strict:
   integers and floats interoperate, but strings never coerce to numbers.
   Numeric operands and arithmetic results must remain finite. Empty quantifier
   collections fail closed rather than authorizing through vacuous truth.
   Quantifier binders using the reserved `__tarl_*` runtime namespace are
   rejected.

   If `evaluate(..., policy_text=...)` or `evaluate_with_proof(...)` supplies a
   policy different from `runtime.policy` while the runtime schema was derived,
   the runtime derives and binds a schema from that exact override. It denies
   when override derivation is incomplete or invalid; it does not reuse the
   base policy's derived schema. An explicitly attached schema remains the
   caller's authoritative binding.
4. **Default** — a governed function with no attached
   policy engine or no authority is **denied** with a proof. A call that no
   layer explicitly allowed is denied (deny-by-default).

A `GovernanceViolation` is a hard floor: `spillage` error handlers do **not**
catch it, so governed denials cannot be swallowed by user error handling. This
includes denials raised while importing a `.thirsty` module. Imported modules
retain active defining and calling restrictions, including live import locks.
All active locks must accept an import and agree on returned source content;
the interpreter executes that checked content without a fresh source read.
Malformed source is refused before recovered statements execute. Import checks
do not establish the original source identity of an arbitrary foreign closure
supplied by the embedding host.

For verification, `ProofVerifier` rejects unsigned proofs by default. Local
inspection of unsigned proofs must opt in explicitly with
`ProofVerifier(require_signature=False)` or `tarl verify --allow-unsigned`.
Hardened deployments can also restrict signature algorithms (for example,
Ed25519-only) and require policy-source binding. The CLI exposes these as
`tarl verify --ed25519-only --policy <policy.tarl>`. Signed proofs use one
canonical lowercase hexadecimal signature encoding. Replay identity binds the
complete proof semantics, signing key, algorithm, and decoded signature bytes,
so a cryptographically identical re-encoding cannot obtain a second use.
Authority consumers must also supply the expected original context. A
registered-source `ALLOW` requires
the exact source-enriched evaluated context as well; the verifier accepts only
valid top-level `source:<name>` additions that leave the original context
unchanged.

An escalation quorum is a separate positive-authority consumer. A
`QuorumResolver` must be configured with an independent `ProofVerifier` and the
exact policy source. It promotes only an `ESCALATE` decision whose proof is
independently verified, cryptographically signed, policy-bound, internally
consistent, unexpired, and bound to a passed authoritative context schema. Each
approval signs the SHA-256 digest of the complete proof artifact; duplicate
approver identities or duplicate public-key material count once. A time-bound
promoted decision retains its verified signed expiry. Every resolution requires
the exact original request context, an explicit timezone-aware trusted clock,
and a verifier configured with a maximum proof age and replay guard; the
resolver fails closed when any is absent. Registered-source escalation proofs
also require the exact evaluated context. Deployments should additionally use a
shared durable replay store and configure policy revocation; approval signatures
over a proof digest do not make an unbounded proof fresh, current, or single-use
by themselves.

All public executable builds to `js`, `llvm-*`, or `wasm-pyodide` require
`thirsty build --allow-governance-loss`, including headerless and `core` source.
The targets cannot preserve host policy and authority configuration. Thirst of
Gods JavaScript transpilation requires the same explicit acknowledgement.
An accepted build must write its disclosure manifest before producing the
executable artifact or invoking a native toolchain; `--emit-manifest` is not
required to obtain that mandatory record. A manifest write failure prevents
that build from producing an executable.

The manifest records source hash, optional policy hash, statically discovered
capabilities, context schema, semantic mode and governance posture, proof and
audit requirements, visible Shadow Thirst status, and governance-loss status.
It is a disclosure of bounded static analysis, not a complete dynamic effect
inventory or proof of executable safety. Pyodide still preserves explicit
governed source declarations and denies their effects without a policy.

### Static proof-obligation reporting

`thirsty prove` is a static, no-side-effect path:

```bash
thirsty prove program.thirsty --policy policy.tarl --emit-manifest
```

It lexes, parses, checks, and walks the AST, then emits a machine-readable JSON
report. It does not instantiate the interpreter and does not execute program
side effects. The report includes functions, imports, sensitive stdlib calls,
governed calls, required TARL actions, required capabilities, context schema,
authority requirements, contract obligations, proof mode, audit requirement,
Shadow Thirst status, governance-loss status, diagnostics, and unresolved proof
gaps. Required TARL actions include capability actions and governed function-call
actions.

Context schema handling is fail-closed. If `--context-schema schema.json` is
provided, that explicit schema is authoritative. Without an explicit schema,
`thirsty prove` derives field names and simple kinds from TARL policy
references where possible. Ambiguous references are reported as
`context_schema.status = incomplete`, and `thirsty prove` exits non-zero instead
of claiming the proof obligation set is complete.
Explicit schema files may use a list of field objects or a compact mapping:

```json
{"fields": {"user.role": "string", "risk": {"kind": "number", "required": false}}}
```

Schema field names use the same dotted-path notation as policies, and generated
schemas declare `tarl.context.nested-json.v1` with no normalization. A schema
that declares another representation or requests normalization is rejected.
The loader also rejects duplicate/conflicting representation metadata,
duplicate field names, unknown kinds, non-boolean `required`, and
`on_violation: ALLOW`; schema metadata is never coerced silently.

Malformed explicit schema entries fail with validation errors instead of being
treated as proof-ready.

Runtime-derived schemas follow the evaluated policy identity. A differing
`policy_text` override receives a fresh derivation and proof binding; an
incomplete override schema produces DENY rather than inheriting the base
policy's derived schema.

`thirsty explain-denial program.thirsty --policy policy.tarl` emits a
machine-readable explanation of missing policy, context, authority, and proof
conditions for the same static obligation set.

From the CLI:

```bash
thirsty run program.thirsty --authority admin --policy access.tarl
```

`--authority` injects the authority tag into the governance context; `--policy`
routes governed calls through the named `.tarl` policy. A denial prints
`governance denied: <fn>: <reason>` (with the proof verdict/hash when policy
routing produced one) and exits non-zero.

### Extended governance surfaces

The governed interpreter routes shipped filesystem, network, process, and
other sensitive stdlib effects through `CapabilityBroker`. Every shipped
stdlib export has an explicit sensitive or non-ambient classification;
unknown, missing, or non-callable exports fail import validation. An import
ALLOW does not grant the imported function's sensitive capability. External adapters
must call that same broker before acting; deployments remain responsible for
preserving the path when they add new adapters.

## Runtime Evaluation

### TarlRuntime

The `TarlRuntime` class provides:

1. **LRU Caching** (128 entries) — Policies are cached by policy identity plus
   original/evaluated context binding and transformation metadata
2. **Parallel rule evaluation** — Decision-only evaluation may submit rules
   concurrently; selecting the winning rule still follows source order
3. **Adaptive submission** — Hit counts affect task submission order, never
   policy priority. Proof and required-audit evaluation preserve source order
4. **Policy Hotswapping** — Policies can be updated at runtime without restart
5. **Optional durable audit** — `set_archive(TarlAuditArchive(...))` persists
   generated proofs. `set_require_audit(True)` denies when an archive is absent
   or cannot persist, including `evaluate()` without a requested proof result.
   Hardened interpreter mode alone does not create an archive. The CLI exposes
   `--audit-db` and `--require-audit` under the default governance posture.

### CLI Usage

Evaluate a policy against a context:

```bash
tarl eval policy.tarl --context '{"role":"user","level":2}'
```

For a dotted policy path, pass nested JSON and bind the same representation
when verifying its proof:

```bash
tarl eval policy.tarl --context '{"user":{"role":"admin"}}'
tarl verify proof.json --context '{"user":{"role":"admin"}}'
```

If the policy uses a registered source, verification preserves and checks the
transformation explicitly:

```bash
tarl verify source-proof.json \
    --context '{"role":"admin"}' \
    --evaluated-context '{"role":"admin","source:trusted_roles":["admin"]}'
```

Temporal policy windows, time-bound verdicts, `CURRENT_*` builtins, and
`ELAPSED_SINCE` require an explicitly zoned trusted evaluation time on the CLI.
A configured runtime clock that cannot produce such a time fails closed without
falling back to the host clock. Temporal metadata and durations are parsed
strictly, expiry cannot grant `ALLOW`, and proof authority is capped at the
earliest exclusive policy or rule cutoff:

```bash
tarl eval policy.tarl --context '{"role":"user"}' --now 2026-07-01T12:00:00Z
```

Parse and display a policy:

```bash
tarl parse policy.tarl
```

## Security Considerations

1. **Context Injection** — Contexts are supplied at runtime; validate all sources
2. **Policy Updates** — Policies should be cryptographically signed before deployment
3. **Audit Logging** — Attach an archive and require persistence for deployments
   that depend on durable decision records; checkpoint the chain externally
4. **Performance** — Cache identity binds policy, context, schema, and source
   values; temporally constrained policies bypass the decision cache

## Future Enhancements

- **Cryptographic Policy Signatures** — Sign policies to prevent tampering
- **Signed policy distribution** — Bind deployed policy sources to an external
  release/transparency process
- **Adapter conformance automation** — Inventory deployment-specific adapters
  and prove that each reaches the broker
- **External trust services** — HSM-backed key custody and independently hosted
  durable replay/audit infrastructure
- **Metrics & Analytics** — Track policy evaluation metrics for optimization
