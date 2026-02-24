/**
 * Class and Function Handlers Module
 * Provides function definitions, class declarations, async functions, and module system
 */

const fs = require('fs');
const path = require('path');

/**
 * Class and function handlers class that needs access to interpreter context
 */
class ClassFunctionHandlers {
  constructor(interpreter) {
    this.interpreter = interpreter;
  }

  /**
   * Handle glass (function declaration) - DEPRECATED
   * Legacy string-based parsing removed in favor of AST Parser.
   */
  handleGlass(lines, startIndex) {
    throw new Error('Legacy handleGlass is deprecated. Use AST Parser.');
  }

  /**
   * Handle fountain (class declaration) - DEPRECATED
   * Legacy string-based parsing removed in favor of AST Parser.
   */
  handleFountain(lines, startIndex) {
    throw new Error('Legacy handleFountain is deprecated. Use AST Parser.');
  }

  /**
   * Handle cascade (async function) - DEPRECATED
   * Legacy string-based parsing removed in favor of AST Parser.
   */
  handleCascade(lines, startIndex) {
    throw new Error('Legacy handleCascade is deprecated. Use AST Parser.');
  }

  /**
   * Handle import statement
   * Delegates to AST Parser logic in modern pipeline.
   * Kept for legacy module bridge logic.
   */
  handleImport(line) {
    // Rewiring to use AST-based module loading if possible
    const { Tokenizer } = require('../engine/tokenizer');
    const { Parser } = require('../engine/parser');
    const tokenizer = new Tokenizer(line);
    const tokens = tokenizer.tokenize();
    const parser = new Parser(tokens);
    const node = parser.parseStatement();

    if (node.type === 'ImportStatement') {
      const exports = this.loadModule(node.modulePath);
      if (node.defaultName) {
        this.interpreter.variables[node.defaultName] = exports;
      }
      node.names.forEach(name => {
        if (exports.hasOwnProperty(name)) {
          const exported = exports[name];
          if (exported && typeof exported === 'object' && exported.params) {
            this.interpreter.functions[name] = exported;
          } else {
            this.interpreter.variables[name] = exported;
          }
        } else {
          throw new Error(`Module does not export '${name}'`);
        }
      });
    }
  }

  /**
   * Handle export statement
   */
  handleExport(line) {
    const match = line.match(/export\s+(\w+)/);
    if (match) {
      const varName = match[1];
      if (this.interpreter.variables.hasOwnProperty(varName)) {
        this.interpreter.exports[varName] = this.interpreter.variables[varName];
      } else if (this.interpreter.functions.hasOwnProperty(varName)) {
        this.interpreter.exports[varName] = this.interpreter.functions[varName];
      } else {
        throw new Error(`Cannot export undefined identifier: ${varName}`);
      }
    }
  }

  /**
   * Load a module from file
   */
  loadModule(modulePath) {
    // Resolve relative paths
    let absolutePath = modulePath;
    if (this.interpreter.currentFile && !path.isAbsolute(modulePath)) {
      absolutePath = path.resolve(path.dirname(this.interpreter.currentFile), modulePath);
    }

    // Check cache
    if (this.interpreter.modules[absolutePath]) {
      return this.interpreter.modules[absolutePath];
    }

    // Load and execute module
    if (!fs.existsSync(absolutePath)) {
      throw new Error(`Module not found: ${absolutePath}`);
    }

    const code = fs.readFileSync(absolutePath, 'utf8');

    // Create new interpreter instance for module
    const ThirstyInterpreter = require('../index');
    const moduleInterpreter = new ThirstyInterpreter({
      currentFile: absolutePath,
      security: this.interpreter.securityEnabled,
      securityMode: this.interpreter.securityManager.mode
    });

    // Execute module code
    moduleInterpreter.execute(code);

    // Cache and return exports
    this.interpreter.modules[absolutePath] = moduleInterpreter.exports;
    return moduleInterpreter.exports;
  }

