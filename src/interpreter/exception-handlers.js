//                                           [2026-03-03 13:45]
//                                          Productivity: Active
/**
 * Exception Handlers Module
 * Provides try/catch/finally/throw functionality for error handling
 *
 * MAXIMUM ALLOWED DESIGN:
 * - Complete exception handling with stack traces
 * - Support for typed exceptions
 * - Finally block with guaranteed execution
 * - Nested try/catch support
 * - Error propagation and bubbling
 * - Integration with existing error system
 */

/**
 * ThirstyError - Base error class for Thirsty-lang exceptions
 */
class ThirstyError extends Error {
  constructor(message, type = 'Error', context = {}) {
    super(message);
    this.name = `Thirsty${type}`;
    this.thirstyType = type;
    this.context = context;
    this.timestamp = new Date().toISOString();

    // Capture stack trace
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ThirstyError);
    }
  }

  /**
   * Convert to Thirsty-lang error object
   */
  toThirstyObject() {
    return {
      message: this.message,
      type: this.thirstyType,
      name: this.name,
      stack: this.stack,
      context: this.context,
      timestamp: this.timestamp
    };
  }

  /**
   * Create from JavaScript Error
   */
  static fromError(err, context = {}) {
    if (err instanceof ThirstyError) {
      return err;
    }
    const thirstyErr = new ThirstyError(err.message, 'Error', context);
    thirstyErr.stack = err.stack;
    return thirstyErr;
  }
}

/**
 * Exception Handlers class for try/catch/finally/throw
 */
class ExceptionHandlers {
  constructor(interpreter) {
    this.interpreter = interpreter;
    this.exceptionStack = []; // Track exception context
  }

