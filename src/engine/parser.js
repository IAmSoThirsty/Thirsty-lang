#!/usr/bin/env node

/**
 * Thirsty-Lang Parser
 * ====================
 * Recursive-descent parser that consumes a Token[] stream and produces an AST.
 *
 * Expression precedence (lowest → highest):
 *   1. ||          (logical OR)
 *   2. &&          (logical AND)
 *   3. == !=       (equality)
 *   4. < > <= >=   (comparison)
 *   5. + -         (additive)
 *   6. * / %       (multiplicative)
 *   7. ! -         (unary prefix)
 *   8. . [] ()     (postfix: member, index, call)
 *   9. literals, identifiers, grouped expressions
 */

'use strict';

const { TokenType } = require('./tokenizer');

// ── AST Node Types ───────────────────────────────────────────────────────────
const NodeType = Object.freeze({
    Program: 'Program',
    // Literals
    NumberLiteral: 'NumberLiteral',
    StringLiteral: 'StringLiteral',
    BooleanLiteral: 'BooleanLiteral',
    NullLiteral: 'NullLiteral',
    ArrayLiteral: 'ArrayLiteral',
    // Expressions
    Identifier: 'Identifier',
    BinaryExpression: 'BinaryExpression',
    UnaryExpression: 'UnaryExpression',
    CallExpression: 'CallExpression',
    MemberExpression: 'MemberExpression',
    IndexExpression: 'IndexExpression',
    AssignmentExpression: 'AssignmentExpression',
    // Statements
    VariableDeclaration: 'VariableDeclaration',
    ReservoirDeclaration: 'ReservoirDeclaration',
    PourStatement: 'PourStatement',
    SipStatement: 'SipStatement',
    IfStatement: 'IfStatement',
    WhileStatement: 'WhileStatement',
    FunctionDeclaration: 'FunctionDeclaration',
    ClassDeclaration: 'ClassDeclaration',
    ReturnStatement: 'ReturnStatement',
    ThrowStatement: 'ThrowStatement',
    TryCatchStatement: 'TryCatchStatement',
    ShieldBlock: 'ShieldBlock',
    SanitizeStatement: 'SanitizeStatement',
    ArmorStatement: 'ArmorStatement',
    MorphStatement: 'MorphStatement',
    DetectStatement: 'DetectStatement',
    DefendStatement: 'DefendStatement',
    ImportStatement: 'ImportStatement',
    ExportStatement: 'ExportStatement',
    CascadeDeclaration: 'CascadeDeclaration',
    ExpressionStatement: 'ExpressionStatement',
    BlockStatement: 'BlockStatement',
    ObjectLiteral: 'ObjectLiteral',
});

// ── Parser ───────────────────────────────────────────────────────────────────
class Parser {
    /**
     * @param {Token[]} tokens - Token stream from the Tokenizer
     */
    constructor(tokens) {
        this.tokens = tokens;
        this.pos = 0;
    }

    // ── Public API ─────────────────────────────────────────────────────────────

    /**
     * Parse the token stream into a Program AST node.
     * @returns {{ type: 'Program', body: object[] }}
     */
    parse() {
        const body = [];
        while (!this.isAtEnd()) {
            const stmt = this.parseStatement();
            if (stmt) body.push(stmt);
        }
        return { type: NodeType.Program, body };
    }

    // ── Token navigation ──────────────────────────────────────────────────────

    current() {
        return this.tokens[this.pos];
    }

    peek(offset = 0) {
        const idx = this.pos + offset;
        return idx < this.tokens.length ? this.tokens[idx] : this.tokens[this.tokens.length - 1];
    }

    advance() {
        const tok = this.current();
        if (!this.isAtEnd()) this.pos++;
        return tok;
    }

    isAtEnd() {
        return this.current().type === TokenType.EOF;
    }

    /**
     * Check if the current token matches the given type and optionally value.
     */
    check(type, value) {
        const tok = this.current();
        if (tok.type !== type) return false;
        if (value !== undefined && tok.value !== value) return false;
        return true;
    }

    /**
     * Consume the current token if it matches; otherwise throw.
     */
    expect(type, value) {
        const tok = this.current();
        if (tok.type !== type || (value !== undefined && tok.value !== value)) {
            const expected = value !== undefined ? `${type}(${value})` : type;
            this.error(`Expected ${expected}, got ${tok.type}(${tok.value})`, tok);
        }
        return this.advance();
    }

