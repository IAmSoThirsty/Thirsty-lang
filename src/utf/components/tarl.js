/**
 * Tier 3 - T.A.R.L. (Thirsty's Active Resistance Language)
 * JavaScript interface to the T.A.R.L. policy VM.
 *
 * Subsystems (available via getSubsystems()):
 *   1. TARLLexer            — tokenises T.A.R.L. rule source
 *   2. TARLParser           — produces an AST from the token stream
 *   3. TARLAST              — AST node factory functions
 *   4. TARLCompiler         — compiles AST to VM bytecode
 *   5. TARLVirtualMachine   — stack-based bytecode executor
 *   6. TARLJit              — caching JIT layer over the VM
 *   7. TARLStdLib           — built-in functions for rule conditions
 *   8. TARLDevTooling       — lint / format / LSP helpers
 */

const path = require('path');

// ── ResourceLimitError ───────────────────────────────────────────────────────

class ResourceLimitError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ResourceLimitError';
  }
}

// ── Subsystem 1: TARLLexer ───────────────────────────────────────────────────

const KEYWORDS = new Set(['rule', 'if', 'and', 'or', 'not', 'reject', 'allow', 'escalate']);

class TARLLexer {
  constructor(source) {
    this.source = source;
    this.pos    = 0;
    this.line   = 1;
    this.col    = 1;
  }

  /** Tokenises the entire source and returns an array of token objects. */
  tokenize() {
    const tokens = [];
    let tok;
    while ((tok = this.nextToken()).type !== 'EOF') {
      tokens.push(tok);
    }
    tokens.push(tok);
    return tokens;
  }

  /** Returns the next token from the source. */
  nextToken() {
    this._skipWhitespaceAndComments();

    if (this.pos >= this.source.length) {
      return this._tok('EOF', '');
    }

    const ch = this.source[this.pos];

    // Strings.
    if (ch === '"') return this._readString();

    // Numbers.
    if (/[0-9]/.test(ch)) return this._readNumber();

    // Two-character operators.
    const two = this.source.slice(this.pos, this.pos + 2);
    if (two === '==') return this._advance('EQUALS', '==', 2);
    if (two === '!=') return this._advance('NEQ',    '!=', 2);
    if (two === '<=') return this._advance('LTE',    '<=', 2);
    if (two === '>=') return this._advance('GTE',    '>=', 2);

    // Single-character tokens.
    const singles = {
      '(': 'LPAREN', ')': 'RPAREN',
      '{': 'LBRACE', '}': 'RBRACE',
      '<': 'LT',     '>': 'GT',
      ';': 'SEMICOLON', ',': 'COMMA', '.': 'DOT',
    };
    if (singles[ch]) return this._advance(singles[ch], ch, 1);

    // Identifiers and keywords.
    if (/[a-zA-Z_]/.test(ch)) return this._readIdentifier();

    // Unknown character — skip it.
    this._advance('UNKNOWN', ch, 1);
    return this.nextToken();
  }

  _skipWhitespaceAndComments() {
    while (this.pos < this.source.length) {
      const ch = this.source[this.pos];
      if (ch === '\n') { this.line++; this.col = 1; this.pos++; continue; }
      if (/\s/.test(ch)) { this.col++; this.pos++; continue; }
      // Single-line comments.
      if (this.source.slice(this.pos, this.pos + 2) === '//') {
        while (this.pos < this.source.length && this.source[this.pos] !== '\n') this.pos++;
        continue;
      }
      break;
    }
  }

  _readString() {
    const line = this.line;
    const col  = this.col;
    this.pos++; // skip opening "
    let value = '';
    while (this.pos < this.source.length && this.source[this.pos] !== '"') {
      if (this.source[this.pos] === '\\') {
        this.pos++;
        const esc = this.source[this.pos] || '';
        value += esc === 'n' ? '\n' : esc === 't' ? '\t' : esc;
      } else {
        value += this.source[this.pos];
      }
      this.pos++;
    }
    this.pos++; // skip closing "
    return { type: 'STRING', value, line, col };
  }

  _readNumber() {
    const line  = this.line;
    const col   = this.col;
    let   raw   = '';
    while (this.pos < this.source.length && /[0-9.]/.test(this.source[this.pos])) {
      raw += this.source[this.pos++];
    }
    return { type: 'NUMBER', value: raw.includes('.') ? parseFloat(raw) : parseInt(raw, 10), line, col };
  }

