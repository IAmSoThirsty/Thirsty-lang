#!/usr/bin/env node

/**
 * Thirsty-Lang AST Interpreter
 * =============================
 * Tree-walking interpreter that visits AST nodes produced by the Parser.
 *
 * Design:
 *   - Environment chain for lexical scoping (parent → child frames)
 *   - ReturnSignal for function returns (not JS exceptions)
 *   - Loop safety limit (MAX_LOOP_ITERATIONS)
 *   - Call-depth limit (MAX_CALL_DEPTH)
 *   - Integrates with SecurityManager, stdlib, and module system
 * 
 * Safety:
 *   - visits are wrapped in security checks
 *   - variables can be armored (read-only)
 */

'use strict';

const { NodeType } = require('./parser');
const { initializeStandardLibrary } = require('../interpreter/stdlib');

// ── Signals ──────────────────────────────────────────────────────────────────

class ReturnSignal {
    constructor(value) {
        this.type = 'return';
        this.value = value;
    }
}

class ThrowSignal {
    constructor(value) {
        this.type = 'throw';
        this.value = value;
    }
}

// ── ThirstyError (matches legacy exception-handlers) ─────────────────────────

class ThirstyError extends Error {
    constructor(message, type = 'Error', context = {}) {
        super(message);
        this.name = `Thirsty${type}`;
        this.thirstyType = type;
        this.context = context;
        this.timestamp = new Date().toISOString();
        if (Error.captureStackTrace) Error.captureStackTrace(this, ThirstyError);
    }

    toThirstyObject() {
        return {
            message: this.message,
            type: this.thirstyType,
            name: this.name,
            stack: this.stack,
            context: this.context,
            timestamp: this.timestamp,
        };
    }

    static fromError(err, context = {}) {
        if (err instanceof ThirstyError) return err;
        const te = new ThirstyError(err.message, 'Error', context);
        te.stack = err.stack;
        return te;
    }
}

// ── Environment (lexical scope frame) ────────────────────────────────────────

class Environment {
    constructor(parent = null) {
        this.parent = parent;
        this.store = Object.create(null); // Prevents prototype pollution
        this.armored = new Set(); // variable names that are read-only
    }

    /** Define a new variable in this scope. */
    define(name, value) {
        this.store[name] = value;
    }

    /** Set an existing variable (walks up scope chain). */
    set(name, value) {
        // Check armor
        if (this.armored.has(name)) {
            console.warn(`Warning: Cannot modify armored variable '${name}'`);
            return;
        }
        if (name in this.store) {
            this.store[name] = value;
            return;
        }
        if (this.parent) {
            this.parent.set(name, value);
            return;
        }
        // If not found anywhere, define in current scope (global-style assignment)
        this.store[name] = value;
    }

    /** Get a variable (walks up scope chain). */
    get(name) {
        if (Object.prototype.hasOwnProperty.call(this.store, name)) {
            return this.store[name];
        }
        if (this.parent) {
            return this.parent.get(name);
        }
        throw new ThirstyError(`Undefined identifier: ${name}`, 'ReferenceError');
    }

    /** Check if a variable exists anywhere in the chain. */
    has(name) {
        if (Object.prototype.hasOwnProperty.call(this.store, name)) return true;
        if (this.parent) return this.parent.has(name);
        return false;
    }

    /** Mark a variable as armored (read-only). */
    armorVar(name) {
        this.armored.add(name);
    }

    /** Create a child scope. */
    child() {
        return new Environment(this);
    }

    /** Flat snapshot of all visible variables (for backward-compat). */
    allVariables() {
        const result = {};
        if (this.parent) Object.assign(result, this.parent.allVariables());
        Object.assign(result, this.store);
        return result;
    }
}

const { Logger } = require('./logger');

// ── AST Interpreter ──────────────────────────────────────────────────────────

