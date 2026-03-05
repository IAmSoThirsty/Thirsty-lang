# Thirsty-Lang Language Specification

## Version 3.0.0

## Introduction

Thirsty-Lang is an interpreted programming language with water-themed keywords, enterprise-grade security, and a proper AST-based execution engine. The interpreter follows a **Source → Tokenizer → Parser → AST → Interpreter** pipeline with lexical scoping and operator precedence.

## Architecture

```
Source Code  →  Tokenizer  →  Token Stream  →  Parser  →  AST  →  Interpreter  →  Output
```

- **Tokenizer** (`src/engine/tokenizer.js`) — converts source text into a stream of typed tokens with line/column tracking
- **Parser** (`src/engine/parser.js`) — recursive-descent parser that builds an Abstract Syntax Tree with 9-level operator precedence
- **Interpreter** (`src/engine/ast-interpreter.js`) — tree-walking interpreter with `Environment` chain for lexical scoping

## Syntax

### Comments

Comments start with `//` and continue to the end of the line:

```thirsty
// This is a comment
drink x = 5 // inline comment
```

### Variables

Variables are declared using the `drink` keyword:

```thirsty
drink varname = value
```

Variable names must start with a letter or underscore and can contain letters, digits, and underscores.

### Data Types

| Type | Examples | Description |
|------|----------|-------------|
| **String** | `"Hello"`, `'World'` | Text enclosed in double or single quotes |
| **Number** | `42`, `98.6`, `-10` | Integer or floating-point |
| **Boolean** | `true`, `false` | Logical values |
| **Array** | `[1, 2, 3]` | Ordered collection (see Reservoirs) |
| **Object** | Class instances | Created via `fountain` classes |

```thirsty
drink message = "Hello"
drink count = 42
drink temperature = 98.6
drink active = true
drink negative = -5
```

### Output

The `pour` keyword outputs a value to the console:

```thirsty
pour "Hello, World!"
pour varname
pour 2 + 3
```

### Input

The `sip` keyword reads input from the user:

```thirsty
sip username
```

### Expressions

#### Arithmetic Operators

| Operator | Description | Precedence |
|----------|-------------|------------|
| `+` | Addition / string concatenation | Low |
| `-` | Subtraction | Low |
| `*` | Multiplication | Medium |
| `/` | Division | Medium |
| `%` | Modulo (remainder) | Medium |

```thirsty
drink result = 10 + 5 * 2    // 20 (proper precedence)
drink remainder = 17 % 5      // 2
drink grouped = (2 + 3) * 4   // 20 (parenthesized)
```

#### Comparison Operators

| Operator | Description |
|----------|-------------|
| `>` | Greater than |
| `<` | Less than |
| `>=` | Greater than or equal |
| `<=` | Less than or equal |
| `==` | Equal to |
| `!=` | Not equal to |

#### Logical Operators

| Operator | Description |
|----------|-------------|
| `&&` | Logical AND |
| `\|\|` | Logical OR |
| `!` | Logical NOT (unary) |

```thirsty
thirsty age >= 18 && hasLicense == true {
  pour "Can drive"
}

thirsty temp > 100 || humidity > 80 {
  pour "Uncomfortable weather"
}
```

#### Unary Operators

| Operator | Description |
|----------|-------------|
| `-` | Numeric negation |
| `!` | Logical NOT |

```thirsty
drink x = -10
drink y = -x       // 10
drink flag = !true  // false
```

#### Operator Precedence (lowest to highest)

1. `||` — logical OR
2. `&&` — logical AND
3. `==`, `!=` — equality
4. `<`, `>`, `<=`, `>=` — comparison
5. `+`, `-` — additive
6. `*`, `/`, `%` — multiplicative
7. `-`, `!` — unary prefix
8. `.`, `[]`, `()` — member access, indexing, calls

#### Parenthesized Expressions

Parentheses override normal precedence:

```thirsty
drink a = (1 + 2) * (3 + 4)   // 21
drink b = ((10 - 2) / 4) + 1  // 3
```

### String Concatenation

Strings can be concatenated using the `+` operator. Non-string values are automatically converted:

