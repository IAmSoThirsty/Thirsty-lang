# Thirsty-Lang Quick Start Guide 🚀💧

## One-Line Setup

```bash
./setup_all.sh
```

That's it! Everything will be installed and verified.

## What Gets Installed

✅ Node.js dependencies
✅ Python virtual environment (.venv)
✅ All required files verified
✅ Tests executed
✅ Everything ready to use

## Quick Commands

### Run Programs

```bash

# Node.js (primary)

npm start examples/hello.thirsty

# Python (alternative)

python3 src/thirsty_interpreter.py examples/hello.thirsty

# Docker

docker-compose run --rm thirsty node src/cli.js examples/hello.thirsty
```

### Interactive REPLs

```bash

# Node.js REPL

npm run repl

# Python REPL

python3 src/thirsty_repl.py

# Docker Node.js REPL

docker-compose run --rm repl

# Docker Python REPL

docker-compose run --rm python-repl
```

### Learning

```bash

# Interactive training

npm run train

# Or in Docker

docker-compose run --rm training
```

### Development Tools

```bash
npm run lint examples/hello.thirsty    # Code linting
npm run format examples/hello.thirsty  # Code formatting
npm run profile examples/hello.thirsty # Performance profiling
npm run debug examples/hello.thirsty   # Debugger
npm run doc examples/hello.thirsty     # Generate docs
npm run ast examples/hello.thirsty     # Show AST
npm test                               # Run tests
```

## Language Basics

```thirsty
// Variables
drink message = "Hello, World!"
drink number = 42

// Output
pour message
pour number

// Input
sip userName
pour userName
```

## File Extensions

- `.thirsty` — Thirsty-Lang (Core)
- `.tog` — Thirst of Gods
- `.tarl` — T.A.R.L.
- `.shadow` — Thirsty's Shadow

## Help & Documentation

```bash

# Main documentation

cat README.md

# Python setup

cat PYTHON_SETUP.md

# Docker guide

cat DOCKER.md

# Complete summary

cat IMPLEMENTATION_SUMMARY.md

# Dependencies info

cat DEPENDENCIES.txt
```

## Troubleshooting

### Node.js not found

```bash

# Install Node.js from https://nodejs.org

<<<<<<< HEAD
# Required: v18.0.0 or higher
=======
# Required: v14.0.0 or higher
>>>>>>> 6adac05eb16ea0a433fc45859d939d6b5ee167f6

```

### Python not found

```bash

# Install Python from https://python.org

# Required: 3.8 or higher

```

### Permission denied

```bash
chmod +x setup_all.sh setup_venv.sh quickstart.sh
chmod +x src/*.py
```

### Docker issues

```bash

# Check Docker is running

docker --version

# Rebuild containers

docker-compose build --no-cache
```

## Quick Test

```bash

# Test Node.js

node src/cli.js examples/hello.thirsty

# Test Python

python3 src/thirsty_interpreter.py examples/hello.thirsty

# Run test suite

npm test
```

## What's Available

### Runtimes

- ✅ Node.js (Primary)
- ✅ Python (Alternative)
- ✅ Docker (Containerized)

### Tools

- ✅ REPL (Interactive shell)
- ✅ Training (Interactive lessons)
- ✅ Debugger
- ✅ Linter
- ✅ Formatter
- ✅ Profiler
- ✅ Doc Generator
- ✅ AST Generator
- ✅ Transpiler (to JS, Python, Go, Rust, Java, C)
- ✅ Package Manager
- ✅ Web Playground

### Support

- ✅ VS Code extension
- ✅ GitHub Actions CI/CD
- ✅ Complete documentation
- ✅ Example programs
- ✅ Test suite

## Directory Structure

```text
Thirsty-Lang/
├── examples/           # Example programs
├── src/               # Source code (JS + Python)
├── docs/              # Documentation
├── playground/        # Web playground
└── vscode-extension/  # VS Code extension
```

## Need More Help?

1. Read `README.md` - Complete guide
2. Read `PYTHON_SETUP.md` - Python specific
3. Read `DOCKER.md` - Docker specific
4. Check `docs/` directory - Full documentation
5. Open an issue on GitHub

## Version

Current version: **2.0.0**

See `VERSION.txt` and `CHANGELOG.md` for details.

---

### Stay hydrated and happy coding! 💧✨

For detailed information, see the complete README.md