class ASTInterpreter {
    /**
     * @param {object} host - The ThirstyInterpreter instance (for security, stdlib, modules)
     */
    constructor(host) {
        this.host = host;

        // Limits
        this.MAX_LOOP_ITERATIONS = host.MAX_LOOP_ITERATIONS || 10000;
        this.MAX_CALL_DEPTH = host.MAX_CALL_DEPTH || 100;

        // State
        this.globalEnv = new Environment();
        this.callStack = [];
        this.functions = {};  // name → { params, bodyNode, isAsync }
        this.classes = {};  // name → { name, methods, properties }
        this.logger = host.logger || new Logger({ component: 'AST_ENGINE' });

        // Initialize Standard Library
        const stdlib = initializeStandardLibrary();
        for (const [name, module] of Object.entries(stdlib)) {
            this.globalEnv.define(name, module);
        }

        // Bridge host variables
        if (host.variables) {
            for (const [k, v] of Object.entries(host.variables)) {
                this.globalEnv.define(k, v);
            }
        }
    }

    // ── Public API ─────────────────────────────────────────────────────────────

    /**
     * Execute a Program AST node.
     * @param {object} program - { type: 'Program', body: [...] }
     */
    run(program) {
        this.execBlock(program.body, this.globalEnv);
        // Sync back to host for backward-compat
        this.syncToHost();
    }

    /** Sync interpreter state back to host.variables / host.functions / host.classes. */
    syncToHost() {
        this.host.variables = this.globalEnv.allVariables();
        this.host.functions = { ...this.functions };
        this.host.classes = { ...this.classes };
    }

    // ── Block execution ────────────────────────────────────────────────────────

    execBlock(statements, env) {
        for (const stmt of statements) {
            const result = this.execStatement(stmt, env);
            if (result instanceof ReturnSignal) return result;
            if (result instanceof ThrowSignal) throw result;
        }
        return undefined;
    }

    // ── Statement dispatch ─────────────────────────────────────────────────────

    execStatement(node, env) {
        switch (node.type) {
            case NodeType.VariableDeclaration: return this.execVarDecl(node, env);
            case NodeType.ReservoirDeclaration: return this.execReservoirDecl(node, env);
            case NodeType.PourStatement: return this.execPour(node, env);
            case NodeType.SipStatement: return this.execSip(node, env);
            case NodeType.IfStatement: return this.execIf(node, env);
            case NodeType.WhileStatement: return this.execWhile(node, env);
            case NodeType.FunctionDeclaration: return this.execFuncDecl(node, env);
            case NodeType.ClassDeclaration: return this.execClassDecl(node, env);
            case NodeType.CascadeDeclaration: return this.execCascadeDecl(node, env);
            case NodeType.ReturnStatement: return this.execReturn(node, env);
            case NodeType.ThrowStatement: return this.execThrow(node, env);
            case NodeType.TryCatchStatement: return this.execTryCatch(node, env);
            case NodeType.ShieldBlock: return this.execShield(node, env);
            case NodeType.SanitizeStatement: return this.execSanitize(node, env);
            case NodeType.ArmorStatement: return this.execArmor(node, env);
            case NodeType.MorphStatement: return this.execMorph(node, env);
            case NodeType.DetectStatement: return this.execDetect(node, env);
            case NodeType.DefendStatement: return this.execDefend(node, env);
            case NodeType.ImportStatement: return this.execImport(node, env);
            case NodeType.ExportStatement: return this.execExport(node, env);
            case NodeType.ExpressionStatement: return this.evalExpr(node.expression, env);
            default:
                throw new Error(`Unknown AST node type: ${node.type}`);
        }
    }

    // ── Variable Declaration ───────────────────────────────────────────────────