  /**
   * Instantiate a class (new ClassName())
   */
  instantiateClass(className, args) {
    if (!this.interpreter.classes.hasOwnProperty(className)) {
      throw new Error(`Undefined class: ${className}`);
    }

    const classDef = this.interpreter.classes[className];

    // Create instance object
    const instance = {
      __class: className,
      __properties: {},
      __methods: {}
    };

    // Initialize properties with default values
    for (const prop of classDef.properties) {
      instance.__properties[prop.name] = this.interpreter.evaluateExpression(prop.defaultValue);
    }

    // Bind methods to the instance
    for (const methodName in classDef.methods) {
      instance.__methods[methodName] = classDef.methods[methodName];
    }

    // Call constructor if exists (constructor is a special method named 'fountain')
    if (classDef.methods.hasOwnProperty('fountain')) {
      this.callInstanceMethod(instance, 'fountain', args);
    }

    return instance;
  }

  /**
   * Call a method on a class instance
   */
  callInstanceMethod(instance, methodName, args) {
    if (!instance.__methods.hasOwnProperty(methodName)) {
      throw new Error(`Method '${methodName}' not found in class ${instance.__class}`);
    }

    const method = instance.__methods[methodName];

    // Check argument count
    if (args.length !== method.params.length) {
      throw new Error(`Method ${methodName} expects ${method.params.length} arguments, got ${args.length}`);
    }

    // Save current variable scope
    const savedVariables = { ...this.interpreter.variables };

    // Create new scope with method parameters and 'this' reference
    const methodScope = { ...this.interpreter.variables };
    for (let i = 0; i < method.params.length; i++) {
      methodScope[method.params[i]] = args[i];
    }

    // Add 'this' reference to instance properties
    methodScope.this = instance.__properties;

    this.interpreter.variables = methodScope;

    try {
      // Execute method body
      this.interpreter.executeBlock(method.body, 0);

      // Restore variable scope
      this.interpreter.variables = savedVariables;

      return undefined;
    } catch (e) {
      // Handle return statement
      if (e.type === 'return') {
        this.interpreter.variables = savedVariables;
        return e.value;
      }
      // Re-throw other errors
      throw e;
    }
  }

  /**
   * Call a user-defined function
   */
  callFunction(funcName, args) {
    if (!this.interpreter.functions.hasOwnProperty(funcName)) {
      // Check if it's a class name instead
      if (this.interpreter.classes.hasOwnProperty(funcName)) {
        throw new Error(`'${funcName}' is a class, not a function. Cannot call as function.`);
      }
      throw new Error(`Undefined function: ${funcName}`);
    }

    // Check call stack depth
    if (this.interpreter.callStack.length >= this.interpreter.MAX_CALL_DEPTH) {
      throw new Error(`Maximum call depth exceeded (${this.interpreter.MAX_CALL_DEPTH})`);
    }

    const func = this.interpreter.functions[funcName];

    // Check argument count
    if (args.length !== func.params.length) {
      throw new Error(`Function ${funcName} expects ${func.params.length} arguments, got ${args.length}`);
    }

    // If async function, return a promise
    if (func.async) {
      return this.callAsyncFunction(funcName, args);
    }

    // Save current variable scope
    const savedVariables = { ...this.interpreter.variables };

    // Create new scope with function parameters
    const funcScope = { ...this.interpreter.variables };
    for (let i = 0; i < func.params.length; i++) {
      funcScope[func.params[i]] = args[i];
    }
    this.interpreter.variables = funcScope;

    // Track call stack
    this.interpreter.callStack.push({ function: funcName, line: func.line });

    try {
      // Execute function body
      this.interpreter.executeBlock(func.body, 0);

      // Pop call stack
      this.interpreter.callStack.pop();

      // Restore variable scope
      this.interpreter.variables = savedVariables;

      return undefined;
    } catch (e) {
      // Handle return statement
      if (e.type === 'return') {
        this.interpreter.callStack.pop();
        this.interpreter.variables = savedVariables;
        return e.value;
      }
      // Re-throw other errors
      throw e;
    }
  }

