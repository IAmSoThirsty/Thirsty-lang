# GitHub Linguist Submission Guide for Thirsty-lang

This document provides guidance for submitting Thirsty-lang to the GitHub Linguist project for official language recognition.

## Overview

**Thirsty-lang** is a water-themed, defensive programming language with built-in security features and T.A.R.L. integration. This guide outlines the requirements and process for getting Thirsty-lang officially recognized by GitHub Linguist.

## Prerequisites Checklist

Before submitting to GitHub Linguist, ensure all requirements are met:

### 1. Minimum Usage Requirements
- [ ] **200+ unique public repositories** using Thirsty-lang on GitHub
- [ ] Public, non-trivial examples of real-world codebases
- [ ] Active community and ongoing maintenance

**Current Status**: In development - building community adoption

### 2. Technical Requirements

#### ✅ File Extensions
- `.thirsty` (primary)
- `.thirstyplus`
- `.thirstyplusplus`
- `.thirstofgods`

#### ✅ Syntax Grammar
Located in: `vscode-extension/syntaxes/thirsty.tmLanguage.json`

The TextMate grammar includes:
- Comments (`//`)
- Keywords (drink, pour, sip, thirsty, hydrated, refill, glass, fountain, etc.)
- Strings (double and single quoted)
- Numbers (integers and decimals)
- Operators (=, +, -, *, /, >, <, ==, !=, >=, <=)

#### ✅ Language Metadata
Located in: `linguist.yml`

Contains:
- Language name: Thirsty
- Type: programming
- Color: #00bfff (water blue)
- File extensions
- TextMate scope: source.thirsty
- Ace mode: text
- Language ID: 1001001001

#### ✅ Sample Code
Located in: `samples/` directory

Includes:
- `hello-world.thirsty` - Basic syntax
- `fibonacci.thirsty` - Functions and loops
- `calculator.thirsty` - Object-oriented programming
- `arrays.thirsty` - Data structures
- `security.thirsty` - Security features
- `stdlib.thirsty` - Standard library usage

#### ✅ Documentation
- [README.md](README.md) - Main documentation
- [SPECIFICATION.md](docs/SPECIFICATION.md) - Language specification
- [TUTORIAL.md](TUTORIAL.md) - Learning guide
- [QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) - Syntax reference

### 3. Repository Configuration

#### ✅ .gitattributes
Located in: `.gitattributes`

Properly configured with:
- Language detection for all file extensions
- Documentation markup
- Vendored path exclusions

## Submission Process

When ready to submit to GitHub Linguist:

### Step 1: Fork the Linguist Repository

```bash
git clone https://github.com/github/linguist.git
cd linguist
```

### Step 2: Add Language Definition

Edit `lib/linguist/languages.yml` and add:

```yaml
Thirsty:
  type: programming
  color: "#00bfff"
  aliases:
    - thirsty-lang
    - thirsty
  extensions:
    - .thirsty
    - .thirstyplus
    - .thirstyplusplus
    - .thirstofgods
  tm_scope: source.thirsty
  ace_mode: text
  language_id: 1001001001
  interpreters:
    - thirsty
  filenames: []
```

### Step 3: Add TextMate Grammar

Copy `vscode-extension/syntaxes/thirsty.tmLanguage.json` to:
```
linguist/vendor/grammars/thirsty.tmLanguage.json
```

### Step 4: Add Sample Files

Copy files from `samples/` to:
```
linguist/samples/Thirsty/
```

Include at least:
- `hello-world.thirsty`
- `fibonacci.thirsty`
- `calculator.thirsty`

### Step 5: Update Tests

In `linguist/test/test_blob.rb`, add tests for Thirsty-lang file detection:

```ruby
def test_thirsty_language
  assert_equal 'Thirsty', Linguist::FileBlob.new("test.thirsty").language.name
  assert_equal 'Thirsty', Linguist::FileBlob.new("test.thirstyplus").language.name
end
```

### Step 6: Run Tests

```bash
bundle install
bundle exec rake test
```

### Step 7: Create Pull Request

Submit a PR to https://github.com/github/linguist with:

**Title**: "Add Thirsty-lang programming language"

**Description**:
```
This PR adds support for Thirsty-lang, a water-themed defensive programming language.

**Language Details:**
- Name: Thirsty-lang
- Type: Programming language
- Website: https://github.com/IAmSoThirsty/Thirsty-lang
- Extensions: .thirsty, .thirstyplus, .thirstyplusplus, .thirstofgods

**Features:**
- Water-themed syntax (drink, pour, sip, thirsty, hydrated, refill)
- Object-oriented programming with 'fountain' keyword
- Built-in security features (shield, sanitize, armor)
- Standard library with Math and String utilities
- T.A.R.L. security integration

**Files Included:**
- Language definition in languages.yml
- TextMate grammar (thirsty.tmLanguage.json)
- Sample code files demonstrating language features

**Documentation:**
- Repository: https://github.com/IAmSoThirsty/Thirsty-lang
- Comprehensive README with examples
- Complete language specification
```

## Current Status

### ✅ Completed
- [x] Language design and implementation
- [x] TextMate grammar for syntax highlighting
- [x] Sample code files
- [x] Complete documentation
- [x] VS Code extension
- [x] .gitattributes configuration
- [x] linguist.yml metadata file

### 🔄 In Progress
- [ ] Building community adoption (target: 200+ public repos)
- [ ] Publishing to NPM for wider distribution
- [ ] Creating tutorial content and guides

### 📋 Next Steps
1. Publish package to NPM
2. Promote language adoption
3. Create more example projects
4. Build community of users
5. Submit to Linguist when adoption threshold is met

## References

- [GitHub Linguist](https://github.com/github/linguist)
- [Linguist Contributing Guide](https://github.com/github/linguist/blob/master/CONTRIBUTING.md)
- [How to add a new language](https://github.com/github/linguist/blob/master/CONTRIBUTING.md#adding-a-language)
- [TextMate Grammar Guide](https://macromates.com/manual/en/language_grammars)

## Contact

For questions about Thirsty-lang:
- GitHub: https://github.com/IAmSoThirsty/Thirsty-lang
- Issues: https://github.com/IAmSoThirsty/Thirsty-lang/issues

---

**Note**: This is a preparatory guide. Actual submission to GitHub Linguist should only occur after meeting the minimum usage requirements (200+ unique public repositories).