    execVarDecl(node, env) {
        const value = this.evalExpr(node.value, env);
        const target = node.target;

        if (target.type === NodeType.Identifier) {
            // Simple: drink x = 5
            env.set(target.name, value);
        } else if (target.type === NodeType.MemberExpression) {
            // Property: drink obj.prop = val
            const obj = this.evalExpr(target.object, env);
            if (obj && typeof obj === 'object' && obj.__class && obj.__properties) {
                obj.__properties[target.property] = value;
            } else if (obj && typeof obj === 'object') {
                obj[target.property] = value;
            } else {
                throw new Error(`Cannot set property '${target.property}' on non-object`);
            }
        } else if (target.type === NodeType.IndexExpression) {
            // Index: drink arr[0] = val
            const obj = this.evalExpr(target.object, env);
            const idx = this.evalExpr(target.index, env);
            if (Array.isArray(obj)) {
                obj[idx] = value;
            } else {
                throw new Error(`Cannot index non-array`);
            }
        } else {
            throw new Error(`Invalid assignment target`);
        }

        return undefined;
    }

    // ── Reservoir Declaration ──────────────────────────────────────────────────

    execReservoirDecl(node, env) {
        const elements = node.elements.map(el => this.evalExpr(el, env));
        env.set(node.name, elements);
        return undefined;
    }

    // ── Pour ───────────────────────────────────────────────────────────────────

    execPour(node, env) {
        const value = this.evalExpr(node.expression, env);
        console.log(value);
        return undefined;
    }

    // ── Sip (input) ────────────────────────────────────────────────────────────

    execSip(node, env) {
        let input = '';
        if (node.prompt) {
            // In a real CLI environment, this would wait for user input
            // For now, we simulate or handle via the host
            process.stdout.write(node.prompt + ' ');
        }

        // Bridge to host input handler if available
        if (this.host.inputHandler) {
            input = this.host.inputHandler(node.prompt);
        }

        if (node.target) {
            env.set(node.target, input);
        }

        return input;
    }

    // ── If Statement ───────────────────────────────────────────────────────────

    execIf(node, env) {
        const condition = this.evalExpr(node.condition, env);
        if (this.isTruthy(condition)) {
            return this.execBlock(node.consequent.body, env);
        } else if (node.alternate) {
            if (node.alternate.type === NodeType.IfStatement) {
                return this.execIf(node.alternate, env);
            } else {
                return this.execBlock(node.alternate.body, env);
            }
        }
        return undefined;
    }

    // ── While (refill) ────────────────────────────────────────────────────────

    execWhile(node, env) {
        let iterations = 0;
        while (this.isTruthy(this.evalExpr(node.condition, env))) {
            if (iterations >= this.MAX_LOOP_ITERATIONS) {
                throw new Error(`Loop exceeded maximum iterations (${this.MAX_LOOP_ITERATIONS})`);
            }
            const result = this.execBlock(node.body.body, env);
            if (result instanceof ReturnSignal) return result;
            iterations++;
        }
        return undefined;
    }

    // ── Function Declaration ───────────────────────────────────────────────────

    execFuncDecl(node, env) {
        this.functions[node.name] = {
            params: node.params,
            bodyNode: node.body,
            isAsync: false,
            closureEnv: env,
        };
        return undefined;
    }

    // ── Cascade (async function) Declaration ───────────────────────────────────

    execCascadeDecl(node, env) {
        this.functions[node.name] = {
            params: node.params,
            bodyNode: node.body,
            isAsync: true,
            closureEnv: env,
        };
        if (this.host.asyncFunctions) {
            this.host.asyncFunctions.add(node.name);
        }
        return undefined;
    }

    // ── Class Declaration ──────────────────────────────────────────────────────

    execClassDecl(node, env) {
        const methods = {};
        for (const m of node.methods) {
            methods[m.name] = {
                params: m.params,
                bodyNode: m.body,
            };
        }

        const properties = node.properties.map(p => ({
            name: p.name,
            defaultValue: p.defaultValue, // AST node — evaluated at instantiation
        }));

        this.classes[node.name] = {
            name: node.name,
            methods,
            properties,
        };
        return undefined;
    }

    // ── Return ─────────────────────────────────────────────────────────────────

    execReturn(node, env) {
        const value = node.value ? this.evalExpr(node.value, env) : undefined;
        return new ReturnSignal(value);
    }

    // ── Throw ──────────────────────────────────────────────────────────────────