```thirsty
drink greeting = "Hello, " + "World!"
pour "Score: " + 42  // "Score: 42"
```

### Control Flow

#### If / Else (`thirsty` / `hydrated`)

```thirsty
thirsty temperature > 30 {
  pour "It's hot!"
}
hydrated {
  pour "It's cool"
}
```

#### Else-If Chains (`hydrated thirsty`)

```thirsty
drink score = 85

thirsty score >= 90 {
  pour "A grade"
} hydrated thirsty score >= 80 {
  pour "B grade"
} hydrated thirsty score >= 70 {
  pour "C grade"
} hydrated {
  pour "Below C"
}
```

#### While Loop (`refill`)

```thirsty
drink water = 3

refill water > 0 {
  pour water
  drink water = water - 1
}
```

A safety limit of 10,000 iterations prevents infinite loops.

### Functions (`glass`)

Functions are declared with the `glass` keyword:

```thirsty
glass calculateIntake(weight, activity) {
  drink base = weight * 0.033
  drink bonus = activity * 0.5
  return base + bonus
}

drink daily = calculateIntake(70, 2)
pour "Daily target: " + daily + " liters"
```

Functions support:

- Parameters and return values
- Lexical scoping (closure semantics)
- Recursion (with a call depth limit of 100)
- Early return via `return`

### Async Functions (`cascade`)

```thirsty
cascade fetchData(url) {
  drink response = await Http.get(url)
  return response.body
}
```

### Arrays (`reservoir`)

Arrays are declared with the `reservoir` keyword:

```thirsty
reservoir numbers = [1, 2, 3, 4, 5]
pour numbers[0]       // 1
pour numbers.length   // 5
```

#### Array Methods

| Method | Description |
|--------|-------------|
| `push(value)` | Add element to end |
| `pop()` | Remove and return last element |
| `shift()` | Remove and return first element |
| `unshift(value)` | Add element to beginning |
| `slice(start, end)` | Return sub-array |
| `indexOf(value)` | Find index of element |
| `includes(value)` | Check if element exists |
| `join(separator)` | Join elements into string |
| `reverse()` | Reverse array in place |
| `sort()` | Sort array in place |
| `length` | Number of elements |

### Classes (`fountain`)

Classes are declared with the `fountain` keyword:

```thirsty
fountain WaterTracker {
  drink total_intake = 0
  drink goal = 8

  glass addWater(amount) {
    drink this.total_intake = this.total_intake + amount
    pour "Added " + amount + " liters"
  }

  glass getProgress() {
    return this.total_intake / this.goal * 100
  }

  glass getStatus() {
    thirsty this.total_intake >= this.goal {
      return "Goal reached!"
    }
    hydrated {
      drink remaining = this.goal - this.total_intake
      return remaining + " liters to go"
    }
  }
}

drink tracker = WaterTracker()
tracker.addWater(2.5)
tracker.addWater(3.0)
pour tracker.getProgress() + "%"
```

### Exception Handling (`try` / `catch` / `finally`)

```thirsty
try {
  drink result = riskyOperation()
} catch error {
  pour "Error: " + error.message
} finally {
  pour "Cleanup complete"
}
```

### Modules

#### Exporting

```thirsty
glass add(a, b) {
  return a + b
}

drink PI = 3.14159

export add
export PI
```

#### Importing

```thirsty
import { add, PI } from "math-utils.thirsty"
import MathUtils from "math-utils.thirsty"
```

Modules are cached after first load.

## Security Features

Thirsty-Lang includes defensive programming primitives:

### Shield — Protected Code Blocks

```thirsty
shield secureApp {
  drink userData = "<script>alert('xss')</script>"
  sanitize userData
  pour userData  // Script tags removed
}
```

### Sanitize — XSS Prevention

Removes dangerous HTML/script content from string variables:

```thirsty
drink input = "<script>steal(data)</script>"
sanitize input
// input is now clean
```

### Armor — Variable Protection

Makes a variable read-only. Subsequent assignments are silently blocked with a warning:

```thirsty
drink secret = "classified"
armor secret
drink secret = "hacked"  // Warning: Cannot modify armored variable 'secret'
pour secret  // "classified"
```

