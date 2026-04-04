<!--                                         [2026-03-03 13:45] -->
<!--                                        Productivity: Active -->
# Thirsty-lang Expansions

Thirsty-lang comes in multiple flavors to suit different levels of thirst! 💧

## Base: Thirsty-lang

The core language with basic features:

- Variable declaration (`drink`)
- Output (`pour`)
- Comments

**Use when**: You're just starting your hydration journey.

## Thirst of Gods (Tier 2)

Enhanced features for intermediate users:

### Additional Features

- **Control Flow**: `thirsty` (if) and `hydrated` (else)
- **Arithmetic**: Basic math operations (+, -, *, /)
- **Comparison**: equals, greater than, less than
- **String concatenation**: Join strings with `+`

### New Keywords

- `thirsty condition` - If statement
- `hydrated` - Else statement
- `parched` - Boolean true
- `quenched` - Boolean false

### Example

```thirstyplus
drink temperature = 25
thirsty temperature > 20
  pour "It's warm! Drink more water!"
hydrated
  pour "Stay hydrated anyway!"
```

**Use when**: You need basic logic and control flow.

## T.A.R.L. (Tier 3)

Advanced features for power users:

### ✅ Implemented Features

- **Loops**: `refill` for iteration
- **Functions**: `glass` for function declarations with parameters and return values
- **Arrays**: `reservoir` for dynamic collections
- **Standard Library**: Built-in Math and String utilities

### Keywords

- `refill condition` - While loop
- `glass name(params)` - Function definition
- `sip` - Input from user
- `reservoir` - Array declaration
- `return` - Return from function

### Example

```thirstyplusplus
glass calculateHydration(weight) {
  drink dailyWater = weight * 0.033
  return dailyWater
}

drink myWeight = 70
drink needed = calculateHydration(myWeight)
pour needed

reservoir drinks = ["water", "juice", "tea"]
drink i = 0
refill i < drinks.length {
  pour drinks[i]
  drink i = i + 1
}

// Using standard library
drink area = Math.PI * Math.pow(5, 2)
pour "Circle area: " + area
```

**Use when**: Building complex applications with functions and data structures.

## Shadow Thirst (Tier 4)

The most powerful variant with divine capabilities:

### ✅ Implemented Features

- **Classes**: `fountain` for object-oriented programming
- **Object Instantiation**: Create instances of classes
- **Class Methods**: Define and call methods on instances
- **Class Properties**: Instance variables with default values
- **this keyword**: Access instance properties within methods

### 🔮 Future Features (Planned)

- **Async/Await**: `cascade` and `await` for asynchronous operations
- **Modules**: `import` and `export` for code organization
- **Error Handling**: `spillage` (try) and `cleanup` (catch)

### Keywords

- `fountain ClassName` - Class declaration
- `this` - Reference to instance properties

### Example

```thirstofgods
fountain HydrationTracker {
  drink totalWater = 0
  drink goal = 2000

  glass addWater(amount) {
    drink this.totalWater = this.totalWater + amount
    pour "Added " + amount + "ml. Total: " + this.totalWater + "ml"
  }

  glass checkGoal() {
    thirsty this.totalWater >= this.goal {
      pour "Goal reached! Great hydration!"
      return true
    }
    hydrated {
      drink remaining = this.goal - this.totalWater
      pour "Still need " + remaining + "ml to reach goal"
      return false
    }
  }
}

drink tracker = HydrationTracker()
tracker.addWater(500)
tracker.addWater(800)
tracker.checkGoal()
```

**Use when**: Building enterprise-level applications with object-oriented design.

## TSCG (Tier 5)

The Symbolic Compression Grammar tier for code compression:

### ✅ Implemented Features

- **Symbolic Tokenization**: Convert code to symbol-based representation
- **Symbol Dictionary**: Pre-initialized with all Thirsty-lang keywords
- **File Compression**: Compress individual files or entire repositories
- **Hash Verification**: SHA-256 hashes for integrity checking
- **Git-Aware Scanning**: Respects .gitignore patterns

### CLI Commands

- `thirsty-compress compress <dir> <output>` - Compress directory
- `thirsty-compress decompress <input> <dir>` - Decompress to directory
- `thirsty-compress analyze <dir>` - Analyze repository size

### Example

