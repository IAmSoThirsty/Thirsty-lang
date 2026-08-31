# Contributing to Thirsty-Lang

Thank you for your interest in contributing to Thirsty-Lang. This guide tracks
the checks enforced by the repository at version 0.8.6. Start with the
[canonical Thirsty-Lang 101 manual](docs/THIRSTY_LANG_101.md) for the complete
language, governance, security, and operations map.

## Code of Conduct

All contributors are expected to uphold a respectful, inclusive, and constructive environment. Harassment, discrimination, or any form of unprofessional behavior will not be tolerated.

When contributing, please:
- Be respectful and considerate of others
- Provide constructive feedback
- Focus on what is best for the community and the project
- Show empathy towards other community members
## How to Contribute

### Reporting Issues

If you find a bug or have a feature request, please email FounderOfTP@thirstysprojects.com with full details.

When reporting, please include:
- A clear description of the issue
- Steps to reproduce
- Expected behavior vs actual behavior
- Version information (output of `thirsty --version`)
- Any relevant error messages or stack traces

### Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run the test suite: `python -m pytest tests/ -v`
5. Commit your changes with clear commit messages
6. Push to your fork
7. Open a Pull Request

### Development Setup

```bash
# Clone the repository
git clone https://github.com/IAmSoThirsty/Thirsty-lang.git
cd Thirsty-lang

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # PowerShell: .\.venv\Scripts\Activate.ps1

# Install code, analysis, and documentation dependencies
python -m pip install --upgrade pip
python -m pip install -e ".[dev,analysis,docs]"

# Verify installation
thirsty --version
thirst-of-gods --help
tarl --help
tarl-lsp --help
shadow-thirst --help
tscg --help
tscg-b --help
```

### Development Workflow

Run the same code gates used by CI before committing:

```bash
# Format code, if your change touched Python
black src/ tests/

# Lint without silently rewriting the tree
ruff check src tests

# Type-check the installed package surface
mypy -p utf

# Run the release-equivalent suite and coverage floor
python -m pytest tests/ -q --cov=utf --cov-report=term-missing --cov-fail-under=90
```

The repository does not currently ship a pre-commit configuration. Do not rely
on local hooks as evidence that CI will pass. The authoritative gates are
`.github/workflows/smoke.yml` and `.github/workflows/release.yml`.

For documentation or PDF changes, also run:

```bash
python scripts/build_thirsty_lang_101.py
python scripts/verify_thirsty_lang_101.py output/pdf/Thirsty-Lang-101.pdf
python -m pytest tests/test_thirsty_lang_101_pdf.py -q
```

### Code Standards

- Python 3.11+ required
- Keep runtime dependencies explicit and minimal; `cryptography>=41.0` is a
  required dependency for the shipped proof and authority surfaces
- All water-metaphor keywords implemented exactly per spec
- Every AST node must carry span tracking
- Tests are required for all new features
- Default = DENY at every governance gate

### Pull Request Guidelines

- Keep pull requests focused on a single concern
- Add or update tests as needed
- Update documentation if the API or behavior changes
- Ensure all tests pass before requesting review
- If documentation changes a normative security or governance claim, update
  the canonical manual and its generated PDF in the same change

## Governance

Thirsty-Lang follows a default-DENY governance model. All changes are reviewed for:
- Security implications
- Backward compatibility
- Specification compliance
- Test coverage adequacy

## Questions?

If you have questions about contributing, please email FounderOfTP@thirstysprojects.com.

---

**Thirsty's Projects LLC**
