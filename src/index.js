#!/usr/bin/env node

/**
 * Thirsty-lang Interpreter
 * A fun programming language for the thirsty
 */

class ThirstyInterpreter {
  constructor() {
    this.variables = {};
    this.MAX_LOOP_ITERATIONS = 10000; // Safety limit for loops
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
    // drink - Variable declaration
    if (line.startsWith('drink ')) {
      this.handleDrink(line);
    }
    // pour - Output statement
    else if (line.startsWith('pour ')) {
      this.handlePour(line);
    }
    // sip - Input statement (placeholder)
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
   * Handle input statement: sip varname
   */
  handleSip(line) {
    // Placeholder for input functionality
    console.log('Input functionality not yet implemented');
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