    /**
     * If current token matches, advance and return true; else return false.
     */
    match(type, value) {
        if (this.check(type, value)) {
            this.advance();
            return true;
        }
        return false;
    }

    error(message, token) {
        const tok = token || this.current();
        throw new SyntaxError(
            `[Thirsty-Lang] Parse error at ${tok.line}:${tok.column} — ${message}`
        );
    }

    // ── Statement parsing ──────────────────────────────────────────────────────

    parseStatement() {
        const tok = this.current();

        if (tok.type === TokenType.KEYWORD) {
            switch (tok.value) {
                case 'drink': return this.parseVariableDeclaration();
                case 'reservoir': return this.parseReservoirDeclaration();
                case 'pour': return this.parsePourStatement();
                case 'sip': return this.parseSipStatement();
                case 'thirsty': return this.parseIfStatement();
                case 'refill': return this.parseWhileStatement();
                case 'glass': return this.parseFunctionDeclaration();
                case 'fountain': return this.parseClassDeclaration();
                case 'cascade': return this.parseCascadeDeclaration();
                case 'return': return this.parseReturnStatement();
                case 'throw': return this.parseThrowStatement();
                case 'try': return this.parseTryCatchStatement();
                case 'shield': return this.parseShieldBlock();
                case 'sanitize': return this.parseSanitizeStatement();
                case 'armor': return this.parseArmorStatement();
                case 'morph': return this.parseMorphStatement();
                case 'detect': return this.parseDetectStatement();
                case 'defend': return this.parseDefendStatement();
                case 'import': return this.parseImportStatement();
                case 'export': return this.parseExportStatement();
                case 'await': return this.parseAwaitStatement();
                default: break;
            }
        }

        // Expression statement (function calls, method calls, etc.)
        return this.parseExpressionStatement();
    }

    // ── drink varname = expr ───────────────────────────────────────────────────

    parseVariableDeclaration() {
        const tok = this.expect(TokenType.KEYWORD, 'drink');

        // Could be:  drink varname = expr
        //            drink obj.prop = expr
        //            drink arr[index] = expr
        const target = this.parsePostfix(this.parsePrimary());

        this.expect(TokenType.OPERATOR, '=');
        const init = this.parseExpression();

        return {
            type: NodeType.VariableDeclaration,
            target,
            value: init,
            line: tok.line, column: tok.column,
        };
    }

    // ── reservoir name = [elements] ────────────────────────────────────────────

    parseReservoirDeclaration() {
        const tok = this.expect(TokenType.KEYWORD, 'reservoir');
        const name = this.expect(TokenType.IDENTIFIER).value;
        this.expect(TokenType.OPERATOR, '=');
        const elements = this.parseArrayLiteral();

        return {
            type: NodeType.ReservoirDeclaration,
            name,
            elements: elements.elements,
            line: tok.line, column: tok.column,
        };
    }

    // ── pour expr ──────────────────────────────────────────────────────────────

    parsePourStatement() {
        const tok = this.expect(TokenType.KEYWORD, 'pour');
        const expr = this.parseExpression();
        return { type: NodeType.PourStatement, expression: expr, line: tok.line, column: tok.column };
    }

    // ── sip "prompt" | sip varname ─────────────────────────────────────────────

    parseSipStatement() {
        const tok = this.expect(TokenType.KEYWORD, 'sip');
        let prompt = null;
        let target = null;

        // sip "prompt" target
        // sip target
        if (this.check(TokenType.STRING)) {
            prompt = this.advance().value;
            if (this.check(TokenType.IDENTIFIER)) {
                target = this.advance().value;
            }
        } else if (this.check(TokenType.IDENTIFIER)) {
            target = this.advance().value;
        }

        return {
            type: NodeType.SipStatement,
            prompt,
            target,
            line: tok.line,
            column: tok.column
        };
    }

    // ── thirsty condition { ... } hydrated { ... } ────────────────────────────

