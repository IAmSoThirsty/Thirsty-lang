/**
 * Tier 4 - Shadow Thirsty
 * Dual-plane compiler: surface plane + security-hardened shadow plane.
 */

const crypto = require('crypto');

class ShadowThirsty {
  constructor(options = {}) {
    this.tier = 4;
    this.name = 'Shadow Thirsty';
    this.options = options;
    this._secret = options.secret || crypto.randomBytes(32).toString('hex');
  }

  compile(code, options = {}) {
    const planeA = this._compileSurface(code, options);
    const planeB = this._compileShadow(code, options);
    return {
      planeA,
      planeB,
      version: 1,
      timestamp: Date.now(),
    };
  }

  _compileSurface(code, options) {
    const lines = code.split('\n').filter(l => l.trim() && !l.trim().startsWith('//'));
    const tokens = lines.map(line => line.trim());
    const checksum = crypto.createHash('sha256').update(code).digest('hex');
    return {
      plane: 'A',
      tokens,
      lineCount: lines.length,
      checksum,
      metadata: { optimized: options.optimize || false },
    };
  }

  _compileShadow(code, options) {
    const checksum = crypto.createHash('sha256').update(code).digest('hex');
    const hmac = crypto.createHmac('sha256', this._secret).update(code).digest('hex');
    const lines = code.split('\n').filter(l => l.trim() && !l.trim().startsWith('//'));
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
      metadata: { hardened: true, tamperDetection: true },
    };
  }

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
      valid: true,
      checksum: compiled.planeA.checksum,
      plane: 'dual-verified',
      timestamp: compiled.timestamp,
    };
  }

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
}

module.exports = { ShadowThirsty };
