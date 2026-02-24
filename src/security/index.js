#!/usr/bin/env node

/**
 * Thirsty-Lang Security Module
 * Enhanced security with T.A.R.L. integration
 */

const { SecurityBridge } = require('./bridge');
const { ThreatDetector } = require('./threat-detector');
const { CodeMorpher } = require('./code-morpher');
const { DefenseCompiler } = require('./defense-compiler');
const { PolicyEngine } = require('./policy-engine');
const { Logger } = require('../engine/logger');

/**
 * SecurityManager - Provides HTML sanitization and variable protection
 * Enhanced with T.A.R.L. runtime integration
 */
class SecurityManager {
  constructor(options = {}) {
    this.enabled = options.enabled !== false;
    this.mode = options.mode || 'defensive';

    // Initialize T.A.R.L. bridge if enabled
    this.useTarl = options.useTarl !== false;
    this.bridge = null;
    this.threatDetector = null;
    this.codeMorpher = null;
    this.defenseCompiler = null;
    this.policyEngine = null;
    this.initialized = false;

    // Runtime state for AST engine
    this.shieldActive = false;
    this.shieldContext = null;
    this.protections = new Set();
    this.detectionTarget = null;
    this.defenseLevel = 'moderate';
    this.logger = new Logger({ component: 'SECURITY' });
  }

  /**
   * Initialize T.A.R.L. integration
   */
  async initialize() {
    if (this.initialized || !this.useTarl) {
      return;
    }

    try {
      this.bridge = new SecurityBridge();
      await this.bridge.initialize();

      this.threatDetector = new ThreatDetector(this.bridge);
      this.codeMorpher = new CodeMorpher(this.bridge);
      this.defenseCompiler = new DefenseCompiler(this.bridge);
      this.policyEngine = new PolicyEngine(this.bridge);

      this.initialized = true;
      this.logger.info('T.A.R.L. security integration initialized');
    } catch (err) {
      this.logger.error('Failed to initialize T.A.R.L. integration', { error: err.message, stack: err.stack });
      this.useTarl = false;
    }
  }

  /**
   * Enter shielded context (for 'shield' keyword)
   */
  enterShieldedContext(context) {
    this.shieldActive = true;
    this.shieldContext = context;
    this.logger.info(`Entering shielded context`, { context });
  }

  /**
   * Exit shielded context
   */
  exitShieldedContext() {
    this.shieldActive = false;
    this.logger.info(`Exiting shielded context`, { context: this.shieldContext });
    this.shieldContext = null;
  }

  /**
   * Enable specific protections (for 'morph' keyword)
   */
  enableProtections(protections) {
    if (!Array.isArray(protections)) return;
    protections.forEach(p => this.protections.add(p));

    if (this.initialized && this.codeMorpher) {
      protections.forEach(p => {
        if (this.codeMorpher.morphStrategies[p] !== undefined) {
          this.codeMorpher.setStrategy(p, true);
        }
      });
    }
    this.logger.info(`Protections enabled`, { protections });
  }

  /**
   * Enable threat detection (for 'detect' keyword)
   */
  enableDetection(target) {
    this.detectionTarget = target;
    if (this.initialized && this.threatDetector) {
      this.logger.info(`Threat detection target set`, { target });
      this.threatDetector.startMonitoring(target);
    }
  }

  /**
   * Set defense level (for 'defend' keyword)
   */
  setDefenseLevel(level) {
    this.defenseLevel = level;
    this.logger.info(`Global defense level set`, { level });
    if (this.initialized && this.policyEngine) {
      // Logic to adjust policy rules based on level
    }
  }

  /**
   * Sanitize input - HTML encoding to prevent XSS
   */
  secureInput(input, context = {}) {
    if (!this.enabled) {
      return input;
    }

    const sanitized = this.sanitizeHTML(String(input));

    return {
      original: input,
      sanitized,
      modified: input !== sanitized
    };
  }

  /**
   * HTML encoding - escapes special characters to prevent injection
   */
  sanitizeHTML(input) {
    return input
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#x27;')
      .replace(/\//g, '&#x2F;');
  }

  /**
   * Set security mode (kept for compatibility)
   */
  setMode(mode) {
    this.mode = mode;
    return { mode: this.mode };
  }

  /**
   * Enable/disable security
   */
  setEnabled(enabled) {
    this.enabled = !!enabled;
    return { enabled: this.enabled };
  }

  /**
   * Detect threats using advanced detection
   */
  async detectThreats(input, context = {}) {
    if (!this.initialized || !this.threatDetector) {
      return { detected: false, threats: [] };
    }

    return await this.threatDetector.detect(input, context);
  }

  /**
   * Compile code with defensive measures
   */
  async compileSecure(code, options = {}) {
    if (!this.initialized || !this.defenseCompiler) {
      return { code, original: code };
    }

    return await this.defenseCompiler.compile(code, options);
  }

  /**
   * Load security policies
   */
  async loadPolicies(policyPath) {
    if (!this.initialized || !this.policyEngine) {
      throw new Error('Policy engine not initialized');
    }

    return await this.policyEngine.loadPolicies(policyPath);
  }

  /**
   * Shutdown security bridge
   */
  async shutdown() {
    if (this.bridge) {
      await this.bridge.shutdown();
    }
    if (this.policyEngine) {
      this.policyEngine.shutdown();
    }
  }
}

// Export security manager and components
module.exports = {
  SecurityManager,
  SecurityBridge,
  ThreatDetector,
  CodeMorpher,
  DefenseCompiler,
  PolicyEngine
};