    parseIfStatement() {
        const tok = this.expect(TokenType.KEYWORD, 'thirsty');
        const condition = this.parseExpression();
        const consequent = this.parseBlock();

        let alternate = null;
        if (this.check(TokenType.KEYWORD, 'hydrated')) {
            this.advance();
            // Check for else-if chain:  hydrated thirsty condition { ... }
            if (this.check(TokenType.KEYWORD, 'thirsty')) {
                alternate = this.parseIfStatement();
            } else {
                alternate = this.parseBlock();
            }
        }

        return {
            type: NodeType.IfStatement,
            condition,
            consequent,
            alternate,
            line: tok.line, column: tok.column,
        };
    }

    // ── refill condition { ... } ───────────────────────────────────────────────

    parseWhileStatement() {
        const tok = this.expect(TokenType.KEYWORD, 'refill');
        const condition = this.parseExpression();
        const body = this.parseBlock();
        return { type: NodeType.WhileStatement, condition, body, line: tok.line, column: tok.column };
    }

    // ── glass name(params) { ... } ────────────────────────────────────────────

    parseFunctionDeclaration() {
        const tok = this.expect(TokenType.KEYWORD, 'glass');
        const name = this.expect(TokenType.IDENTIFIER).value;
        const params = this.parseParamList();
        const body = this.parseBlock();
        return {
            type: NodeType.FunctionDeclaration,
            name, params, body,
            line: tok.line, column: tok.column,
        };
    }

    // ── fountain Name { ... } ─────────────────────────────────────────────────

    parseClassDeclaration() {
        const tok = this.expect(TokenType.KEYWORD, 'fountain');
        const name = this.expect(TokenType.IDENTIFIER).value;
        this.expect(TokenType.PUNCTUATION, '{');

        const methods = {};
        const properties = [];

        while (!this.check(TokenType.PUNCTUATION, '}') && !this.isAtEnd()) {
            if (this.check(TokenType.KEYWORD, 'glass')) {
                const method = this.parseFunctionDeclaration();
                if (!method.name) {
                    this.error('Class methods must have a name', method);
                }
                methods[method.name] = method;
            } else if (this.check(TokenType.KEYWORD, 'drink') || this.check(TokenType.KEYWORD, 'define')) {
                const propTok = this.advance(); // consume drink or define
                const propName = this.expect(TokenType.IDENTIFIER).value;
                this.expect(TokenType.OPERATOR, '=');
                const defaultValue = this.parseExpression();
                properties.push({ name: propName, defaultValue, line: propTok.line });
            } else {
                this.error('Expected method (glass) or property (drink) inside class body');
            }
        }

        this.expect(TokenType.PUNCTUATION, '}');

        return {
            type: NodeType.ClassDeclaration,
            name, methods, properties,
            line: tok.line, column: tok.column,
        };
    }

    // ── cascade name(params) { ... } ──────────────────────────────────────────

    parseCascadeDeclaration() {
        const tok = this.expect(TokenType.KEYWORD, 'cascade');
        const name = this.expect(TokenType.IDENTIFIER).value;
        const params = this.parseParamList();
        const body = this.parseBlock();
        return {
            type: NodeType.CascadeDeclaration,
            name, params, body,
            line: tok.line, column: tok.column,
        };
    }

    // ── return expr? ───────────────────────────────────────────────────────────

    parseReturnStatement() {
        const tok = this.expect(TokenType.KEYWORD, 'return');
        let value = null;
        // If the next token is NOT `}` or EOF, parse an expression
        if (!this.check(TokenType.PUNCTUATION, '}') && !this.isAtEnd()) {
            value = this.parseExpression();
        }
        return { type: NodeType.ReturnStatement, value, line: tok.line, column: tok.column };
    }

    // ── throw expr ─────────────────────────────────────────────────────────────

    parseThrowStatement() {
        const tok = this.expect(TokenType.KEYWORD, 'throw');
        const value = this.parseExpression();
        return { type: NodeType.ThrowStatement, value, line: tok.line, column: tok.column };
    }

    // ── try { ... } catch (e) { ... } finally { ... } ─────────────────────────