  _readIdentifier() {
    const line  = this.line;
    const col   = this.col;
    let   value = '';
    while (this.pos < this.source.length && /[a-zA-Z0-9_\-]/.test(this.source[this.pos])) {
      value += this.source[this.pos++];
    }
    const type = KEYWORDS.has(value.toLowerCase()) ? value.toUpperCase() : 'IDENTIFIER';
    return { type, value, line, col };
  }

  _advance(type, value, n) {
    const line = this.line;
    const col  = this.col;
    this.pos += n;
    this.col += n;
    return { type, value, line, col };
  }

  _tok(type, value) {
    return { type, value, line: this.line, col: this.col };
  }
}

// ── Subsystem 3: TARLAST (AST node factories) ────────────────────────────────

const TARLAST = {
  Program:    (rules)                  => ({ type: 'Program', rules }),
  Rule:       (name, conditions, actions) => ({ type: 'Rule', name, conditions, actions }),
  Condition:  (left, op, right)        => ({ type: 'Condition', left, op, right }),
  Action:     (type, message)          => ({ type: 'Action', actionType: type, message }),
  BinaryExpr: (op, left, right)        => ({ type: 'BinaryExpr', op, left, right }),
  MemberExpr: (obj, prop)              => ({ type: 'MemberExpr', obj, prop }),
  CallExpr:   (callee, args)           => ({ type: 'CallExpr', callee, args }),
  Literal:    (value)                  => ({ type: 'Literal', value }),
  Identifier: (name)                   => ({ type: 'Identifier', name }),
};

// ── Subsystem 2: TARLParser ──────────────────────────────────────────────────

class TARLParser {
  constructor(tokens) {
    this.tokens = tokens;
    this.pos    = 0;
  }

  /** Parses the full token stream and returns a Program AST node. */
  parse() {
    const rules = [];
    while (!this._atEnd()) {
      if (this._peek().type === 'RULE') {
        rules.push(this.parseRule());
      } else {
        this._advance(); // skip unexpected tokens at top level
      }
    }
    return TARLAST.Program(rules);
  }

  /** Parses a single rule definition. */
  parseRule() {
    this._expect('RULE');
    const name = this._expect('IDENTIFIER').value;
    this._expect('LBRACE');
    const conditions = [];
    const actions    = [];
    while (!this._atEnd() && this._peek().type !== 'RBRACE') {
      if (this._peek().type === 'IF') {
        const { cond, act } = this._parseIfBlock();
        conditions.push(cond);
        actions.push(...act);
      } else {
        this._advance();
      }
    }
    this._expect('RBRACE');
    return TARLAST.Rule(name, conditions, actions);
  }

  /** Parses an if (...) { ... } block. */
  _parseIfBlock() {
    this._expect('IF');
    this._expect('LPAREN');
    const cond = this.parseCondition();
    this._expect('RPAREN');
    this._expect('LBRACE');
    const act = [];
    while (!this._atEnd() && this._peek().type !== 'RBRACE') {
      act.push(this.parseAction());
    }
    this._expect('RBRACE');
    return { cond, act };
  }

  /**
   * Parses a condition expression supporting AND / OR / NOT and
   * comparison operators.
   */
  parseCondition() {
    return this._parseOr();
  }

  _parseOr() {
    let left = this._parseAnd();
    while (!this._atEnd() && this._peek().type === 'OR') {
      this._advance();
      const right = this._parseAnd();
      left = TARLAST.BinaryExpr('or', left, right);
    }
    return left;
  }

  _parseAnd() {
    let left = this._parseNot();
    while (!this._atEnd() && this._peek().type === 'AND') {
      this._advance();
      const right = this._parseNot();
      left = TARLAST.BinaryExpr('and', left, right);
    }
    return left;
  }

  _parseNot() {
    if (!this._atEnd() && this._peek().type === 'NOT') {
      this._advance();
      const operand = this._parseComparison();
      return TARLAST.BinaryExpr('not', operand, null);
    }
    return this._parseComparison();
  }

  _parseComparison() {
    const left = this._parsePrimary();
    const opTypes = ['EQUALS', 'NEQ', 'LT', 'GT', 'LTE', 'GTE'];
    if (!this._atEnd() && opTypes.includes(this._peek().type)) {
      const op    = this._advance().value;
      const right = this._parsePrimary();
      return TARLAST.Condition(left, op, right);
    }
    return left;
  }

