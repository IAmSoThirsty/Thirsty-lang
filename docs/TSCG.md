# TSCG Documentation

## Overview

TSCG (Thirsty Symbolic Compression Grammar) is a two-tier compression system for Thirsty-lang that provides ultra-efficient repository compression with hash-stable binary encoding.

## Architecture

### Tier 5: Symbolic Compression (TSCG)

The symbolic compression layer converts source code into compact symbolic representations by:

1. **Tokenization**: Breaking down code into atomic units (keywords, identifiers, operators, literals)
2. **Symbol Mapping**: Creating a bidirectional dictionary of tokens to numeric IDs
3. **Compression**: Replacing tokens with their numeric symbol IDs
4. **Hash Verification**: Generating SHA-256 hashes for integrity checking

**Features:**
- Pre-initialized dictionary for all Thirsty-lang keywords (Tiers 1-4)
- Dynamic symbol allocation for identifiers and custom tokens
- Preserves code structure and semantics
- Maintains string literals and comments intact
- Git-aware file scanning with .gitignore support

### Tier 6: Binary Encoding (TSCG-B)

The binary encoding layer converts TSCG symbolic data into ultra-compact binary format:

1. **Variable-Length Encoding**: Efficient integer encoding (VarInt)
2. **Binary Serialization**: Converts all data structures to binary
3. **Compression**: Applies gzip compression (level 9)
4. **Hash Stability**: Maintains consistent hashes for verification

**Binary Format:**
```
[Magic Header: 5 bytes "TSCGB"]
[Version: 1 byte]
[Metadata: variable]
[Dictionary Length: 4 bytes]
[Dictionary: variable]
[Files Length: 4 bytes]
[Files: variable]
[Content Hash: 32 bytes SHA-256]
```

**Features:**
- Ultra-compact binary format
- Variable-length integer encoding for efficiency
- Gzip compression for maximum size reduction
- Content hash verification
- Micro payload support (~20 bytes for small files)

## Installation

```bash
npm install thirsty-lang
```

Or install CLI globally:

```bash
npm install -g thirsty-lang
```

## CLI Usage

### Compress Repository

Compress an entire repository into a TSCG-B binary file:

```bash
thirsty-compress compress <directory> <output.tscg>
```

**Examples:**

```bash
# Compress current directory
thirsty-compress compress . my-repo.tscg

# Compress specific directory
thirsty-compress compress ./src output.tscg

# Compress only Thirsty-lang files
thirsty-compress compress . thirsty-only.tscg --ext .thirsty,.thirstyplus,.thirstyplusplus

# Include hidden files
thirsty-compress compress . full-repo.tscg --include-hidden

# Disable .gitignore awareness
thirsty-compress compress . everything.tscg --no-git-aware
```

### Decompress Repository

Restore a TSCG-B binary file to its original directory structure:

```bash
thirsty-compress decompress <input.tscg> <output-directory>
```

**Examples:**

```bash
# Decompress to new directory
thirsty-compress decompress my-repo.tscg ./restored

# Decompress to current directory
thirsty-compress decompress backup.tscg .
```

### Micro Payload Compression

Create ultra-compact payloads for single files:

```bash
thirsty-compress micro <file> <output.tscg>
```

**Examples:**

```bash
# Compress single file
thirsty-compress micro hello.thirsty hello.tscg

# Compress example file
thirsty-compress micro examples/functions.thirstyplusplus functions.tscg
```

**Note:** Micro payloads achieve maximum compression for single files, though very small files may have compression overhead due to metadata.

### Analyze Repository

Analyze repository size without compressing:

```bash
thirsty-compress analyze <directory>
```

**Examples:**

```bash
# Analyze current directory
thirsty-compress analyze .

# Analyze specific directory
thirsty-compress analyze ./src

# Analyze only JavaScript files
thirsty-compress analyze . --ext .js,.ts
```

### Verify Integrity

Verify TSCG-B file integrity and view metadata:

```bash
thirsty-compress verify <file.tscg>
```

**Examples:**

```bash
# Verify compressed file
thirsty-compress verify my-repo.tscg

# Verify before decompression
thirsty-compress verify backup.tscg
```

### Export to JSON

Export TSCG-B binary to human-readable JSON:

```bash
thirsty-compress export <input.tscg> <output.json>
```

**Examples:**

```bash
# Export for inspection
thirsty-compress export my-repo.tscg inspect.json

# Export for analysis
thirsty-compress export compressed.tscg readable.json
```

### Import from JSON

Convert JSON back to TSCG-B binary:

```bash
thirsty-compress import <input.json> <output.tscg>
```

**Examples:**

