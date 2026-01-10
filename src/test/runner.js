/**
 * Test Runner for Thirsty-lang
 */

const ThirstyInterpreter = require('../index');

class TestRunner {
  constructor() {
    this.passed = 0;
    this.failed = 0;
    this.tests = [];
  }

  test(name, fn) {
    this.tests.push({ name, fn });
  }

  run() {
    console.log('Running Thirsty-lang Tests...\n');

    for (const { name, fn } of this.tests) {
      try {
        fn();
        this.passed++;
        console.log(`✓ ${name}`);
      } catch (error) {
        this.failed++;
        console.log(`✗ ${name}`);
        console.log(`  ${error.message}`);
      }
    }

    console.log(`\n${this.passed + this.failed} tests, ${this.passed} passed, ${this.failed} failed`);
    process.exit(this.failed > 0 ? 1 : 0);
  }

  assertEqual(actual, expected, message) {
    if (actual !== expected) {
      throw new Error(message || `Expected ${expected}, got ${actual}`);
    }
  }
}

const runner = new TestRunner();

// Test variable declaration and retrieval
runner.test('Variable declaration with string', () => {
  const interpreter = new ThirstyInterpreter();
  interpreter.execute('drink water = "H2O"');
  runner.assertEqual(interpreter.variables.water, 'H2O', 'Variable should store string value');
});

runner.test('Variable declaration with number', () => {
  const interpreter = new ThirstyInterpreter();
  interpreter.execute('drink amount = 42');
  runner.assertEqual(interpreter.variables.amount, 42, 'Variable should store number value');
});

runner.test('Pour statement with literal', () => {
  const interpreter = new ThirstyInterpreter();
  const oldLog = console.log;
  let output = '';
  console.log = (msg) => { output = msg; };
  
  interpreter.execute('pour "Hello, Thirsty World!"');
  console.log = oldLog;
  
  runner.assertEqual(output, 'Hello, Thirsty World!', 'Should output literal string');
});

runner.test('Pour statement with variable', () => {
  const interpreter = new ThirstyInterpreter();
  const oldLog = console.log;
  let output = '';
  console.log = (msg) => { output = msg; };
  
  interpreter.execute('drink message = "Hydrate!"\npour message');
  console.log = oldLog;
  
  runner.assertEqual(output, 'Hydrate!', 'Should output variable value');
});

runner.test('Multiple statements', () => {
  const interpreter = new ThirstyInterpreter();
  interpreter.execute('drink a = 1\ndrink b = 2\ndrink c = 3');
  runner.assertEqual(interpreter.variables.a, 1);
  runner.assertEqual(interpreter.variables.b, 2);
  runner.assertEqual(interpreter.variables.c, 3);
});

runner.test('Comments are ignored', () => {
  const interpreter = new ThirstyInterpreter();
  interpreter.execute('// This is a comment\ndrink water = "clean"');
  runner.assertEqual(interpreter.variables.water, 'clean', 'Comments should be ignored');
});

runner.test('String concatenation', () => {
  const interpreter = new ThirstyInterpreter();
  const oldLog = console.log;
  let output = '';
  console.log = (msg) => { output = msg; };
  
  interpreter.execute('drink first = "Hello"\ndrink second = "World"\npour first + " " + second');
  console.log = oldLog;
  
  runner.assertEqual(output, 'Hello World', 'Should concatenate strings');
});

runner.test('Arithmetic expression evaluation', () => {
  const interpreter = new ThirstyInterpreter();
  const oldLog = console.log;
  let outputs = [];
  console.log = (msg) => { outputs.push(msg); };
  
  interpreter.execute('pour 10 + 5\npour 10 - 5\npour 10 * 5\npour 10 / 5');
  console.log = oldLog;
  
  runner.assertEqual(outputs[0], 15, 'Should evaluate addition');
  runner.assertEqual(outputs[1], 5, 'Should evaluate subtraction');
  runner.assertEqual(outputs[2], 50, 'Should evaluate multiplication');
  runner.assertEqual(outputs[3], 2, 'Should evaluate division');
});

runner.test('Operator precedence', () => {
  const interpreter = new ThirstyInterpreter();
  const oldLog = console.log;
  let output;
  console.log = (msg) => { output = msg; };
  
  interpreter.execute('pour 2 + 3 * 4');
  console.log = oldLog;
  
  runner.assertEqual(output, 14, 'Should respect operator precedence (multiply before add)');
});

runner.test('Conditional statements (thirsty)', () => {
  const interpreter = new ThirstyInterpreter();
  const oldLog = console.log;
  let output = '';
  console.log = (msg) => { output = msg; };
  
  interpreter.execute('drink x = 10\nthirsty x > 5 {\npour "yes"\n}');
  console.log = oldLog;
  
  runner.assertEqual(output, 'yes', 'Should execute if block when condition is true');
});

runner.test('Conditional with hydrated (else) block', () => {
  const interpreter = new ThirstyInterpreter();
  const oldLog = console.log;
  let output = '';
  console.log = (msg) => { output = msg; };
  
  interpreter.execute('drink x = 3\nthirsty x > 5 {\npour "yes"\n}\nhydrated {\npour "no"\n}');
  console.log = oldLog;
  
  runner.assertEqual(output, 'no', 'Should execute else block when condition is false');
});

runner.test('Comparison operators', () => {
  const interpreter = new ThirstyInterpreter();
  const oldLog = console.log;
  let outputs = [];
  console.log = (msg) => { outputs.push(msg); };
  
  interpreter.execute('drink a = 5\ndrink b = 10\nthirsty a < b {\npour "less"\n}\nthirsty a == 5 {\npour "equal"\n}');
  console.log = oldLog;
  
  runner.assertEqual(outputs[0], 'less', 'Should handle less than');
  runner.assertEqual(outputs[1], 'equal', 'Should handle equality');
});

runner.test('Loop (refill) functionality', () => {
  const interpreter = new ThirstyInterpreter();
  const oldLog = console.log;
  let outputs = [];
  console.log = (msg) => { outputs.push(msg); };
  
  interpreter.execute('drink i = 0\nrefill i < 3 {\npour i\ndrink i = i + 1\n}');
  console.log = oldLog;
  
  runner.assertEqual(outputs.length, 3, 'Loop should execute 3 times');
  runner.assertEqual(outputs[0], 0, 'First iteration');
  runner.assertEqual(outputs[1], 1, 'Second iteration');
  runner.assertEqual(outputs[2], 2, 'Third iteration');
});

runner.test('Error: Division by zero', () => {
  const interpreter = new ThirstyInterpreter();
  let errorCaught = false;
  
  try {
    interpreter.execute('pour 10 / 0');
  } catch (error) {
    errorCaught = error.message.includes('Division by zero');
  }
  
  runner.assertEqual(errorCaught, true, 'Should throw error for division by zero');
});

runner.test('Error: Unmatched braces', () => {
  const interpreter = new ThirstyInterpreter();
  let errorCaught = false;
  
  try {
    interpreter.execute('thirsty true {\npour "test"');
  } catch (error) {
    errorCaught = error.message.includes('Unmatched');
  }
  
  runner.assertEqual(errorCaught, true, 'Should throw error for unmatched braces');
});

runner.test('Error: Invalid expression', () => {
  const interpreter = new ThirstyInterpreter();
  let errorCaught = false;
  
  try {
    interpreter.execute('pour unknownVariable');
  } catch (error) {
    errorCaught = error.message.includes('Unknown expression');
  }
  
  runner.assertEqual(errorCaught, true, 'Should throw error for unknown expression');
});

runner.run();