  _parsePrimary() {
    if (this._atEnd()) return TARLAST.Literal(null);

    const tok = this._peek();

    if (tok.type === 'LPAREN') {
      this._advance();
      const expr = this.parseCondition();
      this._expect('RPAREN');
      return expr;
    }

    if (tok.type === 'STRING') {
      this._advance();
      return TARLAST.Literal(tok.value);
    }

    if (tok.type === 'NUMBER') {
      this._advance();
      return TARLAST.Literal(tok.value);
    }

    if (tok.type === 'IDENTIFIER') {
      this._advance();
      // Member expression: foo.bar.baz
      if (!this._atEnd() && this._peek().type === 'DOT') {
        let obj = tok.value;
        while (!this._atEnd() && this._peek().type === 'DOT') {
          this._advance(); // consume '.'
          const prop = this._advance().value;
          obj = `${obj}.${prop}`;
        }
        // Call expression: foo.bar(...)
        if (!this._atEnd() && this._peek().type === 'LPAREN') {
          const args = this._parseArgs();
          return TARLAST.CallExpr(obj, args);
        }
        return TARLAST.Identifier(obj);
      }
      // Call expression: foo(...)
      if (!this._atEnd() && this._peek().type === 'LPAREN') {
        const args = this._parseArgs();
        return TARLAST.CallExpr(tok.value, args);
      }
      return TARLAST.Identifier(tok.value);
    }

    // Fallback: consume and return null literal.
    this._advance();
    return TARLAST.Literal(null);
  }

  _parseArgs() {
    this._expect('LPAREN');
    const args = [];
    while (!this._atEnd() && this._peek().type !== 'RPAREN') {
      args.push(this._parsePrimary());
      if (!this._atEnd() && this._peek().type === 'COMMA') this._advance();
    }
    this._expect('RPAREN');
    return args;
  }

  /** Parses an action statement: allow|reject|escalate("message"); */
  parseAction() {
    const tok = this._peek();
    const actionKeywords = ['ALLOW', 'REJECT', 'ESCALATE'];
    if (actionKeywords.includes(tok.type)) {
      const actionType = tok.value.toLowerCase();
      this._advance();
      this._expect('LPAREN');
      let message = '';
      if (!this._atEnd() && this._peek().type === 'STRING') {
        message = this._advance().value;
      }
      this._expect('RPAREN');
      if (!this._atEnd() && this._peek().type === 'SEMICOLON') this._advance();
      return TARLAST.Action(actionType, message);
    }
    // Unexpected token — skip it.
    this._advance();
    return null;
  }

  _peek()    { return this.tokens[this.pos] || { type: 'EOF', value: '' }; }
  _advance() { return this.tokens[this.pos++] || { type: 'EOF', value: '' }; }
  _atEnd()   { return this.pos >= this.tokens.length || this._peek().type === 'EOF'; }

  _expect(type) {
    const tok = this._advance();
    if (tok.type !== type) {
      throw new Error(`TARLParser: expected ${type} but got ${tok.type} ('${tok.value}') at ${tok.line}:${tok.col}`);
    }
    return tok;
  }
}

// ── Subsystem 4: TARLCompiler ────────────────────────────────────────────────

class TARLCompiler {
  constructor() {
    this._bytecode = [];
    this._labels   = {};
    this._patches  = []; // [{index, label}]
  }

  /**
   * Compiles a Program AST to bytecode.
   * @param {object} ast
   * @returns {{ bytecode: object[], labels: object }}
   */
  compile(ast) {
    this._bytecode = [];
    this._labels   = {};
    this._patches  = [];

    if (ast.type !== 'Program') throw new Error('TARLCompiler: expected Program node');

    for (const rule of ast.rules) {
      this._compileRule(rule);
    }

    this._resolvePatches();
    return { bytecode: this._bytecode, labels: this._labels };
  }

  _compileRule(rule) {
    const startLabel = `rule_${rule.name}_start`;
    const endLabel   = `rule_${rule.name}_end`;

    this._label(startLabel);
    this._emit({ op: 'RULE_START', name: rule.name });

    for (let i = 0; i < rule.conditions.length; i++) {
      const actionList = rule.actions.slice(i, i + 1);
      const cond = rule.conditions[i];
      const skipLabel = `rule_${rule.name}_skip_${i}`;
      this._compileCondition(cond);
      this._emitJumpIfFalse(skipLabel);
      for (const action of actionList) {
        if (action) this._compileAction(action);
      }
      this._label(skipLabel);
    }

    this._label(endLabel);
    this._emit({ op: 'RULE_END', name: rule.name });
  }

