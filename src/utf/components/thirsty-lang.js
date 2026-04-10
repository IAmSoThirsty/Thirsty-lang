/**
 * Tier 1 - Thirsty-Lang
 * Core language wrapper around the existing ThirstyInterpreter.
 */

const path = require('path');
const fs = require('fs');
const { ThirstyInterpreter } = require(path.join(__dirname, '..', '..', 'index'));

class ThirstyLang {
  constructor(options = {}) {
    this.tier = 1;
    this.name = 'Thirsty-Lang';
    this.interpreter = new ThirstyInterpreter(options);
  }

  execute(code) {
    this.interpreter.execute(code);
    return this;
  }

  executeFile(filePath) {
    const code = fs.readFileSync(filePath, 'utf8');
    this.execute(code);
    return this;
  }

  getVariables() {
    return { ...this.interpreter.variables };
  }
}

module.exports = { ThirstyLang };