    parseTryCatchStatement() {
        const tok = this.expect(TokenType.KEYWORD, 'try');
        const tryBlock = this.parseBlock();

        let catchVar = null;
        let catchBlock = null;
        let finallyBlock = null;

        if (this.check(TokenType.KEYWORD, 'catch')) {
            this.advance();
            this.expect(TokenType.PUNCTUATION, '(');
            catchVar = this.expect(TokenType.IDENTIFIER).value;
            this.expect(TokenType.PUNCTUATION, ')');
            catchBlock = this.parseBlock();
        }

        if (this.check(TokenType.KEYWORD, 'finally')) {
            this.advance();
            finallyBlock = this.parseBlock();
        }

        if (!catchBlock && !finallyBlock) {
            this.error('try block must have at least a catch or finally block', tok);
        }

        return {
            type: NodeType.TryCatchStatement,
            tryBlock, catchVar, catchBlock, finallyBlock,
            line: tok.line, column: tok.column,
        };
    }

    // ── shield name { ... } ───────────────────────────────────────────────────

    parseShieldBlock() {
        const tok = this.expect(TokenType.KEYWORD, 'shield');
        const name = this.expect(TokenType.IDENTIFIER).value;
        const body = this.parseBlock();
        return { type: NodeType.ShieldBlock, name, body, line: tok.line, column: tok.column };
    }

    // ── sanitize varname ───────────────────────────────────────────────────────

    parseSanitizeStatement() {
        const tok = this.expect(TokenType.KEYWORD, 'sanitize');
        const varName = this.expect(TokenType.IDENTIFIER).value;
        return { type: NodeType.SanitizeStatement, varName, line: tok.line, column: tok.column };
    }

    // ── armor varname ──────────────────────────────────────────────────────────

    parseArmorStatement() {
        const tok = this.expect(TokenType.KEYWORD, 'armor');
        const varName = this.expect(TokenType.IDENTIFIER).value;
        return { type: NodeType.ArmorStatement, varName, line: tok.line, column: tok.column };
    }

    // ── morph on: [...] ────────────────────────────────────────────────────────

    parseMorphStatement() {
        const tok = this.expect(TokenType.KEYWORD, 'morph');
        // morph on: ["injection", "overflow", ...]
        // Parse the rest as raw key-value style
        const config = {};
        if (this.check(TokenType.IDENTIFIER, 'on')) {
            this.advance();
            this.expect(TokenType.PUNCTUATION, ':');
            const arr = this.parseArrayLiteral();
            config.on = arr.elements;
        }
        return { type: NodeType.MorphStatement, config, line: tok.line, column: tok.column };
    }

    // ── detect attacks { ... } ─────────────────────────────────────────────────

    parseDetectStatement() {
        const tok = this.expect(TokenType.KEYWORD, 'detect');
        const target = this.expect(TokenType.IDENTIFIER).value;
        const body = this.parseBlock();
        return { type: NodeType.DetectStatement, target, body, line: tok.line, column: tok.column };
    }

    // ── defend with: "level" ───────────────────────────────────────────────────

    parseDefendStatement() {
        const tok = this.expect(TokenType.KEYWORD, 'defend');
        const config = {};
        if (this.check(TokenType.IDENTIFIER, 'with')) {
            this.advance();
            this.expect(TokenType.PUNCTUATION, ':');
            config.with = this.parseExpression();
        }
        return { type: NodeType.DefendStatement, config, line: tok.line, column: tok.column };
    }

    // ── import { name1 } from "path" | import Name from "path" ─────────────────

    parseImportStatement() {
        const tok = this.expect(TokenType.KEYWORD, 'import');
        let names = [];
        let defaultName = null;

        if (this.check(TokenType.PUNCTUATION, '{')) {
            // Destructured import: import { a, b } from "path"
            this.advance();
            while (!this.check(TokenType.PUNCTUATION, '}') && !this.isAtEnd()) {
                names.push(this.expect(TokenType.IDENTIFIER).value);
                if (!this.check(TokenType.PUNCTUATION, '}')) {
                    this.expect(TokenType.PUNCTUATION, ',');
                }
            }
            this.expect(TokenType.PUNCTUATION, '}');
        } else {
            // Default import: import Name from "path"
            defaultName = this.expect(TokenType.IDENTIFIER).value;
        }

        this.expect(TokenType.KEYWORD, 'from');
        const modulePath = this.expect(TokenType.STRING).value;

        return {
            type: NodeType.ImportStatement,
            names, defaultName, modulePath,
            line: tok.line, column: tok.column,
        };
    }

