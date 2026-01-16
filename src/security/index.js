#!/usr/bin/env node

/**
 * Thirsty-lang Security Module
 * Basic input sanitization for XSS prevention
 */

/**
 * Security Manager - Provides basic sanitization functionality
 */
class SecurityManager {
  constructor(options = {}) {
    this.enabled = options.enabled !== false;
    this.mode = options.mode || 'defensive';
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
}

// Export security manager
module.exports = {
  SecurityManager
};