  _compileCondition(node) {
    if (!node) { this._emit({ op: 'LOAD_CONST', value: true }); return; }

    switch (node.type) {
      case 'Condition':
        this._compileExpr(node.left);
        this._compileExpr(node.right);
        this._emit({ op: 'COMPARE', operator: node.op });
        break;
      case 'BinaryExpr':
        if (node.op === 'and') {
          this._compileCondition(node.left);
          this._compileCondition(node.right);
          this._emit({ op: 'COMPARE', operator: 'and' });
        } else if (node.op === 'or') {
          this._compileCondition(node.left);
          this._compileCondition(node.right);
          this._emit({ op: 'COMPARE', operator: 'or' });
        } else if (node.op === 'not') {
          this._compileCondition(node.left);
          this._emit({ op: 'COMPARE', operator: 'not' });
        } else {
          this._compileExpr(node);
        }
        break;
      default:
        this._compileExpr(node);
    }
  }

  _compileExpr(node) {
    if (!node) { this._emit({ op: 'LOAD_CONST', value: null }); return; }

    switch (node.type) {
      case 'Literal':
        this._emit({ op: 'LOAD_CONST', value: node.value });
        break;
      case 'Identifier':
        this._emit({ op: 'LOAD_FIELD', field: node.name });
        break;
      case 'MemberExpr':
        this._emit({ op: 'LOAD_FIELD', field: `${node.obj}.${node.prop}` });
        break;
      case 'CallExpr':
        for (const arg of node.args) this._compileExpr(arg);
        this._emit({ op: 'CALL_STDLIB', fn: node.callee, argc: node.args.length });
        break;
      default:
        this._emit({ op: 'LOAD_CONST', value: null });
    }
  }

  _compileAction(action) {
    this._emit({ op: 'CALL_ACTION', actionType: action.actionType, message: action.message });
  }

  _emit(instr) {
    this._bytecode.push(instr);
    return this._bytecode.length - 1;
  }

  _label(name) {
    this._labels[name] = this._bytecode.length;
  }

  _emitJumpIfFalse(label) {
    const idx = this._emit({ op: 'JUMP_IF_FALSE', target: -1, _label: label });
    this._patches.push({ index: idx, label });
  }

  _resolvePatches() {
    for (const { index, label } of this._patches) {
      if (this._labels[label] !== undefined) {
        this._bytecode[index].target = this._labels[label];
      }
    }
  }
}

// ── Subsystem 5: TARLVirtualMachine ─────────────────────────────────────────

class TARLVirtualMachine {
  constructor(options = {}) {
    this.options = options;
    this._stack   = [];
    this._verdict = null;
    this._trace   = [];
  }

  /**
   * Executes compiled bytecode against a context object.
   * @param {object[]} bytecode
   * @param {object}   context
   * @returns {{ verdict: string, reason?: string, trace: object[] }}
   */
  execute(bytecode, context) {
    this.reset();
    const maxInstructions = this.options.maxInstructions || 10000;
    const maxStackDepth   = this.options.maxStackDepth   || 256;
    let   pc = 0;
    let   instructionCount = 0;

    while (pc < bytecode.length) {
      if (++instructionCount > maxInstructions) {
        throw new ResourceLimitError(`Instruction limit (${maxInstructions}) exceeded`);
      }
      if (this._stack.length > maxStackDepth) {
        throw new ResourceLimitError(`Stack depth limit (${maxStackDepth}) exceeded`);
      }

      const instr = bytecode[pc];
      this._trace.push({ pc, op: instr.op });

      switch (instr.op) {
        case 'RULE_START':
          pc++;
          break;

        case 'RULE_END':
          pc++;
          break;

        case 'LOAD_CONST':
          this._stack.push(instr.value);
          pc++;
          break;

        case 'LOAD_FIELD': {
          const parts = instr.field.split('.');
          let   val   = context;
          for (const p of parts) {
            val = val != null ? val[p] : undefined;
          }
          this._stack.push(val);
          pc++;
          break;
        }

        case 'COMPARE': {
          const op = instr.operator;
          if (op === 'not') {
            const a = this._pop();
            this._stack.push(!a);
          } else if (op === 'and') {
            const b = this._pop(), a = this._pop();
            this._stack.push(Boolean(a) && Boolean(b));
          } else if (op === 'or') {
            const b = this._pop(), a = this._pop();
            this._stack.push(Boolean(a) || Boolean(b));
          } else {
            const right = this._pop(), left = this._pop();
            this._stack.push(this._compare(left, op, right));
          }
          pc++;
          break;
        }

        case 'JUMP_IF_FALSE': {
          const cond = this._pop();
          pc = !cond ? instr.target : pc + 1;
          break;
        }

        case 'JUMP':
          pc = instr.target;
          break;

        case 'CALL_ACTION': {
          const actionType = instr.actionType;
          if (actionType === 'reject') {
            this._verdict = { verdict: 'DENY',  reason: instr.message };
          } else if (actionType === 'escalate') {
            this._verdict = { verdict: 'ESCALATE', reason: instr.message };
          } else {
            this._verdict = { verdict: 'ALLOW', reason: instr.message };
          }
          pc++;
          break;
        }

        case 'CALL_STDLIB': {
          const args = [];
          for (let i = 0; i < instr.argc; i++) args.unshift(this._pop());
          const fn = TARLStdLib[instr.fn];
          this._stack.push(fn ? fn(...args) : undefined);
          pc++;
          break;
        }

        default:
          pc++;
      }
    }

    return this._verdict || { verdict: 'ALLOW', trace: this._trace };
  }