### Additional Security Keywords

| Keyword | Description |
|---------|-------------|
| `morph on: [...]` | Dynamic protection configuration |
| `detect target { ... }` | Threat monitoring block |
| `defend with: level` | Defense level configuration |

## Reserved Keywords

| Keyword | Purpose |
|---------|---------|
| `drink` | Variable declaration |
| `pour` | Output / print |
| `sip` | Input |
| `thirsty` | If statement |
| `hydrated` | Else clause |
| `refill` | While loop |
| `glass` | Function declaration |
| `fountain` | Class declaration |
| `cascade` | Async function declaration |
| `reservoir` | Array declaration |
| `return` | Return from function |
| `throw` | Throw an error |
| `try` | Try block |
| `catch` | Catch block |
| `finally` | Finally block |
| `import` | Import module |
| `export` | Export identifier |
| `shield` | Protected code block |
| `sanitize` | XSS sanitization |
| `armor` | Variable protection |
| `morph` | Code mutation |
| `detect` | Threat monitoring |
| `defend` | Defense configuration |
| `await` | Await async result |
| `new` | Object instantiation |
| `true` | Boolean true |
| `false` | Boolean false |

## Built-in Libraries

### Math

| Method | Description |
|--------|-------------|
| `Math.PI` | Pi constant (3.14159...) |
| `Math.abs(x)` | Absolute value |
| `Math.floor(x)` | Round down |
| `Math.ceil(x)` | Round up |
| `Math.round(x)` | Round to nearest |
| `Math.pow(base, exp)` | Exponentiation |
| `Math.sqrt(x)` | Square root |
| `Math.min(a, b)` | Minimum |
| `Math.max(a, b)` | Maximum |
| `Math.random()` | Random 0–1 |

### String

| Method | Description |
|--------|-------------|
| `String.toUpperCase(s)` | Convert to uppercase |
| `String.toLowerCase(s)` | Convert to lowercase |
| `String.trim(s)` | Remove whitespace |
| `String.length(s)` | String length |
| `String.includes(s, sub)` | Check substring |
| `String.split(s, delim)` | Split into array |
| `String.replace(s, old, new)` | Replace substring |

### File I/O

| Method | Description |
|--------|-------------|
| `File.read(path)` | Read file synchronously |
| `File.write(path, content)` | Write file synchronously |
| `File.exists(path)` | Check if file exists |
| `File.delete(path)` | Delete a file |
| `File.readAsync(path)` | Read file (async) |
| `File.writeAsync(path, content)` | Write file (async) |

### HTTP

| Method | Description |
|--------|-------------|
| `Http.get(url)` | GET request (async) |
| `Http.post(url, data)` | POST request (async) |
| `Http.fetch(url, options)` | Generic HTTP request (async) |

### JSON

| Method | Description |
|--------|-------------|
| `JSON.parse(string)` | Parse JSON string |
| `JSON.stringify(value)` | Convert to JSON string |

## Grammar (EBNF)

