#!/usr/bin/env node

/**
 * Thirsty-lang Interpreter
 * Enterprise-grade programming language with defensive security capabilities
 */

const { SecurityManager } = require('./security/index');

class ThirstyInterpreter {
  constructor(options = {}) {
    this.variables = {};
    this.MAX_LOOP_ITERATIONS = 10000; // Safety limit for loops
    
    // Security features
    this.securityEnabled = options.security !== false;
    this.securityManager = new SecurityManager({
      enabled: this.securityEnabled,
      mode: options.securityMode || 'defensive',
      policy: { securityLevel: options.securityLevel || 'moderate' }
    });
    this.shieldActive = false;
    this.shieldContext = null;
    this.armoredVariables = new Set();
    this.sanitizedVariables = new Set();
  }

  /**
   * Parse and execute Thirsty-lang code
   * @param {string} code - The Thirsty-lang source code
   */
  execute(code) {
    const lines = code.split('\n');
    this.executeBlock(lines, 0);
  }

  /**
   * Execute a block of code starting from a given index
   * Returns the index after the block ends
   */
  executeBlock(lines, startIndex) {
    let i = startIndex;
    
    while (i < lines.length) {
      const line = lines[i].trim();
      
      // Skip empty lines and comments
      if (!line || line.startsWith('//')) {
        i++;
        continue;
      }
      
      // Handle control flow
      if (line.startsWith('thirsty ')) {
        i = this.handleThirsty(lines, i);
      } else if (line.startsWith('refill ')) {
        i = this.handleRefill(lines, i);
      } else if (line.startsWith('shield ')) {
        i = this.handleShield(lines, i);
      } else if (line === '}') {
        // End of block
        return i + 1;
      } else {
        this.executeLine(line);
        i++;
      }
    }
    
    return i;
  }

  /**
   * Execute a single line of code
   * @param {string} line - A single line of Thirsty-lang code
   */
  executeLine(line) {
    // Security keywords
    if (line.startsWith('sanitize ')) {
      this.handleSanitize(line);
    }
    else if (line.startsWith('armor ')) {
      this.handleArmor(line);
    }
    else if (line.startsWith('morph ')) {
      this.handleMorph(line);
    }
    else if (line.startsWith('detect ')) {
      this.handleDetect(line);
    }
    else if (line.startsWith('defend ')) {
      this.handleDefend(line);
    }
    // Core keywords
    else if (line.startsWith('drink ')) {
      this.handleDrink(line);
    }
    // pour - Output statement
    else if (line.startsWith('pour ')) {
      this.handlePour(line);
    }
    // sip - Input statement
    else if (line.startsWith('sip ')) {
      this.handleSip(line);
    }
    else {
      throw new Error(`Unknown statement: ${line}`);
    }
  }

  /**
   * Find matching closing brace for a control flow block
   * Returns the index of the closing brace or -1 if not found
   */
  findMatchingBrace(lines, startIndex) {
    let braceCount = 1;
    let i = startIndex + 1;
    
    while (i < lines.length && braceCount > 0) {
      const currentLine = lines[i].trim();
      // Count braces only for control flow statements
      if (currentLine.startsWith('thirsty ') && currentLine.endsWith('{')) {
        braceCount++;
      } else if (currentLine.startsWith('refill ') && currentLine.endsWith('{')) {
        braceCount++;
      } else if (currentLine === 'hydrated {') {
        braceCount++;
      } else if (currentLine === '}') {
        braceCount--;
        if (braceCount === 0) {
          return i;
        }
      }
      i++;
    }
    
    return -1; // No matching brace found
  }