    execThrow(node, env) {
        const value = this.evalExpr(node.value, env);
        let error;
        if (typeof value === 'string') {
            error = new ThirstyError(value, 'ThrownError');
        } else if (typeof value === 'object' && value !== null) {
            error = new ThirstyError(value.message || String(value), value.type || 'ThrownError', value);
        } else {
            error = new ThirstyError(String(value), 'ThrownError');
        }
        throw error;
    }

    // ── Try / Catch / Finally ──────────────────────────────────────────────────

    execTryCatch(node, env) {
        let caughtError = null;

        try {
            const result = this.execBlock(node.tryBlock.body, env);
            if (result instanceof ReturnSignal) return result;
        } catch (err) {
            if (err instanceof ReturnSignal) return err;
            caughtError = ThirstyError.fromError(err);
        }

        if (caughtError && node.catchBlock) {
            const catchEnv = env.child();
            catchEnv.define(node.catchVar, caughtError.toThirstyObject());
            try {
                const result = this.execBlock(node.catchBlock.body, catchEnv);
                if (result instanceof ReturnSignal) return result;
                caughtError = null; // handled
            } catch (catchErr) {
                if (catchErr instanceof ReturnSignal) return catchErr;
                caughtError = ThirstyError.fromError(catchErr);
            }
        }

        if (node.finallyBlock) {
            try {
                const result = this.execBlock(node.finallyBlock.body, env);
                if (result instanceof ReturnSignal) return result;
            } catch (finallyErr) {
                if (finallyErr instanceof ReturnSignal) return finallyErr;
                caughtError = ThirstyError.fromError(finallyErr);
            }
        }

        if (caughtError) throw caughtError;
        return undefined;
    }

    // ── Shield Block ───────────────────────────────────────────────────────────

    execShield(node, env) {
        // Shield creates a protected execution context
        const mgr = this.host.securityManager;
        if (mgr && typeof mgr.enterShieldedContext === 'function') {
            mgr.enterShieldedContext(node.name);
        }
        try {
            return this.execBlock(node.body.body, env);
        } finally {
            if (mgr && typeof mgr.exitShieldedContext === 'function') {
                mgr.exitShieldedContext();
            }
        }
    }

    // ── Sanitize ───────────────────────────────────────────────────────────────

    execSanitize(node, env) {
        if (!env.has(node.varName)) {
            throw new Error(`Cannot sanitize undefined variable: ${node.varName}`);
        }
        let value = env.get(node.varName);
        if (typeof value === 'string') {
            // Remove dangerous HTML/script content
            value = value.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
            value = value.replace(/<[^>]+>/g, '');
            value = value.replace(/javascript:/gi, '');
            value = value.replace(/on\w+\s*=/gi, '');
            env.set(node.varName, value);
        }
        return undefined;
    }

    // ── Armor ──────────────────────────────────────────────────────────────────

    execArmor(node, env) {
        if (!env.has(node.varName)) {
            throw new Error(`Cannot armor undefined variable: ${node.varName}`);
        }
        env.armorVar(node.varName);
        return undefined;
    }

    // ── Morph ──────────────────────────────────────────────────────────────────

    execMorph(node, env) {
        // Security transform configuration
        const mgr = this.host.securityManager;
        if (mgr && typeof mgr.enableProtections === 'function' && node.config.on) {
            const protections = node.config.on.map(el => this.evalExpr(el, env));
            this.logger.info(`Protections enabled`, { protections });
            mgr.enableProtections(protections);
        }
        return undefined;
    }

