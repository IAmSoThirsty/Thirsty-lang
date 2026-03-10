# Thirsty-lang Sample Code

This directory contains representative examples of Thirsty-lang code for use in GitHub Linguist submissions and language demonstrations.

## Sample Files

### hello-world.thirsty
The simplest possible Thirsty-lang program demonstrating basic variable declaration and output.

**Features:**
- Variable declaration with `drink`
- Output with `pour`

**Run:**
```bash
thirsty samples/hello-world.thirsty
```

### fibonacci.thirsty
A Fibonacci sequence calculator demonstrating loops, functions, and arithmetic operations.

**Features:**
- Function declarations with `glass`
- Loops with `refill`
- Conditional logic with `thirsty`/`hydrated`
- Arithmetic operations
- String concatenation

**Run:**
```bash
thirsty samples/fibonacci.thirsty
```

### calculator.thirsty
An object-oriented calculator demonstrating classes and methods.

**Features:**
- Class declarations with `fountain`
- Methods and properties
- The `this` keyword
- Conditional error handling
- Object instantiation

**Run:**
```bash
thirsty samples/calculator.thirsty
```

### arrays.thirsty
Array operations and data structure manipulation.

**Features:**
- Array declarations with `reservoir`
- Array methods: push, pop, join, indexOf, includes, sort, reverse, slice
- Working with collections

**Run:**
```bash
thirsty samples/arrays.thirsty
```

### security.thirsty
Security features and defensive programming capabilities.

**Features:**
- Shield blocks for protected execution
- `sanitize` for XSS prevention
- `armor` for variable protection
- Security-first programming

**Run:**
```bash
thirsty samples/security.thirsty
```

### stdlib.thirsty
Standard library utilities including Math and String operations.

**Features:**
- Math utilities: PI, E, abs, sqrt, pow, floor, ceil, round, min, max
- String utilities: toUpperCase, toLowerCase, trim, split, replace, charAt, substring
- Built-in library usage

**Run:**
```bash
thirsty samples/stdlib.thirsty
```

## Purpose

These samples are designed to:

1. **Demonstrate Language Features**: Show the full range of Thirsty-lang capabilities
2. **GitHub Linguist Submission**: Provide representative code for language recognition
3. **Education**: Help new users learn the language syntax and idioms
4. **Testing**: Verify language implementation correctness

## Using These Samples

### With Node.js
```bash
npm install -g thirsty-lang
thirsty samples/<filename>.thirsty
```

### From Repository
```bash
node src/cli.js samples/<filename>.thirsty
```

### With Python Implementation
```bash
python3 src/thirsty_interpreter.py samples/<filename>.thirsty
```

## Adding New Samples

When adding new samples:

1. Use clear, well-commented code
2. Demonstrate specific language features
3. Keep examples focused and concise
4. Follow Thirsty-lang idioms and best practices
5. Test thoroughly before committing

## Related Documentation

- [README.md](../README.md) - Main project documentation
- [SPECIFICATION.md](../docs/SPECIFICATION.md) - Language specification
- [TUTORIAL.md](../TUTORIAL.md) - Step-by-step tutorial
- [LINGUIST_SUBMISSION.md](../LINGUIST_SUBMISSION.md) - GitHub Linguist submission guide

## License

These sample files are part of the Thirsty-lang project and are subject to the same license terms as the main project. See [LICENSE](../LICENSE) for details.
