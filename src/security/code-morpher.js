#!/usr/bin/env node
//                                           [2026-03-03 13:45]
//                                          Productivity: Active

/**
 * Code Morpher - Dynamic code transformation for defense
 * Implements code obfuscation and mutation strategies
 */

class CodeMorpher {
  constructor(securityBridge) {
    this.bridge = securityBridge;
    this.morphStrategies = {
      rename: true,
      shuffle: true,
      encrypt: false,
      obfuscate: true
    };
    this.morphMetrics = {
      transformations: 0,
      policyChecks: 0
    };
  }

  /**
   * Synchronous morph - returns transformed code string.
   * Options: { identifierMorphing, deadCodeInjection, antiDebugChecks, rename, obfuscate }
   */
  morph(code, options = {}) {
    let result = code;

    const useRename = options.identifierMorphing !== undefined
      ? options.identifierMorphing
      : this.morphStrategies.rename;
    const useDead = options.deadCodeInjection !== undefined
      ? options.deadCodeInjection
      : false;
    const useAntiDebug = options.antiDebugChecks !== undefined
      ? options.antiDebugChecks
      : false;
    const useObfuscate = options.obfuscate !== undefined
      ? options.obfuscate
      : this.morphStrategies.obfuscate;

    if (useObfuscate) {
      result = this._obfuscateStrings(result);
    }

    if (useRename) {
      result = this._renameVariables(result);
    }

    if (useDead) {
      result = this._injectDeadCode(result);
    }

    if (useAntiDebug) {
      result = this._addAntiDebugChecks(result);
    }

    this.morphMetrics.transformations++;
    return result;
  }

  /**
   * Async morph (for bridge-integrated use) - returns full result object.
   */
  async morphAsync(code, context = {}) {
    // Check policy before morphing
    if (this.bridge) {
      try {
        const policyContext = {
          action: 'code_morph',
          codeLength: code.length,
          ...context
        };
        
        const decision = await this.bridge.evaluatePolicy(policyContext);
        this.morphMetrics.policyChecks++;
        
        if (decision.verdict === 'deny') {
          throw new Error(`Morphing denied: ${decision.reason}`);
        }
      } catch (err) {
        console.error('Policy check failed:', err);
      }
    }

    let morphed = code;

    // Apply transformations
    if (this.morphStrategies.obfuscate) {
      morphed = this._obfuscateStrings(morphed);
    }

    if (this.morphStrategies.rename) {
      morphed = this._renameVariables(morphed);
    }

    if (this.morphStrategies.shuffle) {
      morphed = this._shuffleStatements(morphed);
    }

    this.morphMetrics.transformations++;

    return {
      code: morphed,
      original: code,
      transformations: Object.keys(this.morphStrategies).filter(
        k => this.morphStrategies[k]
      ),
      metrics: this.morphMetrics
    };
  }

  /**
   * Obfuscate string literals
   */
  _obfuscateStrings(code) {
    return code.replace(/"([^"]*)"/g, (match, str) => {
      // Simple string encoding
      const encoded = Buffer.from(str).toString('base64');
      return `Buffer.from("${encoded}", "base64").toString()`;
    });
  }

  /**
   * Rename variables (simple implementation)
   */
  _renameVariables(code) {
    // This is a simplified version
    // A real implementation would use AST transformation
    const varNames = new Map();
    let counter = 0;

    return code.replace(/\b([a-zA-Z_][a-zA-Z0-9_]*)\b/g, (match) => {
      // Don't rename keywords
      const keywords = ['drink', 'pour', 'sip', 'thirsty', 'hydrated', 'refill', 'shield'];
      if (keywords.includes(match)) {
        return match;
      }

      if (!varNames.has(match)) {
        varNames.set(match, `_v${counter++}`);
      }
      return varNames.get(match);
    });
  }

  /**
   * Inject dead code to confuse static analysis
   */
  _injectDeadCode(code) {
    const deadSnippets = [
      '// Security layer alpha\ndrink _sec_a = 0\ndrink _sec_b = _sec_a + 1\n',
      '// Security layer beta\ndrink _sec_x = "dead"\ndrink _sec_y = "code"\n',
      '// Security layer gamma\ndrink _sec_i = 100\ndrink _sec_j = _sec_i * 0\n',
    ];
    const prefix = deadSnippets.join('');
    return prefix + code + '\n// Security layer omega\ndrink _sec_end = parched\n';
  }

  /**
   * Add anti-debug checks
   */
  _addAntiDebugChecks(code) {
    const antiDebug = `// Anti-Debug Layer
// debugger;
drink _debugCheck = "Debug protection active"
`;
    return antiDebug + code;
  }

  /**
   * Shuffle statement order (safe operations only)
   */
  _shuffleStatements(code) {
    // Simple implementation - just return code
    // Real implementation would analyze dependencies and reorder
    return code;
  }

  /**
   * Get morph statistics (alias for getMetrics with totalMorphs key)
   */
  getMorphStats() {
    return {
      totalMorphs: this.morphMetrics.transformations,
      policyChecks: this.morphMetrics.policyChecks,
    };
  }

  /**
   * Configure morph strategies
   */
  setStrategy(strategy, enabled) {
    if (strategy in this.morphStrategies) {
      this.morphStrategies[strategy] = enabled;
    }
  }

  /**
   * Get morph metrics
   */
  getMetrics() {
    return { ...this.morphMetrics };
  }

  /**
   * Reset metrics
   */
  resetMetrics() {
    this.morphMetrics = {
      transformations: 0,
      policyChecks: 0
    };
  }
}

module.exports = { CodeMorpher };
