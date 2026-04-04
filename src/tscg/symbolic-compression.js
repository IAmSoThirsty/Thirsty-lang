/**
 * TSCG - Thirsty Symbolic Compression Grammar (Tier 5)
 *
 * Symbolic compression layer that converts code structures into
 * compact symbolic representations for efficient storage and transmission.
 */

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

class SymbolicCompression {
  constructor() {
    // Symbol dictionary for common patterns
    this.symbolMap = new Map();
    this.reverseMap = new Map();
    this.nextSymbolId = 1;

    // Initialize common Thirsty-lang tokens
    this.initializeSymbolDictionary();
  }

  initializeSymbolDictionary() {
    // Core keywords (Tier 1)
    const coreTokens = [
      'drink', 'pour', 'sip', '//', '/*', '*/',
    ];

    // Thirst of Gods keywords (Tier 2)
    const tier2Tokens = [
      'thirsty', 'hydrated', 'parched', 'quenched',
    ];

    // T.A.R.L. keywords (Tier 3)
    const tier3Tokens = [
      'glass', 'refill', 'reservoir', 'return',
      'shield', 'armor', 'sanitize', 'detect', 'morph',
    ];

    // Shadow Thirst keywords (Tier 4)
    const tier4Tokens = [
      'fountain', 'cascade', 'await', 'this',
      'spillage', 'cleanup', 'import', 'export',
    ];

    // Operators and common patterns
    const operators = [
      '+', '-', '*', '/', '=', '==', '!=', '<', '>', '<=', '>=',
      '(', ')', '{', '}', '[', ']', ',', '.', ';',
    ];

    // Combine all tokens
    const allTokens = [
      ...coreTokens,
      ...tier2Tokens,
      ...tier3Tokens,
      ...tier4Tokens,
      ...operators,
    ];

    // Create bidirectional mapping
    allTokens.forEach(token => {
      const symbolId = this.nextSymbolId++;
      this.symbolMap.set(token, symbolId);
      this.reverseMap.set(symbolId, token);
    });
  }

  /**
   * Compress a single file into symbolic representation
   */
  compressFile(filePath, content) {
    const tokens = this.tokenize(content);
    const symbols = tokens.map(token => {
      // Use existing symbol or create new one
      if (!this.symbolMap.has(token)) {
        const symbolId = this.nextSymbolId++;
        this.symbolMap.set(token, symbolId);
        this.reverseMap.set(symbolId, token);
      }
      return this.symbolMap.get(token);
    });

    return {
      path: filePath,
      symbols,
      hash: this.hashContent(content),
    };
  }

  /**
   * Decompress symbolic representation back to original content
   */
  decompressFile(compressedData) {
    const tokens = compressedData.symbols.map(symbolId => {
      return this.reverseMap.get(symbolId) || `<UNKNOWN:${symbolId}>`;
    });

    return this.reconstructContent(tokens);
  }

  /**
   * Tokenize source code into processable units
   */
  tokenize(content) {
    const tokens = [];
    let current = '';
    let inString = false;
    let stringChar = null;
    let inComment = false;
    let commentType = null;

    for (let i = 0; i < content.length; i++) {
      const char = content[i];
      const nextChar = content[i + 1];

      // Handle strings
      if ((char === '"' || char === "'") && !inComment) {
        if (!inString) {
          if (current) {
            tokens.push(...this.tokenizeSegment(current));
            current = '';
          }
          inString = true;
          stringChar = char;
          current = char;
        } else if (char === stringChar && content[i - 1] !== '\\') {
          current += char;
          tokens.push(current);
          current = '';
          inString = false;
          stringChar = null;
        } else {
          current += char;
        }
        continue;
      }

      if (inString) {
        current += char;
        continue;
      }

      // Handle comments
      if (char === '/' && nextChar === '/' && !inComment) {
        if (current) {
          tokens.push(...this.tokenizeSegment(current));
          current = '';
        }
        inComment = true;
        commentType = 'line';
        current = '//';
        i++; // Skip next char
        continue;
      }

      if (char === '/' && nextChar === '*' && !inComment) {
        if (current) {
          tokens.push(...this.tokenizeSegment(current));
          current = '';
        }
        inComment = true;
        commentType = 'block';
        current = '/*';
        i++; // Skip next char
        continue;
      }

      if (inComment) {
        if (commentType === 'line' && char === '\n') {
          tokens.push(current);
          tokens.push('\n');
          current = '';
          inComment = false;
          commentType = null;
        } else if (commentType === 'block' && char === '*' && nextChar === '/') {
          current += '*/';
          tokens.push(current);
          current = '';
          inComment = false;
          commentType = null;
          i++; // Skip next char
        } else {
          current += char;
        }
        continue;
      }

      // Handle whitespace
      if (/\s/.test(char)) {
        if (current) {
          tokens.push(...this.tokenizeSegment(current));
          current = '';
        }
        if (char === '\n' || char === '\t') {
          tokens.push(char);
        } else {
          tokens.push(' ');
        }
        continue;
      }

      // Handle operators and delimiters
      const operators = ['(', ')', '{', '}', '[', ']', ',', '.', ';', '+', '-', '*', '/', '=', '<', '>', '!'];
      if (operators.includes(char)) {
        if (current) {
          tokens.push(...this.tokenizeSegment(current));
          current = '';
        }

        // Handle multi-char operators
        if ((char === '=' || char === '!' || char === '<' || char === '>') && nextChar === '=') {
          tokens.push(char + nextChar);
          i++; // Skip next char
        } else {
          tokens.push(char);
        }
        continue;
      }

      current += char;
    }

    if (current) {
      if (inString || inComment) {
        tokens.push(current);
      } else {
        tokens.push(...this.tokenizeSegment(current));
      }
    }

    return tokens;
  }

