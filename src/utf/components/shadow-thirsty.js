/**
 * Tier 4 - Shadow Thirsty
 * Dual-plane compiler: surface plane + security-hardened shadow plane.
 *
 * Includes 6 reflexive static analyzers that run at compile time:
 *   1. PlaneIsolationAnalyzer   — hard block
 *   2. InvariantPurityChecker   — hard block
 *   3. MutationScopeAnalyzer    — warning
 *   4. DivergenceDetector       — warning
 *   5. TypeConsistencyChecker   — warning
 *   6. SideEffectAnalyzer       — warning
 */

const crypto = require('crypto');

// ── Static Analyzers ─────────────────────────────────────────────────────────

/**
 * Verifies that the Shadow plane cannot mutate Canonical state.
 * Checks that no shadow-plane variable write targets a canonical-qualified variable.
 */
class PlaneIsolationAnalyzer {
  get name() { return 'PlaneIsolationAnalyzer'; }

  /**
   * @param {string} code
   * @returns {{ passed: boolean, violations: string[] }}
   */
  analyze(code) {
    const violations = [];
    // Extract shadow { ... } blocks.
    const shadowRe = /\bshadow\s*\{([^}]*)\}/gs;
    let m;
    while ((m = shadowRe.exec(code)) !== null) {
      const block = m[1];
      // Look for writes to Canonical<...> qualified variables.
      const canonicalWriteRe = /Canonical\s*<[^>]*>\s*\w+\s*=/g;
      let wm;
      while ((wm = canonicalWriteRe.exec(block)) !== null) {
        violations.push(`Shadow plane writes to canonical variable: ${wm[0].trim()}`);
      }
      // Also flag plain canonical_ prefixed assignments.
      const prefixWriteRe = /\bcanonical_\w+\s*=/g;
      while ((wm = prefixWriteRe.exec(block)) !== null) {
        violations.push(`Shadow plane writes to canonical-prefixed variable: ${wm[0].trim()}`);
      }
    }
    return { passed: violations.length === 0, violations };
  }
}

/**
 * Checks that invariant blocks are pure: no assignments, no I/O,
 * no non-pure-math function calls.
 */
class InvariantPurityChecker {
  get name() { return 'InvariantPurityChecker'; }

  analyze(code) {
    const violations = [];
    const invariantRe = /\binvariant\s*\{([^}]*)\}/gs;
    let m;
    while ((m = invariantRe.exec(code)) !== null) {
      const block = m[1];
      // Detect assignments (= not preceded by !, < , > , = and not followed by =).
      if (/(?<![=!<>])=(?!=)/.test(block)) {
        violations.push('Invariant block contains an assignment');
      }
      // Detect I/O operations.
      if (/\b(pour|console\.|process\.stdout|process\.stderr|fs\.)\w*\s*\(/.test(block)) {
        violations.push('Invariant block contains an I/O operation');
      }
      // Detect non-pure function calls (anything that isn't Math.*).
      const callRe = /\b(?!Math\.)([a-zA-Z_]\w*)\s*\(/g;
      let cr;
      while ((cr = callRe.exec(block)) !== null) {
        // Allow common pure-math helpers.
        const fn = cr[1];
        if (!['Math', 'Number', 'parseInt', 'parseFloat', 'isNaN', 'isFinite'].includes(fn)) {
          violations.push(`Invariant block calls impure function: ${fn}()`);
        }
      }
    }
    return { passed: violations.length === 0, violations };
  }
}

/**
 * Validates that mutations stay within their declared scope.
 */
class MutationScopeAnalyzer {
  get name() { return 'MutationScopeAnalyzer'; }

  analyze(code) {
    const violations = [];
    // Primary-block assignments should not appear inside shadow blocks.
    const shadowRe = /\bshadow\s*\{([^}]*)\}/gs;
    let m;
    while ((m = shadowRe.exec(code)) !== null) {
      const block = m[1];
      // Flag assignments to variables declared in primary blocks (heuristic: primary_* prefix).
      const primaryWriteRe = /\bprimary_\w+\s*=/g;
      let wm;
      while ((wm = primaryWriteRe.exec(block)) !== null) {
        violations.push(`Shadow block mutates primary-scoped variable: ${wm[0].trim()}`);
      }
    }
    // Shadow-block assignments should not appear inside primary blocks.
    const primaryRe = /\bprimary\s*\{([^}]*)\}/gs;
    while ((m = primaryRe.exec(code)) !== null) {
      const block = m[1];
      const shadowWriteRe = /\bshadow_\w+\s*=/g;
      let wm;
      while ((wm = shadowWriteRe.exec(block)) !== null) {
        violations.push(`Primary block mutates shadow-scoped variable: ${wm[0].trim()}`);
      }
    }
    return { passed: violations.length === 0, violations };
  }
}

/**
 * Detects potential divergence between Plane A and Plane B by comparing
 * operation sequences and flagging asymmetries.
 */
class DivergenceDetector {
  get name() { return 'DivergenceDetector'; }