    // ── export varname ─────────────────────────────────────────────────────────

    parseExportStatement() {
        const tok = this.expect(TokenType.KEYWORD, 'export');
        const name = this.expect(TokenType.IDENTIFIER).value;
        return { type: NodeType.ExportStatement, name, line: tok.line, column: tok.column };
    }

    // ── await expr (as statement) ──────────────────────────────────────────────

    parseAwaitStatement() {
        const tok = this.expect(TokenType.KEYWORD, 'await');
        const expr = this.parseExpression();
        return { type: NodeType.ExpressionStatement, expression: expr, isAwait: true, line: tok.line, column: tok.column };
    }

    // ── Expression statement ───────────────────────────────────────────────────

    parseExpressionStatement() {
        const tok = this.current();
        const expr = this.parseExpression();
        return { type: NodeType.ExpressionStatement, expression: expr, line: tok.line, column: tok.column };
    }

    // ── Block: { statement* } ─────────────────────────────────────────────────

    parseBlock() {
        this.expect(TokenType.PUNCTUATION, '{');
        const body = [];
        while (!this.check(TokenType.PUNCTUATION, '}') && !this.isAtEnd()) {
            const stmt = this.parseStatement();
            if (stmt) body.push(stmt);
        }
        this.expect(TokenType.PUNCTUATION, '}');
        return { type: NodeType.BlockStatement, body };
    }

    // ── Param list: (a, b, c) ─────────────────────────────────────────────────

    parseParamList() {
        this.expect(TokenType.PUNCTUATION, '(');
        const params = [];
        while (!this.check(TokenType.PUNCTUATION, ')') && !this.isAtEnd()) {
            params.push(this.expect(TokenType.IDENTIFIER).value);
            if (!this.check(TokenType.PUNCTUATION, ')')) {
                this.expect(TokenType.PUNCTUATION, ',');
            }
        }
        this.expect(TokenType.PUNCTUATION, ')');
        return params;
    }

    // ── Expression parsing (precedence climbing) ───────────────────────────────

    parseExpression() {
        return this.parseAssignment();
    }

    // Level 0: Assignment (=)
    parseAssignment() {
        const left = this.parseLogicalOr();

        if (this.check(TokenType.OPERATOR, '=')) {
            const tok = this.advance();
            const right = this.parseAssignment(); // Right-associative

            // Validate that left is a valid assignment target
            if (left.type !== NodeType.Identifier &&
                left.type !== NodeType.MemberExpression &&
                left.type !== NodeType.IndexExpression) {
                this.error('Invalid assignment target', tok);
            }

            return {
                type: NodeType.AssignmentExpression,
                left,
                operator: '=',
                right,
                line: tok.line, column: tok.column,
            };
        }

        return left;
    }

    // Level 1: ||
    parseLogicalOr() {
        let left = this.parseLogicalAnd();
        while (this.check(TokenType.OPERATOR, '||')) {
            const op = this.advance().value;
            const right = this.parseLogicalAnd();
            left = { type: NodeType.BinaryExpression, operator: op, left, right };
        }
        return left;
    }

    // Level 2: &&
    parseLogicalAnd() {
        let left = this.parseEquality();
        while (this.check(TokenType.OPERATOR, '&&')) {
            const op = this.advance().value;
            const right = this.parseEquality();
            left = { type: NodeType.BinaryExpression, operator: op, left, right };
        }
        return left;
    }

    // Level 3: == !=
    parseEquality() {
        let left = this.parseComparison();
        while (this.check(TokenType.OPERATOR, '==') || this.check(TokenType.OPERATOR, '!=')) {
            const op = this.advance().value;
            const right = this.parseComparison();
            left = { type: NodeType.BinaryExpression, operator: op, left, right };
        }
        return left;
    }

    // Level 4: < > <= >=
    parseComparison() {
        let left = this.parseAdditive();
        while (
            this.check(TokenType.OPERATOR, '<') ||
            this.check(TokenType.OPERATOR, '>') ||
            this.check(TokenType.OPERATOR, '<=') ||
            this.check(TokenType.OPERATOR, '>=')
        ) {
            const op = this.advance().value;
            const right = this.parseAdditive();
            left = { type: NodeType.BinaryExpression, operator: op, left, right };
        }
        return left;
    }