  /**
   * Tokenize a code segment (identifiers, keywords, numbers)
   */
  tokenizeSegment(segment) {
    segment = segment.trim();
    if (!segment) return [];

    // Check if it's a keyword
    if (this.symbolMap.has(segment)) {
      return [segment];
    }

    // Check if it's a number
    if (/^\d+(\.\d+)?$/.test(segment)) {
      return [segment];
    }

    // It's an identifier
    return [segment];
  }

  /**
   * Reconstruct content from tokens
   */
  reconstructContent(tokens) {
    let content = '';
    let prevToken = null;

    for (let i = 0; i < tokens.length; i++) {
      const token = tokens[i];

      // Handle newlines and tabs
      if (token === '\n' || token === '\t') {
        content += token;
        prevToken = token;
        continue;
      }

      // Add space between tokens (with exceptions)
      if (prevToken &&
          prevToken !== '\n' &&
          prevToken !== '\t' &&
          prevToken !== ' ' &&
          !this.isDelimiter(prevToken) &&
          !this.isDelimiter(token) &&
          token !== ' ') {
        content += ' ';
      }

      if (token !== ' ') {
        content += token;
      }

      prevToken = token;
    }

    return content;
  }

  /**
   * Check if token is a delimiter that doesn't need spacing
   */
  isDelimiter(token) {
    return ['(', ')', '{', '}', '[', ']', ',', '.', ';'].includes(token);
  }

  /**
   * Hash content for verification
   */
  hashContent(content) {
    return crypto.createHash('sha256').update(content).digest('hex');
  }

  /**
   * Compress entire directory recursively
   */
  compressDirectory(dirPath, options = {}) {
    const {
      includeHidden = false,
      gitAware = true,
      extensions = null, // null = all files
    } = options;

    const compressed = {
      root: dirPath,
      files: [],
      symbolDictionary: {},
      metadata: {
        timestamp: Date.now(),
        version: '1.0.0',
        tier: 5,
      },
    };

    // Build file list
    const files = this.scanDirectory(dirPath, includeHidden, gitAware, extensions);

    // Compress each file
    files.forEach(filePath => {
      try {
        const content = fs.readFileSync(filePath, 'utf8');
        const relativePath = path.relative(dirPath, filePath);
        const compressedFile = this.compressFile(relativePath, content);
        compressed.files.push(compressedFile);
      } catch (error) {
        console.warn(`Warning: Could not compress ${filePath}: ${error.message}`);
      }
    });

    // Export symbol dictionary
    this.symbolMap.forEach((id, token) => {
      compressed.symbolDictionary[id] = token;
    });

    return compressed;
  }

  /**
   * Scan directory for files
   */
  scanDirectory(dirPath, includeHidden, gitAware, extensions) {
    const files = [];
    const gitignorePatterns = gitAware ? this.loadGitignore(dirPath) : [];

    const scan = (currentPath) => {
      const entries = fs.readdirSync(currentPath, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(currentPath, entry.name);
        const relativePath = path.relative(dirPath, fullPath);

        // Skip hidden files if not included
        if (!includeHidden && entry.name.startsWith('.')) {
          continue;
        }

        // Skip .git directory
        if (entry.name === '.git') {
          continue;
        }

        // Check gitignore
        if (gitAware && this.isIgnored(relativePath, gitignorePatterns)) {
          continue;
        }

        if (entry.isDirectory()) {
          scan(fullPath);
        } else if (entry.isFile()) {
          // Check extension filter
          if (extensions === null || extensions.includes(path.extname(entry.name))) {
            files.push(fullPath);
          }
        }
      }
    };

    scan(dirPath);
    return files;
  }

  /**
   * Load .gitignore patterns
   */
  loadGitignore(dirPath) {
    const gitignorePath = path.join(dirPath, '.gitignore');
    if (!fs.existsSync(gitignorePath)) {
      return [];
    }

    const content = fs.readFileSync(gitignorePath, 'utf8');
    return content
      .split('\n')
      .map(line => line.trim())
      .filter(line => line && !line.startsWith('#'));
  }

  /**
   * Check if path matches gitignore patterns
   */
  isIgnored(filePath, patterns) {
    return patterns.some(pattern => {
      // Simple pattern matching (can be enhanced)
      const regex = new RegExp(
        '^' + pattern
          .replace(/\./g, '\\.')
          .replace(/\*/g, '.*')
          .replace(/\?/g, '.')
          + '$'
      );
      return regex.test(filePath);
    });
  }

  /**
   * Get compression statistics
   */
  getCompressionStats(original, compressed) {
    const originalSize = JSON.stringify(original).length;
    const compressedSize = JSON.stringify(compressed).length;
    const ratio = ((1 - compressedSize / originalSize) * 100).toFixed(2);

    return {
      originalSize,
      compressedSize,
      compressionRatio: ratio + '%',
      filesCompressed: compressed.files.length,
      symbolsUsed: Object.keys(compressed.symbolDictionary).length,
    };
  }
}

module.exports = SymbolicCompression;
