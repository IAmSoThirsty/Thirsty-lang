/**
 * UTF Configuration Manager
 * Manages which tiers are enabled, their options, and inter-tier contracts.
 */

class UTFConfig {
  constructor(options = {}) {
    this.tiers = {
      1: { name: 'thirsty-lang', enabled: true, options: options.tier1 || {} },
      2: { name: 'thirst-of-gods', enabled: options.tier2 !== false, options: options.tier2 || {} },
      3: { name: 'tarl', enabled: options.tier3 !== false, options: options.tier3 || {} },
      4: { name: 'shadow-thirsty', enabled: options.tier4 !== false, options: options.tier4 || {} },
      5: { name: 'tscg', enabled: options.tier5 !== false, options: options.tscg || {} },
      6: { name: 'tscg-b', enabled: options.tier6 !== false, options: options.tscgb || {} },
    };
    this.contracts = options.contracts || {};
  }

  isTierEnabled(tier) {
    return !!(this.tiers[tier] && this.tiers[tier].enabled);
  }

  getTierOptions(tier) {
    return (this.tiers[tier] && this.tiers[tier].options) || {};
  }

  setTierEnabled(tier, enabled) {
    if (this.tiers[tier]) {
      this.tiers[tier].enabled = enabled;
    }
  }

  getTierNames() {
    return Object.values(this.tiers).map(t => t.name);
  }
}

module.exports = { UTFConfig };
