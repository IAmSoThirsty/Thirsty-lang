/**
 * AST Standard Library and Input Tests
 */

const { ThirstyInterpreter } = require('../index');

class StdlibTestRunner {
    constructor() {
        this.passed = 0;
        this.failed = 0;
    }

    assertEqual(actual, expected, message) {
        if (actual !== expected) {
            throw new Error(message || `Expected ${expected}, got ${actual}`);
        }
    }

    async run() {
        console.log('Running AST Stdlib & Input Tests...\n');

        const tests = [
            {
                name: 'Math.PI access',
                fn: () => {
                    const interpreter = new ThirstyInterpreter();
                    interpreter.execute('drink pi = Math.PI');
                    this.assertEqual(interpreter.variables.pi, 3.14159265359);
                }
            },
            {
                name: 'Math.abs function call',
                fn: () => {
                    const interpreter = new ThirstyInterpreter();
                    interpreter.execute('drink x = -42\ndrink result = Math.abs(x)');
                    this.assertEqual(interpreter.variables.result, 42);
                }
            },
            {
                name: 'JSON.stringify and JSON.parse',
                fn: () => {
                    const interpreter = new ThirstyInterpreter();
                    interpreter.execute('drink obj = [1, 2, "three"]\ndrink json = JSON.stringify(obj)\ndrink parsed = JSON.parse(json)');
                    this.assertEqual(JSON.stringify(interpreter.variables.parsed), JSON.stringify([1, 2, "three"]));
                }
            },
            {
                name: 'Sip statement with target assignment',
                fn: () => {
                    const interpreter = new ThirstyInterpreter();
                    // Mock input handler
                    interpreter.inputHandler = (prompt) => 'simulated input';
                    interpreter.execute('sip "Enter data:" myVar');
                    this.assertEqual(interpreter.variables.myVar, 'simulated input');
                }
            },
            {
                name: 'Sanitize keyword',
                fn: () => {
                    const interpreter = new ThirstyInterpreter();
                    interpreter.execute('drink raw = "<b>alert(1)</b>"\nsanitize raw');
                    // Removes tags but keeps content
                    this.assertEqual(interpreter.variables.raw, 'alert(1)');
                }
            },
            {
                name: 'Shield keyword execution',
                fn: () => {
                    const interpreter = new ThirstyInterpreter();
                    interpreter.execute('shield highSecurity { drink x = 1 }');
                    this.assertEqual(interpreter.securityManager.shieldActive, false);
                }
            },
            {
                name: 'Morph keyword execution',
                fn: () => {
                    const interpreter = new ThirstyInterpreter();
                    interpreter.execute('morph on: ["id_rename", "obfuscate"]');
                    this.assertEqual(interpreter.securityManager.protections.has("id_rename"), true);
                    this.assertEqual(interpreter.securityManager.protections.has("obfuscate"), true);
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

new StdlibTestRunner().run();
