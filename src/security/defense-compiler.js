#!/usr/bin/env node
//                                           [2026-03-03 13:45]
//                                          Productivity: Active

/**
 * Defense Compiler - Compile code with defensive transformations
 * Integrates with T.A.R.L. for policy-driven compilation
 */

const { ThreatDetector } = require('./threat-detector');
const { CodeMorpher } = require('./code-morpher');

class DefenseCompiler {
  /**
   * Constructor accepts either a SecurityBridge instance (legacy) or an options object.
   * Options: { defenseEnabled, morphingEnabled, policy: { securityLevel } }
   */
  constructor(bridgeOrOptions) {
    // Support both bridge instance and plain options object
    if (bridgeOrOptions && typeof bridgeOrOptions.evaluatePolicy === 'function') {
      // Legacy: SecurityBridge passed directly
      this.bridge = bridgeOrOptions;
      this.defenseEnabled = true;
      this.morphingEnabled = true;
      this.policy = { securityLevel: 'moderate' };
    } else {
      const opts = bridgeOrOptions || {};
      this.bridge = null;
      this.defenseEnabled = opts.defenseEnabled !== false;
      this.morphingEnabled = opts.morphingEnabled !== false;
      this.policy = opts.policy || { securityLevel: 'moderate' };
    }

    this.threatDetector = new ThreatDetector(this.bridge);
    this.codeMorpher = new CodeMorpher(this.bridge);
    this.compileMetrics = {
      compilations: 0,
      successfulCompilations: 0,
      threatsBlocked: 0,
      transformations: 0,
    };
  }

  /**
   * Synchronous compile - wraps code with security layers.
   * Returns { code, original, securityLayers, threats, transformations }
   */
  compile(code, options = {}) {
    this.compileMetrics.compilations++;

    const threats = this.threatDetector.detectInputThreats(code);
    const securityLayers = [];

    let compiled = code;

    if (this.defenseEnabled) {
      // Add Security runtime header
      compiled = `// Security: Defense compiler active (level: ${this.policy.securityLevel})\n` + compiled;
      securityLayers.push('SecurityHeader');

      if (this.morphingEnabled && options.morph !== false) {
        compiled = this.codeMorpher.morph(compiled, { obfuscate: false, rename: false });
        securityLayers.push('CodeMorph');
        this.compileMetrics.transformations++;
      }

      compiled = this._addRuntimeGuards(compiled);
      securityLayers.push('RuntimeGuards');
    }

    this.compileMetrics.successfulCompilations++;

    return {
      code: compiled,
      original: code,
      threats,
      securityLayers,
      transformations: securityLayers,
      metrics: this.getCompilationStats(),
    };
  }

  /**
   * Get compilation statistics
   */
  getCompilationStats() {
    return {
      totalCompilations: this.compileMetrics.compilations,
      successfulCompilations: this.compileMetrics.successfulCompilations,
      threatsBlocked: this.compileMetrics.threatsBlocked,
      transformations: this.compileMetrics.transformations,
    };
  }

  /**
   * Async compile (for bridge-integrated use)
   */
  async compileAsync(code, options = {}) {
    this.compileMetrics.compilations++;

    const context = {
      source: options.source || 'unknown',
      mode: options.mode || 'defensive',
      ...options
    };

    // Step 1: Threat detection
    const threatResult = await this.threatDetector.detect(code, context);
    
    if (threatResult.action === 'blocked') {
      this.compileMetrics.threatsBlocked++;
      throw new Error(`Compilation blocked: ${threatResult.reason}`);
    }

    if (threatResult.action === 'escalate') {
      console.warn('Security escalation:', threatResult.reason);
    }

    // Step 2: Check compilation policy
    if (this.bridge) {
      try {
        const policyContext = {
          action: 'compile',
          threats: threatResult.threats,
          mode: context.mode,
          ...context
        };
        
        const decision = await this.bridge.evaluatePolicy(policyContext);
        
        if (decision.verdict === 'deny') {
          throw new Error(`Compilation denied: ${decision.reason}`);
        }
      } catch (err) {
        if (err.message.includes('denied')) {
          throw err;
        }
        console.error('Policy check failed:', err);
      }
    }

    // Step 3: Apply code transformations
    let compiled = code;
    const transformations = [];

    if (options.morph !== false) {
      try {
        const morphResult = await this.codeMorpher.morphAsync(code, context);
        compiled = morphResult.code;
        transformations.push(...morphResult.transformations);
        this.compileMetrics.transformations++;
      } catch (err) {
        console.error('Morphing failed:', err);
      }
    }

    // Step 4: Add runtime guards
    if (options.addGuards !== false) {
      compiled = this._addRuntimeGuards(compiled);
      transformations.push('runtime_guards');
    }

    return {
      code: compiled,
      original: code,
      threats: threatResult.threats,
      transformations,
      metrics: this.getMetrics()
    };
  }

  /**
   * Add runtime security guards
   */
  _addRuntimeGuards(code) {
    // Add security checks at runtime
    const guards = `
// Runtime Security Guards
const __SECURITY_CONTEXT__ = {
  enabled: true,
  checkViolations: function(varName) {
    if (this.protectedVars && this.protectedVars.has(varName)) {
      console.warn('Security: Attempted modification of protected variable:', varName);
      return false;
    }
    return true;
  },
  protectedVars: new Set()
};

`;
    return guards + code;
  }

  /**
   * Get compilation metrics
   */
  getMetrics() {
    return {
      ...this.compileMetrics,
      threatDetector: this.threatDetector.getMetrics(),
      codeMorpher: this.codeMorpher.getMetrics()
    };
  }

  /**
   * Reset metrics
   */
  resetMetrics() {
    this.compileMetrics = {
      compilations: 0,
      successfulCompilations: 0,
      threatsBlocked: 0,
      transformations: 0,
    };
    this.threatDetector.resetMetrics();
    this.codeMorpher.resetMetrics ? this.codeMorpher.resetMetrics() : null;
  }
}

module.exports = { DefenseCompiler };
