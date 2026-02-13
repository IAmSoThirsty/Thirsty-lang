/**
 * Control Flow Handlers Module
 * Provides conditional (thirsty/hydrated) and loop (refill) functionality
 */

/**
 * Control flow handlers class that needs access to interpreter context
 */
class ControlFlowHandlers {
  constructor(interpreter) {
    this.interpreter = interpreter;
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
    const thenBlockEnd = this.interpreter.findMatchingBrace(lines, startIndex);

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
      this.interpreter.executeBlock(lines.slice(startIndex + 1, thenBlockEnd), 0);

      // Skip past hydrated block if it exists
      if (hydratedStart !== -1) {
        const hydratedEnd = this.interpreter.findMatchingBrace(lines, thenBlockEnd + 1);
        if (hydratedEnd === -1) {
          throw new Error(`Unmatched opening brace for hydrated block at line ${thenBlockEnd + 2}`);
        }
        return hydratedEnd + 1;
      }

      return thenBlockEnd + 1;
    } else if (hydratedStart !== -1) {
      // Execute the hydrated (else) block
      const hydratedEnd = this.interpreter.findMatchingBrace(lines, thenBlockEnd + 1);
      if (hydratedEnd === -1) {
        throw new Error(`Unmatched opening brace for hydrated block at line ${thenBlockEnd + 2}`);
      }
      this.interpreter.executeBlock(lines.slice(hydratedStart, hydratedEnd), 0);
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
      return this.interpreter.evaluateExpression(parts[0]) === this.interpreter.evaluateExpression(parts[1]);
    }
    if (condition.includes('!=')) {
      const parts = condition.split('!=', 2).map(p => p.trim());
      return this.interpreter.evaluateExpression(parts[0]) !== this.interpreter.evaluateExpression(parts[1]);
    }
    if (condition.includes('>=')) {
      const parts = condition.split('>=', 2).map(p => p.trim());
      return this.interpreter.evaluateExpression(parts[0]) >= this.interpreter.evaluateExpression(parts[1]);
    }
    if (condition.includes('<=')) {
      const parts = condition.split('<=', 2).map(p => p.trim());
      return this.interpreter.evaluateExpression(parts[0]) <= this.interpreter.evaluateExpression(parts[1]);
    }
    if (condition.includes('>')) {
      const parts = condition.split('>', 2).map(p => p.trim());
      return this.interpreter.evaluateExpression(parts[0]) > this.interpreter.evaluateExpression(parts[1]);
    }
    if (condition.includes('<')) {
      const parts = condition.split('<', 2).map(p => p.trim());
      return this.interpreter.evaluateExpression(parts[0]) < this.interpreter.evaluateExpression(parts[1]);
    }

    // Boolean expression
    return Boolean(this.interpreter.evaluateExpression(condition));
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
    const blockEnd = this.interpreter.findMatchingBrace(lines, startIndex);

    if (blockEnd === -1) {
      throw new Error(`Unmatched opening brace for refill statement at line ${startIndex + 1}`);
    }

    // Execute the loop
    let iterations = 0;

    while (this.evaluateCondition(condition) && iterations < this.interpreter.MAX_LOOP_ITERATIONS) {
      this.interpreter.executeBlock(lines.slice(startIndex + 1, blockEnd), 0);
      iterations++;
    }

    if (iterations >= this.interpreter.MAX_LOOP_ITERATIONS) {
      throw new Error(`Loop exceeded maximum iterations (${this.interpreter.MAX_LOOP_ITERATIONS})`);
    }

    return blockEnd + 1;
  }
}

module.exports = { ControlFlowHandlers };
