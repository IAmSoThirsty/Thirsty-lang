#!/usr/bin/env node

/**
 * Thirsty-lang Interpreter
 * Enterprise-grade programming language with defensive security capabilities
 */

const { SecurityManager } = require('./security/index');
const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

class ThirstyInterpreter {
  constructor(options = {}) {
    this.variables = {};
    this.functions = {}; // Store user-defined functions
    this.classes = {}; // Store class definitions
    this.arrays = {}; // Store arrays (reservoirs)
    this.callStack = []; // Track function calls for debugging
    this.MAX_LOOP_ITERATIONS = 10000; // Safety limit for loops
    this.MAX_CALL_DEPTH = 100; // Prevent stack overflow
    
    // Module system
    this.modules = {}; // Cache for loaded modules
    this.exports = {}; // Exports from current module
    this.currentFile = options.currentFile || null; // Current file being executed
    
    // Async/await support
    this.asyncFunctions = new Set(); // Track async functions
    this.pendingPromises = []; // Track pending promises
    
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
    
    // Initialize standard library
    this.initializeStandardLibrary();
  }
  
  /**
   * Initialize the standard library with built-in functions
   */
  initializeStandardLibrary() {
    // Math utilities
    this.variables.Math = {
      __builtin: true,
      PI: 3.14159265359,
      E: 2.71828182846,
      abs: (x) => Math.abs(x),
      sqrt: (x) => Math.sqrt(x),
      pow: (x, y) => Math.pow(x, y),
      floor: (x) => Math.floor(x),
      ceil: (x) => Math.ceil(x),
      round: (x) => Math.round(x),
      min: (...args) => Math.min(...args),
      max: (...args) => Math.max(...args),
      random: () => Math.random()
    };
    
    // String utilities
    this.variables.String = {
      __builtin: true,
      toUpperCase: (str) => String(str).toUpperCase(),
      toLowerCase: (str) => String(str).toLowerCase(),
      trim: (str) => String(str).trim(),
      split: (str, separator) => String(str).split(separator),
      replace: (str, search, replacement) => String(str).replace(search, replacement),
      charAt: (str, index) => String(str).charAt(index),
      substring: (str, start, end) => String(str).substring(start, end)
    };
    
    // File I/O utilities
    this.variables.File = {
      __builtin: true,
      read: (filePath) => {
        try {
          return fs.readFileSync(filePath, 'utf8');
        } catch (err) {
          throw new Error(`Failed to read file: ${err.message}`);
        }
      },
      write: (filePath, content) => {
        try {
          fs.writeFileSync(filePath, String(content), 'utf8');
          return true;
        } catch (err) {
          throw new Error(`Failed to write file: ${err.message}`);
        }
      },
      exists: (filePath) => {
        return fs.existsSync(filePath);
      },
      delete: (filePath) => {
        try {
          fs.unlinkSync(filePath);
          return true;
        } catch (err) {
          throw new Error(`Failed to delete file: ${err.message}`);
        }
      },
      readAsync: async (filePath) => {
        return new Promise((resolve, reject) => {
          fs.readFile(filePath, 'utf8', (err, data) => {
            if (err) reject(new Error(`Failed to read file: ${err.message}`));
            else resolve(data);
          });
        });
      },
      writeAsync: async (filePath, content) => {
        return new Promise((resolve, reject) => {
          fs.writeFile(filePath, String(content), 'utf8', (err) => {
            if (err) reject(new Error(`Failed to write file: ${err.message}`));
            else resolve(true);
          });
        });
      }
    };
    
    // Network utilities (HTTP requests)
    this.variables.Http = {
      __builtin: true,
      get: (url) => {
        return new Promise((resolve, reject) => {
          const urlObj = new URL(url);
          const protocol = urlObj.protocol === 'https:' ? https : http;
          
          protocol.get(url, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
              resolve({
                status: res.statusCode,
                headers: res.headers,
                body: data
              });
            });
          }).on('error', (err) => {
            reject(new Error(`HTTP GET failed: ${err.message}`));
          });
        });
      },
      post: (url, postData) => {
        return new Promise((resolve, reject) => {
          const urlObj = new URL(url);
          const protocol = urlObj.protocol === 'https:' ? https : http;
          const data = typeof postData === 'string' ? postData : JSON.stringify(postData);
          
          const options = {
            hostname: urlObj.hostname,
            port: urlObj.port,
            path: urlObj.pathname + urlObj.search,
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Content-Length': Buffer.byteLength(data)
            }
          };
          
          const req = protocol.request(options, (res) => {
            let responseData = '';
            res.on('data', (chunk) => { responseData += chunk; });
            res.on('end', () => {
              resolve({
                status: res.statusCode,
                headers: res.headers,
                body: responseData
              });
            });
          });
          
          req.on('error', (err) => {
            reject(new Error(`HTTP POST failed: ${err.message}`));
          });
          
          req.write(data);
          req.end();
        });
      },
      fetch: async (url, options = {}) => {
        const method = (options.method || 'GET').toUpperCase();
        if (method === 'POST' || method === 'PUT' || method === 'PATCH') {
          return this.variables.Http.post(url, options.body || '');
        } else {
          return this.variables.Http.get(url);
        }
      }
    };
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
      
      // Handle module imports/exports
      if (line.startsWith('import ')) {
        this.handleImport(line);
        i++;
        continue;
      } else if (line.startsWith('export ')) {
        this.handleExport(line);
        i++;
        continue;
      }
      
      // Handle async function declarations (cascade keyword)
      if (line.startsWith('cascade ')) {
        i = this.handleCascade(lines, i);
        continue;
      }
      
      // Handle control flow
      if (line.startsWith('thirsty ')) {
        i = this.handleThirsty(lines, i);
      } else if (line.startsWith('refill ')) {
        i = this.handleRefill(lines, i);
      } else if (line.startsWith('shield ')) {
        i = this.handleShield(lines, i);
      } else if (line.startsWith('glass ')) {
        i = this.handleGlass(lines, i);
      } else if (line.startsWith('fountain ')) {
        i = this.handleFountain(lines, i);
      } else if (line.startsWith('return ')) {
        throw { type: 'return', value: this.evaluateExpression(line.substring(7).trim()) };
      } else if (line === 'return') {
        throw { type: 'return', value: undefined };
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
    else if (line.startsWith('reservoir ')) {
      this.handleReservoir(line);
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
      // Check if it's a method call (varname.method(...))
      const methodCallMatch = line.match(/^(\w+)\.(\w+)\s*\(([^)]*)\)$/);
      if (methodCallMatch) {
        const varName = methodCallMatch[1];
        const methodName = methodCallMatch[2];
        const argsStr = methodCallMatch[3].trim();
        
        if (!this.variables.hasOwnProperty(varName)) {
          throw new Error(`Unknown variable: ${varName}`);
        }
        
        const obj = this.variables[varName];
        
        // Handle array methods
        if (Array.isArray(obj)) {
          this.handleArrayMethod(varName, obj, methodName, argsStr);
          return;
        }
        
        // Handle class instance methods
        if (obj && typeof obj === 'object' && obj.__class && obj.__methods) {
          const args = argsStr ? this.parseArguments(argsStr) : [];
          const evaluatedArgs = args.map(arg => this.evaluateExpression(arg));
          this.callInstanceMethod(obj, methodName, evaluatedArgs);
          return;
        }
        
        throw new Error(`Method '${methodName}' not supported for variable '${varName}'`);
      }
      
      // Check if it's a function call (function_name(...))
      const funcCallMatch = line.match(/^(\w+)\s*\(([^)]*)\)$/);
      if (funcCallMatch) {
        const funcName = funcCallMatch[1];
        const argsStr = funcCallMatch[2].trim();
        const args = argsStr ? this.parseArguments(argsStr) : [];
        const evaluatedArgs = args.map(arg => this.evaluateExpression(arg));
        this.callFunction(funcName, evaluatedArgs);
      } else {
        throw new Error(`Unknown statement: ${line}`);
      }
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
      // Count braces only for control flow statements and class/function declarations
      if (currentLine.startsWith('thirsty ') && currentLine.endsWith('{')) {
        braceCount++;
      } else if (currentLine.startsWith('refill ') && currentLine.endsWith('{')) {
        braceCount++;
      } else if (currentLine === 'hydrated {') {
        braceCount++;
      } else if (currentLine.startsWith('glass ') && currentLine.endsWith('{')) {
        braceCount++;
      } else if (currentLine.startsWith('fountain ') && currentLine.endsWith('{')) {
        braceCount++;
      } else if (currentLine.startsWith('shield ') && currentLine.endsWith('{')) {
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
   * Also handles array element assignment: drink arr[index] = value
   * Also handles property assignment: drink obj.property = value
   */
  handleDrink(line) {
    // Check for property assignment (this.property = value)
    const propMatch = line.match(/drink\s+(\w+)\.(\w+)\s*=\s*(.+)/);
    if (propMatch) {
      const objName = propMatch[1];
      const propName = propMatch[2];
      const valueExpr = propMatch[3];
      
      if (!this.variables.hasOwnProperty(objName)) {
        throw new Error(`Unknown variable: ${objName}`);
      }
      
      const obj = this.variables[objName];
      const value = this.evaluateExpression(valueExpr);
      
      // Handle 'this' reference (which is mapped to instance properties)
      if (typeof obj === 'object' && obj !== null) {
        obj[propName] = value;
      } else {
        throw new Error(`Cannot set property '${propName}' on non-object variable '${objName}'`);
      }
      
      return;
    }
    
    // Check for array element assignment
    const arrayMatch = line.match(/drink\s+(\w+)\[(.+)\]\s*=\s*(.+)/);
    if (arrayMatch) {
      const varName = arrayMatch[1];
      const indexExpr = arrayMatch[2];
      const valueExpr = arrayMatch[3];
      
      const index = this.evaluateExpression(indexExpr);
      const value = this.evaluateExpression(valueExpr);
      
      if (!this.variables.hasOwnProperty(varName) || !Array.isArray(this.variables[varName])) {
        throw new Error(`Variable '${varName}' is not an array`);
      }
      
      this.variables[varName][index] = value;
      return;
    }
    
    // Regular variable assignment
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
   * Handle reservoir (array) declaration: reservoir name = [elements]
   */
  handleReservoir(line) {
    const match = line.match(/reservoir\s+(\w+)\s*=\s*\[([^\]]*)\]/);
    if (!match) {
      throw new Error(`Invalid reservoir statement: ${line}`);
    }
    
    const varName = match[1];
    const elementsStr = match[2].trim();
    
    // Parse array elements
    const elements = elementsStr ? this.parseArguments(elementsStr) : [];
    const evaluatedElements = elements.map(elem => this.evaluateExpression(elem));
    
    // Store as a regular variable with array value
    this.variables[varName] = evaluatedElements;
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
   * Handle glass (function declaration) statement
   */
  handleGlass(lines, startIndex) {
    const line = lines[startIndex].trim();
    const match = line.match(/glass\s+(\w+)\s*\(([^)]*)\)\s*{/);
    
    if (!match) {
      throw new Error(`Invalid glass (function) statement: ${line}`);
    }
    
    const funcName = match[1];
    const params = match[2].split(',').map(p => p.trim()).filter(p => p);
    
    // Find the matching closing brace
    const blockEnd = this.findMatchingBrace(lines, startIndex);
    
    if (blockEnd === -1) {
      throw new Error(`Unmatched opening brace for glass statement at line ${startIndex + 1}`);
    }
    
    // Store the function definition
    this.functions[funcName] = {
      params: params,
      body: lines.slice(startIndex + 1, blockEnd),
      line: startIndex
    };
    
    return blockEnd + 1;
  }

  /**
   * Handle fountain (class declaration) statement
   */
  handleFountain(lines, startIndex) {
    const line = lines[startIndex].trim();
    const match = line.match(/fountain\s+(\w+)\s*{/);
    
    if (!match) {
      throw new Error(`Invalid fountain (class) statement: ${line}`);
    }
    
    const className = match[1];
    
    // Find the matching closing brace
    const blockEnd = this.findMatchingBrace(lines, startIndex);
    
    if (blockEnd === -1) {
      throw new Error(`Unmatched opening brace for fountain statement at line ${startIndex + 1}`);
    }
    
    // Parse class body to extract methods and properties
    const classBody = lines.slice(startIndex + 1, blockEnd);
    const methods = {};
    const properties = [];
    
    let i = 0;
    while (i < classBody.length) {
      const bodyLine = classBody[i].trim();
      
      if (!bodyLine || bodyLine.startsWith('//')) {
        i++;
        continue;
      }
      
      // Check for method declaration
      if (bodyLine.startsWith('glass ')) {
        const methodMatch = bodyLine.match(/glass\s+(\w+)\s*\(([^)]*)\)\s*{/);
        if (methodMatch) {
          const methodName = methodMatch[1];
          const params = methodMatch[2].split(',').map(p => p.trim()).filter(p => p);
          
          // Find method body end by counting all braces
          let methodEnd = -1;
          let braceCount = 1;
          
          for (let j = i + 1; j < classBody.length; j++) {
            const currentLine = classBody[j];
            
            // Count all opening and closing braces in the line
            for (const char of currentLine) {
              if (char === '{') braceCount++;
              if (char === '}') braceCount--;
            }
            
            if (braceCount === 0) {
              methodEnd = j;
              break;
            }
          }
          
          if (methodEnd === -1 || braceCount !== 0) {
            throw new Error(`Unmatched opening brace for method ${methodName}`);
          }
          
          methods[methodName] = {
            params: params,
            body: classBody.slice(i + 1, methodEnd)
          };
          
          i = methodEnd + 1;
          continue;
        }
      }
      
      // Check for property declaration
      if (bodyLine.startsWith('drink ')) {
        const propMatch = bodyLine.match(/drink\s+(\w+)\s*=\s*(.+)/);
        if (propMatch) {
          properties.push({
            name: propMatch[1],
            defaultValue: propMatch[2]
          });
        }
      }
      
      i++;
    }
    
    // Store the class definition
    this.classes[className] = {
      name: className,
      methods: methods,
      properties: properties,
      line: startIndex
    };
    
    return blockEnd + 1;
  }

  /**
   * Handle import statement
   * Syntax: import ModuleName from "path/to/module.thirsty"
   *        import { func1, func2 } from "path/to/module.thirsty"
   */
  handleImport(line) {
    // Pattern 1: import ModuleName from "path"
    let match = line.match(/import\s+(\w+)\s+from\s+["']([^"']+)["']/);
    if (match) {
      const moduleName = match[1];
      const modulePath = match[2];
      const exports = this.loadModule(modulePath);
      this.variables[moduleName] = exports;
      return;
    }
    
    // Pattern 2: import { name1, name2 } from "path"
    match = line.match(/import\s+{([^}]+)}\s+from\s+["']([^"']+)["']/);
    if (match) {
      const names = match[1].split(',').map(n => n.trim());
      const modulePath = match[2];
      const exports = this.loadModule(modulePath);
      
      names.forEach(name => {
        if (exports.hasOwnProperty(name)) {
          const exported = exports[name];
          // If it's a function definition, add to functions dictionary
          if (exported && typeof exported === 'object' && exported.params && exported.body) {
            this.functions[name] = exported;
          } else {
            // Otherwise add to variables
            this.variables[name] = exported;
          }
        } else {
          throw new Error(`Module does not export '${name}'`);
        }
      });
      return;
    }
    
    throw new Error(`Invalid import statement: ${line}`);
  }

  /**
   * Handle export statement
   * Syntax: export varname
   *        export glass funcname() { ... }
   */
  handleExport(line) {
    // Pattern: export varname
    const match = line.match(/export\s+(\w+)/);
    if (match) {
      const varName = match[1];
      if (this.variables.hasOwnProperty(varName)) {
        this.exports[varName] = this.variables[varName];
      } else if (this.functions.hasOwnProperty(varName)) {
        this.exports[varName] = this.functions[varName];
      } else {
        throw new Error(`Cannot export undefined identifier: ${varName}`);
      }
      return;
    }
    
    throw new Error(`Invalid export statement: ${line}`);
  }

  /**
   * Load a module from file
   */
  loadModule(modulePath) {
    // Resolve relative paths
    let absolutePath = modulePath;
    if (this.currentFile && !path.isAbsolute(modulePath)) {
      absolutePath = path.resolve(path.dirname(this.currentFile), modulePath);
    }
    
    // Check cache
    if (this.modules[absolutePath]) {
      return this.modules[absolutePath];
    }
    
    // Load and execute module
    if (!fs.existsSync(absolutePath)) {
      throw new Error(`Module not found: ${absolutePath}`);
    }
    
    const code = fs.readFileSync(absolutePath, 'utf8');
    
    // Create new interpreter instance for module
    const moduleInterpreter = new ThirstyInterpreter({
      currentFile: absolutePath,
      security: this.securityEnabled,
      securityMode: this.securityManager.mode
    });
    
    // Execute module code
    moduleInterpreter.execute(code);
    
    // Cache and return exports
    this.modules[absolutePath] = moduleInterpreter.exports;
    return moduleInterpreter.exports;
  }

  /**
   * Handle cascade (async function) statement
   * Syntax: cascade funcname(params) { ... }
   */
  handleCascade(lines, startIndex) {
    const line = lines[startIndex].trim();
    const match = line.match(/cascade\s+(\w+)\s*\(([^)]*)\)\s*{/);
    
    if (!match) {
      throw new Error(`Invalid cascade (async function) statement: ${line}`);
    }
    
    const funcName = match[1];
    const params = match[2].split(',').map(p => p.trim()).filter(p => p);
    
    // Find the matching closing brace
    const blockEnd = this.findMatchingBrace(lines, startIndex);
    
    if (blockEnd === -1) {
      throw new Error(`Unmatched opening brace for cascade statement at line ${startIndex + 1}`);
    }
    
    // Store the async function definition
    this.functions[funcName] = {
      params: params,
      body: lines.slice(startIndex + 1, blockEnd),
      line: startIndex,
      async: true  // Mark as async
    };
    
    this.asyncFunctions.add(funcName);
    
    return blockEnd + 1;
  }

  /**
   * Instantiate a class (new ClassName())
   */
  instantiateClass(className, args) {
    if (!this.classes.hasOwnProperty(className)) {
      throw new Error(`Undefined class: ${className}`);
    }
    
    const classDef = this.classes[className];
    
    // Create instance object
    const instance = {
      __class: className,
      __properties: {},
      __methods: {}
    };
    
    // Initialize properties with default values
    for (const prop of classDef.properties) {
      instance.__properties[prop.name] = this.evaluateExpression(prop.defaultValue);
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
    const savedVariables = { ...this.variables };
    
    // Create new scope with method parameters and 'this' reference
    const methodScope = { ...this.variables };
    for (let i = 0; i < method.params.length; i++) {
      methodScope[method.params[i]] = args[i];
    }
    
    // Add 'this' reference to instance properties
    methodScope.this = instance.__properties;
    
    this.variables = methodScope;
    
    try {
      // Execute method body
      this.executeBlock(method.body, 0);
      
      // Restore variable scope
      this.variables = savedVariables;
      
      return undefined;
    } catch (e) {
      // Handle return statement
      if (e.type === 'return') {
        this.variables = savedVariables;
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
    if (!this.functions.hasOwnProperty(funcName)) {
      // Check if it's a class name instead
      if (this.classes.hasOwnProperty(funcName)) {
        throw new Error(`'${funcName}' is a class, not a function. Cannot call as function.`);
      }
      throw new Error(`Undefined function: ${funcName}`);
    }
    
    // Check call stack depth
    if (this.callStack.length >= this.MAX_CALL_DEPTH) {
      throw new Error(`Maximum call depth exceeded (${this.MAX_CALL_DEPTH})`);
    }
    
    const func = this.functions[funcName];
    
    // Check argument count
    if (args.length !== func.params.length) {
      throw new Error(`Function ${funcName} expects ${func.params.length} arguments, got ${args.length}`);
    }
    
    // If async function, return a promise
    if (func.async) {
      return this.callAsyncFunction(funcName, args);
    }
    
    // Save current variable scope
    const savedVariables = { ...this.variables };
    
    // Create new scope with function parameters
    const funcScope = { ...this.variables };
    for (let i = 0; i < func.params.length; i++) {
      funcScope[func.params[i]] = args[i];
    }
    this.variables = funcScope;
    
    // Track call stack
    this.callStack.push({ function: funcName, line: func.line });
    
    try {
      // Execute function body
      this.executeBlock(func.body, 0);
      
      // Pop call stack
      this.callStack.pop();
      
      // Restore variable scope
      this.variables = savedVariables;
      
      return undefined;
    } catch (e) {
      // Handle return statement
      if (e.type === 'return') {
        this.callStack.pop();
        this.variables = savedVariables;
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
    const func = this.functions[funcName];
    
    // Save current variable scope
    const savedVariables = { ...this.variables };
    
    // Create new scope with function parameters
    const funcScope = { ...this.variables };
    for (let i = 0; i < func.params.length; i++) {
      funcScope[func.params[i]] = args[i];
    }
    this.variables = funcScope;
    
    // Track call stack
    this.callStack.push({ function: funcName, line: func.line });
    
    try {
      // Execute function body asynchronously
      await this.executeBlockAsync(func.body, 0);
      
      // Pop call stack
      this.callStack.pop();
      
      // Restore variable scope
      this.variables = savedVariables;
      
      return undefined;
    } catch (e) {
      // Handle return statement
      if (e.type === 'return') {
        this.callStack.pop();
        this.variables = savedVariables;
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
          this.variables[varName] = value;
          i++;
          continue;
        }
      }
      
      // For other statements, execute normally
      if (line.startsWith('thirsty ')) {
        i = this.handleThirsty(lines, i);
      } else if (line.startsWith('refill ')) {
        i = this.handleRefill(lines, i);
      } else if (line.startsWith('return ')) {
        const value = await this.evaluateExpressionAsync(line.substring(7).trim());
        throw { type: 'return', value: value };
      } else if (line === 'return') {
        throw { type: 'return', value: undefined };
      } else if (line === '}') {
        return i + 1;
      } else {
        this.executeLine(line);
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
      const args = argsStr ? this.parseArguments(argsStr) : [];
      const evaluatedArgs = args.map(arg => this.evaluateExpression(arg));
      
      // If it's an async function, await it
      if (this.asyncFunctions.has(funcName)) {
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
      const args = argsStr ? this.parseArguments(argsStr) : [];
      const evaluatedArgs = args.map(arg => this.evaluateExpression(arg));
      
      if (this.variables.hasOwnProperty(objName)) {
        const obj = this.variables[objName];
        if (obj && obj[methodName] && typeof obj[methodName] === 'function') {
          const result = obj[methodName](...evaluatedArgs);
          
          // If result is a promise, await it
          if (result && typeof result.then === 'function') {
            return await result;
          }
          
          return result;
        }
      }
    }
    
    // For other expressions, evaluate normally
    return this.evaluateExpression(expr);
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
      if (this.isInParentheses(expr, i)) continue;
      
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
      if (this.isInParentheses(expr, i)) continue;
      
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
    
    // Function call or class instantiation - check for name(args) with nested parentheses
    const funcMatch = expr.match(/^(\w+)\s*\(/);
    if (funcMatch) {
      const name = funcMatch[1];
      const startIdx = expr.indexOf('(');
      const argsStr = this.extractParenthesesContent(expr, startIdx);
      const args = argsStr ? this.parseArguments(argsStr) : [];
      const evaluatedArgs = args.map(arg => this.evaluateExpression(arg));
      
      // Check if it's a class (class names typically start with uppercase)
      if (this.classes.hasOwnProperty(name)) {
        return this.instantiateClass(name, evaluatedArgs);
      }
      
      // Check if it's a function
      if (this.functions.hasOwnProperty(name)) {
        return this.callFunction(name, evaluatedArgs);
      }
      
      // Neither class nor function
      throw new Error(`Undefined class or function: ${name}`);
    }
    
    // Array access - varname[index]
    const arrayAccessMatch = expr.match(/^(\w+)\[(.+)\]$/);
    if (arrayAccessMatch) {
      const varName = arrayAccessMatch[1];
      const indexExpr = arrayAccessMatch[2];
      
      if (!this.variables.hasOwnProperty(varName)) {
        throw new Error(`Unknown variable: ${varName}`);
      }
      
      const arr = this.variables[varName];
      if (!Array.isArray(arr)) {
        throw new Error(`Variable '${varName}' is not an array`);
      }
      
      const index = this.evaluateExpression(indexExpr);
      
      if (index < 0 || index >= arr.length) {
        throw new Error(`Array index out of bounds: ${index} (length: ${arr.length})`);
      }
      
      return arr[index];
    }
    
    // Array/string/instance method calls - varname.method(args)
    const methodMatch = expr.match(/^(\w+)\.(\w+)\s*\(([^)]*)\)$/);
    if (methodMatch) {
      const varName = methodMatch[1];
      const methodName = methodMatch[2];
      const argsStr = methodMatch[3].trim();
      
      if (!this.variables.hasOwnProperty(varName)) {
        throw new Error(`Unknown variable: ${varName}`);
      }
      
      const obj = this.variables[varName];
      
      // Handle array methods
      if (Array.isArray(obj)) {
        return this.handleArrayMethod(varName, obj, methodName, argsStr);
      }
      
      // Handle class instance methods
      if (obj && typeof obj === 'object' && obj.__class && obj.__methods) {
        const args = argsStr ? this.parseArguments(argsStr) : [];
        const evaluatedArgs = args.map(arg => this.evaluateExpression(arg));
        return this.callInstanceMethod(obj, methodName, evaluatedArgs);
      }
      
      // Handle built-in library methods (Math, String, etc.)
      if (obj && typeof obj === 'object' && obj.__builtin) {
        const args = argsStr ? this.parseArguments(argsStr) : [];
        const evaluatedArgs = args.map(arg => this.evaluateExpression(arg));
        if (typeof obj[methodName] === 'function') {
          return obj[methodName](...evaluatedArgs);
        }
        throw new Error(`Built-in method '${methodName}' not found in '${varName}'`);
      }
      
      throw new Error(`Method '${methodName}' not supported for variable '${varName}'`);
    }
    
    // Array/string/instance property access - varname.property
    const propertyMatch = expr.match(/^(\w+)\.(\w+)$/);
    if (propertyMatch) {
      const varName = propertyMatch[1];
      const propName = propertyMatch[2];
      
      if (!this.variables.hasOwnProperty(varName)) {
        throw new Error(`Unknown variable: ${varName}`);
      }
      
      const obj = this.variables[varName];
      
      // Handle class instance properties
      if (obj && typeof obj === 'object' && obj.__class && obj.__properties) {
        if (obj.__properties.hasOwnProperty(propName)) {
          return obj.__properties[propName];
        }
        throw new Error(`Property '${propName}' not found in class ${obj.__class}`);
      }
      
      // Handle length property for arrays and strings
      if (propName === 'length') {
        if (Array.isArray(obj) || typeof obj === 'string') {
          return obj.length;
        }
      }
      
      // Handle generic object property access
      if (typeof obj === 'object' && obj !== null && obj.hasOwnProperty(propName)) {
        return obj[propName];
      }
      
      throw new Error(`Property '${propName}' not supported for variable '${varName}'`);
    }
    
    // Variable reference
    if (this.variables.hasOwnProperty(expr)) {
      return this.variables[expr];
    }
    
    throw new Error(`Unknown expression: ${expr}`);
  }

  /**
   * Handle array method calls (push, pop, etc.)
   */
  handleArrayMethod(varName, arr, methodName, argsStr) {
    const args = argsStr ? this.parseArguments(argsStr) : [];
    const evaluatedArgs = args.map(arg => this.evaluateExpression(arg));
    
    switch (methodName) {
      case 'push':
        // Add elements to the end of the array
        for (const arg of evaluatedArgs) {
          arr.push(arg);
        }
        return arr.length;
        
      case 'pop':
        // Remove and return the last element
        if (arr.length === 0) {
          throw new Error(`Cannot pop from empty array '${varName}'`);
        }
        return arr.pop();
        
      case 'shift':
        // Remove and return the first element
        if (arr.length === 0) {
          throw new Error(`Cannot shift from empty array '${varName}'`);
        }
        return arr.shift();
        
      case 'unshift':
        // Add elements to the beginning of the array
        for (const arg of evaluatedArgs) {
          arr.unshift(arg);
        }
        return arr.length;
        
      case 'slice':
        // Return a shallow copy of a portion of the array
        const start = evaluatedArgs[0] || 0;
        const end = evaluatedArgs[1];
        return arr.slice(start, end);
        
      case 'indexOf':
        // Find the index of an element
        if (evaluatedArgs.length === 0) {
          throw new Error(`indexOf requires at least one argument`);
        }
        return arr.indexOf(evaluatedArgs[0]);
        
      case 'includes':
        // Check if array contains an element
        if (evaluatedArgs.length === 0) {
          throw new Error(`includes requires at least one argument`);
        }
        return arr.includes(evaluatedArgs[0]);
        
      case 'join':
        // Join array elements into a string
        const separator = evaluatedArgs[0] !== undefined ? evaluatedArgs[0] : ',';
        return arr.join(separator);
        
      case 'reverse':
        // Reverse the array in place
        arr.reverse();
        return arr;
        
      case 'sort':
        // Sort the array in place
        arr.sort();
        return arr;
        
      default:
        throw new Error(`Unknown array method: ${methodName}`);
    }
  }

  /**
   * Extract content between parentheses, handling nested parentheses
   */
  extractParenthesesContent(expr, startIdx) {
    let depth = 0;
    let content = '';
    
    for (let i = startIdx; i < expr.length; i++) {
      const char = expr[i];
      
      if (char === '(') {
        if (depth > 0) {
          content += char;
        }
        depth++;
      } else if (char === ')') {
        depth--;
        if (depth > 0) {
          content += char;
        } else if (depth === 0) {
          return content;
        }
      } else if (depth > 0) {
        content += char;
      }
    }
    
    throw new Error('Unmatched parentheses in expression');
  }

  /**
   * Parse function call arguments, respecting nested parentheses and strings
   */
  parseArguments(argsStr) {
    const args = [];
    let current = '';
    let depth = 0;
    let inString = false;
    let stringChar = null;
    
    for (let i = 0; i < argsStr.length; i++) {
      const char = argsStr[i];
      
      if ((char === '"' || char === "'") && (i === 0 || argsStr[i-1] !== '\\')) {
        if (!inString) {
          inString = true;
          stringChar = char;
        } else if (char === stringChar) {
          inString = false;
          stringChar = null;
        }
        current += char;
      } else if (char === '(' && !inString) {
        depth++;
        current += char;
      } else if (char === ')' && !inString) {
        depth--;
        current += char;
      } else if (char === ',' && depth === 0 && !inString) {
        args.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }
    
    if (current.trim()) {
      args.push(current.trim());
    }
    
    return args;
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
   * Check if a position is inside parentheses
   */
  isInParentheses(expr, pos) {
    let depth = 0;
    for (let i = 0; i < pos; i++) {
      // Skip if in string
      if (this.isInString(expr, i)) continue;
      
      if (expr[i] === '(') {
        depth++;
      } else if (expr[i] === ')') {
        depth--;
      }
    }
    return depth > 0;
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