  /**
   * Handle try block
   *
   * Syntax:
   *   try {
   *     // code that may throw
   *   } catch (error) {
   *     // error handling
   *   } finally {
   *     // cleanup (optional)
   *   }
   */
  handleTry(lines, startIndex) {
    const line = lines[startIndex].trim();

    if (!line.match(/^try\s*{$/)) {
      throw new Error(`Invalid try statement: ${line}`);
    }

    // Find try block boundaries
    const tryBlockEnd = this.interpreter.findMatchingBrace(lines, startIndex);
    if (tryBlockEnd === -1) {
      throw new Error(`Unmatched opening brace for try block at line ${startIndex + 1}`);
    }

    // Look for catch block
    let catchStart = -1;
    let catchEnd = -1;
    let catchVar = null;
    let finallyStart = -1;
    let finallyEnd = -1;

    let nextIdx = tryBlockEnd;

    // Check for catch block - could be on same line as closing brace or next line
    let currentLine = lines[nextIdx].trim();

    // Check if catch is on the closing brace line (e.g., "} catch (e) {")
    const inlineCatchMatch = currentLine.match(/}\s*catch\s*\((\w+)\)\s*{$/);
    if (inlineCatchMatch) {
      catchVar = inlineCatchMatch[1];
      catchStart = nextIdx + 1;
      catchEnd = this.findNextMatchingBrace(lines, nextIdx);

      if (catchEnd === -1) {
        throw new Error(`Unmatched opening brace for catch block at line ${nextIdx + 1}`);
      }

      nextIdx = catchEnd;
      currentLine = lines[nextIdx].trim();
    } else if (!currentLine.match(/}\s*finally\s*{$/)) {
      // Only advance if this line is not an inline finally (e.g., "} finally {")
      // Check next line for catch
      const peekIdx = tryBlockEnd + 1;
      if (peekIdx < lines.length) {
        const peekedLine = lines[peekIdx].trim();
        const catchMatch = peekedLine.match(/^catch\s*\((\w+)\)\s*{$/);

        if (catchMatch) {
          nextIdx = peekIdx;
          catchVar = catchMatch[1];
          catchStart = nextIdx + 1;
          catchEnd = this.interpreter.findMatchingBrace(lines, nextIdx);

          if (catchEnd === -1) {
            throw new Error(`Unmatched opening brace for catch block at line ${nextIdx + 1}`);
          }

          nextIdx = catchEnd;
          currentLine = lines[nextIdx].trim();
        }
      }
    }

    // Check for finally block - could be on same line as closing brace or next line
    // Check if finally is on the current closing brace line (e.g., "} finally {")
    const inlineFinallyMatch = currentLine.match(/}\s*finally\s*{$/);
    if (inlineFinallyMatch) {
      finallyStart = nextIdx + 1;
      finallyEnd = this.findNextMatchingBrace(lines, nextIdx);

      if (finallyEnd === -1) {
        throw new Error(`Unmatched opening brace for finally block at line ${nextIdx + 1}`);
      }

      nextIdx = finallyEnd;
    } else {
      // Check next line for finally
      const finallyPeekIdx = nextIdx + 1;
      if (finallyPeekIdx < lines.length) {
        const finallyLine = lines[finallyPeekIdx].trim();

        if (finallyLine === 'finally {') {
          nextIdx = finallyPeekIdx;
          finallyStart = nextIdx + 1;
          finallyEnd = this.interpreter.findMatchingBrace(lines, nextIdx);

          if (finallyEnd === -1) {
            throw new Error(`Unmatched opening brace for finally block at line ${nextIdx + 1}`);
          }

          nextIdx = finallyEnd;
        }
      }
    }

    // Must have at least catch or finally
    if (catchStart === -1 && finallyStart === -1) {
      throw new Error('try block must have at least a catch or finally block');
    }

    // Execute try block with exception handling
    let caughtError = null;
    let tryResult = null;

    try {
      // Push exception context
      this.exceptionStack.push({
        type: 'try',
        lineStart: startIndex,
        lineEnd: tryBlockEnd
      });

      // Execute try block
      const tryLines = lines.slice(startIndex + 1, tryBlockEnd);
      tryResult = this.interpreter.executeBlock(tryLines, 0);

    } catch (err) {
      // Catch any error (including returns)
      if (err && err.type === 'return') {
        // Return statements propagate through
        caughtError = err;
      } else {
        // Regular error - convert to ThirstyError
        caughtError = ThirstyError.fromError(err, {
          tryBlock: true,
          lineStart: startIndex,
          lineEnd: tryBlockEnd
        });
      }
    } finally {
      this.exceptionStack.pop();
    }

    // Execute catch block if error was caught and catch exists
    if (caughtError && caughtError.type !== 'return' && catchStart !== -1) {
      try {
        // Push exception context
        this.exceptionStack.push({
          type: 'catch',
          lineStart: catchStart - 1,
          lineEnd: catchEnd,
          error: caughtError
        });

        // Set catch variable to error object
        if (caughtError instanceof ThirstyError) {
          this.interpreter.variables[catchVar] = caughtError.toThirstyObject();
        } else {
          this.interpreter.variables[catchVar] = {
            message: String(caughtError),
            type: 'Error',
            stack: null
          };
        }

        // Execute catch block
        const catchLines = lines.slice(catchStart, catchEnd);
        this.interpreter.executeBlock(catchLines, 0);

        // Error was handled
        caughtError = null;

      } catch (catchErr) {
        // Error in catch block becomes new error
        if (catchErr && catchErr.type === 'return') {
          caughtError = catchErr;
        } else {
          caughtError = ThirstyError.fromError(catchErr, {
            catchBlock: true,
            originalError: caughtError
          });
        }
      } finally {
        this.exceptionStack.pop();
      }
    }

    // Execute finally block (guaranteed)
    if (finallyStart !== -1) {
      try {
        this.exceptionStack.push({
          type: 'finally',
          lineStart: finallyStart - 1,
          lineEnd: finallyEnd
        });

        const finallyLines = lines.slice(finallyStart, finallyEnd);
        this.interpreter.executeBlock(finallyLines, 0);

      } catch (finallyErr) {
        // Error in finally block overrides previous error
        if (finallyErr && finallyErr.type === 'return') {
          caughtError = finallyErr;
        } else {
          caughtError = ThirstyError.fromError(finallyErr, {
            finallyBlock: true,
            originalError: caughtError
          });
        }
      } finally {
        this.exceptionStack.pop();
      }
    }

    // Re-throw uncaught error
    if (caughtError) {
      throw caughtError;
    }

    // Return index of first line AFTER the entire try/catch/finally structure.
    // nextIdx currently points to the closing brace of the last block;
    // adding 1 lets executeBlock continue with the next statement.
    return nextIdx + 1;
  }

  /**
   * Handle throw statement
   *
   * Syntax:
   *   throw "error message"
   *   throw expression
   *   throw { message: "...", type: "..." }
   */
  handleThrow(line) {
    const throwMatch = line.match(/^throw\s+(.+)$/);

    if (!throwMatch) {
      throw new Error(`Invalid throw statement: ${line}`);
    }

    const expression = throwMatch[1].trim();

    // Evaluate the expression to throw
    let value;
    try {
      value = this.interpreter.evaluateExpression(expression);
    } catch (err) {
      throw new ThirstyError('Error evaluating throw expression', 'EvaluationError', {
        expression,
        cause: err.message
      });
    }

    // Create ThirstyError from thrown value
    let error;

    if (typeof value === 'string') {
      error = new ThirstyError(value, 'ThrownError');
    } else if (typeof value === 'object' && value !== null) {
      const message = value.message || String(value);
      const type = value.type || 'ThrownError';
      error = new ThirstyError(message, type, value);
    } else {
      error = new ThirstyError(String(value), 'ThrownError');
    }

    throw error;
  }

  /**
   * Get current exception context
   */
  getExceptionContext() {
    return this.exceptionStack[this.exceptionStack.length - 1] || null;
  }

  /**
   * Get full exception stack
   */
  getExceptionStack() {
    return [...this.exceptionStack];
  }

  /**
   * Find matching brace for inline catch/finally blocks.
   * Starts from a line that contains both } and { (e.g., "} catch (e) {").
   *
   * Key rule: "} catch/finally {" is treated as closing OUR block only when
   * we are at depth 1 (braceCount === 1). When nested deeper (braceCount > 1),
   * it is a sibling transition inside an inner block and has net effect of 0.
   */
  findNextMatchingBrace(lines, startIndex) {
    let braceCount = 1;
    let i = startIndex + 1;

    while (i < lines.length && braceCount > 0) {
      const currentLine = lines[i].trim();

      if (currentLine.includes('} catch') || currentLine.includes('} finally')) {
        if (braceCount === 1) {
          // At the top level of the block we're scanning: this closes our block.
          braceCount--;
          if (braceCount === 0) {
            return i;
          }
        }
        // else: this } catch/finally is inside a nested block — net 0, skip.
      } else {
        const openCount = (currentLine.match(/{/g) || []).length;
        const closeCount = (currentLine.match(/}/g) || []).length;
        braceCount += openCount - closeCount;
        if (braceCount === 0) {
          return i;
        }
      }

      i++;
    }

    return -1; // No matching brace found
  }
}

module.exports = { ExceptionHandlers, ThirstyError };