    // Level 5: + -
    parseAdditive() {
        let left = this.parseMultiplicative();
        while (this.check(TokenType.OPERATOR, '+') || this.check(TokenType.OPERATOR, '-')) {
            const op = this.advance().value;
            const right = this.parseMultiplicative();
            left = { type: NodeType.BinaryExpression, operator: op, left, right };
        }
        return left;
    }

    // Level 6: * / %
    parseMultiplicative() {
        let left = this.parseUnary();
        while (
            this.check(TokenType.OPERATOR, '*') ||
            this.check(TokenType.OPERATOR, '/') ||
            this.check(TokenType.OPERATOR, '%')
        ) {
            const op = this.advance().value;
            const right = this.parseUnary();
            left = { type: NodeType.BinaryExpression, operator: op, left, right };
        }
        return left;
    }

    // Level 7: ! (unary NOT), - (unary negate)
    parseUnary() {
        if (this.check(TokenType.OPERATOR, '!')) {
            const op = this.advance().value;
            const operand = this.parseUnary();
            return { type: NodeType.UnaryExpression, operator: op, operand };
        }
        if (this.check(TokenType.OPERATOR, '-')) {
            const op = this.advance().value;
            const operand = this.parseUnary();
            return { type: NodeType.UnaryExpression, operator: op, operand };
        }
        return this.parsePostfix(this.parsePrimary());
    }

    // Level 8: . [] () (member access, indexing, function calls)
    parsePostfix(expr) {
        while (true) {
            if (this.check(TokenType.PUNCTUATION, '.')) {
                this.advance();
                const prop = this.expect(TokenType.IDENTIFIER).value;

                // Check if it's a method call: obj.method(args)
                if (this.check(TokenType.PUNCTUATION, '(')) {
                    const args = this.parseArgList();
                    expr = {
                        type: NodeType.CallExpression,
                        callee: { type: NodeType.MemberExpression, object: expr, property: prop },
                        arguments: args,
                    };
                } else {
                    expr = { type: NodeType.MemberExpression, object: expr, property: prop };
                }
            } else if (this.check(TokenType.PUNCTUATION, '[')) {
                this.advance();
                const index = this.parseExpression();
                this.expect(TokenType.PUNCTUATION, ']');
                expr = { type: NodeType.IndexExpression, object: expr, index };
            } else if (this.check(TokenType.PUNCTUATION, '(') && expr.type === NodeType.Identifier) {
                // Standalone function call: funcName(args)
                const args = this.parseArgList();
                expr = { type: NodeType.CallExpression, callee: expr, arguments: args };
            } else {
                break;
            }
        }
        return expr;
    }

