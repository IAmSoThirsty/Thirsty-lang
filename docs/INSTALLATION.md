# Installation and Setup Guide

## Prerequisites

Before installing Thirsty-Lang, ensure you have:

- **Node.js** version 18.0.0 or higher
- **npm** (comes with Node.js) or **yarn**
- A terminal/command prompt
- A code editor (VS Code recommended)

## Installation Methods

### Method 1: Clone from GitHub (Recommended)

```bash

# Clone the repository

<<<<<<< HEAD
git clone https://github.com/IAmSoThirsty/Thirsty-Lang.git

# Navigate to the directory

cd Thirsty-Lang
=======
git clone https://github.com/IAmSoThirsty/Thirsty-lang.git

# Navigate to the directory

cd Thirsty-lang
>>>>>>> 6adac05eb16ea0a433fc45859d939d6b5ee167f6

# Install dependencies (if any in future)

npm install

# Verify installation

npm test
```

### Method 2: Direct Download

1. Download the repository as a ZIP file from GitHub
2. Extract to your desired location
3. Open terminal in the extracted folder
4. Run `npm install`
5. Run `npm test` to verify

## Installing the CLI Globally (Optional)

To use the `thirsty` command from anywhere:

```bash

<<<<<<< HEAD
# In the Thirsty-Lang directory
=======
# In the Thirsty-lang directory
>>>>>>> 6adac05eb16ea0a433fc45859d939d6b5ee167f6

npm link

# Now you can use 'thirsty' from anywhere

thirsty run myprogram.thirsty
thirsty repl
thirsty train
```

## Verification

After installation, verify everything works:

```bash

# Run tests

npm test

# Run an example

npm start examples/hello.thirsty

# Start the REPL

npm run repl

# (press Ctrl+C twice to exit)

# Start training

npm run train

# (select option 6 to exit)

```

## Setting Up Your First Project

```bash

<<<<<<< HEAD
# Create a new Thirsty-Lang project
=======
# Create a new Thirsty-lang project
>>>>>>> 6adac05eb16ea0a433fc45859d939d6b5ee167f6

node src/thirsty-cli.js init my-first-project

# Navigate to your project

cd my-first-project

# Run the program

thirsty run src/main.thirsty
```

## Installing the VS Code Extension

1. Open VS Code
2. Copy `.vscode/extensions/Thirsty-Lang` to your VS Code extensions folder:
   - **Windows**: `%USERPROFILE%\.vscode\extensions\`
   - **macOS**: `~/.vscode/extensions/`
   - **Linux**: `~/.vscode/extensions/`
3. Reload VS Code
4. Open any `.thirsty` file to see syntax highlighting!

## Troubleshooting

### "Command not found: thirsty"

If the `thirsty` command isn't found after `npm link`:

```bash

# Try running with full path

<<<<<<< HEAD
node /path/to/Thirsty-Lang/src/thirsty-cli.js
=======
node /path/to/Thirsty-lang/src/thirsty-cli.js
>>>>>>> 6adac05eb16ea0a433fc45859d939d6b5ee167f6

# Or use npm scripts

npm start
npm run repl
npm run train
```

### Node.js version issues

Check your Node.js version:

```bash
node --version
```

If it's below 18.0.0, upgrade Node.js from [nodejs.org](https://nodejs.org)

### Tests failing

Make sure you're in the Thirsty-Lang directory:

```bash
cd /path/to/Thirsty-Lang
npm test
```

### Permission errors on Linux/macOS

You may need to make scripts executable:

```bash
chmod +x src/*.js
```

## Next Steps

After installation:

1. 🎓 **Start learning**: Run `npm run train` for interactive lessons
2. 🔍 **Explore examples**: Check out the `examples/` directory
3. 📚 **Read docs**: Browse the `docs/` directory
4. 🎮 **Try the playground**: Open `playground/index.html` in a browser
5. 💻 **Start coding**: Create your first Thirsty-Lang program!

## Getting Help

- 📖 Read the [FAQ](FAQ.md)
- 📚 Check the [Quick Reference](QUICK_REFERENCE.md)
- 🐛 Report issues on [GitHub](https://github.com/IAmSoThirsty/Thirsty-Lang/issues)

## Uninstallation

To remove Thirsty-Lang:

```bash

# If you used npm link

npm unlink

# Remove the directory

<<<<<<< HEAD
rm -rf /path/to/Thirsty-Lang
=======
rm -rf /path/to/Thirsty-lang
>>>>>>> 6adac05eb16ea0a433fc45859d939d6b5ee167f6
```

Stay hydrated! 💧