  /**
   * Call an async function (cascade)
   */
  async callAsyncFunction(funcName, args) {
    const func = this.interpreter.functions[funcName];

    // Save current variable scope
    const savedVariables = { ...this.interpreter.variables };

    // Create new scope with function parameters
    const funcScope = { ...this.interpreter.variables };
    for (let i = 0; i < func.params.length; i++) {
      funcScope[func.params[i]] = args[i];
    }
    this.interpreter.variables = funcScope;

    // Track call stack
    this.interpreter.callStack.push({ function: funcName, line: func.line });

    try {
      // Execute function body asynchronously
      await this.interpreter.executeBlockAsync(func.body, 0);

      // Pop call stack
      this.interpreter.callStack.pop();

      // Restore variable scope
      this.interpreter.variables = savedVariables;

      return undefined;
    } catch (e) {
      // Handle return statement
      if (e.type === 'return') {
        this.interpreter.callStack.pop();
        this.interpreter.variables = savedVariables;
        return e.value;
      }
      // Re-throw other errors
      throw e;
    }
  }

  /**
   * Execute a block of code asynchronously
   */
  async executeBlockAsync(lines, startIndex) {
    let i = startIndex;

    while (i < lines.length) {
      const line = lines[i].trim();

      // Skip empty lines and comments
      if (!line || line.startsWith('//')) {
        i++;
        continue;
      }

      // Handle await keyword
      if (line.startsWith('await ')) {
        const expr = line.substring(6).trim();
        const result = await this.evaluateExpressionAsync(expr);
        i++;
        continue;
      }

      // Handle variable assignment with await
      if (line.startsWith('drink ') && line.includes('await ')) {
        const match = line.match(/drink\s+(\w+)\s*=\s*await\s+(.+)/);
        if (match) {
          const varName = match[1];
          const expr = match[2];
          const value = await this.evaluateExpressionAsync(expr);
          this.interpreter.variables[varName] = value;
          i++;
          continue;
        }
      }

      // For other statements, execute normally
      if (line.startsWith('thirsty ')) {
        i = this.interpreter.handleThirsty(lines, i);
      } else if (line.startsWith('refill ')) {
        i = this.interpreter.handleRefill(lines, i);
      } else if (line.startsWith('return ')) {
        const value = await this.evaluateExpressionAsync(line.substring(7).trim());
        throw { type: 'return', value: value };
      } else if (line === 'return') {
        throw { type: 'return', value: undefined };
      } else if (line === '}') {
        return i + 1;
      } else {
        this.interpreter.executeLine(line);
        i++;
      }
    }

    return i;
  }

  /**
   * Evaluate an expression asynchronously (for await)
   */
  async evaluateExpressionAsync(expr) {
    expr = expr.trim();

    // Check if it's a function call
    const funcCallMatch = expr.match(/^(\w+)\s*\(([^)]*)\)$/);
    if (funcCallMatch) {
      const funcName = funcCallMatch[1];
      const argsStr = funcCallMatch[2].trim();
      const args = argsStr ? this.interpreter.parseArguments(argsStr) : [];
      const evaluatedArgs = args.map(arg => this.interpreter.evaluateExpression(arg));

      // If it's an async function, await it
      if (this.interpreter.asyncFunctions.has(funcName)) {
        return await this.callAsyncFunction(funcName, evaluatedArgs);
      }

      // Otherwise call normally
      const result = this.callFunction(funcName, evaluatedArgs);

      // If result is a promise, await it
      if (result && typeof result.then === 'function') {
        return await result;
      }

      return result;
    }

    // Check if it's a method call (e.g., Http.get(...))
    const methodCallMatch = expr.match(/^(\w+)\.(\w+)\s*\(([^)]*)\)$/);
    if (methodCallMatch) {
      const objName = methodCallMatch[1];
      const methodName = methodCallMatch[2];
      const argsStr = methodCallMatch[3].trim();
      const args = argsStr ? this.interpreter.parseArguments(argsStr) : [];
      const evaluatedArgs = args.map(arg => this.interpreter.evaluateExpression(arg));

      if (this.interpreter.variables.hasOwnProperty(objName)) {
        const obj = this.interpreter.variables[objName];
        if (obj && typeof obj === 'object' && obj[methodName]) {
          const result = obj[methodName](...evaluatedArgs);

          // If result is a promise, await it
          if (result && typeof result.then === 'function') {
            return await result;
          }

          return result;
        }
      }
    }

    // For other expressions, evaluate synchronously
    return this.interpreter.evaluateExpression(expr);
  }
}

module.exports = { ClassFunctionHandlers };
