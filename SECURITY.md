# Security Policy

## Supported Versions

Thirsty-Lang is currently in alpha (v0.8.6). Security updates are applied to
the latest release only.

Versions through 0.8.5 must not be used for load-bearing authorization with
dotted context paths. Upgrade to 0.8.6 for fail-closed missing, malformed, and
conflicting context handling. The repaired release also fails closed on hidden
invalid boolean/quantifier values, empty quantifier collections, non-finite
numeric results, stale per-policy derived schemas, and inadmissible quorum
proofs. Quorum promotion additionally requires the exact request context,
trusted verification time, proof freshness, and replay enforcement. Proof
signatures have one canonical lowercase hexadecimal encoding, and replay
identity binds the complete proof semantics plus decoded signature bytes.
Configured trusted clocks and CLI trusted-time values must be timezone-aware;
an invalid clock fails closed without host-clock fallback. Malformed temporal
directives are rejected, expiry can never grant `ALLOW`, and proof authority is
  capped at the earliest exclusive policy or rule cutoff. The 0.8.6 package,
  branch CI, release workflow, GHCR build, and fresh-install regression matrix
  passed. Independent constitutional acceptance remains required before the
  Competence Register can unblock load-bearing positive authority.

| Version           | Supported          |
| ----------------- | ------------------ |
| 0.8.6             | :white_check_mark: |
| 0.8.5 and earlier | :x:                |

## Reporting a Vulnerability

Thirsty-Lang takes security seriously. The project is designed around governance-first principles where security is a first-class concern at every tier.

If you discover a security vulnerability in Thirsty-Lang, please report it privately before disclosing it publicly.

### How to Report

**Do not report security vulnerabilities through public channels.**

Send a detailed report to FounderOfTP@thirstysprojects.com.

### What to Include

To help us respond quickly, please include:
- Type of vulnerability
- Full reproduction steps
- Affected tiers and components
- Potential impact
- Any suggested mitigations (if known)

### Response Timeline

- **Acknowledgment**: Within 48 hours of receiving your report
- **Investigation**: Within 5 business days
- **Fix and Release**: Timeline depends on severity and complexity
- **Public Disclosure**: After a fix is released, typically within 30 days

### Disclosure Policy

We follow a coordinated disclosure process:
1. Reporter submits vulnerability details
2. We acknowledge receipt within 48 hours
3. We investigate and develop a fix
4. A security release is prepared and published
5. The vulnerability is publicly disclosed after the fix is available

## Security-Relevant Components

The following shipped components have security implications and receive
priority attention:

- **T.A.R.L. (Tier 3)**: Policy enforcement engine with default-DENY
- **Shadow Thirst (Tier 4)**: Mutation analysis and invariant verification
- **TSCG/TSCG-B (Tiers 5-6)**: Symbolic constraint grammar and binary protocol
- **Capability broker and governed interpreter**: load-bearing positive verdict
  admission and sensitive effect mediation
- **Authority, verifier, durable stores, and audit archive**: signature,
  replay, revocation, time, and persistence controls

The top-level `governance/` tree and `src/psia` are repository-local surfaces;
they are not included in the published 0.8.6 Python package and are not part of
its installed security boundary.

## Offensive Threat Model

The adversary model and challenge catalog are maintained in
[`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md). Security claims should map to a
  challenge ID, a passing test, or a roadmap gap. In hardened use, a missing
  policy, missing authority, missing proof, failed signature verification, or
  stale proof must fail closed. Durable audit persistence is an explicit
  embedding control: attach `TarlAuditArchive` and call
  `set_require_audit(True)`. If an attached required archive cannot persist the
  proof, the runtime denies; `--hardened` alone does not create an audit sink.

## Default DENY

Thirsty-Lang's core security principle is **default DENY at every governance
gate**. A governed action cannot advance through the capability broker without
the policy, context, authority, and proof required by that gate. The symbolic
and binary tiers provide analysis or integrity services; they should not be
mistaken for independent authorization gates.

## Security Best Practices

- Always run untrusted code in governed mode
- Review T.A.R.L. policies before deployment
- Verify Shadow Thirst promotion results
- Attach a durable audit archive, enable required persistence, checkpoint it,
  and verify its hash chain
- Follow [`docs/PRODUCTION_DEPLOYMENT.md`](docs/PRODUCTION_DEPLOYMENT.md) and the
  [canonical Thirsty-Lang 101 manual](docs/THIRSTY_LANG_101.md)

---

**Thirsty's Projects LLC**
