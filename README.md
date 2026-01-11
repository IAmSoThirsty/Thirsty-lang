# Thirsty-lang 💧🔒

This is my Language for anyone and everyone who is Thirsty - now with **Defensive Programming** capabilities!

## About

Thirsty-lang is a unique, expressive programming language designed to be **defensive and combative** against all known code threats. It combines fun water-themed syntax with enterprise-grade security features.

## Features

### ✅ Fully Functional
- ✨ Simple and intuitive syntax
- 📥 Variable assignment (`drink`)
- 📤 Output statements (`pour`)
- 🔄 Control flow (if/else, loops)
- ➕ Arithmetic operations (+, -, *, /) with proper precedence
- 🔗 String concatenation
- 🔒 **Basic Security Features:**
  - 🛡️ Shield blocks - Protected execution contexts
  - 🧹 Sanitize - HTML encoding to prevent XSS injection
  - 🔐 Armor - Variable protection against modification
- 🔍 Built-in REPL for experimenting
- 🐍 **Python implementation included**
- 🐳 **Docker and Docker Compose support**
- 🔒 **Virtual environment setup**

### 📋 Planned Features (Not Yet Implemented)
- 🐛 Full-featured debugger
- 📊 Performance profiler
- 🎨 Code formatter and linter
- 📚 Automatic documentation generator
- 🌐 Web playground
- 🔄 Transpiler to JavaScript, Python, Go, Rust, Java, and C
- 📦 Package manager
- 🌳 AST generator
- 🎯 Multiple language editions (Base, Plus, PlusPlus, ThirstOfGods)
- 🔌 VS Code extension support
- 🎓 Interactive training program

## Getting Started

### Prerequisites

**Choose your runtime:**
- **Node.js** (Primary): 14 or higher
- **Python** (Alternative): 3.8 or higher
- **Docker** (Optional): For containerized execution

### Installation

#### Node.js Setup (Primary)
```bash
npm install
```

#### Python Setup (Alternative)
```bash
# Automated setup
./setup_venv.sh

# Manual setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Docker Setup (Optional)
```bash
# Build and run with Docker Compose
docker-compose up

# Or build Docker image directly
docker build -t thirsty-lang .
```

See [DOCKER.md](DOCKER.md) for detailed Docker instructions and [PYTHON_SETUP.md](PYTHON_SETUP.md) for Python setup guide.

### Quick Start

#### Using Node.js
```bash
# Run a program
npm start examples/hello.thirsty

# Or use the unified CLI
node src/thirsty-cli.js run examples/hello.thirsty
```

#### Using Python
```bash
# Activate virtual environment (if using)
source .venv/bin/activate

# Run a program
python3 src/thirsty_interpreter.py examples/hello.thirsty

# Start Python REPL
python3 src/thirsty_repl.py
```

#### Using Docker
```bash
# Run a program
docker-compose run --rm thirsty node src/cli.js examples/hello.thirsty

# Start Node.js REPL
docker-compose run --rm repl

# Start Python REPL
docker-compose run --rm python-repl
```

### Interactive Training Program 🎓

Learn Thirsty-lang interactively with our built-in training program:

```bash
npm run train
```

The training program includes:
- 💧 **Base Thirsty-lang**: Fundamentals for beginners
- 💧+ **Thirsty Plus**: Control flow and logic
- 💧++ **Thirsty Plus Plus**: Functions and loops
- ⚡ **ThirstOfGods**: Advanced OOP and async features

### Running Thirsty-lang Programs

```bash
npm start examples/hello.thirsty
```

### Running Tests

```bash
npm test

# Run security tests
node src/test/security-tests.js
```

## Language Syntax

### Core Keywords (Water-Themed)

- `drink` - Variable declaration
- `pour` - Output/print statement
- `sip` - Input statement  
- `thirsty` - If statement
- `hydrated` - Else statement
- `refill` - Loop statement
- `glass` - Function declaration

### Security Keywords (Defensive Programming)

- `shield` - Mark code blocks for protection
- `morph` - Enable dynamic code mutation
- `detect` - Set up threat monitoring
- `defend` - Automatic countermeasures
- `sanitize` - Input/output cleaning
- `armor` - Memory protection

### Example Programs

#### Basic Program
```thirsty
drink water = "Hello, World!"
pour water
```

#### Secure Program with Basic Protection
```thirsty
shield mySecureApp {
  drink userData = "<script>alert('xss')</script>"
  sanitize userData  // Removes XSS with HTML encoding
  
  drink secretKey = "my-secret-123"
  armor secretKey    // Protects from modification
  
  pour "Hello, " + userData  // Safe output
}
```

**Note:** `morph`, `detect`, and `defend` keywords can be used but are configuration placeholders only. The real security comes from `shield` (execution context), `sanitize` (HTML encoding), and `armor` (variable protection).

See more examples in the `examples/` and `examples/security/` directories.

## Basic Security Features

Thirsty-lang includes basic security features for educational purposes:

### What Actually Works

**1. Shield Blocks** - Protected execution contexts
```thirsty
shield secureApp {
  // Code here runs in isolated context
}
```

**2. Sanitization** - HTML encoding to prevent XSS
```thirsty
drink userInput = "<script>alert('xss')</script>"
sanitize userInput  // Becomes: &lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;
```
- Escapes `<`, `>`, `&`, `"`, `'`, `/`
- Prevents script injection
- Real HTML encoding