    evalAssignment(node, env) {
        const value = this.evalExpr(node.right, env);
        const target = node.left;

        if (target.type === NodeType.Identifier) {
            env.set(target.name, value);
        } else if (target.type === NodeType.MemberExpression) {
            const obj = this.evalExpr(target.object, env);
            // Block sensitive properties
            const prop = target.property;
            const BLOCKLIST = ['constructor', '__proto__', 'prototype'];
            if (BLOCKLIST.includes(prop)) {
                this.logger.security(`Illegal property assignment attempt`, { property: prop });
                throw new Error(`Security Violation: Illegal assignment to property '${prop}'`);
            }
            if (obj && typeof obj === 'object') {
                if (obj.__class && obj.__properties) {
                    obj.__properties[prop] = value;
                } else {
                    obj[prop] = value;
                }
            }
        } else if (target.type === NodeType.IndexExpression) {
            const obj = this.evalExpr(target.object, env);
            const idx = this.evalExpr(target.index, env);
            if (Array.isArray(obj)) {
                obj[idx] = value;
            } else if (obj && typeof obj === 'object') {
                // Block sensitive properties via indexing
                const BLOCKLIST = ['constructor', '__proto__', 'prototype'];
                if (BLOCKLIST.includes(String(idx))) {
                    this.logger.security(`Illegal indexed property assignment attempt`, { index: idx });
                    throw new Error(`Security Violation: Illegal assignment to property '${idx}' via indexing`);
                }
                obj[idx] = value;
            }
        }
        return value;
    }

    // ── Detect ─────────────────────────────────────────────────────────────────

    execDetect(node, env) {
        const mgr = this.host.securityManager;
        if (mgr && typeof mgr.enableDetection === 'function') {
            mgr.enableDetection(node.target);
        }
        return this.execBlock(node.body.body, env);
    }

    // ── Defend ─────────────────────────────────────────────────────────────────

    execDefend(node, env) {
        const mgr = this.host.securityManager;
        if (mgr && typeof mgr.setDefenseLevel === 'function' && node.config.with) {
            const level = this.evalExpr(node.config.with, env);
            mgr.setDefenseLevel(level);
        }
        return undefined;
    }

    // ── Import ─────────────────────────────────────────────────────────────────

    execImport(node, env) {
        if (this.host.classFunctionHandlers) {
            // Delegate to existing module loading system
            const exports = this.host.classFunctionHandlers.loadModule(node.modulePath);

            if (node.defaultName) {
                env.set(node.defaultName, exports);
            }

            for (const name of node.names) {
                if (exports.hasOwnProperty(name)) {
                    const exported = exports[name];
                    if (exported && typeof exported === 'object' && exported.params && exported.body) {
                        // Legacy function definition — convert to new format
                        this.functions[name] = {
                            params: exported.params,
                            bodyNode: null,      // will use legacy execution
                            legacyBody: exported.body,
                            isAsync: !!exported.async,
                            closureEnv: env,
                        };
                    } else {
                        env.set(name, exported);
                    }
                } else {
                    throw new Error(`Module does not export '${name}'`);
                }
            }
        }
        return undefined;
    }

    // ── Export ─────────────────────────────────────────────────────────────────

    execExport(node, env) {
        if (env.has(node.name)) {
            this.host.exports[node.name] = env.get(node.name);
        } else if (this.functions[node.name]) {
            this.host.exports[node.name] = this.functions[node.name];
        } else {
            throw new Error(`Cannot export undefined identifier: ${node.name}`);
        }
        return undefined;
    }

    // ── Expression evaluation ──────────────────────────────────────────────────

    evalExpr(node, env) {
        switch (node.type) {
            case NodeType.NumberLiteral: return node.value;
            case NodeType.StringLiteral: return node.value;
            case NodeType.BooleanLiteral: return node.value;
            case NodeType.ArrayLiteral: return node.elements.map(el => this.evalExpr(el, env));
            case NodeType.ObjectLiteral: return this.evalObjectLiteral(node, env);
            case NodeType.Identifier: return this.evalIdentifier(node, env);
            case NodeType.BinaryExpression: return this.evalBinary(node, env);
            case NodeType.UnaryExpression: return this.evalUnary(node, env);
            case NodeType.CallExpression: return this.evalCall(node, env);
            case NodeType.MemberExpression: return this.evalMember(node, env);
            case NodeType.IndexExpression: return this.evalIndex(node, env);
            case NodeType.AssignmentExpression: return this.evalAssignment(node, env);
            default:
                throw new Error(`Unknown expression node: ${node.type}`);
        }
    }

