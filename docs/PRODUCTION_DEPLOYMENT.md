# Production Deployment Requirement

**Applies to:** Thirsty-Lang 0.8.6+ · **Audience:** operators embedding the
governed runtime to authorize real-world, high-risk actions.

The reference runtime meets its hardened-runtime acceptance bar (WHITEPAPER §8)
and, as of 0.7.0, ships the operational machinery that earlier releases left to
the embedder: unified broker mediation, durable cross-process replay/audit
state, and deployment key management. This document is the **checklist** a
deployment must satisfy before it is production-ready. The CI
`production-acceptance` job and `tests/test_production_acceptance.py` enforce the
core of it on every change.

Anything below that is unchecked means the deployment is **not** production-ready
for governed execution.

---

## 1. Run hardened, fail-closed

- [ ] Run every governed entrypoint with `thirsty run --hardened`. Hardened mode
  requires an authenticated (signed) authority **and** Ed25519-signed proofs at
  every gate, or it fails closed.
- [ ] Always attach a policy (`--policy <file>.tarl`). A governed function or
  sensitive stdlib call with no policy engine + authority is **denied with a
  proof** — governed mode never implies authority.
- [ ] Treat a `GovernanceViolation` (CLI exit code `2`) as a hard stop, never a
  warning. The accompanying `TarlProof` is the audit record of the denial.

## 2. One enforcement path (broker + path guard)

- [ ] In-language stdlib effects and any out-of-language adapters (FFI, MCP/tool,
  subprocess) both flow through one `CapabilityBroker`
  (`Interpreter.make_broker()` / `utf.tarl.broker`). Do not add a side adapter
  that performs an effect without `broker.require(...)`.
- [ ] Set a filesystem confinement root for governed file access:
  `Interpreter.set_path_guard([allowed_root, ...])`. File targets are then
  brokered on the **canonical** path, so traversal/symlink escapes fail closed
  before the effect (C042).

## 3. Context authority and registered-source transformations

- [ ] Attach an explicit `ContextSchema`, or require
  `TarlRuntime.ensure_context_schema()` to derive a complete schema, before a
  positive verdict can authorize an effect. A raw evaluator `ALLOW` without a
  passed, proof-bound schema is diagnostic output, not advancement authority.
- [ ] Route load-bearing use through `CapabilityBroker` or the governed
  interpreter. Both apply the positive-context-authority gate and replace an
  inadmissible `ALLOW` with a fail-closed denial.
- [ ] Bind proof verification to the exact original request context. If a policy
  uses registered sources, also provide the exact evaluated context. Verification
  permits only valid top-level `source:<name>` additions whose removal reproduces
  the original context; callers may not supply reserved source fields.
- [ ] Keep caller contexts, registered-source values, and explicit schema files
  inside the strict finite JSON domain. Duplicate keys, non-finite numbers,
  Python-only values, coercive schema metadata, and representation conflicts
  fail closed.
- [ ] Do not rely on expression short-circuiting to skip invalid data. TARL
  validates both boolean operands and every quantifier element, rejects reserved
  `__tarl_*` binders, treats empty quantifier collections as no authorization
  evidence, forbids string-to-number comparison coercion, and requires finite
  numeric operands and arithmetic results (C065–C067).
- [ ] If an embedding passes a differing `policy_text` override to a runtime
  whose schema was derived, require a fresh complete derivation for that exact
  override. An incomplete override must deny; do not reuse the base policy's
  derived schema (C068).

## 4. Durable, cross-process replay & revocation state

In-memory replay/revocation state is lost on restart and not shared across
workers — a replayed proof would be accepted by a second process. Use the
durable stores in `utf.tarl.durable`:

- [ ] Wire a `DurableReplayGuard("<path>.db")` into every `ProofVerifier`
  (`verify --replay-db <db>` from the CLI). The store must be shared by all
  verifying processes (a shared volume or a single DB host).
- [ ] Preserve the store during upgrades. Version 0.8.6 records a complete
  semantic replay identity and a canonicalized legacy identity, so proofs used
  before upgrade remain single-use. Proof signatures must retain their one
  lowercase hexadecimal encoding.
- [ ] Maintain a `RevocationStore("<path>.db")` and hydrate verifiers from it
  (`verify --revocation-store <db>`). Revoke a compromised/rotated policy with
  `tarl revoke <policy-hash> --store <db>`; list with `tarl revoke --list`.

## 5. External audit checkpoints

The audit archive (`TarlAuditArchive`) is SQLite-durable and hash-chained, but a
local attacker who can rewrite the DB could re-link a truncated suffix.

- [ ] On a schedule, write the chain head to a **trusted external location**:
  `tarl audit checkpoint --db <audit.db> --out <head.txt>` and store `head.txt`
  somewhere the runtime host cannot silently rewrite.