```bash
# Compress entire repository
thirsty-compress compress . my-repo.tscg

# Analyze compression potential
thirsty-compress analyze ./src

# Decompress repository
thirsty-compress decompress my-repo.tscg ./restored
```

**Use when**: Backing up, distributing, or archiving Thirsty-lang code.

## TSCG-B (Tier 6)

The Binary Encoding tier for ultra-compact storage:

### ✅ Implemented Features

- **Binary Encoding**: Convert TSCG symbols to efficient binary format
- **Variable-Length Integers**: Optimize small numbers (1 byte for 0-127)
- **Gzip Compression**: Level 9 compression for maximum size reduction
- **Micro Payloads**: Target ~20 byte payloads for single files
- **Hash-Stable Format**: Consistent hashing for verification
- **Export/Import**: JSON export for inspection and debugging

### CLI Commands

- `thirsty-compress micro <file> <output>` - Create micro payload
- `thirsty-compress verify <file>` - Verify integrity
- `thirsty-compress export <input> <output>` - Export to JSON
- `thirsty-compress import <input> <output>` - Import from JSON

### Example

```bash
# Create ultra-compact micro payload
thirsty-compress micro hello.thirsty hello.tscg

# Verify compressed file
thirsty-compress verify my-repo.tscg

# Export for inspection
thirsty-compress export my-repo.tscg inspect.json

# Import from JSON
thirsty-compress import modified.json updated.tscg
```

**Use when**: Maximum compression is needed for storage or transmission.

## Choosing Your Edition

| Feature | Base | Thirst of Gods | T.A.R.L. | Shadow Thirst | TSCG | TSCG-B |
|---------|------|----------------|----------|---------------|------|--------|
| Variables | ✓ | ✓ | ✓ | ✓ | N/A | N/A |
| Output | ✓ | ✓ | ✓ | ✓ | N/A | N/A |
| Control Flow | ✗ | ✓ | ✓ | ✓ | N/A | N/A |
| Operators | ✗ | ✓ | ✓ | ✓ | N/A | N/A |
| Loops | ✗ | ✓ | ✓ | ✓ | N/A | N/A |
| Functions | ✗ | ✗ | ✓ | ✓ | N/A | N/A |
| Arrays | ✗ | ✗ | ✓ | ✓ | N/A | N/A |
| Standard Library | ✗ | ✗ | ✓ | ✓ | N/A | N/A |
| Classes | ✗ | ✗ | ✗ | ✓ | N/A | N/A |
| OOP | ✗ | ✗ | ✗ | ✓ | N/A | N/A |
| Compression | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| Binary Encoding | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |

## Running Your Code

All language tiers (1-4) are available in the standard Thirsty-lang interpreter:

```bash
# Run any Thirsty-lang program
npm start examples/hello.thirsty
npm start examples/functions.thirsty
npm start examples/arrays.thirsty
npm start examples/classes.thirsty
npm start examples/stdlib.thirsty
```

**TSCG Compression (Tiers 5-6):**

```bash
# Compress repository
thirsty-compress compress . my-repo.tscg

# Decompress repository
thirsty-compress decompress my-repo.tscg ./restored

# Run TSCG tests
npm run test:tscg
```

**Note:** Language features (Tiers 1-4) are all available by default. The tier system is a progressive learning path. TSCG (Tiers 5-6) provides compression utilities separate from the language runtime.

## Migration Path

Start with base Thirsty-lang and ascend through the tiers! Each tier is backward compatible with the previous one.

1. **Start with Base (Tier 1)**: Learn variables and output
2. **Move to Thirst of Gods (Tier 2)**: Add control flow and conditionals
3. **Advance to T.A.R.L. (Tier 3)**: Master functions, arrays, and the standard library
4. **Ascend to Shadow Thirst (Tier 4)**: Embrace object-oriented programming
5. **Utilize TSCG (Tier 5)**: Compress and distribute your code efficiently
6. **Optimize with TSCG-B (Tier 6)**: Achieve maximum compression with binary encoding

Stay hydrated at every level! 💧✨

## Additional Resources

- **[TSCG Documentation](./TSCG.md)** - Complete TSCG compression guide
- **[README.md](../README.md)** - Main project documentation
- **[TUTORIAL.md](./TUTORIAL.md)** - Language tutorial
- **[DOCUMENTATION.md](../DOCUMENTATION.md)** - Full language reference
