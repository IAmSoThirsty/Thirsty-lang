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
capped at the earliest exclusive policy or rule cutoff. Independent
repaired-artifact acceptance remains required before the
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

The following components have security implications and receive priority attention:

- **T.A.R.L. (Tier 3)**: Policy enforcement engine with default-DENY
- **Shadow Thirst (Tier 4)**: Mutation analysis and invariant verification
- **TSCG/TSCG-B (Tiers 5-6)**: Symbolic constraint grammar and binary protocol
- **Triumvirate Server**: 3-pillar governance (ethics, security, constitutional)
- **Iron Path**: Sovereign execution with cryptographic audit trails
- **PSIA Pipeline**: 7-stage security preprocessing pipeline

## Offensive Threat Model

The adversary model and challenge catalog are maintained in
[`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md). Security claims should map to a
challenge ID, a passing test, or a roadmap gap. In hardened use, a missing
policy, missing authority, missing proof, failed signature verification, stale
proof, or unavailable audit sink must fail closed.

## Default DENY

Thirsty-Lang's core security principle: **Default DENY at every governance gate.** Every tier enforces a default-deny posture — code cannot execute, data cannot flow, and mutations cannot commit unless explicitly authorized.

## Security Best Practices

- Always run untrusted code in governed mode
- Review T.A.R.L. policies before deployment
- Verify Shadow Thirst promotion results
- Enable Iron Path for production deployments
- Keep audit trails enabled and backed up

---

**Thirsty's Projects LLC**
