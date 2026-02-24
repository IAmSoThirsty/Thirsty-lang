# Thirsty-Lang Quick Reference

## Basic Syntax

### Variables

```thirsty
drink name = "value"
drink count = 42
drink temperature = 25.5
```

### Output

```thirsty
pour "Hello, World!"
pour variable_name
```

### Comments

```thirsty
// This is a single-line comment
```

## Keywords

### Base Thirsty-Lang

- `drink` - Declare a variable
- `pour` - Output a value
- `sip` - Input (future)

### Thirst of Gods

- `thirsty` - If statement
- `hydrated` - Else statement
- `parched` - Boolean true
- `quenched` - Boolean false

### T.A.R.L

- `glass` - Function declaration
- `refill` - Loop
- `reservoir` - Array
- `bottle` - Object
- `return` - Return from function

### Thirsty's Shadow

- `fountain` - Class declaration
- `cascade` - Async function
- `await` - Wait for async
- `spillage` - Try block
- `cleanup` - Catch block
- `sacred` - Constant
- `ocean` - Map/dictionary
- `stream` - Generator
- `import` - Import module
- `export` - Export module

## Data Types

- **String**: `"text"` or `'text'`
- **Number**: `42` or `3.14`
- **Boolean**: `parched` (true) or `quenched` (false)

## Operators

- `=` - Assignment
- `+` - Addition
- `-` - Subtraction
- `*` - Multiplication
- `/` - Division
- `>` - Greater than
- `<` - Less than
- `==` - Equal to
- `!=` - Not equal to

## Examples

### Hello World

```thirsty
drink message = "Hello, World!"
pour message
```

### Variables and Math

```thirsty
drink a = 10
drink b = 20
drink sum = a + b
pour sum
```

### Conditional (Thirst of Gods)

```thirsty
drink temp = 30
thirsty temp > 25 {
  pour "It's hot!"
}
hydrated {
  pour "It's cool"
}
```

### Function (T.A.R.L.)

```thirsty
glass greet(name) {
  pour "Hello, " + name
}

greet("World")
```

### Class (Thirsty's Shadow)

```thirsty
fountain Person {
  drink name = ""

  glass init(n) {
    drink this.name = n
  }

  glass sayHello() {
    pour "Hello, I'm " + this.name
  }
}

drink person = Person()
person.sayHello()
```

## CLI Commands

```bash
thirsty run file.thirsty       # Run a program
thirsty repl                   # Start REPL
thirsty train                  # Interactive training
thirsty debug file.thirsty     # Debug program
thirsty format file.thirsty    # Format code
thirsty lint file.thirsty      # Lint code
thirsty profile file.thirsty   # Profile performance
thirsty doc file.thirsty       # Generate docs
thirsty ast file.thirsty       # Show AST
thirsty transpile file.thirsty # Transpile
```

Stay hydrated! 💧