  reset() {
    this._stack   = [];
    this._verdict = null;
    this._trace   = [];
  }

  _pop() {
    return this._stack.length > 0 ? this._stack.pop() : undefined;
  }

  _compare(left, op, right) {
    switch (op) {
      case '==':  return left == right;   // eslint-disable-line eqeqeq
      case '!=':  return left != right;   // eslint-disable-line eqeqeq
      case '<':   return left <  right;
      case '>':   return left >  right;
      case '<=':  return left <= right;
      case '>=':  return left >= right;
      default:    return false;
    }
  }
}

// ── Subsystem 7: TARLStdLib ──────────────────────────────────────────────────

const TARLStdLib = {
  // String operations
  contains:     (haystack, needle)  => String(haystack).includes(String(needle)),
  startsWith:   (str, prefix)       => String(str).startsWith(String(prefix)),
  endsWith:     (str, suffix)       => String(str).endsWith(String(suffix)),
  matches:      (str, pattern)      => new RegExp(pattern).test(String(str)),
  // Collection operations
  includes:     (arr, item)         => Array.isArray(arr) && arr.includes(item),
  length:       (val)               => val == null ? 0 : (val.length || 0),
  // Security helpers
  isSafe:       (val)               => typeof val === 'string' && !/[<>"'`]/.test(val),
  isValidUrl:   (url)               => { try { new URL(url); return true; } catch { return false; } },
  isPrivateIp:  (ip)                => /^(10\.|172\.(1[6-9]|2\d|3[01])\.|192\.168\.)/.test(String(ip)),
  // Type checks
  isString:     (v)                 => typeof v === 'string',
  isNumber:     (v)                 => typeof v === 'number',
  isArray:      (v)                 => Array.isArray(v),
};

// ── Subsystem 6: TARLJit ─────────────────────────────────────────────────────

class TARLJit {
  constructor(vm) {
    this.vm        = vm;
    this._cache    = new Map(); // ruleName → { bytecode, hits, fn }
    this.threshold = 5;
  }

  /**
   * Checks the cache; JIT-compiles a fast-path after `threshold` calls.
   * @param {{ name: string, bytecode: object[] }} rule
   * @param {object} context
   * @returns {object} verdict
   */
  compile(rule, context) {
    const key = rule.name;
    if (!this._cache.has(key)) {
      this._cache.set(key, { bytecode: rule.bytecode, hits: 0, fn: null });
    }
    const cached = this._cache.get(key);
    cached.hits++;

    if (cached.hits >= this.threshold && !cached.fn) {
      const bytecode = cached.bytecode;
      const vm       = this.vm;
      // JIT-compile: wrap in a fast-path closure that skips cache lookup.
      cached.fn = (ctx) => { vm.reset(); return vm.execute(bytecode, ctx); };
    }

    if (cached.fn) return cached.fn(context);
    return this.vm.execute(cached.bytecode, context);
  }

  /**
   * Pre-compiles frequently-used rules to trigger JIT after warmup.
   * @param {Array<{ name: string, bytecode: object[] }>} rules
   */
  warmup(rules) {
    for (const rule of rules) {
      for (let i = 0; i < this.threshold; i++) {
        this.compile(rule, {});
      }
    }
  }

  /** Returns per-rule JIT statistics. */
  getStats() {
    const stats = {};
    for (const [name, entry] of this._cache) {
      stats[name] = { hits: entry.hits, jitCompiled: !!entry.fn };
    }
    return stats;
  }
}

// ── Subsystem 8: TARLDevTooling ───────────────────────────────────────────────

class TARLDevTooling {
  constructor() {}

  /**
   * Lints TARL source and returns errors and warnings.
   * @param {string} source
   * @returns {{ errors: object[], warnings: object[] }}
   */
  lint(source) {
    const errors   = [];
    const warnings = [];

    const openBraces  = (source.match(/\{/g) || []).length;
    const closeBraces = (source.match(/\}/g) || []).length;
    if (openBraces !== closeBraces) {
      errors.push({ message: 'Unbalanced braces', line: 1 });
    }

    const openParens  = (source.match(/\(/g) || []).length;
    const closeParens = (source.match(/\)/g) || []).length;
    if (openParens !== closeParens) {
      errors.push({ message: 'Unbalanced parentheses', line: 1 });
    }

    if (!/\brule\s/.test(source)) {
      warnings.push({ message: 'No rules defined', line: 1 });
    }

    return { errors, warnings };
  }

  /**
   * Returns a consistently indented version of the source.
   * @param {string} source
   * @returns {string}
   */
  format(source) {
    let indent = 0;
    return source.split('\n').map(line => {
      const t = line.trim();
      if (!t) return '';
      if (t === '}') indent = Math.max(0, indent - 1);
      const out = '  '.repeat(indent) + t;
      if (t.endsWith('{')) indent++;
      return out;
    }).join('\n');
  }

  /**
   * Returns a human-readable explanation for a rule in the given context.
   * @param {string} ruleName
   * @param {object} context
   * @returns {string}
   */
  explain(ruleName, context) {
    return `Rule '${ruleName}' will be evaluated against context: ${JSON.stringify(context)}`;
  }

  /**
   * Returns an execution trace for the given bytecode + context.
   * @param {TARLVirtualMachine} vm
   * @param {object[]} bytecode
   * @param {object} context
   * @returns {object[]}
   */
  trace(vm, bytecode, context) {
    const tracer   = [];
    const original = vm.execute.bind(vm);
    // Re-execute and collect trace.
    vm.reset();
    const result = vm.execute(bytecode, context);
    for (const entry of vm._trace) {
      tracer.push({ ...entry, instr: bytecode[entry.pc] });
    }
    return tracer;
  }

  /**
   * Returns LSP hover information for a position in the source.
   * @param {string} source
   * @param {number} line
   * @param {number} col
   * @returns {{ word: string, docs: string }}
   */
  lspHover(source, line, col) {
    const lines      = source.split('\n');
    const targetLine = lines[line] || '';
    const word       = (targetLine.slice(col).match(/^\w+/) || [''])[0];
    const docs = {
      rule:     'Defines a TARL policy rule',
      if:       'Conditional check within a rule',
      reject:   'Deny the evaluated request',
      allow:    'Allow the evaluated request',
      escalate: 'Escalate to a higher-authority policy',
      and:      'Logical AND of two conditions',
      or:       'Logical OR of two conditions',
      not:      'Logical NOT of a condition',
    };
    return { word, docs: docs[word] || `TARL identifier: ${word}` };
  }

  /**
   * Returns LSP completion items at the given position.
   * @param {string} source
   * @param {number} line
   * @param {number} col
   * @returns {object[]}
   */
  lspComplete(source, line, col) {
    return [
      { label: 'rule',     kind: 'keyword', detail: 'Define a TARL policy rule' },
      { label: 'if',       kind: 'keyword', detail: 'Conditional check' },
      { label: 'reject',   kind: 'keyword', detail: 'Deny action' },
      { label: 'allow',    kind: 'keyword', detail: 'Allow action' },
      { label: 'escalate', kind: 'keyword', detail: 'Escalate action' },
      { label: 'and',      kind: 'keyword', detail: 'Logical AND' },
      { label: 'or',       kind: 'keyword', detail: 'Logical OR' },
      { label: 'not',      kind: 'keyword', detail: 'Logical NOT' },
    ];
  }
}

// ── Main TARL Class ───────────────────────────────────────────────────────────

class TARL {
  constructor(options = {}) {
    this.tier    = 3;
    this.name    = 'T.A.R.L.';
    this.options = options;
    this.policies = new Map();
    this.metrics  = {
      evaluations:    0,
      allowed:        0,
      denied:         0,
      errors:         0,
      totalLatencyMs: 0,
    };
    this._bridge           = null;
    this._bridgeAvailable  = false;
    this._rateLimitState   = new Map();
    this._compiledRules    = new Map(); // name → { bytecode, labels }
    this._threatLog        = [];

    // Subsystem instances.
    this._vm       = new TARLVirtualMachine({
      maxStackDepth:   options.maxStackDepth   || 256,
      maxInstructions: options.maxInstructions || 10000,
    });
    this._compiler = new TARLCompiler();
    this._jit      = new TARLJit(this._vm);
    this._devTools = new TARLDevTooling();

    this._registerBuiltinPolicies();
  }

  _registerBuiltinPolicies() {
    this.policies.set('input-sanitization', {
      name: 'input-sanitization',
      description: 'Sanitize and validate all inputs',
      evaluate: (context) => {
        const { input } = context;
        if (input === undefined || input === null) {
          return { verdict: 'DENY', reason: 'Input is null or undefined' };
        }
        if (typeof input === 'string') {
          const dangerous = /<script|eval\s*\(|__proto__|constructor\s*\[/i;
          if (dangerous.test(input)) {
            return { verdict: 'DENY', reason: 'Potentially dangerous input detected' };
          }
        }
        return { verdict: 'ALLOW', reason: 'Input passed sanitization check' };
      },
    });

    this.policies.set('rate-limiting', {
      name: 'rate-limiting',
      description: 'Enforce rate limits on operations',
      evaluate: (context) => {
        const key      = context.key      || 'default';
        const limit    = context.limit    || 100;
        const windowMs = context.windowMs || 60000;
        const now      = Date.now();
        const state    = this._rateLimitState.get(key) || { count: 0, windowStart: now };
        if (now - state.windowStart > windowMs) { state.count = 0; state.windowStart = now; }
        state.count++;
        this._rateLimitState.set(key, state);
        if (state.count > limit) {
          return { verdict: 'DENY', reason: `Rate limit exceeded: ${state.count}/${limit} in window` };
        }
        return { verdict: 'ALLOW', reason: `Request ${state.count}/${limit} in current window` };
      },
    });

    this.policies.set('access-control', {
      name: 'access-control',
      description: 'Enforce access control rules',
      evaluate: (context) => {
        const { role, resource, action } = context;
        if (!role)     return { verdict: 'DENY', reason: 'No role specified' };
        if (!resource) return { verdict: 'DENY', reason: 'No resource specified' };
        const acl = {
          admin: { read: true, write: true,  execute: true,  delete: true  },
          user:  { read: true, write: true,  execute: true,  delete: false },
          guest: { read: true, write: false, execute: false, delete: false },
        };
        const permissions = acl[role] || acl['guest'];
        const act = action || 'read';
        if (permissions[act]) {
          return { verdict: 'ALLOW', reason: `Role '${role}' has '${act}' permission on '${resource}'` };
        }
        return { verdict: 'DENY', reason: `Role '${role}' lacks '${act}' permission on '${resource}'` };
      },
    });
  }

  async _tryInitBridge() {
    if (this._bridge !== null) return;
    try {
      const { SecurityBridge } = require(path.join(__dirname, '..', '..', 'security', 'bridge'));
      this._bridge = new SecurityBridge(this.options);
      await this._bridge.initialize();
      this._bridgeAvailable = true;
    } catch (e) {
      this._bridge          = null;
      this._bridgeAvailable = false;
    }
  }

  /**
   * Evaluates all policies (including any compiled TARL rules) against the
   * given context. Returns the first DENY/ESCALATE verdict encountered, or
   * ALLOW if all policies pass.
   * @param {object} context
   * @returns {Promise<{ verdict: string, policy?: string, reason?: string, results: object[] }>}
   */
  async evaluate(context) {
    const start = Date.now();
    this.metrics.evaluations++;
    this._cerberusHook('evaluate', context);
    try {
      const results = [];

      // Run standard policies.
      for (const [name, policy] of this.policies) {
        const result = await Promise.resolve(policy.evaluate(context));
        results.push({ policy: name, ...result });
        if (result.verdict === 'DENY') {
          this._cerberusHook('deny', { policy: name, reason: result.reason });
          this.metrics.denied++;
          this.metrics.totalLatencyMs += Date.now() - start;
          return { verdict: 'DENY', policy: name, reason: result.reason, results };
        }
      }

      // Run compiled TARL bytecode rules.
      for (const [name, compiled] of this._compiledRules) {
        try {
          const verdict = this._vm.execute(compiled.bytecode, context);
          results.push({ policy: name, ...verdict });
          if (verdict.verdict === 'DENY' || verdict.verdict === 'ESCALATE') {
            this._cerberusHook(verdict.verdict.toLowerCase(), { policy: name, reason: verdict.reason });
            this.metrics.denied++;
            this.metrics.totalLatencyMs += Date.now() - start;
            return { verdict: verdict.verdict, policy: name, reason: verdict.reason, results };
          }
        } catch (e) {
          if (e instanceof ResourceLimitError) {
            this._cerberusHook('resource_limit', { policy: name, error: e.message });
          }
          results.push({ policy: name, verdict: 'ERROR', reason: e.message });
        }
      }

      this.metrics.allowed++;
      this.metrics.totalLatencyMs += Date.now() - start;
      return { verdict: 'ALLOW', results };
    } catch (err) {
      this.metrics.errors++;
      this.metrics.totalLatencyMs += Date.now() - start;
      return { verdict: 'DENY', reason: `Policy evaluation error: ${err.message}` };
    }
  }

  /**
   * Parses TARL rule source and registers it as a compiled policy rule.
   * @param {string} source — complete TARL rule syntax
   * @returns {TARL}
   */
  parseRule(source) {
    const tokens  = new TARLLexer(source).tokenize();
    const ast     = new TARLParser(tokens).parse();
    const compiled = this._compiler.compile(ast);
    for (const rule of ast.rules) {
      this._compiledRules.set(rule.name, compiled);
    }
    return this;
  }

  /**
   * Parses a TARL rule and registers it as a named policy.
   * @param {string} name
   * @param {string} source
   * @returns {TARL}
   */
  addRuleFromSource(name, source) {
    const tokens   = new TARLLexer(source).tokenize();
    const ast      = new TARLParser(tokens).parse();
    const compiled = this._compiler.compile(ast);
    this._compiledRules.set(name, compiled);
    this.policies.set(name, {
      name,
      evaluate: (ctx) => {
        try {
          const vm = new TARLVirtualMachine(this.options);
          return vm.execute(compiled.bytecode, ctx);
        } catch (e) {
          return { verdict: 'DENY', reason: e.message };
        }
      },
    });
    return this;
  }

  /**
   * Parses a full TARL program source and returns compiled bytecode.
   * @param {string} source
   * @returns {{ bytecode: object[], labels: object, ast: object }}
   */
  compile(source) {
    const tokens  = new TARLLexer(source).tokenize();
    const ast     = new TARLParser(tokens).parse();
    const result  = this._compiler.compile(ast);
    return { ...result, ast };
  }

  addPolicy(name, ruleFn) {
    if (typeof name !== 'string') throw new TypeError('Policy name must be a string');
    if (typeof ruleFn !== 'function') throw new TypeError('Policy rule must be a function');
    this.policies.set(name, { name, evaluate: ruleFn });
    return this;
  }

  removePolicy(name) {
    this.policies.delete(name);
    return this;
  }

  getMetrics() {
    return {
      ...this.metrics,
      avgLatencyMs: this.metrics.evaluations > 0
        ? this.metrics.totalLatencyMs / this.metrics.evaluations
        : 0,
      policyCount: this.policies.size,
    };
  }

  listPolicies() {
    return Array.from(this.policies.keys());
  }

  /**
   * Returns all 8 subsystem instances as a named object.
   * @returns {object}
   */
  getSubsystems() {
    return {
      TARLLexer:          TARLLexer,
      TARLParser:         TARLParser,
      TARLAST:            TARLAST,
      TARLCompiler:       this._compiler,
      TARLVirtualMachine: this._vm,
      TARLJit:            this._jit,
      TARLStdLib:         TARLStdLib,
      TARLDevTooling:     this._devTools,
    };
  }

  /**
   * Hook for the Cerberus threat detection framework.
   * @param {'evaluate'|'deny'|'escalate'|'resource_limit'} event
   * @param {object} context
   */
  _cerberusHook(event, context) {
    if (this.options.cerberus) {
      this.options.cerberus.emit(event, { ...context, source: 'T.A.R.L.' });
    }
    if (event === 'deny' || event === 'escalate' || event === 'resource_limit') {
      this._threatLog.push({ event, context, timestamp: Date.now() });
    }
  }
}

module.exports = {
  TARL,
  TARLLexer,
  TARLParser,
  TARLAST,
  TARLCompiler,
  TARLVirtualMachine,
  TARLJit,
  TARLStdLib,
  TARLDevTooling,
  ResourceLimitError,
};
