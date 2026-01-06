# Thirsty-lang 💧

A fun, water-themed programming language designed for learning and experimentation.

## ⚠️ Current Status: Educational/Experimental

Thirsty-lang is currently an **educational toy language** with **basic functionality**. While it has extensive documentation, many advanced features are conceptual or in early development stages.

**📊 For a complete breakdown of what works vs. what doesn't, see [FEATURE_STATUS.md](FEATURE_STATUS.md)**

## ✅ What Actually Works Now

### Core Language Features (Fully Functional)
- ✅ **Variable declarations** (`drink varname = value`)
- ✅ **Output statements** (`pour expression`)
- ✅ **Comments** (// comment)
- ✅ **String literals** ("text" or 'text')
- ✅ **Number literals** (integers and floats)
- ✅ **String concatenation** (with + operator)
- ✅ **Arithmetic operations** (+, -, *, /)
- ✅ **Comparison operators** (==, !=, <, >, <=, >=)
- ✅ **Conditional statements** (`thirsty condition { }` and `hydrated { }`)
- ✅ **Basic loops** (`refill condition { }`) - Note: Limited functionality

### Development Tools (Functional)
- ✅ **Basic Interpreter** - Runs .thirsty files
- ✅ **CLI** - Command-line interface to run programs
- ✅ **REPL** - Interactive console (basic version)
- ✅ **Test Suite** - Basic tests pass

### Additional Implementations
- ✅ **Python implementation** - Basic interpreter in Python
- ✅ **Docker support** - Containerized execution

## 🚧 Limitations & Known Issues

### What Doesn't Work Yet
- ❌ **Input (`sip`)** - Placeholder only, not functional
- ❌ **Functions** (`glass`) - Not implemented
- ❌ **Arrays/Lists** - Not implemented  
- ❌ **Advanced expressions** - No complex arithmetic in assignments
- ❌ **Security features** (`shield`, `morph`, `detect`, etc.) - Documented but not functional
- ❌ **Most advanced tools** (debugger, profiler, transpiler) - Stubs/placeholders
- ❌ **Language editions** (Plus, PlusPlus, ThirstOfGods) - Documented but not implemented
- ❌ **Package manager** - Placeholder only

### Technical Limitations
- Limited expression evaluation in variable assignments
- Loop variables cannot be updated with expressions (e.g., `counter = counter + 1` doesn't work)
- No function calls or procedures
- No module/import system
- No standard library

## 📦 Installation

### Prerequisites
- **Node.js** 14 or higher (primary)
- **Python** 3.8+ (alternative implementation)
- **Docker** (optional)

### Quick Setup
```bash
# Clone the repository
git clone https://github.com/IAmSoThirsty/Thirsty-lang.git
cd Thirsty-lang

# Install Node.js dependencies (if any)
npm install
```

## 🚀 Quick Start

### Running Your First Program

Create a file `hello.thirsty`:
```thirsty
drink message = "Hello, World!"
pour message
```

Run it:
```bash
npm start hello.thirsty
# or
node src/cli.js hello.thirsty
```

### More Examples

**Variables and Output:**
```thirsty
drink name = "Alice"
drink greeting = "Hello, "
pour greeting + name
```

**Arithmetic:**
```thirsty
drink a = 10
drink b = 5
drink sum = 15
pour "10 + 5 ="
pour sum
```

**Conditionals:**
```thirsty
drink temperature = 25

thirsty temperature > 30 {
  pour "It's hot!"
}
hydrated {
  pour "It's nice!"
}
```

**Simple Loops:**
```thirsty
drink count = 5

pour "Countdown:"
refill count > 0 {
  pour count
  drink count = 4  // Note: Can't use count - 1 yet
}
```

## 📁 Project Structure

```
Thirsty-lang/
├── src/
│   ├── index.js           # Main interpreter (WORKS)
│   ├── cli.js             # CLI runner (WORKS)
│   ├── repl.js            # Interactive REPL (WORKS - basic)
│   ├── thirsty_interpreter.py  # Python version (WORKS - basic)
│   └── test/              # Test suite (WORKS)
├── examples/              # Example programs
│   ├── hello.thirsty      # Hello World (WORKS)
│   ├── variables.thirsty  # Variables (WORKS)
│   ├── arithmetic.thirsty # Math operations (WORKS)
│   └── control-flow.thirsty # If/else (WORKS)
├── docs/                  # Documentation (mostly aspirational)
├── README.md              # This file
└── package.json           # NPM configuration
```

## 🎯 What This Language Is Good For

### ✅ Appropriate Uses
- **Learning** - Understanding how interpreters work
- **Education** - Teaching basic programming concepts
- **Fun** - Playful water-themed coding
- **Experimentation** - Trying out language design ideas

### ❌ Not Appropriate For
- Production code
- Real applications
- Performance-critical tasks
- Anything requiring reliability or security

## 🔧 Available Commands

```bash
# Run a program
npm start <file.thirsty>
node src/cli.js <file.thirsty>

# Interactive REPL (basic)
npm run repl

# Run tests
npm test

# Python version
python3 src/thirsty_interpreter.py <file.thirsty>

# Docker
docker-compose run --rm thirsty node src/cli.js <file.thirsty>
```

## 🧪 Testing

```bash
npm test
```

Current test coverage:
- ✅ Variable declarations
- ✅ Output statements
- ✅ Numbers and strings
- ✅ Comments
- ✅ Multiple statements

## 🗺️ Roadmap & Future Plans

The following features are **planned but not yet implemented**:

### Phase 1: Core Functionality
- [ ] Proper input functionality (`sip`)
- [ ] Expression evaluation in assignments
- [ ] Function definitions and calls
- [ ] Arrays and basic data structures

### Phase 2: Advanced Features  
- [ ] Classes and objects
- [ ] Module system
- [ ] Standard library
- [ ] Error handling (try/catch)

### Phase 3: Tooling
- [ ] Real debugger
- [ ] Working transpiler
- [ ] Code formatter
- [ ] Language server protocol

### Phase 4: Security (Conceptual)
- [ ] Input sanitization
- [ ] Security features (if viable)

**Note:** These are aspirational goals. There's no guarantee they'll be implemented.

## 📚 Documentation

- [Language Specification](docs/SPECIFICATION.md) - Full syntax reference (aspirational)
- [Tutorial](docs/TUTORIAL.md) - Step-by-step guide
- [FAQ](docs/FAQ.md) - Common questions

**Important:** Much of the documentation describes planned features, not current functionality. Refer to this README for what actually works.

## 🤝 Contributing

Contributions are welcome! This is an educational project, perfect for:
- Learning about interpreters
- Practicing open source contributions
- Experimenting with language features

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## ⚖️ License

See LICENSE file for details.

## 💡 Philosophy

Thirsty-lang started as an ambitious project with many documented features. However, being honest about capabilities is more important than impressive documentation. This README reflects the **actual current state** of the project.

The goal is to build something **real and functional**, even if simple, rather than having extensive documentation for features that don't work.

## 🙏 Acknowledgments

This is a learning project. Thanks to everyone who uses it to learn about programming language implementation!

## 📞 Get Help

- 🐛 [Report Issues](https://github.com/IAmSoThirsty/Thirsty-lang/issues)
- 💡 [Request Features](https://github.com/IAmSoThirsty/Thirsty-lang/issues/new)
- ⭐ [Star on GitHub](https://github.com/IAmSoThirsty/Thirsty-lang)

---

**Stay hydrated and code honestly! 💧**

*A work-in-progress programming language that values transparency over hype.*
