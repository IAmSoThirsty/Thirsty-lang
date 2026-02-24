# Thirsty-Lang Expansions

Thirsty-Lang comes in four tiers to suit different levels of thirst! 💧

## Tier 1: Thirsty-Lang (`.thirsty`)

The core language with fundamental features:

- Variable declaration (`drink`)
- Output (`pour`)
- Comments

**Use when**: You're just starting your hydration journey.

## Tier 2: Thirst of Gods (`.tog`)

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

### Thirst of Gods Example

```thirsty
drink temperature = 25
thirsty temperature > 20
  pour "It's warm! Drink more water!"
hydrated
  pour "Stay hydrated anyway!"
```

**Use when**: You need basic logic and control flow.

## Tier 3: T.A.R.L. (`.tarl`)

Advanced features for power users — Tactical Analysis & Response Language:

### ✅ Implemented Features

- **Loops**: `refill` for iteration
- **Functions**: `glass` for function declarations with parameters and return values
- **Arrays**: `reservoir` for dynamic collections
- **Standard Library**: Built-in Math and String utilities
- **Security**: `shield`, `sanitize`, `armor`, `detect`, `defend`

### T.A.R.L. Keywords

- `refill condition` - While loop
- `glass name(params)` - Function definition
- `sip` - Input from user
- `reservoir` - Array declaration
- `return` - Return from function
- `shield` - Protected code block
- `sanitize` - Input cleaning
- `armor` - Memory protection

### T.A.R.L. Example

```thirsty
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

**Use when**: Building complex applications with functions, data structures, and security.

## Tier 4: Thirsty's Shadow (`.shadow`)

The most powerful tier with shadow-realm capabilities:

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
- **Shadow Computing**: Dual-reality execution model

### Shadow Keywords

- `fountain ClassName` - Class declaration
- `this` - Reference to instance properties
- `cascade` - Async function
- `morph` - Code obfuscation

### Shadow Example

```thirsty
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

## Choosing Your Tier

| Feature | Thirsty-Lang | Thirst of Gods | T.A.R.L. | Thirsty's Shadow |
| --------- | :---: | :---: | :---: | :---: |
| Variables | ✓ | ✓ | ✓ | ✓ |
| Output | ✓ | ✓ | ✓ | ✓ |
| Control Flow | ✗ | ✓ | ✓ | ✓ |
| Operators | ✗ | ✓ | ✓ | ✓ |
| Loops | ✗ | ✓ | ✓ | ✓ |
| Functions | ✗ | ✗ | ✓ | ✓ |
| Arrays | ✗ | ✗ | ✓ | ✓ |
| Standard Library | ✗ | ✗ | ✓ | ✓ |
| Security Features | ✗ | ✗ | ✓ | ✓ |
| Classes | ✗ | ✗ | ✗ | ✓ |
| OOP | ✗ | ✗ | ✗ | ✓ |

## Running Your Code

All tiers are currently available in the standard Thirsty-Lang interpreter:

```bash
# Run any Thirsty-Lang program
npm start examples/hello.thirsty
npm start examples/functions.thirsty
npm start examples/arrays.thirsty
npm start examples/classes.thirsty
npm start examples/stdlib.thirsty
```

**Note:** All features from all tiers are available by default. The tier system is designed as a progressive learning path rather than separate runtime modes.

## Migration Path

Start with Thirsty-Lang and ascend as your thirst grows! Each tier is backward compatible.

1. **Start with Thirsty-Lang**: Learn variables and output
2. **Ascend to Thirst of Gods**: Add control flow and conditionals
3. **Master T.A.R.L.**: Functions, arrays, security, and the standard library
4. **Enter Thirsty's Shadow**: Embrace OOP and shadow computing

Stay hydrated at every tier! 💧✨
