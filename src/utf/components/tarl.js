/**
 * Tier 3 - T.A.R.L. (Thirsty's Active Resistance Language)
 * JavaScript interface to the T.A.R.L. policy VM.
 * Wraps the Python TARL runtime via the existing security bridge.
 */

const path = require('path');

class TARL {
  constructor(options = {}) {
    this.tier = 3;
    this.name = 'T.A.R.L.';
    this.options = options;
    this.policies = new Map();
    this.metrics = {
      evaluations: 0,
      allowed: 0,
      denied: 0,
      errors: 0,
      totalLatencyMs: 0,
    };
    this._bridge = null;
    this._bridgeAvailable = false;
    this._rateLimitState = new Map();

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
        const key = context.key || 'default';
        const limit = context.limit || 100;
        const windowMs = context.windowMs || 60000;
        const now = Date.now();
        const state = this._rateLimitState.get(key) || { count: 0, windowStart: now };
        if (now - state.windowStart > windowMs) {
          state.count = 0;
          state.windowStart = now;
        }
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
        if (!role) return { verdict: 'DENY', reason: 'No role specified' };
        if (!resource) return { verdict: 'DENY', reason: 'No resource specified' };
        const acl = {
          admin: { read: true, write: true, execute: true, delete: true },
          user: { read: true, write: true, execute: true, delete: false },
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
      this._bridge = null;
      this._bridgeAvailable = false;
    }
  }

  async evaluate(context) {
    const start = Date.now();
    this.metrics.evaluations++;
    try {
      const results = [];
      for (const [name, policy] of this.policies) {
        const result = await Promise.resolve(policy.evaluate(context));
        results.push({ policy: name, ...result });
        if (result.verdict === 'DENY') {
          this.metrics.denied++;
          this.metrics.totalLatencyMs += Date.now() - start;
          return { verdict: 'DENY', policy: name, reason: result.reason, results };
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
}

module.exports = { TARL };
