/**
 * UTF Registry — Universal Thirsty Family component registry
 * Exposes factory methods for all 6 UTF tiers.
 */

const { ThirstyLang } = require('./components/thirsty-lang');
const { ThirstOfGods } = require('./components/thirst-of-gods');
const { TARL } = require('./components/tarl');
const { ShadowThirsty } = require('./components/shadow-thirsty');
const { TSCG } = require('./components/tscg');
const { TSCGB } = require('./components/tscg-b');
const { UTFConfig } = require('./config');

class UTFRegistry {
  constructor(options = {}) {
    this.config = new UTFConfig(options);
  }

  createTier1(options = {}) {
    return new ThirstyLang({ ...this.config.getTierOptions(1), ...options });
  }

  createTier2(options = {}) {
    return new ThirstOfGods({ ...this.config.getTierOptions(2), ...options });
  }

  createTier3(options = {}) {
    return new TARL({ ...this.config.getTierOptions(3), ...options });
  }

  createTier4(options = {}) {
    return new ShadowThirsty({ ...this.config.getTierOptions(4), ...options });
  }

  createTier5(options = {}) {
    return new TSCG({ ...this.config.getTierOptions(5), ...options });
  }

  createTier6(options = {}) {
    return new TSCGB({ ...this.config.getTierOptions(6), ...options });
  }

  create(tierNameOrNumber, options = {}) {
    const map = {
      1: 'createTier1', 'thirsty-lang': 'createTier1',
      2: 'createTier2', 'thirst-of-gods': 'createTier2',
      3: 'createTier3', 'tarl': 'createTier3',
      4: 'createTier4', 'shadow-thirsty': 'createTier4',
      5: 'createTier5', 'tscg': 'createTier5',
      6: 'createTier6', 'tscg-b': 'createTier6',
    };
    const method = map[tierNameOrNumber];
    if (!method) throw new Error(`Unknown UTF tier: ${tierNameOrNumber}`);
    return this[method](options);
  }

  getTierInfo() {
    return [
      { tier: 1, name: 'Thirsty-Lang', description: 'Core language — variables, control flow, security primitives', ext: '.thirsty' },
      { tier: 2, name: 'Thirst of Gods', description: 'OOP, async/await, advanced data structures', ext: '.thirstofgods' },
      { tier: 3, name: 'T.A.R.L.', description: 'Defensive policy VM', ext: null },
      { tier: 4, name: 'Shadow Thirsty', description: 'Dual-plane verified compiler', ext: null },
      { tier: 5, name: 'TSCG', description: 'Symbolic compression engine', ext: null },
      { tier: 6, name: 'TSCG-B', description: 'Binary encoding layer', ext: null },
    ];
  }
}

module.exports = {
  UTFRegistry,
  UTFConfig,
  ThirstyLang,
  ThirstOfGods,
  TARL,
  ShadowThirsty,
  TSCG,
  TSCGB,
};
