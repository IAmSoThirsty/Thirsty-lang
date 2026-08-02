# Signing Wheel Releases

This guide covers how to sign Thirsty-Lang wheel distributions using GPG.

## Setup (One-time)

### 1. Generate GPG Key (if not already done)

```bash
gpg --gen-key
# Follow prompts:
# - Key type: RSA
# - Key size: 4096
# - Name: Thirsty's Projects LLC
# - Email: releases@thirsty-projects.local
# - No passphrase (or use one for extra security)
```

### 2. Export Public Key

```bash
gpg --export --armor <YOUR_KEY_ID> > public_key.asc
# Upload to keyserver (optional, for verifying published signatures)
gpg --send-keys <YOUR_KEY_ID> --keyserver keyserver.ubuntu.com
```

### 3. Add Private Key to GitHub Secrets

1. Export private key:
   ```bash
   gpg --export-secret-key --armor <YOUR_KEY_ID> > private_key.asc
   ```

2. In GitHub repo settings → Secrets and variables → Actions:
   - Add `GPG_PRIVATE_KEY` = contents of private_key.asc
   - Add `GPG_PASSPHRASE` = passphrase (if key is protected)

## Release Workflow with Signing

### Manual Signing (Local)

```bash
# Build wheel
python -m build

# Sign wheel
gpg --detach-sign --armor dist/thirsty_lang-0.8.6-py3-none-any.whl
# Creates: thirsty_lang-0.8.6-py3-none-any.whl.asc

# Upload both files to PyPI
twine upload dist/thirsty_lang-0.8.6* --sign --identity <YOUR_KEY_ID>
```

### Automated Signing (GitHub Actions)

The release workflow can be enhanced to sign wheels:

```yaml
- name: Install GPG
  run: sudo apt-get install -y gnupg

- name: Import GPG key
  run: |
    echo "${{ secrets.GPG_PRIVATE_KEY }}" | gpg --import
    gpg --list-secret-keys

- name: Sign wheels
  run: |
    cd dist
    for wheel in *.whl; do
      gpg --detach-sign --armor "$wheel"
    done

- name: Publish with signatures
  uses: pypa/gh-action-pypi-publish@ba38be9e461d3875417946c167d0b5f3d385a247 # release/v1
  with:
    skip-existing: true
```

## Verifying Signatures

Users can verify downloaded wheels:

```bash
# Download public key
curl -O https://keyserver.ubuntu.com/pks/lookup?op=get&search=<KEY_ID>

# Import key
gpg --import public_key.asc

# Verify signature
gpg --verify thirsty_lang-0.8.6-py3-none-any.whl.asc thirsty_lang-0.8.6-py3-none-any.whl
```

## Best Practices

1. **Use a dedicated key** for releases (separate from personal GPG key)
2. **Protect private keys** with strong passphrases
3. **Rotate keys** annually
4. **Publish public key** to multiple keyservers
5. **Document key fingerprint** in project security policy
6. **Test verification** before publicizing signatures

## PyPI Release Authentication

The current `.github/workflows/release.yml` publishes through the pinned PyPI
publish action using a scoped PyPI API token. The token is stored as the
`IAMSOTHIRSTY` secret in the GitHub Actions `release` environment and is passed
with the `__token__` username; it is never stored in the repository.

PyPI Trusted Publishing through GitHub OIDC is not the active authentication
path. A future migration can remove the token input after the PyPI project has a
matching trusted-publisher configuration for owner `IAmSoThirsty`, repository
`Thirsty-lang`, and workflow `release.yml`.

## References

- [PEP 740 — Trusted Publishing](https://peps.python.org/pep-0740/)
- [PyPI Help: Publishing](https://pypi.org/help/)
- [GPG Handbook](https://www.gnupg.org/documentation/)
