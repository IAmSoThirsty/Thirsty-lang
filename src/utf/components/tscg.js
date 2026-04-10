/**
 * Tier 5 - TSCG (Thirsty's Symbolic Compression Grammar)
 * Symbol table-based source compression for Thirsty-lang.
 *
 * Two symbol namespaces coexist:
 *   • Governance symbols  — fixed format §XXX (canonical, stable across instances)
 *   • Thirsty-lang symbols — numeric format §N  (learned per-instance)
 *
 * The bijectivity guarantee holds because governance symbols use a fixed,
 * globally shared table while numeric IDs are tracked per instance.
 */

// Minimum frequency and length thresholds for pattern learning
const MIN_TOKEN_FREQUENCY = 3;
const MIN_TOKEN_LENGTH = 5;
// Minimum pattern length for compression substitution
const MIN_PATTERN_LENGTH = 3;

// ── Governance Semantic Dictionary ───────────────────────────────────────────
//
// Maps governance source patterns to their canonical §XXX compressed forms.
// Longer patterns listed first so they are substituted before shorter prefixes.
// All compressed forms use the fixed §XXX convention to guarantee bijectivity
// without sharing state between instances.

const GOVERNANCE_DICTIONARY = [
  // Canonical full pipeline — compresses the most common governance expression.
  ['COG → Δ_NT → SHD(v) → INV(I) ∧ CAP → QRM(3f+1,2f+1) → COM → ANC', '§GCPIPE'],
  // Parametric forms (longer, must precede bare keyword forms).
  ['QRM(3f+1,2f+1)', '§QRMf'],
  ['SHD(v)',         '§SHDv'],
  ['INV(I)',         '§INVi'],
  // Keyword forms.
  ['COG',  '§COG'],
  ['Δ_NT', '§DNT'],
  ['SHD',  '§SHD'],
  ['INV',  '§INV'],
  ['CAP',  '§CAP'],
  ['QRM',  '§QRM'],
  ['COM',  '§COM'],
  ['ANC',  '§ANC'],
  ['PRO',  '§PRO'],
  ['VER',  '§VER'],
  ['REJ',  '§REJ'],
  // Operator symbols.
  ['→',  '§ARR'],
  ['∧',  '§AND'],
  ['∨',  '§OR'],
  ['¬',  '§NOT'],
  ['⊕',  '§XOR'],
  ['⊢',  '§ENT'],
  ['⊨',  '§SAT'],
  ['∀',  '§ALL'],
  ['∃',  '§EXI'],
  ['Δ',  '§DEL'],
];

class TSCG {
  constructor(options = {}) {
    this.tier = 5;
    this.name = 'TSCG';
    this.options = options;
    this._symbolTable  = new Map(); // pattern → symbol
    this._reverseTable = new Map(); // symbol  → pattern
    this._nextId = 1;
    this._initGovernanceSymbols();
    this._initBuiltinSymbols();
  }

  /** Registers the canonical governance semantic dictionary. */
  _initGovernanceSymbols() {
    for (const [pattern, sym] of GOVERNANCE_DICTIONARY) {
      this._symbolTable.set(pattern, sym);
      this._reverseTable.set(sym, pattern);
    }
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
    const id  = this._nextId++;
    const sym = `§${id}`;
    this._symbolTable.set(pattern, sym);
    this._reverseTable.set(sym, pattern);
  }

  /**
   * Compresses a source string using the governance dictionary and
   * any learned patterns.
   * @param {string} source
   * @returns {{ compressed: string, originalLength: number, compressedLength: number, ratio: number, symbolCount: number }}
   */
  compress(source) {
    if (typeof source !== 'string') throw new TypeError('Source must be a string');

    this._learnPatterns(source);

    let compressed = source;
    // Sort patterns longest-first to avoid partial substitutions.
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
      originalLength:    source.length,
      compressedLength:  compressed.length,
      ratio:             parseFloat(ratio),
      symbolCount:       this._symbolTable.size,
    };
  }

  _learnPatterns(source) {
    const tokenRe = /\b[a-zA-Z_]\w*\b/g;
    const freq    = new Map();
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

  /**
   * Decompresses a previously compressed string or TSCG result object.
   * Handles both governance §XXX symbols and numeric §N symbols.
   * @param {string|object} input
   * @returns {string}
   */
  decompress(input) {
    let source = typeof input === 'string' ? input : input.compressed;
    if (!source) throw new TypeError('Expected a compressed string or TSCG result object');

    // Sort by symbol length descending — ensures longer symbols like §GCPIPE
    // are replaced before shorter overlapping ones like §COG.
    const entries = Array.from(this._reverseTable.entries())
      .sort((a, b) => b[0].length - a[0].length);

    for (const [sym, pattern] of entries) {
      source = source.split(sym).join(pattern);
    }
    return source;
  }

  /**
   * Compresses, then decompresses, proving lossless round-trip.
   * @param {string} source
   * @returns {{ valid: boolean, original: string, roundTripped: string }}
   */
  verify(source) {
    if (typeof source !== 'string') throw new TypeError('Source must be a string');
    const result      = this.compress(source);
    const roundTripped = this.decompress(result);
    return {
      valid:        roundTripped === source,
      original:     source,
      roundTripped,
    };
  }

  /**
   * Returns a plain object mapping each symbol to its original pattern.
   * @returns {object}
   */
  getSymbolTable() {
    const table = {};
    for (const [pattern, sym] of this._symbolTable) {
      table[sym] = pattern;
    }
    return table;
  }

  /**
   * Manually registers a symbol mapping.
   * Accepts both §N (numeric) and §XXX (governance) formats.
   * @param {string} pattern
   * @param {string} sym
   * @returns {TSCG}
   */
  addSymbol(pattern, sym) {
    if (!/^§[\w]+$/.test(sym)) {
      throw new Error('Symbol must match §<id> format (e.g. §42 or §COG)');
    }
    this._symbolTable.set(pattern, sym);
    this._reverseTable.set(sym, pattern);
    return this;
  }

  /** Resets all symbols and re-initialises the built-in tables. */
  reset() {
    this._symbolTable.clear();
    this._reverseTable.clear();
    this._nextId = 1;
    this._initGovernanceSymbols();
    this._initBuiltinSymbols();
    return this;
  }
}

module.exports = { TSCG, GOVERNANCE_DICTIONARY };
