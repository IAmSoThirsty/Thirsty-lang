# Publishing Thirsty-Lang

Guides for publishing across all three distribution channels.

---

## 1. VS Code Marketplace

### Prerequisites

- Node.js ≥ 14
- A [Visual Studio Marketplace](https://marketplace.visualstudio.com/manage) publisher account (publisher: `IAmSoThirsty`)
- A Personal Access Token (PAT) from [Azure DevOps](https://dev.azure.com/) with **Marketplace (Manage)** scope

### Steps

```bash
# Install the packaging tool
npm install -g @vscode/vsce

# Navigate to the extension directory
cd vscode-extension

# Login to your publisher (one-time)
vsce login IAmSoThirsty
# Paste your PAT when prompted

# Package into a .vsix file (for testing)
vsce package --no-dependencies

# Publish to the Marketplace
vsce publish --no-dependencies
```

### Verification

1. Install the `.vsix` locally first: **Extensions → ⋯ → Install from VSIX…**
2. Open a `.thirsty`, `.tog`, `.tarl`, or `.shadow` file — verify syntax highlighting, snippets, and bracket matching work.
3. After publishing, search "Thirsty-Lang" on the [Marketplace](https://marketplace.visualstudio.com/) to confirm it appears.

### Updating

```bash
# Bump version and publish
vsce publish minor   # 1.0.0 → 1.1.0
vsce publish patch   # 1.0.0 → 1.0.1
```

---

## 2. npm

### Prerequisites

- Node.js ≥ 14
- An [npmjs.com](https://www.npmjs.com/) account
- `npm login` completed

### Steps

```bash
# From the repo root
cd /path/to/Thirsty-Lang

# Verify what will be published
npm pack --dry-run

# Test locally
npm link
thirsty examples/hello.thirsty

# Publish (public, unscoped)
npm publish

# Or publish under a scope
npm publish --access public
```

### Verification

```bash
# Install globally from npm to verify
npm install -g Thirsty-Lang
thirsty --help
thirsty examples/hello.thirsty
```

### Updating

```bash
# Bump version, commit, tag, and publish
npm version patch   # or minor / major
npm publish
```

---

## 3. PyPI

### Prerequisites

- Python ≥ 3.8
- `build` and `twine` packages: `pip install build twine`
- A [PyPI](https://pypi.org/) account and API token
- (Recommended) A [TestPyPI](https://test.pypi.org/) account for dry-runs

### Steps

```bash
# From the repo root
cd /path/to/Thirsty-Lang

# Build the sdist and wheel
python -m build

# Verify the package contents
tar -tzf dist/thirsty_lang-2.0.0.tar.gz | head -20

# Upload to TestPyPI first
twine upload --repository testpypi dist/*
# Visit: https://test.pypi.org/project/Thirsty-Lang/

# Install from TestPyPI to verify
pip install -i https://test.pypi.org/simple/ Thirsty-Lang
thirsty examples/hello.thirsty
python -m thirsty_lang examples/hello.thirsty

# Upload to production PyPI
twine upload dist/*
```

### Configuration

Create `~/.pypirc` for convenience:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_TOKEN_HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR_TEST_TOKEN_HERE
```

### Verification

```bash
pip install Thirsty-Lang
thirsty examples/hello.thirsty
python -m thirsty_lang examples/hello.thirsty
python -c "from thirsty_lang import ThirstyInterpreter; print('OK')"
```

### Updating

```bash
# Update version in pyproject.toml, then:
python -m build
twine upload dist/*
```

---

## Pre-Publish Checklist

- [ ] All tests pass: `npm test`
- [ ] Version bumped in `package.json`, `pyproject.toml`, `VERSION.txt`, and `thirsty_lang/__init__.py`
- [ ] `CHANGELOG.md` updated with release notes
- [ ] `icon.png` present in `vscode-extension/`
- [ ] `.npmignore` excludes dev artifacts
- [ ] `README.md` is current and accurate
- [ ] Playground runs correctly in browser
