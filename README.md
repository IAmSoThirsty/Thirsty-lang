# Thirsty-Lang 💧

[![NPM Version](https://img.shields.io/npm/v/thirsty-lang.svg)](https://www.npmjs.com/package/thirsty-lang)
[![CI](https://github.com/IAmSoThirsty/Thirsty-Lang/actions/workflows/ci.yml/badge.svg)](https://github.com/IAmSoThirsty/Thirsty-Lang/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Custom-blue.svg)](LICENSE)

> A water-themed programming language for anyone and everyone who is Thirsty — featuring four tiers, defensive programming, and T.A.R.L. security integration.

## Quick Start

```bash
# npm
npm install -g thirsty-lang
thirsty examples/hello.thirsty

# pip
pip install thirsty-lang
python -m thirsty_lang examples/hello.thirsty

# From source
node src/cli.js examples/hello.thirsty
```

## The Four Tiers

Thirsty-Lang is a **language family** with four tiers, each building on the previous:

| Tier | Extension | Level | Key Features |
| ---- | --------- | ----- | ------------ |
| 💧 **Thirsty-Lang** | `.thirsty` | Beginner | Variables (`drink`), Output (`pour`), Input (`sip`), Comments |
| ⚡ **Thirst of Gods** | `.tog` | Intermediate | Conditionals (`thirsty`/`hydrated`), Loops (`refill`), Arithmetic, Comparison |
| 🛡️ **T.A.R.L.** | `.tarl` | Advanced | Functions (`glass`), Arrays (`reservoir`), Standard Library, Security (`shield`/`sanitize`/`armor`) |
| 🔮 **Thirsty's Shadow** | `.shadow` | Master | Classes (`fountain`), OOP, `this` keyword, Methods, Properties |

See [docs/EXPANSIONS.md](docs/EXPANSIONS.md) for the full tier specification.

## Language Syntax

### Core Keywords

| Keyword | Purpose | Example |
| ------- | ------- | ------- |
| `drink` | Variable declaration | `drink water = "Hello"` |
| `pour` | Output/print | `pour water` |
| `sip` | Input | `sip answer` |
| `thirsty` | If statement | `thirsty x > 5 { ... }` |
| `hydrated` | Else statement | `hydrated { ... }` |
| `refill` | Loop | `refill count > 0 { ... }` |
| `glass` | Function declaration | `glass greet(name) { ... }` |
| `reservoir` | Array declaration | `reservoir items = [1, 2, 3]` |
| `fountain` | Class declaration | `fountain MyClass { ... }` |

### Security Keywords

| Keyword | Purpose |
| ------- | ------- |
| `shield` | Protected execution context |
| `sanitize` | HTML encoding (XSS prevention) |
| `armor` | Variable protection against modification |
| `morph` | Code mutation flag |
| `detect` | Threat monitoring flag |
| `defend` | Defense strategy flag |

### Examples

#### Hello World

```thirsty
drink message = "Hello, Thirsty World!"
pour message
```

#### Control Flow (Thirst of Gods)

```thirsty
drink temperature = 35

thirsty temperature > 30 {
  pour "It's hot! Stay hydrated!"
}
hydrated {
  pour "Nice weather!"
}
```

#### Functions and Arrays (T.A.R.L.)

```thirsty
glass calculateIntake(weight, activity) {
  drink base = weight * 0.033
  drink bonus = activity * 0.5
  return base + bonus
}

reservoir log = [2.0, 1.5, 2.5, 3.0]
pour "Hydration log: " + log.join(", ")
```

#### Classes (Thirsty's Shadow)

```thirsty
fountain Calculator {
  glass add(a, b) {
    return a + b
  }

  glass multiply(a, b) {
    return a * b
  }
}

drink calc = Calculator()
pour "10 + 5 = " + calc.add(10, 5)
```

#### Security Features

```thirsty
shield mySecureApp {
  drink userData = "<script>alert('xss')</script>"
  sanitize userData

  drink secretKey = "my-secret-123"
  armor secretKey

  pour "Safe output: " + userData
}
```

See more examples in [`examples/`](examples/) and [`examples/advanced/`](examples/advanced/).

## Installation

### Node.js (Primary Runtime)

```bash
npm install -g thirsty-lang    # Global install
thirsty examples/hello.thirsty # Run a program
thirsty-repl                   # Interactive REPL
```

### Python (Alternative Runtime)

```bash
pip install thirsty-lang
python -m thirsty_lang examples/hello.thirsty
```

Or from source:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 src/thirsty_interpreter.py examples/hello.thirsty
```

### Docker

```bash
docker-compose up
# Or: docker build -t thirsty-lang .
```

See [DOCKER.md](DOCKER.md) for detailed Docker instructions and [PYTHON_SETUP.md](PYTHON_SETUP.md) for Python setup.

## Developer Tools

All tools are implemented and functional:

| Tool | Command | Description |
| ---- | ------- | ----------- |
| **REPL** | `npm run repl` | Interactive Read-Eval-Pour-Loop |
| **Debugger** | `node src/debugger.js <file>` | Step through code, set breakpoints |
| **Formatter** | `node src/formatter.js <file>` | Beautify Thirsty code |
| **Linter** | `node src/linter.js <file>` | Check code quality and style |
| **Profiler** | `node src/profiler.js <file>` | Analyze performance |
| **Doc Generator** | `node src/doc-generator.js <file>` | Generate documentation from code |
| **AST Generator** | `node src/ast.js <file>` | Generate Abstract Syntax Trees |
| **Transpiler** | `node src/transpiler.js <file>` | Transpile to JavaScript |
| **Package Manager** | `node src/package-manager.js init` | Manage Thirsty packages |
| **Training** | `npm run train` | Interactive language tutorial |
| **Playground** | Open `playground/index.html` | Browser-based editor and interpreter |

## Testing

```bash
npm test                 # 37 tests — all passing
npm run test:security    # Security integration tests
npm run test:bridge      # Bridge tests
npm run test:all         # Run everything
```

## T.A.R.L. Security Integration

Thirsty-Lang integrates with **T.A.R.L. (Tactical Analysis & Response Language)** from Project-AI:

- **Dual Runtime**: JavaScript/Node.js + Python T.A.R.L. runtime
- **Threat Detection**: Pattern-based analysis via `src/security/threat-detector.js`
- **Code Morphing**: Dynamic transformation via `src/security/code-morpher.js`
- **Defense Compiler**: Defensive compilation via `src/security/defense-compiler.js`
- **Policy Engine**: YAML/JSON policies via `src/security/policy-engine.js`
- **Security Bridge**: JS ↔ Python communication via `src/security/bridge.js`

See [TARL_INTEGRATION.md](TARL_INTEGRATION.md) and [SECURITY_API.md](SECURITY_API.md).

## Feature Matrix

### 💧 Thirsty-Lang (`.thirsty`)

- ✅ Variable declaration (`drink`)
- ✅ Output statements (`pour`)
- ✅ Input statements (`sip`)
- ✅ Comments (`//`)
- ✅ String and number literals

### ⚡ Thirst of Gods (`.tog`)

All Thirsty-Lang features, plus:

- ✅ Conditionals (`thirsty`/`hydrated`)
- ✅ Comparison operators (`>`, `<`, `>=`, `<=`, `==`, `!=`)
- ✅ Arithmetic (`+`, `-`, `*`, `/`)
- ✅ String concatenation
- ✅ Boolean values

### 🛡️ T.A.R.L. (`.tarl`)

All Thirst of Gods features, plus:

- ✅ Functions (`glass`) with parameters and return values
- ✅ Arrays (`reservoir`) with push, pop, shift, indexOf, includes, join, slice, reverse, sort
- ✅ Loops (`refill`) with conditions
- ✅ Security features (`shield`, `sanitize`, `armor`)
- ✅ Standard Library — Math (PI, abs, sqrt, pow, floor, ceil, round, min, max, random) and String (toUpperCase, toLowerCase, trim, split, replace, charAt, substring)

### 🔮 Thirsty's Shadow (`.shadow`)

All T.A.R.L. features, plus:

- ✅ Classes (`fountain`) with properties and methods
- ✅ Object instantiation
- ✅ `this` keyword for property access
- ✅ State mutation (`drink this.x = ...`)

## VS Code Extension

Syntax highlighting, bracket matching, and snippets for all four file types.

```
Install: Copy vscode-extension/ to your VS Code extensions directory
Supports: .thirsty, .tog, .tarl, .shadow
```

See [vscode-extension/README.md](vscode-extension/README.md) for details.

## Project Structure

```
Thirsty-Lang/
├── src/
│   ├── index.js                # Main Node.js interpreter
│   ├── cli.js                  # CLI runner
│   ├── thirsty-cli.js          # Unified CLI
│   ├── repl.js                 # Interactive REPL
│   ├── training.js             # Interactive training program
│   ├── debugger.js             # Debugger
│   ├── formatter.js            # Code formatter
│   ├── linter.js               # Code linter
│   ├── profiler.js             # Performance profiler
│   ├── doc-generator.js        # Documentation generator
│   ├── ast.js                  # AST generator
│   ├── transpiler.js           # Multi-language transpiler
│   ├── package-manager.js      # Package manager
│   ├── thirsty_interpreter.py  # Python interpreter
│   ├── thirsty_repl.py         # Python REPL
│   ├── thirsty_utils.py        # Python utilities
│   ├── security/               # T.A.R.L. security modules
│   └── test/                   # Test suite (37 tests)
├── thirsty_lang/               # Python pip package
│   ├── __init__.py
│   ├── __main__.py
│   ├── interpreter.py
│   └── py.typed
├── tarl/                       # T.A.R.L. runtime
├── examples/                   # Example programs
│   ├── hello.thirsty
│   ├── functions.thirsty
│   ├── arrays.thirsty
│   ├── classes.thirsty
│   └── advanced/               # .tog, .tarl, .shadow examples
├── docs/                       # Documentation
│   ├── EXPANSIONS.md           # Four-tier system guide
│   ├── PUBLISHING.md           # Publishing to npm, PyPI, VS Code
│   ├── SPECIFICATION.md        # Language specification
│   ├── TUTORIAL.md             # Step-by-step tutorial
│   ├── QUICK_REFERENCE.md      # Syntax cheat sheet
│   └── FAQ.md                  # Frequently asked questions
├── playground/                 # Premium web playground
├── vscode-extension/           # VS Code extension + icon
├── tools/                      # Benchmark tools
├── package.json                # npm package config
├── pyproject.toml              # pip package config
├── Dockerfile                  # Docker container
├── docker-compose.yml          # Docker multi-service
├── CHANGELOG.md                # Version history
└── .github/workflows/          # CI/CD (ci.yml, publish.yml)
```

## Documentation

| Document | Description |
| -------- | ----------- |
| [EXPANSIONS.md](docs/EXPANSIONS.md) | Four-tier language system |
| [SPECIFICATION.md](docs/SPECIFICATION.md) | Complete syntax and semantics |
| [TUTORIAL.md](docs/TUTORIAL.md) | Step-by-step learning guide |
| [QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) | Syntax cheat sheet |
| [FAQ.md](docs/FAQ.md) | Frequently asked questions |
| [INSTALLATION.md](docs/INSTALLATION.md) | Setup instructions |
| [PUBLISHING.md](docs/PUBLISHING.md) | npm, PyPI, VS Code publishing |
| [SECURITY_GUIDE.md](docs/SECURITY_GUIDE.md) | Security practices |
| [TARL_INTEGRATION.md](TARL_INTEGRATION.md) | T.A.R.L. integration guide |
| [SECURITY_API.md](SECURITY_API.md) | Security API reference |
| [PYTHON_SETUP.md](PYTHON_SETUP.md) | Python setup guide |
| [DOCKER.md](DOCKER.md) | Docker guide |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [RELEASE_GUIDE.md](RELEASE_GUIDE.md) | Release process |

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the terms in the [LICENSE](LICENSE) file.

## Author

Created by someone who believes coding should be refreshing! 💧

---

- 🐛 [Report Issues](https://github.com/IAmSoThirsty/Thirsty-Lang/issues)
- 💡 [Request Features](https://github.com/IAmSoThirsty/Thirsty-Lang/issues/new)
- ⭐ [Star on GitHub](https://github.com/IAmSoThirsty/Thirsty-Lang)

Stay hydrated and happy coding! 💧✨