- [ ] Verify against it: `tarl audit verify-chain --db <audit.db> --checkpoint
  <head.txt>`. A head that no longer matches the checkpoint reveals suffix
  rewrite or truncation.

## 6. Trust-root key management

Three Ed25519 trust roots must be provisioned: **authority issuer**, **proof
signer**, **time authority** (`utf.tarl.keystore`).

- [ ] Generate each key with `tarl keygen <role> --key-id <id> --out <file>`.
  Private key files are written `0600`; keep them off argv and out of logs.
- [ ] Load keys from files, never as hex on the command line. Use
  `thirsty run --sign-proofs-file <signer.key> --authority-key-file <issuer.pub>`
  and `tarl verify --ed25519-key-file <pub>`. The legacy `ID:HEX` flags are
  deprecated because argv is observable.
- [ ] **Rotation:** mint a new key with a fresh `key_id`, register its public
  half alongside the previous one (verifier registries are keyed by `key_id`, and
  `--ed25519-key-file` is repeatable), switch signing to the new key, then retire
  the old public key only after all in-flight artifacts signed by it have
  expired.
- [ ] Provision a `TimeAuthority` key and run temporal policies against a
  `TrustedClock`, not the host clock (C043).
- [ ] Configure each `QuorumResolver` with an independent `ProofVerifier` and
  the exact policy source, plus an explicit timezone-aware trusted clock.
  Promotion requires an `ESCALATE` proof that passes cryptographic signature,
  policy, context, authoritative-schema, freshness, replay, and expiry
  verification; counted approvers must be distinct by identity and key
  material, each Ed25519 approval must bind the digest of the complete proof
  artifact, and a time-bound promotion must retain its verified signed expiry
  (C069).
- [ ] Bind quorum resolution to the current request by supplying its exact
  original context; for a registered-source proof, also supply the evaluated
  context. Do not promote a self-consistent proof without establishing that it
  belongs to the request being authorized.
- [ ] Configure the quorum's `ProofVerifier` with a maximum proof age and a
  replay guard; the resolver refuses promotion without both. Back the replay
  guard with deployment-wide durable state and configure policy revocation as
  an additional deployment control. Digest-bound approvals do not by themselves
  make an unbounded proof fresh, current, or single-use.
- [ ] Treat `valid_until` as an exclusive cutoff. Runtime decisions and proofs
  bind the earlier of the effective policy cutoff and rule duration; independent
  verification and quorum promotion must receive trusted time and enforce that
  exact bound.

## 7. Secret custody (remains with the deployment)

The runtime defines the **formats and flows**; it does not choose where secrets
live. The deployment owns:

- [ ] Storage of private key files and the durable `.db` stores in a vault, HSM,
  or encrypted volume with least-privilege access.
- [ ] Backup/restore and access auditing for those artifacts.
- [ ] Rotation cadence and revocation response runbooks.

## 8. Release gates (enforced in CI)

- [ ] `ruff check src tests` clean.
- [ ] `mypy -p utf` clean.
- [ ] `pytest --cov=utf --cov-fail-under=90` green.
- [ ] Every shipped example runs; all console scripts install and `--help` on
  3.11 and 3.12.
- [ ] `production-acceptance` job green: a governed program runs under
  `--hardened` with file-based keys, an effect is **allowed with a grant** and
  **denied (exit 2) without one**.

---

## Verifying a deployment end to end

```bash
# 1. Provision trust roots
tarl keygen authority-issuer --key-id issuer-1 --out issuer.key
tarl keygen proof-signer     --key-id signer-1 --out signer.key

# 2. Run a governed program hardened, with file-based keys + a policy
thirsty run app.thirsty --thirst-level governed --hardened \
    --policy policy.tarl \
    --authority-token token.json --authority-key-file issuer.key.pub \
    --sign-proofs-file signer.key
#   -> allowed effects run; a denied effect exits 2 with a proof

# 3. Checkpoint and verify the audit chain
tarl audit checkpoint --db audit.db --out head.txt
tarl audit verify-chain --db audit.db --checkpoint head.txt

# 4. Verify a proof with durable replay + revocation, rejecting reuse
tarl verify proof.json --ed25519-key-file signer.key.pub --ed25519-only \
    --context-file context.json \
    --replay-db replay.db --revocation-store revocations.db
```

For a registered-source proof, add
`--evaluated-context-file evaluated-context.json`; both files are mandatory for
accepting that transformed positive decision.

See also: [WHITEPAPER.md](WHITEPAPER.md) §8–§9, [THREAT_MODEL.md](THREAT_MODEL.md)
§"Remaining Gaps", [governance_model.md](governance_model.md),
[STATUS.md](STATUS.md).