**3. Variable Armor** - Protection from modification
```thirsty
drink secretKey = "api-key-123"
armor secretKey            // Variable is now protected
drink secretKey = "hacked" // Warning: modification blocked
```

### Configuration Placeholders

The following keywords are accepted but only set configuration flags:
- `morph on: [...]` - Sets morph flag in shield context
- `detect attacks` - Sets detect flag
- `defend with: "strategy"` - Sets defense strategy flag

These do not provide actual threat detection or countermeasures, they're placeholders for future expansion.

See the `examples/security/` directory for working examples.

## Available Tools

### ✅ Working Tools

#### REPL (Read-Eval-Pour-Loop)
```bash
npm run repl
```
Interactive console for experimenting with Thirsty-lang.

#### CLI Runner
```bash
npm start examples/hello.thirsty
```
Run Thirsty-lang programs from the command line.

### 📋 Planned Tools (Not Yet Implemented)

The following tools are documented but not yet implemented:
- Debugger
- Code Formatter
- Linter
- Performance Profiler
- Documentation Generator
- AST Generator
- Transpiler
- Package Manager
- Web Playground

## Implementation Support

Thirsty-lang includes two complete implementations:

### Node.js Implementation (Primary)
- **Fast and feature-complete**
- All tools and utilities included
- Production-ready
- Run: `node src/cli.js <file.thirsty>`

### Python Implementation (Alternative)
- **Pure Python with standard library**
- Educational and portable
- Cross-platform compatible
- Run: `python3 src/thirsty_interpreter.py <file.thirsty>`

See [PYTHON_SETUP.md](PYTHON_SETUP.md) for detailed Python setup and usage.

### Docker Support
- **Multi-service architecture**
- Development and production images
- Pre-configured services for all tools
- See [DOCKER.md](DOCKER.md) for complete Docker guide

## Language Editions

Thirsty-lang comes in four flavors:

| Edition | Level | Description |
|---------|-------|-------------|
| 💧 **Base** | Beginner | Core features: variables, output |
| 💧+ **Thirsty+** | Intermediate | Adds control flow, conditionals |
| 💧++ **Thirsty++** | Advanced | Functions, loops, arrays |
| ⚡ **ThirstOfGods** | Master | Classes, async/await, modules |

See [docs/EXPANSIONS.md](docs/EXPANSIONS.md) for detailed information.

## Documentation

Full language specification and documentation can be found in the `docs/` directory and root:

### Core Documentation
- [README.md](README.md) - Main documentation (this file)
- [Language Specification](docs/SPECIFICATION.md) - Complete syntax and semantics
- [Expansions Guide](docs/EXPANSIONS.md) - Multi-tier language editions
- [Tutorial](docs/TUTORIAL.md) - Step-by-step learning guide
- [Quick Reference](docs/QUICK_REFERENCE.md) - Syntax cheat sheet
- [FAQ](docs/FAQ.md) - Frequently asked questions
- [Installation Guide](docs/INSTALLATION.md) - Setup instructions

### Setup Guides
- [PYTHON_SETUP.md](PYTHON_SETUP.md) - Python implementation setup
- [DOCKER.md](DOCKER.md) - Docker and containerization guide

### Project Information
- [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute
- [CHANGELOG.md](CHANGELOG.md) - Version history and changes
- [AUTHORS.txt](AUTHORS.txt) - Contributors and authors
- [DEPENDENCIES.txt](DEPENDENCIES.txt) - Dependency information
- [VERSION.txt](VERSION.txt) - Current version
- [LICENSE](LICENSE) - License terms

## VS Code Extension

Syntax highlighting and code snippets are available in `vscode-extension/`.

To install:
1. Copy the `vscode-extension` folder to your VS Code extensions directory
2. Reload VS Code
3. Enjoy syntax highlighting for `.thirsty` files!

See [vscode-extension/README.md](vscode-extension/README.md) for detailed installation instructions.

## Project Structure

```
Thirsty-lang/
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
│   └── test/                   # Test suite
├── examples/                   # Example programs
│   ├── hello.thirsty
│   ├── variables.thirsty
│   ├── hydration.thirsty
│   └── advanced/               # Advanced examples
├── docs/                       # Documentation
├── playground/                 # Web playground
├── vscode-extension/           # VS Code extension
├── tools/                      # Benchmark tools
├── requirements.txt            # Python core dependencies
├── requirements-dev.txt        # Python dev dependencies
├── setup_venv.sh               # Python venv setup script
├── Dockerfile                  # Docker container definition
├── docker-compose.yml          # Docker multi-service setup
├── .dockerignore               # Docker ignore file
├── CHANGELOG.md                # Version history
├── AUTHORS.txt                 # Contributors
├── DEPENDENCIES.txt            # Dependency information
├── VERSION.txt                 # Current version
└── .github/workflows/          # CI/CD
```

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the terms in the LICENSE file.

## Author

Created by someone who believes coding should be refreshing! 💧

## Stay Connected

- 🐛 [Report Issues](https://github.com/IAmSoThirsty/Thirsty-lang/issues)
- 💡 [Request Features](https://github.com/IAmSoThirsty/Thirsty-lang/issues/new)
- ⭐ [Star on GitHub](https://github.com/IAmSoThirsty/Thirsty-lang)

Stay hydrated and happy coding! 💧✨