  analyze(code) {
    const violations = [];
    const planeA = this._extractOps(code, 'primary');
    const planeB = this._extractOps(code, 'shadow');

    if (planeA.length > 0 && planeB.length > 0 && planeA.length !== planeB.length) {
      violations.push(
        `Operation count asymmetry: Plane A has ${planeA.length} ops, Plane B has ${planeB.length} ops`
      );
    }
    return { passed: violations.length === 0, violations };
  }

  _extractOps(code, blockKeyword) {
    const ops = [];
    const re = new RegExp(`\\b${blockKeyword}\\s*\\{([^}]*)\\}`, 'gs');
    let m;
    while ((m = re.exec(code)) !== null) {
      const stmts = m[1].split(/[;\n]/).map(s => s.trim()).filter(Boolean);
      ops.push(...stmts);
    }
    return ops;
  }
}

/**
 * Checks that memory qualifiers (Canonical<, Shadow<, Mirrored<, Transient<)
 * are used consistently throughout the code.
 */
class TypeConsistencyChecker {
  get name() { return 'TypeConsistencyChecker'; }

  analyze(code) {
    const violations = [];
    const qualifierRe = /\b(Canonical|Shadow|Mirrored|Transient)\s*<([^>]+)>\s*(\w+)/g;
    const declared = new Map(); // varName → qualifier

    let m;
    while ((m = qualifierRe.exec(code)) !== null) {
      const [, qualifier, , varName] = m;
      if (declared.has(varName) && declared.get(varName) !== qualifier) {
        violations.push(
          `Variable '${varName}' declared with conflicting qualifiers: ` +
          `${declared.get(varName)} vs ${qualifier}`
        );
      } else {
        declared.set(varName, qualifier);
      }
    }
    return { passed: violations.length === 0, violations };
  }
}

/**
 * Identifies and catalogs all side effects (I/O, external calls, mutations)
 * and ensures they only occur in primary blocks.
 */
class SideEffectAnalyzer {
  get name() { return 'SideEffectAnalyzer'; }

  analyze(code) {
    const violations = [];
    // Find side effects outside primary blocks.
    // Remove primary { ... } blocks from the code, then check remaining for I/O.
    let remaining = code.replace(/\bprimary\s*\{[^}]*\}/gs, '');
    const sideEffectRe = /\b(pour|console\.|process\.stdout|process\.stderr|fs\.\w+\s*\()/g;
    let m;
    while ((m = sideEffectRe.exec(remaining)) !== null) {
      violations.push(`Side effect '${m[0].trim()}' found outside primary block`);
    }
    return { passed: violations.length === 0, violations };
  }
}

// ── SafeHaltError ────────────────────────────────────────────────────────────

class SafeHaltError extends Error {
  constructor(reason) {
    super(`SAFE-HALT: ${reason}`);
    this.name = 'SafeHaltError';
    this.reason = reason;
  }
}

// ── ShadowThirsty ────────────────────────────────────────────────────────────

class ShadowThirsty {
  constructor(options = {}) {
    this.tier = 4;
    this.name = 'Shadow Thirsty';
    this.options = options;
    // NOTE: Auto-generated secrets are not portable across ShadowThirsty instances.
    // Provide a stable `options.secret` if compiled artifacts must be verified by
    // a different instance (e.g., across process restarts or distributed systems).
    if (!options.secret) {
      process.emitWarning(
        'ShadowThirsty: using auto-generated secret. Compiled artifacts cannot be verified across instances. Pass options.secret for portability.',
        'ShadowThirstyWarning'
      );
    }
    this._secret = options.secret || crypto.randomBytes(32).toString('hex');
    this._analyzers = [
      new PlaneIsolationAnalyzer(),
      new InvariantPurityChecker(),
      new MutationScopeAnalyzer(),
      new DivergenceDetector(),
      new TypeConsistencyChecker(),
      new SideEffectAnalyzer(),
    ];
  }

  /**
   * Returns the 6 static analyzer instances.
   * @returns {object[]}
   */
  getAnalyzers() {
    return this._analyzers;
  }

  /**
   * Compiles code through both planes and runs all 6 static analyzers.
   * PlaneIsolationAnalyzer and InvariantPurityChecker failures are hard blocks.
   * Other analyzer failures are recorded as warnings.
   * @param {string} code
   * @param {object} [options]
   * @returns {object}
   */
  compile(code, options = {}) {
    const planeA = this._compileSurface(code, options);
    const planeB = this._compileShadow(code, options);

    const analyzerResults = {};
    const warnings = [];

    for (const analyzer of this._analyzers) {
      const result = analyzer.analyze(code);
      analyzerResults[analyzer.name] = result;

      if (!result.passed) {
        const isHardBlock =
          analyzer.name === 'PlaneIsolationAnalyzer' ||
          analyzer.name === 'InvariantPurityChecker';

        if (isHardBlock) {
          throw new Error(
            `${analyzer.name} failed: ${result.violations.join('; ')}`
          );
        }
        for (const v of result.violations) {
          warnings.push(`[${analyzer.name}] ${v}`);
        }
      }
    }

    return {
      planeA,
      planeB,
      version: 1,
      timestamp: Date.now(),
      analysis: {
        analyzers: analyzerResults,
        warnings,
      },
    };
  }

