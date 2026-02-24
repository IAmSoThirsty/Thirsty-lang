#!/usr/bin/env node

/**
 * Thirsty-Lang CLI
 * Command-line interface for running Thirsty-Lang programs
 */

const fs = require('fs');
const path = require('path');
const { ThirstyInterpreter } = require('./index');

function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.log('Thirsty-Lang Interpreter v1.0.0');
    console.log('Usage: node src/cli.js <filename.thirsty>');
    console.log('       npm start <filename.thirsty>');
    console.log('\nStay hydrated! 💧');
    process.exit(0);
  }

  const filename = args[0];
  
  if (!fs.existsSync(filename)) {
    console.error(`Error: File '${filename}' not found`);
    process.exit(1);
  }

  try {
    const code = fs.readFileSync(filename, 'utf-8');
    const interpreter = new ThirstyInterpreter({
      currentFile: path.resolve(filename)
    });
    interpreter.execute(code);
  } catch (error) {
    console.error(`Error: ${error.message}`);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = main;