    // ── Identifier ─────────────────────────────────────────────────────────────

    evalIdentifier(node, env) {
        if (env.has(node.name)) return env.get(node.name);
        // Check stdlib / host variables
        if (this.host.variables && Object.prototype.hasOwnProperty.call(this.host.variables, node.name)) {
            return this.host.variables[node.name];
        }
        throw new ThirstyError(`Undefined identifier: ${node.name}`, 'ReferenceError');
    }

    // ── Object Literal ─────────────────────────────────────────────────────────

    evalObjectLiteral(node, env) {
        const obj = {};
        for (const [key, valNode] of Object.entries(node.properties)) {
            obj[key] = this.evalExpr(valNode, env);
        }
        return obj;
    }

    // ── Binary Expression ──────────────────────────────────────────────────────

    evalBinary(node, env) {
        const left = this.evalExpr(node.left, env);
        const right = this.evalExpr(node.right, env);

        switch (node.operator) {
            case '+':
                if (typeof left === 'number' && typeof right === 'number') return left + right;
                return String(left) + String(right);
            case '-': return left - right;
            case '*': return left * right;
            case '/':
                if (right === 0) throw new Error(`Division by zero in expression: ${left} / ${right}`);
                return left / right;
            case '%': return left % right;
            case '==': return left === right;
            case '!=': return left !== right;
            case '<': return left < right;
            case '>': return left > right;
            case '<=': return left <= right;
            case '>=': return left >= right;
            case '&&': return left && right;
            case '||': return left || right;
            default:
                throw new Error(`Unknown operator: ${node.operator}`);
        }
    }

    // ── Unary Expression ───────────────────────────────────────────────────────

    evalUnary(node, env) {
        if (node.operator === 'await') {
            // In sync mode, just evaluate the operand
            return this.evalExpr(node.operand, env);
        }
        const operand = this.evalExpr(node.operand, env);
        switch (node.operator) {
            case '-': return -operand;
            case '!': return !operand;
            default:
                throw new Error(`Unknown unary operator: ${node.operator}`);
        }
    }

    // ── Call Expression ────────────────────────────────────────────────────────

    evalCall(node, env) {
        const args = node.arguments.map(a => this.evalExpr(a, env));

        // Method call: obj.method(args)
        if (node.callee.type === NodeType.MemberExpression) {
            return this.evalMethodCall(node.callee, args, env);
        }

        // Class instantiation
        if (node.isNew || this.classes[node.callee.name]) {
            return this.instantiateClass(node.callee.name, args, env);
        }

        // Regular function call
        const funcName = node.callee.name;

        // Check user-defined functions
        if (this.functions[funcName]) {
            return this.callFunction(funcName, args, env);
        }

        // Check if it's a variable holding a callable (stdlib, etc.)
        if (env.has(funcName)) {
            const val = env.get(funcName);
            if (typeof val === 'function') {
                return val(...args);
            }
        }

        throw new Error(`Undefined class or function: ${funcName}`);
    }

    // ── Method call ────────────────────────────────────────────────────────────

    evalMethodCall(callee, args, env) {
        const obj = this.evalExpr(callee.object, env);
        const methodName = callee.property;

        // Array methods
        if (Array.isArray(obj)) {
            return this.handleArrayMethod(obj, methodName, args, callee.object, env);
        }

        // String methods
        if (typeof obj === 'string') {
            return this.handleStringMethod(obj, methodName, args);
        }

        // Class instance methods
        if (obj && typeof obj === 'object' && obj.__class && obj.__methods) {
            return this.callInstanceMethod(obj, methodName, args, env);
        }

        // Built-in library methods (Math, etc.)
        if (obj && typeof obj === 'object' && obj.__builtin) {
            if (typeof obj[methodName] === 'function') {
                return obj[methodName](...args);
            }
            throw new Error(`Built-in method '${methodName}' not found`);
        }

        // Generic object method
        if (obj && typeof obj === 'object' && typeof obj[methodName] === 'function') {
            return obj[methodName](...args);
        }

        throw new Error(`Method '${methodName}' not supported`);
    }

