# VS Code Extension for Thirsty-lang

This directory contains the VS Code extension for Thirsty-lang with syntax highlighting and code snippets.

## Installation

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

- ✨ **Syntax Highlighting** for all Thirsty-lang keywords
- 🎨 **Code Snippets** for common patterns
- 📝 **Auto-completion** for keywords
- 🔧 **Auto-closing** for brackets, quotes, and parentheses
- 💬 **Comment toggling** support

## Supported File Extensions

- `.thirsty` - Base Thirsty-lang
- `.thirstyplus` - Thirst of Gods edition (Tier 2)
- `.thirstyplusplus` - T.A.R.L. edition (Tier 3)
- `.thirstofgods` - Shadow Thirst edition (Tier 4)

## Available Snippets

Type these prefixes and press Tab:

- `drink` - Variable declaration
- `pour` - Output statement
- `//` - Comment
- `thirsty` - If statement (Thirst of Gods)
- `glass` - Function declaration (T.A.R.L.)
- `refill` - Loop (T.A.R.L.)
- `fountain` - Class declaration (Shadow Thirst)
- `cascade` - Async function (Shadow Thirst)

## Troubleshooting

If syntax highlighting doesn't work:

1. Make sure the extension is in the correct location
2. Reload VS Code (Ctrl/Cmd + Shift + P → "Reload Window")
3. Check that you're opening a `.thirsty` file

## Contributing

Want to improve the extension? Edit the files in this directory:

- `syntaxes/thirsty.tmLanguage.json` - Syntax grammar
- `snippets/thirsty.json` - Code snippets
- `language-configuration.json` - Language settings
- `package.json` - Extension metadata

Stay hydrated while coding! 💧