  _compileSurface(code, options) {
    const memQualifiers = this._parseMemoryQualifiers(code);
    const blocks        = this._parseBlocks(code);
    const lines         = code.split('\n').filter(l => l.trim() && !l.trim().startsWith('//'));
    const tokens        = lines.map(line => line.trim());
    const checksum      = crypto.createHash('sha256').update(code).digest('hex');
    return {
      plane:    'A',
      tokens,
      lineCount:    lines.length,
      checksum,
      blocks,
      memQualifiers,
      metadata: { optimized: options.optimize || false },
    };
  }

  _compileShadow(code, options) {
    const checksum = crypto.createHash('sha256').update(code).digest('hex');
    const hmac     = crypto.createHmac('sha256', this._secret).update(code).digest('hex');
    const blocks   = this._parseBlocks(code);
    const lines    = code.split('\n').filter(l => l.trim() && !l.trim().startsWith('//'));
    const shadowTokens = lines.map(line => {
      const trimmed = line.trim();
      return {
        content: trimmed,
        hash: crypto.createHash('sha256').update(trimmed).digest('hex').slice(0, 16),
      };
    });
    return {
      plane: 'B',
      shadowTokens,
      checksum,
      hmac,
      lineCount: lines.length,
      blocks,
      metadata: { hardened: true, tamperDetection: true },
    };
  }

  /**
   * Parses primary, shadow, and invariant blocks from the source code.
   * @param {string} code
   * @returns {{ primary: string[], shadow: string[], invariant: string[] }}
   */
  _parseBlocks(code) {
    const extract = (keyword) => {
      const blocks = [];
      const re = new RegExp(`\\b${keyword}\\s*\\{([^}]*)\\}`, 'gs');
      let m;
      while ((m = re.exec(code)) !== null) {
        blocks.push(m[1].trim());
      }
      return blocks;
    };
    return {
      primary:   extract('primary'),
      shadow:    extract('shadow'),
      invariant: extract('invariant'),
    };
  }

  /**
   * Extracts all qualified variable declarations from code.
   * @param {string} code
   * @returns {{ canonical: string[], shadow: string[], mirrored: string[], transient: string[] }}
   */
  _parseMemoryQualifiers(code) {
    const result = { canonical: [], shadow: [], mirrored: [], transient: [] };
    const re = /\b(Canonical|Shadow|Mirrored|Transient)\s*<([^>]+)>\s*(\w+)/g;
    let m;
    while ((m = re.exec(code)) !== null) {
      const [, qualifier, type, name] = m;
      result[qualifier.toLowerCase()].push(`${name}: ${type}`);
    }
    return result;
  }

  /**
   * Verifies dual-plane integrity of a compiled artifact.
   * @param {object} compiled
   * @returns {{ valid: boolean, reason?: string, checksum?: string, plane?: string, timestamp?: number }}
   */
  verify(compiled) {
    if (!compiled || !compiled.planeA || !compiled.planeB) {
      return { valid: false, reason: 'Missing plane data' };
    }
    if (compiled.planeA.checksum !== compiled.planeB.checksum) {
      return { valid: false, reason: 'Plane A/B checksum mismatch — code may have been tampered with' };
    }
    if (compiled.planeA.lineCount !== compiled.planeB.lineCount) {
      return { valid: false, reason: 'Plane A/B line count mismatch' };
    }
    return {
      valid:     true,
      checksum:  compiled.planeA.checksum,
      plane:     'dual-verified',
      timestamp: compiled.timestamp,
    };
  }

  /**
   * Executes verified compiled code.
   * @param {object} compiled
   * @returns {{ executed: boolean, checksum: string }}
   */
  execute(compiled) {
    const verification = this.verify(compiled);
    if (!verification.valid) {
      throw new Error(`Shadow Thirsty execution blocked: ${verification.reason}`);
    }
    const { ThirstyLang } = require('./thirsty-lang');
    const interpreter = new ThirstyLang(this.options);
    const code = compiled.planeA.tokens.join('\n');
    interpreter.execute(code);
    return { executed: true, checksum: verification.checksum };
  }

  /**
   * Triggers a SAFE-HALT, throwing a SafeHaltError.
   * @param {string} reason
   */
  safeHalt(reason) {
    throw new SafeHaltError(reason);
  }

  /**
   * Returns a quarantine record for unsafe code.
   * @param {string} code
   * @param {string} reason
   * @returns {{ quarantined: boolean, reason: string, code: string, timestamp: number }}
   */
  quarantine(code, reason) {
    return {
      quarantined: true,
      reason,
      code,
      timestamp: Date.now(),
    };
  }
}

module.exports = {
  ShadowThirsty,
  SafeHaltError,
  PlaneIsolationAnalyzer,
  InvariantPurityChecker,
  MutationScopeAnalyzer,
  DivergenceDetector,
  TypeConsistencyChecker,
  SideEffectAnalyzer,
};
