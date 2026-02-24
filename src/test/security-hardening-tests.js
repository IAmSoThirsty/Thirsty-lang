#!/usr/bin/env node

/**
 * Thirsty-Lang Security Hardening Tests
 * ====================================
 * Verifies that prototype pollution and sandbox escapes are blocked.
 */

const { ThirstyInterpreter } = require('../index');
const { ThirstyError } = require('../engine/ast-interpreter');
const { Tokenizer } = require('../engine/tokenizer');

class HardeningTester {
    constructor() {
        this.passed = 0;
        this.failed = 0;
    }

    assertEqual(actual, expected, message) {
        if (actual === expected) {
            return true;
        }
        throw new Error(`${message}: Expected ${expected}, got ${actual}`);
    }

    assertThrows(fn, expectedMessagePart, message, code) {
        try {
            fn();
            throw new Error(`${message}: Expected error containing "${expectedMessagePart}", but no error was thrown`);
        } catch (error) {
            if (error.message.includes(expectedMessagePart)) {
                return true;
            }
            if (error.message.includes('Parse error') && code) {
                const t = new Tokenizer(code);
                console.log(`Tokens for "${code}":`, t.tokenize().map(tok => tok.toString()));
            }
            throw new Error(`${message}: Expected error containing "${expectedMessagePart}", but got "${error.message}"`);
        }
    }

    run() {
        console.log('Running AST Security Hardening Tests...');

        const tests = [
            {
                name: 'Prototype Pollution Block (Environment store)',
                fn: () => {
                    const interpreter = new ThirstyInterpreter();
                    const code = 'drink x = constructor';
                    this.assertThrows(() => {
                        interpreter.execute(code);
                    }, 'Undefined identifier: constructor', 'Accessing "constructor" as identifier should fail', code);
                }
            },
            {
                name: 'Member Access Blocklist (constructor)',
                fn: () => {
                    const interpreter = new ThirstyInterpreter();
                    const code = 'drink obj = {}\ndrink c = obj.constructor';
                    this.assertThrows(() => {
                        interpreter.execute(code);
                    }, 'Security Violation: Illegal access to property \'constructor\'', 'Accessing .constructor should be blocked', code);
                }
            },
            {
                name: 'Member Access Blocklist (__proto__)',
                fn: () => {
                    const interpreter = new ThirstyInterpreter();
                    const code = 'drink obj = {}\ndrink p = obj.__proto__';
                    this.assertThrows(() => {
                        interpreter.execute(code);
                    }, 'Security Violation: Illegal access to property \'__proto__\'', 'Accessing .__proto__ should be blocked', code);
                }
            },
            {
                name: 'Indexed Access Blocklist',
                fn: () => {
                    const interpreter = new ThirstyInterpreter();
                    const code = 'drink obj = {}\ndrink c = obj["constructor"]';
                    this.assertThrows(() => {
                        interpreter.execute(code);
                    }, 'Security Violation: Illegal access to property \'constructor\' via indexing', 'Accessing ["constructor"] should be blocked', code);
                }
            },
            {
                name: 'JSON Logs format verification',
                fn: () => {
                    const logs = [];
                    const originalLog = console.log;
                    console.log = (msg) => logs.push(msg);

                    try {
                        const interpreter = new ThirstyInterpreter({ jsonLogs: true });
                        interpreter.execute('shield TEST { drink x = 1 }');

                        this.assertEqual(logs.length > 0, true, 'Should have logs');
                        const lastLog = JSON.parse(logs[0]);
                        this.assertEqual(lastLog.component, 'SECURITY', 'Component should be SECURITY');
                        this.assertEqual(lastLog.message, 'Entering shielded context', 'Message should match');
                        this.assertEqual(lastLog.context, 'TEST', 'Context should be passed');
                    } finally {
                        console.log = originalLog;
                    }
                }
            },
            {
                name: 'Armored variable protection',
                fn: () => {
                    const interpreter = new ThirstyInterpreter();
                    interpreter.execute('drink x = 10\narmor x');
                    this.assertThrows(() => {
                        interpreter.execute('x = 20');
                    }, 'Cannot assign to armored variable', 'Reassigning armored var should fail');
                }
            }
        ];

        for (const test of tests) {
            try {
                test.fn();
                this.passed++;
                console.log(`✓ ${test.name}`);
            } catch (error) {
                this.failed++;
                console.log(`✗ ${test.name}`);
                console.log(`  ${error.message}`);
            }
        }

        console.log(`\n${this.passed + this.failed} tests, ${this.passed} passed, ${this.failed} failed`);
        if (this.failed > 0) process.exit(1);
    }
}

if (require.main === module) {
    new HardeningTester().run();
}