```bash
# Import modified JSON
thirsty-compress import modified.json updated.tscg

# Re-compress from JSON
thirsty-compress import data.json compressed.tscg
```

## CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--include-hidden` | Include hidden files (starting with `.`) | `false` |
| `--no-git-aware` | Disable .gitignore awareness | `false` (git-aware enabled) |
| `--ext <extensions>` | Filter by file extensions (comma-separated) | All files |

## Programmatic API

### JavaScript/Node.js

```javascript
const TSCGManager = require('thirsty-lang/src/tscg');

const manager = new TSCGManager();

// Compress repository
const result = manager.compressRepository('./src', 'output.tscg', {
  includeHidden: false,
  gitAware: true,
  extensions: ['.thirsty', '.js', '.ts']
});

console.log(`Compressed ${result.stats.files} files`);
console.log(`Output size: ${result.stats.size} bytes`);
console.log(`Compression: ${result.stats.compressionRatio}`);

// Decompress repository
manager.decompressRepository('output.tscg', './restored');

// Create micro payload
manager.compressMicroPayload('hello.thirsty', 'hello.tscg');

// Analyze repository
const analysis = manager.analyzeRepository('./src');
console.log(`Total files: ${analysis.files}`);
console.log(`Total size: ${analysis.totalSize} bytes`);

// Verify integrity
const verification = manager.verifyCompressed('output.tscg');
if (verification.valid) {
  console.log('File is valid!');
}

// Export/Import JSON
manager.exportJSON('output.tscg', 'output.json');
manager.importJSON('output.json', 'rebuilt.tscg');
```

### SymbolicCompression API

```javascript
const SymbolicCompression = require('thirsty-lang/src/tscg/symbolic-compression');

const symbolic = new SymbolicCompression();

// Compress single file
const compressed = symbolic.compressFile('test.thirsty', 'drink x = 5');
console.log(compressed.symbols); // [1, 3, 4, 5]
console.log(compressed.hash);    // SHA-256 hash

// Decompress file
const content = symbolic.decompressFile(compressed);
console.log(content); // 'drink x = 5'

// Tokenize code
const tokens = symbolic.tokenize('drink water = 8');
console.log(tokens); // ['drink', ' ', 'water', ' ', '=', ' ', '8']

// Compress directory
const data = symbolic.compressDirectory('./src', {
  extensions: ['.thirsty']
});
```

### BinaryEncoding API

```javascript
const BinaryEncoding = require('thirsty-lang/src/tscg/binary-encoding');

const binary = new BinaryEncoding();

// Encode TSCG data
const tscgData = { /* symbolic compression data */ };
const encoded = binary.encode(tscgData);

console.log(encoded.binary);      // Buffer
console.log(encoded.hash);        // Content hash
console.log(encoded.stats);       // Compression stats

// Decode binary data
const decoded = binary.decode(encoded.binary);

// Create micro payload
const microPayload = binary.createMicroPayload(singleFileTSCG);
console.log(microPayload.length); // ~20-40 bytes
```

## npm Scripts

Add to your `package.json`:

```json
{
  "scripts": {
    "compress": "thirsty-compress compress . repo.tscg",
    "decompress": "thirsty-compress decompress repo.tscg ./restored",
    "test:tscg": "node src/test/tscg-tests.js"
  }
}
```

Run with:

```bash
npm run compress
npm run decompress
npm run test:tscg
```

## Use Cases

### 1. Repository Backup

Compress entire repository for backup:

```bash
thirsty-compress compress . backup-$(date +%Y%m%d).tscg
```

### 2. Code Distribution

Distribute code in compact format:

```bash
thirsty-compress compress ./dist release.tscg
thirsty-compress decompress release.tscg ./install
```

### 3. Version Control

Store compressed snapshots:

```bash
thirsty-compress compress . snapshots/v1.0.0.tscg
```

### 4. CI/CD Pipeline

Compress build artifacts:

```bash
# In CI pipeline
thirsty-compress compress ./build artifacts.tscg
thirsty-compress verify artifacts.tscg
```

### 5. Code Analysis

Export for analysis tools:

```bash
thirsty-compress compress ./src code.tscg
thirsty-compress export code.tscg analysis.json
# Process analysis.json with custom tools
```

## Performance

### Compression Ratios

| File Type | Typical Ratio | Notes |
|-----------|--------------|-------|
| Thirsty-lang (.thirsty) | 40-60% | High keyword repetition |
| JavaScript/TypeScript | 30-50% | Good symbol reuse |
| Very small files (<100 bytes) | May expand | Metadata overhead |
| Large repositories | 50-70% | Best compression |

### Speed