    // ── Array methods ──────────────────────────────────────────────────────────

    handleArrayMethod(arr, methodName, args, arrNode, env) {
        switch (methodName) {
            case 'push':
                for (const a of args) arr.push(a);
                return arr.length;
            case 'pop':
                if (arr.length === 0) throw new Error(`Cannot pop from empty array`);
                return arr.pop();
            case 'shift':
                if (arr.length === 0) throw new Error(`Cannot shift from empty array`);
                return arr.shift();
            case 'unshift':
                for (const a of args) arr.unshift(a);
                return arr.length;
            case 'slice':
                return arr.slice(args[0] || 0, args[1]);
            case 'indexOf':
                if (args.length === 0) throw new Error(`indexOf requires at least one argument`);
                return arr.indexOf(args[0]);
            case 'includes':
                if (args.length === 0) throw new Error(`includes requires at least one argument`);
                return arr.includes(args[0]);
            case 'join':
                return arr.join(args[0] !== undefined ? args[0] : ',');
            case 'reverse':
                arr.reverse();
                return arr;
            case 'sort':
                arr.sort();
                return arr;
            case 'length':
                return arr.length;
            default:
                throw new Error(`Unknown array method: ${methodName}`);
        }
    }

    // ── String methods ─────────────────────────────────────────────────────────

    handleStringMethod(str, methodName, args) {
        switch (methodName) {
            case 'length': return str.length;
            case 'toUpperCase': return str.toUpperCase();
            case 'toLowerCase': return str.toLowerCase();
            case 'trim': return str.trim();
            case 'includes': return str.includes(args[0]);
            case 'indexOf': return str.indexOf(args[0]);
            case 'slice': return str.slice(args[0], args[1]);
            case 'split': return str.split(args[0]);
            case 'replace': return str.replace(args[0], args[1]);
            default:
                throw new Error(`Unknown string method: ${methodName}`);
        }
    }

    // ── Member access ──────────────────────────────────────────────────────────

    evalMember(node, env) {
        const obj = this.evalExpr(node.object, env);
        const prop = node.property;

        // SECURITY: Prevent access to sensitive JS prototype properties
        const BLOCKLIST = ['constructor', '__proto__', 'prototype', 'call', 'apply', 'bind'];
        if (BLOCKLIST.includes(prop)) {
            this.logger.security(`Illegal property access attempt`, { property: prop });
            throw new Error(`Security Violation: Illegal access to property '${prop}'`);
        }

        // Class instance properties
        if (obj && typeof obj === 'object' && obj.__class && obj.__properties) {
            if (Object.prototype.hasOwnProperty.call(obj.__properties, prop)) return obj.__properties[prop];
            throw new Error(`Property '${prop}' not found in class ${obj.__class}`);
        }

        // Length property
        if (prop === 'length' && (Array.isArray(obj) || typeof obj === 'string')) {
            return obj.length;
        }

        // Generic object property
        if (typeof obj === 'object' && obj !== null && Object.prototype.hasOwnProperty.call(obj, prop)) {
            return obj[prop];
        }

        throw new Error(`Property '${prop}' not supported or access denied`);
    }

    // ── Index access ───────────────────────────────────────────────────────────

    evalIndex(node, env) {
        const obj = this.evalExpr(node.object, env);
        const index = this.evalExpr(node.index, env);

        // SECURITY: Block sensitive properties via indexing
        const BLOCKLIST = ['constructor', '__proto__', 'prototype'];
        if (BLOCKLIST.includes(String(index))) {
            this.logger.security(`Illegal indexed property access attempt`, { index });
            throw new Error(`Security Violation: Illegal access to property '${index}' via indexing`);
        }

        if (Array.isArray(obj)) {
            if (index < 0 || index >= obj.length) {
                throw new Error(`Array index out of bounds: ${index} (length: ${obj.length})`);
            }
            return obj[index];
        }

        if (typeof obj === 'string') {
            return obj[index];
        }

        if (typeof obj === 'object' && obj !== null) {
            return obj[index];
        }

        throw new ThirstyError(`Cannot index into ${typeof obj}`, 'TypeError');
    }

