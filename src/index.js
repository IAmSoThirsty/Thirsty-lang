#!/usr/bin/env node

/**
 * Thirsty-Lang Interpreter
 * Enterprise-grade programming language with defensive security capabilities
 *
 * Architecture:  Source → Tokenizer → Parser → AST → Interpreter
 */

const { SecurityManager } = require('./security/index');
const { initializeStandardLibrary } = require('./interpreter/stdlib');
const { ClassFunctionHandlers } = require('./interpreter/class-function-handlers');
const { Tokenizer } = require('./engine/tokenizer');
const { Parser } = require('./engine/parser');
const { ASTInterpreter, ThirstyError } = require('./engine/ast-interpreter');
const { Logger } = require('./engine/logger');
const fs = require('fs');
const path = require('path');

class ThirstyInterpreter {
  constructor(options = {}) {
    this.variables = {};
    this.functions = {};   // Store user-defined functions
    this.classes = {};     // Store class definitions
    this.arrays = {};      // Store arrays (reservoirs)
    this.callStack = [];   // Track function calls for debugging
    this.MAX_LOOP_ITERATIONS = 10000; // Safety limit for loops
    this.MAX_CALL_DEPTH = 100;        // Prevent stack overflow

    // Module system
    this.modules = {}; // Cache for loaded modules
    this.exports = {}; // Exported identifiers
    this.logger = new Logger({ component: 'THIRSTY_RUNTIME', json: !!options.jsonLogs });

    // Core Security Manager (T.A.R.L. Bridge)
    this.currentFile = options.currentFile || null;

    // Async/await support
    this.asyncFunctions = new Set();
    this.pendingPromises = [];

    // Security features
    this.securityEnabled = options.security !== false;
    // Bypass T.A.R.L. bridge on Windows (sandbox-exec is macOS-only)
    const useTarl = this.securityEnabled && process.platform !== 'win32';

    this.securityManager = new SecurityManager({
      enabled: this.securityEnabled,
      mode: options.securityMode || 'defensive',
      policy: { securityLevel: options.securityLevel || 'moderate' },
      useTarl: useTarl
    });
    this.shieldActive = false;
    this.shieldContext = null;
    this.armoredVariables = new Set();
    this.sanitizedVariables = new Set();

    // Legacy module loader (for import statements)
    this.classFunctionHandlers = new ClassFunctionHandlers(this);

    // Initialize standard library
    this.initializeStandardLibrary();
  }

  /**
   * Define a variable in the global environment
   */
  define(name, value) {
    this.variables[name] = value;
  }

  /**
   * Armor a variable to prevent further modification
   */
  armor(name) {
    this.armoredVariables.add(name);
  }

  /**
   * Activate a shield block
   */
  activateShield(name, context = {}) {
    this.shieldActive = true;
    this.shieldContext = { name, ...context };
    this.logger.info(`Shield '${name}' activated`);
  }

  /**
   * Deactivate current shield block
   */
  deactivateShield() {
    this.shieldActive = false;
    this.shieldContext = null;
  }

  /**
   * Initialize the standard library with built-in functions
   */
  initializeStandardLibrary() {
    const stdlib = initializeStandardLibrary();
    const { initializeDB } = require('./interpreter/db');
    const db = initializeDB();

    // Add all stdlib objects to variables
    this.variables.Math = stdlib.Math;
    this.variables.String = stdlib.String;
    this.variables.Console = stdlib.Console;
    this.variables.Process = stdlib.Process;
    this.variables.Crypto = stdlib.Crypto;
    this.variables.Time = stdlib.Time;
    this.variables.File = stdlib.File;
    this.variables.Http = stdlib.Http;
    this.variables.JSON = stdlib.JSON;
    this.variables.Db = db;

    // Add the fetch method that needs access to this.variables
    this.variables.Http.fetch = stdlib.Http._createFetch(this.variables.Http);
  }

  /**
   * Parse and execute Thirsty-Lang code
   * @param {string} code - The Thirsty-Lang source code
   */
  execute(code) {
    try {
      // Phase 1: Tokenize
      const tokenizer = new Tokenizer(code);
      const tokens = tokenizer.tokenize();

      // Phase 2: Parse
      const parser = new Parser(tokens);
      const ast = parser.parse();

      // Phase 3: Interpret
      const interpreter = new ASTInterpreter(this);

      // Initialize environment with current variables
      for (const [k, v] of Object.entries(this.variables)) {
        interpreter.globalEnv.define(k, v);
      }

      // Load user-defined functions and classes into the AST engine
      interpreter.functions = { ...this.functions };
      interpreter.classes = { ...this.classes };

      interpreter.run(ast);

      // Sync state back to the host
      this.variables = interpreter.globalEnv.allVariables();
      this.functions = { ...interpreter.functions };
      this.classes = { ...interpreter.classes };
    } catch (error) {
      if (error instanceof ThirstyError) throw error;
      throw ThirstyError.fromError(error);
    }
  }

  /**
   * Evaluate a single expression and return its value.
   * @param {string} expr - Expression string
   * @returns {*} The evaluated value
   */
  evaluateExpression(expr) {
    const tokenizer = new Tokenizer(expr);
    const tokens = tokenizer.tokenize();
    const parser = new Parser(tokens);
    const exprNode = parser.parseExpression();

    const interpreter = new ASTInterpreter(this);
    // Populate environment from current variables
    for (const [k, v] of Object.entries(this.variables)) {
      interpreter.globalEnv.define(k, v);
    }

    return interpreter.evalExpr(exprNode, interpreter.globalEnv);
  }

  /**
   * Execute a block of code (AST-based)
   * Replacing deprecated executeBlock string-based logic.
   */
  executeBlock(code) {
    this.execute(code);
  }

  /**
   * Handle function calls via AST engine.
   */
  callFunction(funcName, args) {
    const interpreter = new ASTInterpreter(this);

    // Check call stack depth
    if (this.callStack.length >= this.MAX_CALL_DEPTH) {
      throw new ThirstyError(`Maximum call depth exceeded (${this.MAX_CALL_DEPTH})`, 'StackOverflow');
    }

    // Populate from current state
    for (const [k, v] of Object.entries(this.variables)) {
      interpreter.globalEnv.define(k, v);
    }
    interpreter.functions = { ...this.functions };
    interpreter.classes = { ...this.classes };

    const result = interpreter.callFunction(funcName, args, interpreter.globalEnv);

    // Sync back
    this.variables = interpreter.globalEnv.allVariables();
    return result;
  }

  /**
   * Instantiate a class via AST engine.
   */
  instantiateClass(className, args) {
    const interpreter = new ASTInterpreter(this);
    for (const [k, v] of Object.entries(this.variables)) {
      interpreter.globalEnv.define(k, v);
    }
    interpreter.classes = { ...this.classes };
    interpreter.functions = { ...this.functions };

    return interpreter.instantiateClass(className, args, interpreter.globalEnv);
  }

  /**
   * Call method on class instance via AST engine.
   */
  callInstanceMethod(instance, methodName, args) {
    const interpreter = new ASTInterpreter(this);
    for (const [k, v] of Object.entries(this.variables)) {
      interpreter.globalEnv.define(k, v);
    }
    return interpreter.callInstanceMethod(instance, methodName, args, interpreter.globalEnv);
  }
}

module.exports = { ThirstyInterpreter };