    // Level 9: Primary expressions (literals, identifiers, grouped, arrays)
    parsePrimary() {
        const tok = this.current();

        // Number literal
        if (tok.type === TokenType.NUMBER) {
            this.advance();
            return { type: NodeType.NumberLiteral, value: tok.value, line: tok.line, column: tok.column };
        }

        // String literal
        if (tok.type === TokenType.STRING) {
            this.advance();
            return { type: NodeType.StringLiteral, value: tok.value, line: tok.line, column: tok.column };
        }

        // Boolean literals
        if (tok.type === TokenType.KEYWORD && tok.value === 'true') {
            const t = this.advance();
            return { type: NodeType.BooleanLiteral, value: true, line: t.line, column: t.column };
        }
        if (tok.type === TokenType.KEYWORD && tok.value === 'false') {
            const t = this.advance();
            return { type: NodeType.BooleanLiteral, value: false, line: t.line, column: t.column };
        }
        if (tok.type === TokenType.KEYWORD && tok.value === 'null') {
            const t = this.advance();
            return { type: NodeType.NullLiteral, value: null, line: t.line, column: t.column };
        }

        // 'new' keyword for class instantiation — treat as function call
        if (tok.type === TokenType.KEYWORD && tok.value === 'new') {
            const startTok = this.advance();
            const className = this.expect(TokenType.IDENTIFIER).value;
            const args = this.parseArgList();
            return {
                type: NodeType.CallExpression,
                callee: { type: NodeType.Identifier, name: className },
                arguments: args,
                isNew: true,
                line: startTok.line, column: startTok.column
            };
        }

        // await expression inside an expression context
        if (tok.type === TokenType.KEYWORD && tok.value === 'await') {
            const startTok = this.advance();
            const expr = this.parseUnary();
            return { type: NodeType.UnaryExpression, operator: 'await', operand: expr, line: startTok.line, column: startTok.column };
        }

        // Identifiers (variable names, function names)
        if (tok.type === TokenType.IDENTIFIER) {
            const t = this.advance();
            return { type: NodeType.Identifier, name: t.value, line: t.line, column: t.column };
        }

        // 'this' keyword (treated as identifier)
        if (tok.type === TokenType.KEYWORD && tok.value === 'this') {
            const t = this.advance();
            return { type: NodeType.Identifier, name: 'this', line: t.line, column: t.column };
        }

        // Grouped expression: ( expr )
        if (tok.type === TokenType.PUNCTUATION && tok.value === '(') {
            this.advance();
            const expr = this.parseExpression();
            this.expect(TokenType.PUNCTUATION, ')');
            return expr;
        }

        // Anonymous function expression: glass(args) { ... }
        if (tok.type === TokenType.KEYWORD && (tok.value === 'glass' || tok.value === 'cascade')) {
            const isAsync = tok.value === 'cascade';
            const startTok = this.advance();
            
            // If next is Identifier, it's a statement handled by parseStatement
            // But if we're here, we're in parsePrimary (expression context)
            // So we treat it as an anonymous function
            const params = this.parseParamList();
            const body = this.parseBlock();
            return {
                type: isAsync ? NodeType.CascadeDeclaration : NodeType.FunctionDeclaration,
                name: null, // Anonymous
                params,
                body,
                line: startTok.line, column: startTok.column
            };
        }

        // Array literal: [elem, ...]
        if (tok.type === TokenType.PUNCTUATION && tok.value === '[') {
            return this.parseArrayLiteral();
        }

        // Object literal: { key: val, ... }
        if (tok.type === TokenType.PUNCTUATION && tok.value === '{') {
            return this.parseObjectLiteral();
        }

        this.error(`Unexpected token: ${tok.type}(${tok.value})`, tok);
    }

    // ── Array literal: [a, b, c] ───────────────────────────────────────────────

    parseArrayLiteral() {
        this.expect(TokenType.PUNCTUATION, '[');
        const elements = [];
        while (!this.check(TokenType.PUNCTUATION, ']') && !this.isAtEnd()) {
            elements.push(this.parseExpression());
            if (!this.check(TokenType.PUNCTUATION, ']')) {
                this.expect(TokenType.PUNCTUATION, ',');
            }
        }
        this.expect(TokenType.PUNCTUATION, ']');
        return { type: NodeType.ArrayLiteral, elements };
    }

    parseObjectLiteral() {
        const tok = this.expect(TokenType.PUNCTUATION, '{');
        const properties = {};
        while (!this.check(TokenType.PUNCTUATION, '}') && !this.isAtEnd()) {
            let key;
            if (this.check(TokenType.IDENTIFIER)) {
                key = this.advance().value;
            } else if (this.check(TokenType.STRING)) {
                key = this.advance().value;
            } else {
                this.error('Expected identifier or string for object key');
            }

            this.expect(TokenType.PUNCTUATION, ':');
            const value = this.parseExpression();
            properties[key] = value;

            if (!this.check(TokenType.PUNCTUATION, '}')) {
                this.expect(TokenType.PUNCTUATION, ',');
            }
        }
        this.expect(TokenType.PUNCTUATION, '}');
        return { type: NodeType.ObjectLiteral, properties, line: tok.line, column: tok.column };
    }

    // ── Argument list: (a, b, c) ───────────────────────────────────────────────

    parseArgList() {
        this.expect(TokenType.PUNCTUATION, '(');
        const args = [];
        while (!this.check(TokenType.PUNCTUATION, ')') && !this.isAtEnd()) {
            args.push(this.parseExpression());
            if (!this.check(TokenType.PUNCTUATION, ')')) {
                this.expect(TokenType.PUNCTUATION, ',');
            }
        }
        this.expect(TokenType.PUNCTUATION, ')');
        return args;
    }
}

module.exports = { Parser, NodeType };
