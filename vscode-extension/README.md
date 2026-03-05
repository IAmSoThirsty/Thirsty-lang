# Thirsty-Lang for VS Code 💧

**Full language support for the [Thirsty language family](https://github.com/IAmSoThirsty/Thirsty-Lang)** — syntax highlighting, code snippets, and language configuration for all four tiers.

## The Hydration Language Family

<<<<<<< HEAD
| Tier | Extension | Description |
|---|---|---|
| **Thirsty-Lang** | `.thirsty` | Core water-themed programming |
| **Thirst of Gods** | `.tog` | Divine-tier capabilities |
| **T.A.R.L.** | `.tarl` | Tactical security & analysis |
| **Thirsty's Shadow** | `.shadow` | Shadow computing & dual-reality |
=======
### Manual Installation

1. Copy this entire `vscode-extension` folder
2. Paste it into your VS Code extensions directory:
   - **Windows**: `%USERPROFILE%\.vscode\extensions\thirsty-lang\`
   - **macOS**: `~/.vscode/extensions/thirsty-lang/`
   - **Linux**: `~/.vscode/extensions/thirsty-lang/`
3. Reload VS Code
4. Open any `.thirsty` file to see syntax highlighting!

### Alternative: Symlink (Advanced)

```bash

# From the Thirsty-lang directory

ln -s "$(pwd)/vscode-extension" ~/.vscode/extensions/thirsty-lang
```
>>>>>>> 6adac05eb16ea0a433fc45859d939d6b5ee167f6

## Features

- 🎨 **Syntax Highlighting** — Full TextMate grammar for all Thirsty-Lang keywords
- ✂️ **Code Snippets** — Quick templates for common patterns
- 📝 **Language Configuration** — Auto-closing brackets, comment toggling, indentation rules
- 📁 **All Four Tiers** — `.thirsty`, `.tog`, `.tarl`, and `.shadow` files recognized

## Syntax Preview

```thirsty
// Hello World in Thirsty-Lang
drink message = "Hello, Thirsty World!"
pour message

// Control flow
drink temperature = 30
thirsty temperature > 25 {
  pour "Stay hydrated!"
}
hydrated {
  pour "Drink up anyway!"
}

// Loops
drink glasses = 0
refill glasses < 8 {
  drink glasses = glasses + 1
  pour glasses
}
```

## Core Keywords

| Keyword | Purpose |
|---|---|
| `drink` | Variable declaration |
| `pour` | Output / print |
| `sip` | Input |
| `thirsty` | If statement |
| `hydrated` | Else statement |
| `refill` | Loop |
| `glass` | Function declaration |
| `fountain` | Class declaration |
| `cascade` | Async function |
| `shield` | Protected code block |
| `sanitize` | Input cleaning |
| `armor` | Memory protection |
| `morph` | Code obfuscation |
| `detect` | Threat monitoring |
| `defend` | Countermeasures |
| `reservoir` | Array declaration |

## Installation

### From VS Code Marketplace

1. Open VS Code
2. Press `Ctrl+Shift+X` (Extensions)
3. Search for **"Thirsty-Lang"**
4. Click **Install**

### From VSIX

```bash
code --install-extension Thirsty-Lang-1.0.0.vsix
```

## Requirements

- VS Code ≥ 1.60.0

## Links

- [GitHub Repository](https://github.com/IAmSoThirsty/Thirsty-Lang)
- [Language Specification](https://github.com/IAmSoThirsty/Thirsty-Lang/blob/main/docs/SPECIFICATION.md)
- [npm Package](https://www.npmjs.com/package/Thirsty-Lang)
- [PyPI Package](https://pypi.org/project/Thirsty-Lang/)

## License

MIT — See [LICENSE](LICENSE)

---

**Stay hydrated and happy coding! 💧**