- **Compression**: ~1-5ms per file (typical)
- **Decompression**: ~0.5-2ms per file (typical)
- **Memory**: Minimal, streaming-friendly

### Scalability

- Tested on repositories up to 10,000 files
- Supports files of any size
- Handles all file types (text-based recommended)
- Git-aware scanning for performance

## Technical Details

### Symbol Dictionary

Pre-initialized symbols (Tier 1-4 keywords):

**Tier 1 (Core):**
- `drink`, `pour`, `sip`, `//`, `/*`, `*/`

**Tier 2 (Thirst of Gods):**
- `thirsty`, `hydrated`, `parched`, `quenched`

**Tier 3 (T.A.R.L.):**
- `glass`, `refill`, `reservoir`, `return`
- `shield`, `armor`, `sanitize`, `detect`, `morph`

**Tier 4 (Shadow Thirst):**
- `fountain`, `cascade`, `await`, `this`
- `spillage`, `cleanup`, `import`, `export`

**Operators:**
- `+`, `-`, `*`, `/`, `=`, `==`, `!=`, `<`, `>`, `<=`, `>=`
- `(`, `)`, `{`, `}`, `[`, `]`, `,`, `.`, `;`

### VarInt Encoding

Variable-length integer encoding optimizes for small numbers:

- 0-127: 1 byte
- 128-16,383: 2 bytes
- 16,384-2,097,151: 3 bytes
- And so on...

Most symbol IDs are small (<100), resulting in 1-byte encoding.

### Hash Verification

Two levels of hashing:

1. **File-level**: SHA-256 hash per file for individual verification
2. **Content-level**: SHA-256 hash of entire payload for overall verification

## Troubleshooting

### Issue: Compression increases file size

**Solution:** This is expected for very small files due to metadata overhead. TSCG is optimized for repositories and larger files.

### Issue: Decompression fails

**Solution:** Verify file integrity first:

```bash
thirsty-compress verify file.tscg
```

### Issue: Memory usage is high

**Solution:** TSCG processes files individually. For very large repositories, consider compressing subdirectories separately.

### Issue: .gitignore not respected

**Solution:** Ensure git-aware mode is enabled (default):

```bash
thirsty-compress compress . output.tscg  # git-aware by default
```

Disable with:

```bash
thirsty-compress compress . output.tscg --no-git-aware
```

## Examples

### Complete Workflow

```bash
# 1. Analyze repository
thirsty-compress analyze ./my-project

# 2. Compress entire project
thirsty-compress compress ./my-project project.tscg

# 3. Verify compression
thirsty-compress verify project.tscg

# 4. Export for inspection (optional)
thirsty-compress export project.tscg project.json

# 5. Decompress to new location
thirsty-compress decompress project.tscg ./restored-project

# 6. Verify decompressed files match
diff -r my-project restored-project
```

### Integration with Build Tools

**Webpack:**

```javascript
// webpack.config.js
const { exec } = require('child_process');

module.exports = {
  // ... webpack config
  plugins: [
    {
      apply: (compiler) => {
        compiler.hooks.done.tap('TSCG Compress', () => {
          exec('thirsty-compress compress ./dist dist.tscg');
        });
      }
    }
  ]
};
```

**GitHub Actions:**

```yaml
name: Compress Build

on: [push]

jobs:
  compress:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install Thirsty-lang
        run: npm install -g thirsty-lang
      - name: Compress repository
        run: thirsty-compress compress . repo.tscg
      - name: Upload artifact
        uses: actions/upload-artifact@v2
        with:
          name: compressed-repo
          path: repo.tscg
```

## Testing

Run TSCG tests:

```bash
npm run test:tscg
```

Or directly:

```bash
node src/test/tscg-tests.js
```

## Contributing

TSCG is part of the Thirsty-lang project. Contributions welcome!

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

Same as Thirsty-lang. See [LICENSE](../LICENSE) for details.

## Version History

### 2.0.0 (Current)
- Initial TSCG implementation (Tier 5)
- TSCG-B binary encoding (Tier 6)
- CLI tool with full feature set
- Comprehensive test suite (19 tests)
- Complete documentation

## Related Documentation

- [EXPANSIONS.md](./EXPANSIONS.md) - Language tier overview
- [DOCUMENTATION.md](../DOCUMENTATION.md) - Main language documentation
- [TUTORIAL.md](../TUTORIAL.md) - Language tutorial
- [README.md](../README.md) - Project overview

## Support

- GitHub Issues: https://github.com/IAmSoThirsty/Thirsty-lang/issues
- Documentation: https://github.com/IAmSoThirsty/Thirsty-lang#readme
