#!/usr/bin/env node

/**
 * Thirsty-Lang Tokenizer (Lexer)
 * ==============================
 * Converts source text into a flat Token[] stream.
 *
 * Each token: { type, value, line, column }
 *
 * Token Types:
 *   NUMBER, STRING, IDENTIFIER, KEYWORD, OPERATOR, PUNCTUATION, EOF
 */

'use strict';

// ── Token type constants ─────────────────────────────────────────────────────
const TokenType = Object.freeze({
    NUMBER: 'NUMBER',
    STRING: 'STRING',
    IDENTIFIER: 'IDENTIFIER',
    KEYWORD: 'KEYWORD',
    OPERATOR: 'OPERATOR',
    PUNCTUATION: 'PUNCTUATION',
    EOF: 'EOF',
});

// ── Language keywords ────────────────────────────────────────────────────────
const KEYWORDS = new Set([
    // Core (Thirsty-Lang)
    'drink', 'pour', 'sip',
    // Control flow (Thirst of Gods)
    'thirsty', 'hydrated',
    // Functions & loops (T.A.R.L.)
    'glass', 'refill', 'reservoir', 'return',
    // Classes & advanced (Thirsty's Shadow)
    'fountain', 'cascade', 'sacred', 'new',
    // Security
    'shield', 'sanitize', 'armor', 'morph', 'detect', 'defend',
    // Modules
    'import', 'export', 'from',
    // Exception handling
    'throw', 'try', 'catch', 'finally',
    // Async
    'await',
    // Boolean literals (treated as keywords, evaluated as values)
    'true', 'false',
]);

// ── Multi-character operators (checked longest-first) ────────────────────────
const MULTI_OPS = ['==', '!=', '>=', '<=', '&&', '||'];

// ── Single-character operators ───────────────────────────────────────────────
const SINGLE_OPS = new Set(['+', '-', '*', '/', '%', '>', '<', '!', '=']);

// ── Punctuation ──────────────────────────────────────────────────────────────
const PUNCTUATION = new Set(['(', ')', '{', '}', '[', ']', ',', '.', ':', ';']);

// ── Token class ──────────────────────────────────────────────────────────────
class Token {
    /**
     * @param {string} type   - One of TokenType values
     * @param {*}      value  - The raw value (string for most, number for NUMBER)
     * @param {number} line   - 1-indexed source line
     * @param {number} column - 1-indexed source column
     */
    constructor(type, value, line, column) {
        this.type = type;
        this.value = value;
        this.line = line;
        this.column = column;
    }

    toString() {
        return `Token(${this.type}, ${JSON.stringify(this.value)}, ${this.line}:${this.column})`;
    }
}

// ── Tokenizer ────────────────────────────────────────────────────────────────
class Tokenizer {
    /**
     * @param {string} source - The complete Thirsty-Lang source code
     */
    constructor(source) {
        this.source = source;
        this.pos = 0;
        this.line = 1;
        this.column = 1;
        this.tokens = [];
    }

    // ── Public API ─────────────────────────────────────────────────────────────

    /**
     * Tokenize the entire source and return the token array (including EOF).
     * @returns {Token[]}
     */
    tokenize() {
        while (this.pos < this.source.length) {
            this.skipWhitespaceAndComments();
            if (this.pos >= this.source.length) break;

            const ch = this.source[this.pos];

            if (ch === '"' || ch === "'") {
                this.readString(ch);
            } else if (this.isDigit(ch)) {
                this.readNumber();
            } else if (this.isIdentStart(ch)) {
                this.readIdentifierOrKeyword();
            } else if (this.isMultiOp()) {
                this.readMultiOp();
            } else if (SINGLE_OPS.has(ch)) {
                this.tokens.push(new Token(TokenType.OPERATOR, ch, this.line, this.column));
                this.advance();
            } else if (PUNCTUATION.has(ch)) {
                this.tokens.push(new Token(TokenType.PUNCTUATION, ch, this.line, this.column));
                this.advance();
            } else {
                this.error(`Unexpected character: '${ch}'`);
            }
        }

        this.tokens.push(new Token(TokenType.EOF, null, this.line, this.column));
        return this.tokens;
    }

    // ── Private helpers ────────────────────────────────────────────────────────

    /** Peek at current character without consuming. */
    peek() {
        return this.pos < this.source.length ? this.source[this.pos] : null;
    }

    /** Peek at the next character (pos + 1). */
    peekNext() {
        return (this.pos + 1) < this.source.length ? this.source[this.pos + 1] : null;
    }