```ebnf
program         = { statement } ;

<<<<<<< HEAD
statement       = var_decl
                | reservoir_decl
                | pour_stmt
                | sip_stmt
                | if_stmt
                | while_stmt
                | func_decl
                | cascade_decl
                | class_decl
                | return_stmt
                | throw_stmt
                | try_catch_stmt
                | shield_stmt
                | sanitize_stmt
                | armor_stmt
                | morph_stmt
                | detect_stmt
                | defend_stmt
                | import_stmt
                | export_stmt
                | expr_stmt ;
=======
Commands:

- `break <line>`, `b` - Set breakpoint
- `continue`, `c` - Continue execution
- `step`, `s` - Step into
- `next`, `n` - Step over
- `print <var>`, `p` - Print variable
- `eval <expr>`, `e` - Evaluate expression
- `stack` - Show call stack
- `list`, `l` - Show code listing
>>>>>>> 6adac05eb16ea0a433fc45859d939d6b5ee167f6

var_decl        = "drink" target "=" expression ;
reservoir_decl  = "reservoir" IDENT "=" "[" [ expression { "," expression } ] "]" ;
pour_stmt       = "pour" expression ;
sip_stmt        = "sip" IDENT [ STRING ] ;

if_stmt         = "thirsty" expression block
                  { "hydrated" "thirsty" expression block }
                  [ "hydrated" block ] ;
while_stmt      = "refill" expression block ;

func_decl       = "glass" IDENT "(" [ params ] ")" block ;
cascade_decl    = "cascade" IDENT "(" [ params ] ")" block ;
class_decl      = "fountain" IDENT "{" { property | method } "}" ;
property        = "drink" IDENT "=" expression ;
method          = "glass" IDENT "(" [ params ] ")" block ;
params          = IDENT { "," IDENT } ;

return_stmt     = "return" [ expression ] ;
throw_stmt      = "throw" expression ;
try_catch_stmt  = "try" block "catch" IDENT block [ "finally" block ] ;

shield_stmt     = "shield" IDENT block ;
sanitize_stmt   = "sanitize" IDENT ;
armor_stmt      = "armor" IDENT ;
morph_stmt      = "morph" morph_config ;
detect_stmt     = "detect" IDENT block ;
defend_stmt     = "defend" defend_config ;

import_stmt     = "import" ( "{" IDENT { "," IDENT } "}" "from" STRING
                           | IDENT "from" STRING ) ;
export_stmt     = "export" IDENT ;

block           = "{" { statement } "}" ;

expression      = assignment ;
assignment      = or_expr [ "=" assignment ] ;
or_expr         = and_expr { "||" and_expr } ;
and_expr        = equality { "&&" equality } ;
equality        = comparison { ( "==" | "!=" ) comparison } ;
comparison      = addition { ( "<" | ">" | "<=" | ">=" ) addition } ;
addition        = multiplication { ( "+" | "-" ) multiplication } ;
multiplication  = unary { ( "*" | "/" | "%" ) unary } ;
unary           = ( "-" | "!" | "await" ) unary | postfix ;
postfix         = primary { "." IDENT | "[" expression "]" | "(" [ args ] ")" } ;
primary         = NUMBER | STRING | "true" | "false" | IDENT
                | "(" expression ")"
                | "[" [ expression { "," expression } ] "]"
                | "new" IDENT "(" [ args ] ")" ;
args            = expression { "," expression } ;

target          = IDENT | postfix ;
```

## Error Handling

<<<<<<< HEAD
The parser provides precise error messages with line and column numbers:

- Syntax errors (unexpected tokens, missing braces)
- Undefined variable references
- Division by zero
- Array index out of bounds
- Argument count mismatches
- Maximum loop iteration exceeded (10,000)
- Maximum call depth exceeded (100)

## File Extensions

| Extension | Tier | Named After |
|-----------|------|-------------|
| `.thirsty` | Base | Thirsty-Lang |
| `.tog` | Tier 2 | Thirst of Gods |
| `.tarl` | Tier 3 | T.A.R.L. (Thirsty Autonomous Runtime Language) |
| `.shadow` | Tier 4 | Thirsty's Shadow |

## Examples

### Hello World

```thirsty
drink message = "Hello, World!"
pour message
```

### FizzBuzz

```thirsty
drink i = 1
refill i <= 20 {
  thirsty i % 15 == 0 {
    pour "FizzBuzz"
  } hydrated thirsty i % 3 == 0 {
    pour "Fizz"
  } hydrated thirsty i % 5 == 0 {
    pour "Buzz"
  } hydrated {
    pour i
  }
  drink i = i + 1
}
```

### Class with Methods

```thirsty
fountain Calculator {
  drink result = 0

  glass add(n) {
    drink this.result = this.result + n
    return this.result
  }

  glass multiply(n) {
    drink this.result = this.result * n
    return this.result
  }
}

drink calc = Calculator()
calc.add(5)
calc.multiply(3)
pour "Result: " + calc.result  // 15
```
=======
The interpreter will report errors for:

- Unknown statements
- Invalid syntax
- Undefined variables
- Type mismatches (in future versions)
>>>>>>> 6adac05eb16ea0a433fc45859d939d6b5ee167f6

## Conclusion

Thirsty-Lang is designed to be fun, safe, and capable. Stay hydrated and happy coding! 💧