  /**
   * Handle thirsty (if) statement
   */
  handleThirsty(lines, startIndex) {
    const line = lines[startIndex].trim();
    const match = line.match(/thirsty\s+(.+)\s*{/);
    
    if (!match) {
      throw new Error(`Invalid thirsty statement: ${line}`);
    }
    
    const condition = this.evaluateCondition(match[1]);
    
    // Find the matching closing brace
    const thenBlockEnd = this.findMatchingBrace(lines, startIndex);
    
    if (thenBlockEnd === -1) {
      throw new Error(`Unmatched opening brace for thirsty statement at line ${startIndex + 1}`);
    }
    
    // Check for hydrated (else) block
    let hydratedStart = -1;
    if (thenBlockEnd + 1 < lines.length) {
      const nextLine = lines[thenBlockEnd + 1].trim();
      if (nextLine === 'hydrated {') {
        hydratedStart = thenBlockEnd + 2;
      }
    }
    
    if (condition) {
      // Execute the then block
      this.executeBlock(lines.slice(startIndex + 1, thenBlockEnd), 0);
      
      // Skip past hydrated block if it exists
      if (hydratedStart !== -1) {
        const hydratedEnd = this.findMatchingBrace(lines, thenBlockEnd + 1);
        if (hydratedEnd === -1) {
          throw new Error(`Unmatched opening brace for hydrated block at line ${thenBlockEnd + 2}`);
        }
        return hydratedEnd + 1;
      }
      
      return thenBlockEnd + 1;
    } else if (hydratedStart !== -1) {
      // Execute the hydrated (else) block
      const hydratedEnd = this.findMatchingBrace(lines, thenBlockEnd + 1);
      if (hydratedEnd === -1) {
        throw new Error(`Unmatched opening brace for hydrated block at line ${thenBlockEnd + 2}`);
      }
      this.executeBlock(lines.slice(hydratedStart, hydratedEnd), 0);
      return hydratedEnd + 1;
    }
    
    return thenBlockEnd + 1;
  }

  /**
   * Evaluate a condition for if statements
   * Note: Only handles simple binary comparisons (a op b), not complex expressions
   * Uses strict equality to avoid type coercion issues
   */
  evaluateCondition(condition) {
    condition = condition.trim();
    
    // Comparison operators (check in order of specificity to avoid conflicts)
    // e.g., check >= before >, <= before <, != before =
    if (condition.includes('==')) {
      const parts = condition.split('==', 2).map(p => p.trim());
      return this.evaluateExpression(parts[0]) === this.evaluateExpression(parts[1]);
    }
    if (condition.includes('!=')) {
      const parts = condition.split('!=', 2).map(p => p.trim());
      return this.evaluateExpression(parts[0]) !== this.evaluateExpression(parts[1]);
    }
    if (condition.includes('>=')) {
      const parts = condition.split('>=', 2).map(p => p.trim());
      return this.evaluateExpression(parts[0]) >= this.evaluateExpression(parts[1]);
    }
    if (condition.includes('<=')) {
      const parts = condition.split('<=', 2).map(p => p.trim());
      return this.evaluateExpression(parts[0]) <= this.evaluateExpression(parts[1]);
    }
    if (condition.includes('>')) {
      const parts = condition.split('>', 2).map(p => p.trim());
      return this.evaluateExpression(parts[0]) > this.evaluateExpression(parts[1]);
    }
    if (condition.includes('<')) {
      const parts = condition.split('<', 2).map(p => p.trim());
      return this.evaluateExpression(parts[0]) < this.evaluateExpression(parts[1]);
    }
    
    // Boolean expression
    return Boolean(this.evaluateExpression(condition));
  }

  /**
   * Handle refill (loop) statement
   */
  handleRefill(lines, startIndex) {
    const line = lines[startIndex].trim();
    const match = line.match(/refill\s+(.+)\s*{/);
    
    if (!match) {
      throw new Error(`Invalid refill statement: ${line}`);
    }
    
    const condition = match[1];
    
    // Find the matching closing brace
    const blockEnd = this.findMatchingBrace(lines, startIndex);
    
    if (blockEnd === -1) {
      throw new Error(`Unmatched opening brace for refill statement at line ${startIndex + 1}`);
    }
    
    // Execute the loop
    let iterations = 0;
    
    while (this.evaluateCondition(condition) && iterations < this.MAX_LOOP_ITERATIONS) {
      this.executeBlock(lines.slice(startIndex + 1, blockEnd), 0);
      iterations++;
    }
    
    if (iterations >= this.MAX_LOOP_ITERATIONS) {
      throw new Error(`Loop exceeded maximum iterations (${this.MAX_LOOP_ITERATIONS})`);
    }
    
    return blockEnd + 1;
  }

  /**
   * Handle variable declaration: drink varname = value
   */
  handleDrink(line) {
    const match = line.match(/drink\s+(\w+)\s*=\s*(.+)/);
    if (!match) {
      throw new Error(`Invalid drink statement: ${line}`);
    }
    
    const varName = match[1];
    
    // Check if variable is armored (protected)
    if (this.armoredVariables.has(varName) && this.variables.hasOwnProperty(varName)) {
      console.warn(`Warning: Attempt to modify armored variable '${varName}' blocked`);
      return;
    }
    
    const value = this.evaluateExpression(match[2]);
    this.variables[varName] = value;
  }

  /**
   * Handle output statement: pour expression
   */
  handlePour(line) {
    const expression = line.substring(5).trim(); // Remove 'pour '
    const value = this.evaluateExpression(expression);
    console.log(value);
  }

  /**
   * Handle input statement: sip varname or sip "prompt"
   */
  handleSip(line) {
    const match = line.match(/sip\s+"([^"]+)"/);
    if (match) {
      // For now, return empty string - in production this would use readline
      return "";
    }
    // Placeholder for input functionality
    console.log('Input functionality not yet implemented');
  }

  /**
   * Handle shield (security block) statement
   */
  handleShield(lines, startIndex) {
    const line = lines[startIndex].trim();
    const match = line.match(/shield\s+(\w+)\s*{/);
    
    if (!match) {
      throw new Error(`Invalid shield statement: ${line}`);
    }
    
    const shieldName = match[1];
    const blockEnd = this.findMatchingBrace(lines, startIndex);
    
    if (blockEnd === -1) {
      throw new Error(`Unmatched opening brace for shield statement at line ${startIndex + 1}`);
    }
    
    // Activate shield protection
    const previousShieldState = this.shieldActive;
    const previousContext = this.shieldContext;
    
    this.shieldActive = true;
    this.shieldContext = {
      name: shieldName,
      startLine: startIndex,
      threats: [],
      protected: true
    };
    
    try {
      // Execute the protected block
      this.executeBlock(lines.slice(startIndex + 1, blockEnd), 0);
    } finally {
      // Restore previous shield state
      this.shieldActive = previousShieldState;
      this.shieldContext = previousContext;
    }
    
    return blockEnd + 1;
  }

  /**
   * Handle sanitize (input cleaning) statement
   */
  handleSanitize(line) {
    const match = line.match(/sanitize\s+(\w+)/);
    if (!match) {
      throw new Error(`Invalid sanitize statement: ${line}`);
    }
    
    const varName = match[1];
    
    if (!this.variables.hasOwnProperty(varName)) {
      throw new Error(`Cannot sanitize undefined variable: ${varName}`);
    }
    
    // Apply security sanitization
    const value = this.variables[varName];
    if (this.securityEnabled) {
      const result = this.securityManager.secureInput(value, {
        variable: varName,
        shield: this.shieldContext
      });
      // Extract the sanitized value from the result object
      this.variables[varName] = result.sanitized || result;
    } else {
      // Basic sanitization without security manager
      this.variables[varName] = this.basicSanitize(value);
    }
    
    this.sanitizedVariables.add(varName);
  }

  /**
   * Handle armor (memory protection) statement
   */
  handleArmor(line) {
    const match = line.match(/armor\s+(\w+)/);
    if (!match) {
      throw new Error(`Invalid armor statement: ${line}`);
    }
    
    const varName = match[1];
    
    if (!this.variables.hasOwnProperty(varName)) {
      throw new Error(`Cannot armor undefined variable: ${varName}`);
    }
    
    // Mark variable as armored (protected from modification)
    this.armoredVariables.add(varName);
    
    // In production, this would use Object.freeze or similar mechanisms
    // For now, we'll check this in handleDrink
  }

  /**
   * Handle morph (code obfuscation) statement
   */
  handleMorph(line) {
    const match = line.match(/morph\s+on:\s*\[([^\]]+)\]/);
    if (match) {
      const threats = match[1].split(',').map(t => t.trim().replace(/["']/g, ''));
      // Enable morphing for specified threat types
      if (this.shieldContext) {
        this.shieldContext.morphEnabled = true;
        this.shieldContext.morphThreats = threats;
      }
    }
  }

  /**
   * Handle detect (threat monitoring) statement
   */
  handleDetect(line) {
    const match = line.match(/detect\s+(\w+)/);
    if (match) {
      const detectType = match[1];
      if (this.shieldContext) {
        this.shieldContext.detectEnabled = true;
        this.shieldContext.detectType = detectType;
      }
    }
  }

  /**
   * Handle defend (countermeasures) statement
   */
  handleDefend(line) {
    const match = line.match(/defend\s+with:\s*"(\w+)"/);
    if (match) {
      const strategy = match[1];
      if (this.shieldContext) {
        this.shieldContext.defendStrategy = strategy;
      }
      // Set defense strategy: passive, moderate, aggressive, paranoid
      if (this.securityEnabled) {
        this.securityManager.setMode(strategy === 'aggressive' ? 'offensive' : 'defensive');
      }
    }
  }

  /**
   * Basic sanitization (fallback when security manager not enabled)
   * Production-grade HTML encoding to prevent XSS
   */
  basicSanitize(value) {
    if (typeof value !== 'string') {
      return value;
    }
    
    // HTML encode all special characters to prevent injection
    return value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#x27;')
      .replace(/\//g, '&#x2F;')
      .trim();
  }

  /**
   * Evaluate an expression (variable or literal) with proper operator precedence
   */
  evaluateExpression(expr) {
    expr = expr.trim();
    
    // Handle addition and subtraction (lowest precedence)
    // Only split if there's a + or - NOT inside a higher precedence operation
    for (let i = expr.length - 1; i >= 0; i--) {
      if (this.isInString(expr, i)) continue;
      
      if (expr[i] === '+') {
        const left = expr.substring(0, i).trim();
        const right = expr.substring(i + 1).trim();
        if (left && right) {
          const leftVal = this.evaluateExpression(left);
          const rightVal = this.evaluateExpression(right);
          
          // If both are numbers, do numeric addition
          if (typeof leftVal === 'number' && typeof rightVal === 'number') {
            return leftVal + rightVal;
          }
          // Otherwise string concatenation
          return String(leftVal) + String(rightVal);
        }
      }
      
      if (expr[i] === '-' && i > 0 && !expr.startsWith('-')) {
        const left = expr.substring(0, i).trim();
        const right = expr.substring(i + 1).trim();
        if (left && right) {
          return this.evaluateExpression(left) - this.evaluateExpression(right);
        }
      }
    }
    
    // Handle multiplication and division (higher precedence)
    for (let i = expr.length - 1; i >= 0; i--) {
      if (this.isInString(expr, i)) continue;
      
      if (expr[i] === '*') {
        const left = expr.substring(0, i).trim();
        const right = expr.substring(i + 1).trim();
        if (left && right) {
          return this.evaluateExpression(left) * this.evaluateExpression(right);
        }
      }
      
      if (expr[i] === '/') {
        const left = expr.substring(0, i).trim();
        const right = expr.substring(i + 1).trim();
        if (left && right) {
          const divisor = this.evaluateExpression(right);
          if (divisor === 0) {
            throw new Error(`Division by zero in expression: ${expr}`);
          }
          return this.evaluateExpression(left) / divisor;
        }
      }
    }
    
    // String literal
    if ((expr.startsWith('"') && expr.endsWith('"')) || 
        (expr.startsWith("'") && expr.endsWith("'"))) {
      return expr.slice(1, -1);
    }
    
    // Boolean literals
    if (expr === 'true') return true;
    if (expr === 'false') return false;
    
    // Number literal (including negative numbers)
    if (!isNaN(expr)) {
      return parseFloat(expr);
    }
    
    // Variable reference
    if (this.variables.hasOwnProperty(expr)) {
      return this.variables[expr];
    }
    
    throw new Error(`Unknown expression: ${expr}`);
  }

  /**
   * Check if a position is inside a string literal
   */
  isInString(expr, pos) {
    let inString = false;
    let stringChar = null;
    for (let i = 0; i < pos; i++) {
      if ((expr[i] === '"' || expr[i] === "'") && (i === 0 || expr[i-1] !== '\\')) {
        if (!inString) {
          inString = true;
          stringChar = expr[i];
        } else if (expr[i] === stringChar) {
          inString = false;
          stringChar = null;
        }
      }
    }
    return inString;
  }

  /**
   * Split expression by operator, respecting strings
   */
  splitExpression(expr, operator) {
    const parts = [];
    let current = '';
    let inString = false;
    let stringChar = null;
    
    for (let i = 0; i < expr.length; i++) {
      const char = expr[i];
      
      if ((char === '"' || char === "'") && (i === 0 || expr[i-1] !== '\\')) {
        if (!inString) {
          inString = true;
          stringChar = char;
        } else if (char === stringChar) {
          inString = false;
          stringChar = null;
        }
        current += char;
      } else if (char === operator && !inString) {
        const trimmed = current.trim();
        if (trimmed) { // Only add non-empty parts
          parts.push(trimmed);
        }
        current = '';
      } else {
        current += char;
      }
    }
    
    const trimmed = current.trim();
    if (trimmed) { // Only add non-empty parts
      parts.push(trimmed);
    }
    
    return parts.length > 0 ? parts : [''];
  }
}

module.exports = ThirstyInterpreter;
