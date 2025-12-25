# Thirsty-lang 💧

This is my Language for anyone and everyone who is Thirsty.

## About

Thirsty-lang is a fun, expressive programming language designed to quench your thirst for coding! 

## Features

- ✨ Simple and intuitive syntax
- 🎓 Interactive training program for all skill levels
- 🔍 Built-in REPL for experimenting
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

## Getting Started

### Prerequisites

- Node.js 14 or higher
- npm or yarn

### Installation

```bash
npm install
```

### Quick Start

```bash
# Run a program
npm start examples/hello.thirsty

# Or use the unified CLI
node src/thirsty-cli.js run examples/hello.thirsty
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
```

## Language Syntax

Thirsty-lang uses water-themed keywords:

- `drink` - Variable declaration
- `pour` - Output/print statement
- `sip` - Input statement  
- `thirsty` - If statement
- `hydrated` - Else statement
- `refill` - Loop statement
- `glass` - Function declaration

### Example Program

```thirsty
drink water = "Hello, World!"
pour water
```

See more examples in the `examples/` directory.

## Available Tools

### REPL (Read-Eval-Pour-Loop)
```bash
npm run repl
```
Interactive console with history, variables inspection, and session saving.

### Debugger
```bash
npm run debug examples/hello.thirsty
```
Step through code, set breakpoints, watch variables, and inspect state.

### Code Formatter
```bash
npm run format examples/hello.thirsty
```
Automatically format your code with consistent style.

### Linter
```bash
npm run lint examples/hello.thirsty
```
Check for code quality issues and style violations.

### Performance Profiler
```bash
npm run profile examples/hello.thirsty
```
Measure execution time and identify performance bottlenecks.

### Documentation Generator
```bash
npm run doc examples/hello.thirsty
```
Generate beautiful HTML and Markdown documentation.

### AST Generator
```bash
npm run ast examples/hello.thirsty
```
Visualize the Abstract Syntax Tree of your code.

### Transpiler
```bash
node src/transpiler.js examples/hello.thirsty --target python
```
Convert Thirsty-lang to JavaScript, Python, Go, Rust, Java, or C.

### Package Manager
```bash
node src/package-manager.js init my-project
node src/package-manager.js install
```
Manage dependencies and packages for your projects.

### Web Playground
Open `playground/index.html` in your browser for an interactive web-based editor!

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

Full language specification and documentation can be found in the `docs/` directory:

- [Language Specification](docs/SPECIFICATION.md)
- [Expansions Guide](docs/EXPANSIONS.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## VS Code Extension

Syntax highlighting and code snippets are available in `.vscode/extensions/thirsty-lang/`.

To install:
1. Copy the extension folder to your VS Code extensions directory
2. Reload VS Code
3. Enjoy syntax highlighting for `.thirsty` files!

## Project Structure

```
Thirsty-lang/
├── src/
│   ├── index.js           # Main interpreter
│   ├── cli.js             # CLI runner
│   ├── thirsty-cli.js     # Unified CLI tool
│   ├── repl.js            # Interactive REPL
│   ├── training.js        # Interactive training program
│   ├── debugger.js        # Debugger
│   ├── formatter.js       # Code formatter
│   ├── linter.js          # Code linter
│   ├── profiler.js        # Performance profiler
│   ├── doc-generator.js   # Documentation generator
│   ├── ast.js             # AST generator
│   ├── transpiler.js      # Multi-language transpiler
│   ├── package-manager.js # Package manager
│   └── test/              # Test suite
├── examples/              # Example programs
│   ├── hello.thirsty
│   ├── variables.thirsty
│   ├── hydration.thirsty
│   └── advanced/          # Advanced examples
├── docs/                  # Documentation
├── playground/            # Web playground
├── .vscode/extensions/    # VS Code extension
└── .github/workflows/     # CI/CD

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