    /** Advance one character, updating line/column counters. */
    advance() {
        if (this.pos < this.source.length) {
            if (this.source[this.pos] === '\n') {
                this.line++;
                this.column = 1;
            } else {
                this.column++;
            }
            this.pos++;
        }
    }

    /** Skip whitespace (spaces, tabs, \r, \n) and single-line comments. */
    skipWhitespaceAndComments() {
        while (this.pos < this.source.length) {
            const ch = this.source[this.pos];

            // Whitespace
            if (ch === ' ' || ch === '\t' || ch === '\r' || ch === '\n') {
                this.advance();
                continue;
            }

            // Single-line comment: // ...
            if (ch === '/' && this.peekNext() === '/') {
                while (this.pos < this.source.length && this.source[this.pos] !== '\n') {
                    this.advance();
                }
                continue;
            }

            break;
        }
    }

    /** Read a string literal (single or double quoted). */
    readString(quote) {
        const startLine = this.line;
        const startCol = this.column;
        this.advance(); // skip opening quote

        let value = '';
        while (this.pos < this.source.length) {
            const ch = this.source[this.pos];

            if (ch === '\\') {
                // Escape sequence
                this.advance();
                if (this.pos >= this.source.length) {
                    this.error('Unterminated string literal', startLine, startCol);
                }
                const esc = this.source[this.pos];
                switch (esc) {
                    case 'n': value += '\n'; break;
                    case 't': value += '\t'; break;
                    case 'r': value += '\r'; break;
                    case '\\': value += '\\'; break;
                    case '"': value += '"'; break;
                    case "'": value += "'"; break;
                    default: value += esc; break;
                }
                this.advance();
                continue;
            }

            if (ch === quote) {
                this.advance(); // skip closing quote
                this.tokens.push(new Token(TokenType.STRING, value, startLine, startCol));
                return;
            }

            if (ch === '\n') {
                this.error('Unterminated string literal (newline in string)', startLine, startCol);
            }

            value += ch;
            this.advance();
        }

        this.error('Unterminated string literal', startLine, startCol);
    }

    /** Read a numeric literal (integer or float). */
    readNumber() {
        const startCol = this.column;
        let numStr = '';
        let hasDot = false;

        while (this.pos < this.source.length) {
            const ch = this.source[this.pos];
            if (this.isDigit(ch)) {
                numStr += ch;
                this.advance();
            } else if (ch === '.' && !hasDot) {
                // Check it's a decimal point, not member access
                const next = this.peekNext();
                if (next !== null && this.isDigit(next)) {
                    hasDot = true;
                    numStr += ch;
                    this.advance();
                } else {
                    break; // It's member access (e.g. 5.toString)
                }
            } else {
                break;
            }
        }

        this.tokens.push(new Token(TokenType.NUMBER, parseFloat(numStr), this.line, startCol));
    }

    /** Read an identifier or keyword. */
    readIdentifierOrKeyword() {
        const startCol = this.column;
        let name = '';

        while (this.pos < this.source.length && this.isIdentChar(this.source[this.pos])) {
            name += this.source[this.pos];
            this.advance();
        }

        const type = KEYWORDS.has(name) ? TokenType.KEYWORD : TokenType.IDENTIFIER;
        this.tokens.push(new Token(type, name, this.line, startCol));
    }

    /** Check if current position starts a multi-character operator. */
    isMultiOp() {
        for (const op of MULTI_OPS) {
            if (this.source.substring(this.pos, this.pos + op.length) === op) {
                return true;
            }
        }
        return false;
    }

    /** Read a multi-character operator. */
    readMultiOp() {
        const startCol = this.column;
        for (const op of MULTI_OPS) {
            if (this.source.substring(this.pos, this.pos + op.length) === op) {
                for (let i = 0; i < op.length; i++) this.advance();
                this.tokens.push(new Token(TokenType.OPERATOR, op, this.line, startCol));
                return;
            }
        }
    }

    // ── Character classifiers ──────────────────────────────────────────────────

    isDigit(ch) {
        return ch >= '0' && ch <= '9';
    }

    isIdentStart(ch) {
        return (ch >= 'a' && ch <= 'z') ||
            (ch >= 'A' && ch <= 'Z') ||
            ch === '_';
    }

    isIdentChar(ch) {
        return this.isIdentStart(ch) || this.isDigit(ch);
    }

    // ── Error reporting ────────────────────────────────────────────────────────

    error(message, line, col) {
        const l = line || this.line;
        const c = col || this.column;
        throw new SyntaxError(`[Thirsty-Lang] Tokenizer error at ${l}:${c} — ${message}`);
    }
}

module.exports = { Tokenizer, Token, TokenType, KEYWORDS };
