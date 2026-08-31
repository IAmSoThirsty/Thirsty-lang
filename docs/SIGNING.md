# Release Authentication, Attestations, and Optional Signatures

Edition: Thirsty-Lang 0.8.6 (2026-08-02)

This guide separates three mechanisms that protect different things:

| Mechanism | Purpose | 0.8.6 status |
|---|---|---|
| PyPI API token | Authenticates the upload account | Active |
| PyPI Trusted Publishing and publish attestations | Binds an uploaded file to a supported CI identity through OIDC | Not active for 0.8.6 |
| TARL HMAC or Ed25519 signatures | Bind policy-verdict proofs inside the language runtime | Active; unrelated to package publication |
| Detached OpenPGP signature | Optional out-of-band signature distributed somewhere other than PyPI | Not produced by the release workflow |

The current `.github/workflows/release.yml` validates the tagged commit, builds
the wheel and source distribution, checks metadata, and publishes through the
pinned PyPA action. Authentication uses the project-scoped PyPI API token in
the GitHub `release` environment secret named `IAMSOTHIRSTY`. The repository
does not contain that secret.

## Current 0.8.6 publication contract

The release workflow enforces:

1. The Git tag version matches `pyproject.toml`.
2. Ruff and mypy pass.
3. The full test suite passes with at least 90 percent coverage.
4. The package builds and `twine check` accepts every distribution.
5. The pinned publisher action uploads with `__token__` credentials.

This is authenticated package publication, but it is not PyPI Trusted
Publishing. Consequently the 0.8.6 files do not carry the Trusted Publisher
publish-attestation claim described by PyPI.

## Recommended future migration: Trusted Publishing

PyPI Trusted Publishing exchanges a GitHub Actions OIDC identity for a
short-lived upload token. It removes the long-lived project API token from the
workflow and enables PyPI's supported publish-attestation path.

Migration requires an external PyPI project configuration that exactly matches:

- owner: `IAmSoThirsty`
- repository: `Thirsty-lang`
- workflow: `release.yml`
- environment: `release`

After that external configuration is verified, remove the explicit `user` and
`password` inputs from the PyPA publishing step and grant `id-token: write` to
the publish job. Do not make only one side of this change: a workflow/PyPI
identity mismatch fails publication.

The official PyPA publishing action generates and uploads supported
attestations by default when it publishes through Trusted Publishing. A token-
authenticated upload must not be described as having that OIDC provenance.

## Optional detached OpenPGP signatures

OpenPGP signatures can still be useful when the project operates a separate,
documented distribution channel for both the artifact and signature. They are
not a substitute for PyPI Trusted Publishing.

Current Twine warns that PyPI and TestPyPI silently ignore attached PGP
signatures. Do not use `twine upload --sign` or upload `.asc` files as evidence
that PyPI users received or verified a signature.

If an out-of-band channel is intentionally established:

```bash
python -m build
gpg --detach-sign --armor dist/thirsty_lang-0.8.6-py3-none-any.whl
gpg --verify \
  dist/thirsty_lang-0.8.6-py3-none-any.whl.asc \
  dist/thirsty_lang-0.8.6-py3-none-any.whl
```

Use a dedicated protected release key, keep its passphrase and private material
outside the repository, publish the complete fingerprint through an
authenticated channel, document rotation and revocation, and test the consumer
verification procedure. Never recommend an unprotected private release key.

## TARL proof signing is separate

TARL proof signatures establish authority over an evaluated policy decision,
not provenance for a wheel file. See the
[canonical Thirsty-Lang 101 manual](THIRSTY_LANG_101.md) and
[`governance_model.md`](governance_model.md) for proof canonicalization, HMAC
compatibility, Ed25519 attribution, key identifiers, replay identity, expiry,
and revocation.

## References

- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [PyPI: Producing attestations](https://docs.pypi.org/attestations/producing-attestations/)
- [Twine upload implementation and PGP warning](https://twine.readthedocs.io/en/stable/_modules/twine/commands/upload.html)
- [GNU Privacy Handbook](https://www.gnupg.org/gph/en/manual.html)
