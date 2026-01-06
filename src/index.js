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
   * Handle thirsty (if) statement
   */
  handleThirsty(lines, startIndex) {
    const line = lines[startIndex].trim();
    const match = line.match(/thirsty\s+(.+)\s*{/);
    
    if (!match) {
      throw new Error(`Invalid thirsty statement: ${line}`);
    }
    
    const condition = this.evaluateCondition(match[1]);
    
    // Find the matching closing brace and hydrated block if exists
    let braceCount = 1;
    let i = startIndex + 1;
    let thenBlockEnd = -1;
    let hydratedStart = -1;
    
    while (i < lines.length && braceCount > 0) {
      const currentLine = lines[i].trim();
      // Count braces, but only in non-comment, non-string parts
      // Simple approach: only count standalone braces on lines that start with them
      if (currentLine.startsWith('thirsty ') && currentLine.endsWith('{')) {
        braceCount++;
      } else if (currentLine.startsWith('refill ') && currentLine.endsWith('{')) {
        braceCount++;
      } else if (currentLine === 'hydrated {') {
        braceCount++;
      } else if (currentLine === '}') {
        braceCount--;
        if (braceCount === 0) {
          thenBlockEnd = i;
          break;
        }
      }
      i++;
    }
    
    // Check for hydrated (else) block
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
        let braceCount = 1;
        let j = hydratedStart;
        while (j < lines.length && braceCount > 0) {
          const currentLine = lines[j].trim();
          if (currentLine.startsWith('thirsty ') && currentLine.endsWith('{')) {
            braceCount++;
          } else if (currentLine.startsWith('refill ') && currentLine.endsWith('{')) {
            braceCount++;
          } else if (currentLine === 'hydrated {') {
            braceCount++;
          } else if (currentLine === '}') {
            braceCount--;
            if (braceCount === 0) {
              return j + 1;
            }
          }
          j++;
        }
      }
      
      return thenBlockEnd + 1;
    } else if (hydratedStart !== -1) {
      // Execute the hydrated (else) block
      let braceCount = 1;
      let j = hydratedStart;
      while (j < lines.length && braceCount > 0) {
        const currentLine = lines[j].trim();
        if (currentLine.startsWith('thirsty ') && currentLine.endsWith('{')) {
          braceCount++;
        } else if (currentLine.startsWith('refill ') && currentLine.endsWith('{')) {
          braceCount++;
        } else if (currentLine === 'hydrated {') {
          braceCount++;
        } else if (currentLine === '}') {
          braceCount--;
          if (braceCount === 0) {
            this.executeBlock(lines.slice(hydratedStart, j), 0);
            return j + 1;
          }
        }
        j++;
      }
    }
    
    return thenBlockEnd + 1;
  }

  /**
   * Evaluate a condition for if statements
   * Note: Only handles simple binary comparisons (a op b), not complex expressions
   */
  evaluateCondition(condition) {
    condition = condition.trim();
    
    // Comparison operators (check in order of specificity to avoid conflicts)
    // e.g., check >= before >, <= before <, != before =
    if (condition.includes('==')) {
      const parts = condition.split('==', 2).map(p => p.trim());
      return this.evaluateExpression(parts[0]) == this.evaluateExpression(parts[1]);
    }
    if (condition.includes('!=')) {
      const parts = condition.split('!=', 2).map(p => p.trim());
      return this.evaluateExpression(parts[0]) != this.evaluateExpression(parts[1]);
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
    let braceCount = 1;
    let i = startIndex + 1;
    let blockEnd = -1;
    
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
          blockEnd = i;
          break;
        }
      }
      i++;
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
   * Evaluate an expression (variable or literal)
   */
  evaluateExpression(expr) {
    expr = expr.trim();
    
    // String concatenation with +
    if (expr.includes('+') && !this.isInString(expr, expr.indexOf('+'))) {
      const parts = this.splitExpression(expr, '+');
      let result = '';
      for (const part of parts) {
        const val = this.evaluateExpression(part);
        result += String(val);
      }
      return result;
    }
    
    // Arithmetic operations
    if (expr.includes('-') && !this.isInString(expr, expr.indexOf('-')) && !expr.startsWith('-')) {
      const parts = this.splitExpression(expr, '-');
      let result = this.evaluateExpression(parts[0]);
      for (let i = 1; i < parts.length; i++) {
        result -= this.evaluateExpression(parts[i]);
      }
      return result;
    }
    
    if (expr.includes('*') && !this.isInString(expr, expr.indexOf('*'))) {
      const parts = this.splitExpression(expr, '*');
      let result = this.evaluateExpression(parts[0]);
      for (let i = 1; i < parts.length; i++) {
        result *= this.evaluateExpression(parts[i]);
      }
      return result;
    }
    
    if (expr.includes('/') && !this.isInString(expr, expr.indexOf('/'))) {
      const parts = this.splitExpression(expr, '/');
      let result = this.evaluateExpression(parts[0]);
      for (let i = 1; i < parts.length; i++) {
        result /= this.evaluateExpression(parts[i]);
      }
      return result;
    }
    
    // String literal
    if ((expr.startsWith('"') && expr.endsWith('"')) || 
        (expr.startsWith("'") && expr.endsWith("'"))) {
      return expr.slice(1, -1);
    }
    
    // Boolean literals
    if (expr === 'true') return true;
    if (expr === 'false') return false;
    
    // Number literal
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
        parts.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }
    
    if (current) {
      parts.push(current.trim());
    }
    
    return parts;
  }
}

module.exports = ThirstyInterpreter;
