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

<<<<<<< HEAD
### Base Thirsty-Lang
=======
### Base Thirsty-lang
>>>>>>> 6adac05eb16ea0a433fc45859d939d6b5ee167f6

- `drink` - Declare a variable
- `pour` - Output a value
- `sip` - Input (future)

<<<<<<< HEAD
### Thirst of Gods
=======
### Thirsty+ (Plus)
>>>>>>> 6adac05eb16ea0a433fc45859d939d6b5ee167f6

- `thirsty` - If statement
- `hydrated` - Else statement
- `parched` - Boolean true
- `quenched` - Boolean false

<<<<<<< HEAD
### T.A.R.L
=======
### Thirsty++ (Plus Plus)
>>>>>>> 6adac05eb16ea0a433fc45859d939d6b5ee167f6

- `glass` - Function declaration
- `refill` - Loop
- `reservoir` - Array
- `bottle` - Object
- `return` - Return from function

<<<<<<< HEAD
### Thirsty's Shadow
=======
### ThirstOfGods
>>>>>>> 6adac05eb16ea0a433fc45859d939d6b5ee167f6

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

<<<<<<< HEAD
### Conditional (Thirst of Gods)
=======
### Conditional (Thirsty+)
>>>>>>> 6adac05eb16ea0a433fc45859d939d6b5ee167f6

```thirsty
drink temp = 30
thirsty temp > 25 {
  pour "It's hot!"
}
hydrated {
  pour "It's cool"
}
```

<<<<<<< HEAD
### Function (T.A.R.L.)
=======
### Function (Thirsty++)
>>>>>>> 6adac05eb16ea0a433fc45859d939d6b5ee167f6

```thirsty
glass greet(name) {
  pour "Hello, " + name
<<<<<<< HEAD
}
=======
>>>>>>> 6adac05eb16ea0a433fc45859d939d6b5ee167f6

greet("World")
```

<<<<<<< HEAD
### Class (Thirsty's Shadow)
=======
### Class (ThirstOfGods)

```thirsty
fountain Person
  drink name = ""

  glass init(n)
    this.name = n

  glass sayHello()
    pour "Hello, I'm " + this.name
>>>>>>> 6adac05eb16ea0a433fc45859d939d6b5ee167f6

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
