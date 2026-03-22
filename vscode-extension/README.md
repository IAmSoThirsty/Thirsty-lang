# ============================================================================ #
#                                           [2026-03-18 20:20]
#                                          Productivity: Active
# STATUS: ACTIVE | TIER: MASTER | DATE: 2026-03-18 | TIME: 20:20             #
# COMPLIANCE: Sovereign Substrate / Integrated Service: thirsty-lang-engine / README.md
# ============================================================================ #
# UTF for VS Code

**Full language support for the Universal Thirsty Family (UTF)** — syntax highlighting, snippets, and language configuration for the six official UTF languages.

## The Universal Thirsty Family

| Tier | Extension | Description |
|---|---|---|
| **Thirsty-Lang** | `.thirsty`, `.thirstyplus`, `.thirstyplusplus` | Core water-themed programming |
| **Thirst of Gods** | `.thirstofgods`, `.tog` | Divine-tier orchestration |
| **T.A.R.L.** | `.tarl` | Tactical security and resistance logic |
| **Shadow Thirst** | `.shadow` | Dual-plane and shadow execution |
| **TSCG** | `.tscg` | Thirsty's Symbolic Compression Grammar |
| **TSCG-B** | `.tscgb` | Binary framing layer for TSCG |
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

## Features

- 🎨 **Syntax Highlighting** — Shared TextMate grammar across the full UTF stack
- ✂️ **Code Snippets** — Quick templates for common patterns
- 📝 **Language Configuration** — Auto-closing brackets, comment toggling, indentation rules
- 📁 **Six Official Languages** — `.thirsty`, `.thirstofgods`, `.tog`, `.tarl`, `.shadow`, `.tscg`, and `.tscgb` files recognized

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
3. Search for **"UTF Language Support"**
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
- [Recognition Guide](../UTF_RECOGNITION.md)

## License

MIT — See [LICENSE](LICENSE)

---

**Stay hydrated and ship sovereign languages.**