    // ── Assignment (a = b) ─────────────────────────────────────────────────────

    evalAssignment(node, env) {
        const value = this.evalExpr(node.right, env);
        if (node.left.type === NodeType.Identifier) {
            env.set(node.left.name, value);
        } else if (node.left.type === NodeType.MemberExpression) {
            const obj = this.evalExpr(node.left.object, env);
            obj[node.left.property] = value;
        }
        return value;
    }

    // ── Function calling ───────────────────────────────────────────────────────

    callFunction(funcName, args, callerEnv) {
        const func = this.functions[funcName];

        if (!func) {
            throw new ThirstyError(`Undefined function: ${funcName}`, 'ReferenceError');
        }

        if (this.callStack.length >= this.MAX_CALL_DEPTH) {
            throw new ThirstyError(`Maximum call depth exceeded (${this.MAX_CALL_DEPTH})`, 'StackOverflow');
        }

        if (args.length !== func.params.length) {
            throw new Error(`Function ${funcName} expects ${func.params.length} arguments, got ${args.length}`);
        }

        // Create a new scope parented to globally visible scope (closure semantics)
        const funcEnv = (func.closureEnv || this.globalEnv).child();
        for (let i = 0; i < func.params.length; i++) {
            funcEnv.define(func.params[i], args[i]);
        }

        this.callStack.push({ function: funcName });

        try {
            const result = this.execBlock(func.bodyNode.body, funcEnv);
            this.callStack.pop();
            if (result instanceof ReturnSignal) return result.value;
            return undefined;
        } catch (e) {
            this.callStack.pop();
            throw e;
        }
    }

    // ── Class instantiation ────────────────────────────────────────────────────

    instantiateClass(className, args, env) {
        if (!this.classes[className]) {
            throw new ThirstyError(`Undefined class: ${className}`, 'ReferenceError');
        }

        const classDef = this.classes[className];
        const instance = {
            __class: className,
            __properties: {},
            __methods: {},
        };

        // Evaluate default property values
        for (const prop of classDef.properties) {
            instance.__properties[prop.name] = this.evalExpr(prop.defaultValue, env);
        }

        // Bind methods
        for (const [name, method] of Object.entries(classDef.methods)) {
            instance.__methods[name] = method;
        }

        // Call constructor (named 'fountain')
        if (classDef.methods.fountain) {
            this.callInstanceMethod(instance, 'fountain', args, env);
        }

        return instance;
    }

    // ── Instance method call ───────────────────────────────────────────────────

    callInstanceMethod(instance, methodName, args, env) {
        if (!instance.__methods[methodName]) {
            throw new ThirstyError(`Method '${methodName}' not found in class ${instance.__class}`, 'ReferenceError');
        }

        const method = instance.__methods[methodName];

        if (args.length !== method.params.length) {
            throw new ThirstyError(`Method ${methodName} expects ${method.params.length} arguments, got ${args.length}`, 'TypeError');
        }

        const methodEnv = this.globalEnv.child();
        for (let i = 0; i < method.params.length; i++) {
            methodEnv.define(method.params[i], args[i]);
        }
        // Bind 'this' to instance properties
        methodEnv.define('this', instance.__properties);

        try {
            const result = this.execBlock(method.bodyNode.body, methodEnv);
            if (result instanceof ReturnSignal) return result.value;
            return undefined;
        } catch (e) {
            throw e;
        }
    }

    // ── Helpers ────────────────────────────────────────────────────────────────

    isTruthy(value) {
        return Boolean(value);
    }
}

module.exports = { ASTInterpreter, Environment, ReturnSignal, ThrowSignal, ThirstyError };
