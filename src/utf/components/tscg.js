/**
 * Tier 5 - TSCG (Thirsty's Symbolic Compression Grammar)
 * Symbol table-based source compression for Thirsty-lang.
 * Compressed symbols use the format: §<id>
 */

// Minimum frequency and length thresholds for pattern learning
const MIN_TOKEN_FREQUENCY = 3;
const MIN_TOKEN_LENGTH = 5;
// Minimum pattern length for compression substitution
const MIN_PATTERN_LENGTH = 3;

class TSCG {
  constructor(options = {}) {
    this.tier = 5;
    this.name = 'TSCG';
    this.options = options;
    this._symbolTable = new Map();
    this._reverseTable = new Map();
    this._nextId = 1;
    this._initBuiltinSymbols();
  }

  _initBuiltinSymbols() {
    const builtins = [
      'drink ', 'pour ', 'glass ', 'fountain ', 'reservoir ',
      'return ', 'refill ', 'thirsty ', 'hydrated', 'parched',
      'quenched', 'this.', 'Math.', 'String.', 'true', 'false',
    ];
    for (const pattern of builtins) {
      this._registerSymbol(pattern);
    }
  }

  _registerSymbol(pattern) {
    if (this._symbolTable.has(pattern)) return;
    const id = this._nextId++;
    const sym = `§${id}`;
    this._symbolTable.set(pattern, sym);
    this._reverseTable.set(sym, pattern);
  }

  compress(source) {
    if (typeof source !== 'string') throw new TypeError('Source must be a string');

    this._learnPatterns(source);

    let compressed = source;
    const patterns = Array.from(this._symbolTable.keys())
      .sort((a, b) => b.length - a.length);

    for (const pattern of patterns) {
      if (pattern.length < MIN_PATTERN_LENGTH) continue;
      const sym = this._symbolTable.get(pattern);
      compressed = compressed.split(pattern).join(sym);
    }

    const ratio = source.length > 0
      ? ((1 - compressed.length / source.length) * 100).toFixed(1)
      : '0.0';

    return {
      compressed,
      originalLength: source.length,
      compressedLength: compressed.length,
      ratio: parseFloat(ratio),
      symbolCount: this._symbolTable.size,
    };
  }

  _learnPatterns(source) {
    const tokenRe = /\b[a-zA-Z_]\w*\b/g;
    const freq = new Map();
    let m;
    while ((m = tokenRe.exec(source)) !== null) {
      const tok = m[0];
      freq.set(tok, (freq.get(tok) || 0) + 1);
    }
    for (const [tok, count] of freq) {
      if (count >= MIN_TOKEN_FREQUENCY && tok.length >= MIN_TOKEN_LENGTH) {
        this._registerSymbol(tok);
      }
    }
  }

  decompress(input) {
    let source = typeof input === 'string' ? input : input.compressed;
    if (!source) throw new TypeError('Expected a compressed string or TSCG result object');

    const entries = Array.from(this._reverseTable.entries())
      .sort((a, b) => {
        const ia = parseInt(a[0].slice(1), 10);
        const ib = parseInt(b[0].slice(1), 10);
        return ib - ia;
      });

    for (const [sym, pattern] of entries) {
      source = source.split(sym).join(pattern);
    }
    return source;
  }

  getSymbolTable() {
    const table = {};
    for (const [pattern, sym] of this._symbolTable) {
      table[sym] = pattern;
    }
    return table;
  }

  addSymbol(pattern, sym) {
    if (!/^§\d+$/.test(sym)) throw new Error('Symbol must match §<number> format');
    this._symbolTable.set(pattern, sym);
    this._reverseTable.set(sym, pattern);
    return this;
  }

  reset() {
    this._symbolTable.clear();
    this._reverseTable.clear();
    this._nextId = 1;
    this._initBuiltinSymbols();
    return this;
  }
}

module.exports = { TSCG };
