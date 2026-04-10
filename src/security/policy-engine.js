#!/usr/bin/env node
//                                           [2026-03-03 13:45]
//                                          Productivity: Active

/**
 * Policy Engine - Manage and enforce security policies
 * Integrates with T.A.R.L. runtime for unified policy management
 */

const fs = require('fs');
const path = require('path');
const EventEmitter = require('events');

class PolicyEngine extends EventEmitter {
  constructor(securityBridge) {
    super();
    this.bridge = securityBridge;
    this.policies = new Map();
    this.policyPath = null;
    this.watchHandle = null;
    this.metrics = {
      policyEvaluations: 0,
      policyReloads: 0,
      lastReload: null
    };
  }

  /**
   * Load policies from file (JSON or YAML)
   */
  async loadPolicies(policyPath) {
    this.policyPath = policyPath;

    if (!fs.existsSync(policyPath)) {
      throw new Error(`Policy file not found: ${policyPath}`);
    }

    const content = fs.readFileSync(policyPath, 'utf8');
    let policyData;

    if (policyPath.endsWith('.json')) {
      policyData = JSON.parse(content);
    } else if (policyPath.endsWith('.yaml') || policyPath.endsWith('.yml')) {
      // Simple YAML parsing (for basic cases)
      policyData = this._parseYAML(content);
    } else {
      throw new Error(`Unsupported policy file format: ${policyPath}`);
    }

    // Store policies locally
    this.policies.clear();
    for (const policy of policyData.policies || []) {
      this.policies.set(policy.name, policy);
    }

    // Load into T.A.R.L. runtime
    if (this.bridge) {
      await this.bridge.loadPolicies(policyPath);
    }

    this.metrics.policyReloads++;
    this.metrics.lastReload = new Date().toISOString();

    this.emit('policies_loaded', {
      count: this.policies.size,
      path: policyPath
    });

    return {
      loaded: this.policies.size,
      policies: Array.from(this.policies.keys())
    };
  }

  /**
   * Simple YAML parser (basic implementation)
   */
  _parseYAML(content) {
    // This is a very basic YAML parser for simple structures
    // For production, use a proper YAML library
    const lines = content.split('\n');
    const policies = [];
    let currentPolicy = null;
    let currentRule = null;

    for (const line of lines) {
      const trimmed = line.trim();
      
      if (trimmed.startsWith('- name:')) {
        if (currentPolicy) {
          policies.push(currentPolicy);
        }
        currentPolicy = {
          name: trimmed.substring(7).trim().replace(/['"]/g, ''),
          rules: []
        };
      } else if (trimmed.startsWith('- condition:') && currentPolicy) {
        currentRule = { condition: {} };
      } else if (trimmed.startsWith('verdict:') && currentRule) {
        currentRule.verdict = trimmed.substring(8).trim().replace(/['"]/g, '');
      } else if (trimmed.startsWith('reason:') && currentRule) {
        currentRule.reason = trimmed.substring(7).trim().replace(/['"]/g, '');
        if (currentPolicy) {
          currentPolicy.rules.push(currentRule);
        }
        currentRule = null;
      }
    }

    if (currentPolicy) {
      policies.push(currentPolicy);
    }

    return { policies };
  }

  /**
   * Enable hot-reload of policies
   */
  enableHotReload() {
    if (!this.policyPath) {
      throw new Error('No policy file loaded');
    }

    if (this.watchHandle) {
      return; // Already watching
    }

    this.watchHandle = fs.watch(this.policyPath, async (eventType) => {
      if (eventType === 'change') {
        console.log('Policy file changed, reloading...');
        try {
          await this.reloadPolicies();
          this.emit('policies_reloaded');
        } catch (err) {
          console.error('Failed to reload policies:', err);
          this.emit('reload_error', err);
        }
      }
    });

    console.log('Hot-reload enabled for:', this.policyPath);
  }

  /**
   * Disable hot-reload
   */
  disableHotReload() {
    if (this.watchHandle) {
      this.watchHandle.close();
      this.watchHandle = null;
      console.log('Hot-reload disabled');
    }
  }

  /**
   * Reload policies from disk
   */
  async reloadPolicies() {
    if (!this.policyPath) {
      throw new Error('No policy file loaded');
    }

    return await this.loadPolicies(this.policyPath);
  }

  /**
   * Evaluate action against policies
   */
  async evaluate(action, context = {}) {
    this.metrics.policyEvaluations++;

    if (this.bridge) {
      const policyContext = {
        action,
        ...context
      };
      
      return await this.bridge.evaluatePolicy(policyContext);
    }

    // Fallback: local evaluation
    return {
      verdict: 'allow',
      reason: 'No T.A.R.L. runtime available'
    };
  }

  /**
   * Get policy metrics
   */
  getMetrics() {
    return { ...this.metrics };
  }

  /**
   * Get loaded policies
   */
  getPolicies() {
    return Array.from(this.policies.values());
  }

  /**
   * Shutdown policy engine
   */
  shutdown() {
    this.disableHotReload();
  }
}

/**
 * SecurityPolicyEngine - Standalone synchronous policy engine for
 * input sanitization and threat response without a T.A.R.L. bridge.
 * This is the public-facing, synchronous counterpart to PolicyEngine.
 */
class SecurityPolicyEngine {
  constructor(options = {}) {
    this.securityLevel = options.securityLevel || 'moderate';
    this._levelOrder = ['passive', 'moderate', 'aggressive'];
  }

  /**
   * Sanitize input according to the current security level.
   * Returns { original, sanitized, modified }
   */
  applyInputPolicy(input) {
    const original = input;
    let sanitized = input;

    if (this.securityLevel === 'passive') {
      // Only HTML-encode the most dangerous characters
      sanitized = input
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    } else if (this.securityLevel === 'moderate') {
      sanitized = input
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#x27;');
    } else {
      // aggressive - strip tags and dangerous keywords entirely
      sanitized = input
        .replace(/<[^>]*>/g, '')
        .replace(/\bscript\b/gi, '')
        .replace(/javascript:/gi, '')
        .replace(/on\w+\s*=/gi, '');
    }

    return { original, sanitized, modified: original !== sanitized };
  }

  /**
   * Determine the appropriate response action for a given threat.
   * Returns { action: 'allow' | 'warn' | 'block' }
   */
  handleThreat(threat) {
    const levelIdx = this._levelOrder.indexOf(this.securityLevel);
    const severityMap = { low: 0, medium: 1, high: 2, critical: 3 };
    const severity = severityMap[threat.severity] !== undefined
      ? severityMap[threat.severity]
      : 1;

    if (this.securityLevel === 'passive') {
      return { action: 'allow', reason: 'Passive mode - log only' };
    } else if (this.securityLevel === 'moderate') {
      return severity >= 3
        ? { action: 'block', reason: 'Critical threat blocked' }
        : { action: 'warn', reason: 'Threat detected - warning issued' };
    } else {
      return { action: 'block', reason: 'Aggressive mode - all threats blocked' };
    }
  }

  /**
   * Change the security level at runtime.
   */
  setSecurityLevel(level) {
    if (this._levelOrder.includes(level)) {
      this.securityLevel = level;
    } else {
      throw new Error(`Unknown security level: ${level}. Valid: ${this._levelOrder.join(', ')}`);
    }
  }

  /**
   * Return the current policy configuration.
   */
  getPolicyConfig() {
    return {
      securityLevel: this.securityLevel,
      availableLevels: [...this._levelOrder],
    };
  }
}

module.exports = { PolicyEngine, SecurityPolicyEngine };
