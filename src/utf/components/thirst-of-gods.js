/**
 * Tier 2 - Thirst of Gods
 * OOP/async language processor extending Thirsty-Lang.
 * Adds: fountain inheritance, cascade async, await, import/export, floodmap, poolset, spring interfaces.
 */

const path = require('path');
const fs = require('fs');
const { ThirstyInterpreter } = require(path.join(__dirname, '..', '..', 'index'));

class ThirstOfGods extends ThirstyInterpreter {
  constructor(options = {}) {
    super(options);
    this.tier = 2;
    this.name = 'Thirst of Gods';
    this.interfaces = {};
    this.exports = {};
    this.importedModules = {};
    this._pendingExports = [];
    this._pendingExtends = null;
  }

  execute(code) {
    const preprocessed = this._preprocess(code);
    super.execute(preprocessed);
    // Resolve pending exports after execution
    for (const varName of this._pendingExports) {
      if (this.variables[varName] !== undefined) {
        this.exports[varName] = this.variables[varName];
      }
    }
    this._pendingExports = [];
    // Apply inheritance if needed
    if (this._pendingExtends) {
      const { child, parent } = this._pendingExtends;
      this._pendingExtends = null;
      if (this.classes && this.classes[parent] && this.classes[child]) {
        const parentMethods = this.classes[parent].methods || {};
        const childMethods = this.classes[child].methods || {};
        this.classes[child].methods = { ...parentMethods, ...childMethods };
        this.classes[child].parent = parent;
      }
    }
  }

  executeFile(filePath) {
    const code = fs.readFileSync(filePath, 'utf8');
    this.execute(code);
    return this;
  }

  _preprocess(code) {
    const lines = code.split('\n');
    const processed = [];
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      const trimmed = line.trim();

      // spring interface Name { ... }
      if (/^spring\s+interface\s+\w+/.test(trimmed)) {
        const match = trimmed.match(/^spring\s+interface\s+(\w+)/);
        if (match) {
          const ifaceName = match[1];
          this.interfaces[ifaceName] = { methods: [] };
          i++;
          while (i < lines.length && !lines[i].includes('}')) {
            const mMatch = lines[i].trim().match(/^glass\s+(\w+)/);
            if (mMatch) this.interfaces[ifaceName].methods.push(mMatch[1]);
            i++;
          }
          i++;
          continue;
        }
      }

      // fountain ClassName extends BaseClass
      if (/^fountain\s+\w+\s+extends\s+\w+/.test(trimmed)) {
        const match = trimmed.match(/^fountain\s+(\w+)\s+extends\s+(\w+)/);
        if (match) {
          const [, child, parent] = match;
          this._pendingExtends = { child, parent };
          processed.push(line.replace(/\s+extends\s+\w+/, ''));
          i++;
          continue;
        }
      }

      // cascade funcName(params) -> glass funcName(params)
      if (/^(\s*)cascade\s+\w+/.test(line)) {
        processed.push(line.replace(/^(\s*)cascade\s+/, '$1glass '));
        i++;
        continue;
      }

      // import Name from "path"
      if (/^import\s+\w+\s+from\s+["']/.test(trimmed)) {
        const match = trimmed.match(/^import\s+(\w+)\s+from\s+["']([^"']+)["']/);
        if (match) {
          const [, name, modPath] = match;
          try {
            this.importedModules[name] = require(modPath);
            this.variables[name] = this.importedModules[name];
          } catch (e) {
            // Module unavailable in this environment; import is skipped silently
            // to allow .thirstofgods files to run without all Node.js modules present
          }
        }
        i++;
        continue;
      }

      // export varName
      if (/^export\s+\w+/.test(trimmed)) {
        const match = trimmed.match(/^export\s+(\w+)/);
        if (match) this._pendingExports.push(match[1]);
        i++;
        continue;
      }

      // await expr -> expr (run synchronously)
      if (/\bawait\s+/.test(line)) {
        processed.push(line.replace(/\bawait\s+/g, ''));
        i++;
        continue;
      }

      processed.push(line);
      i++;
    }
    return processed.join('\n');
  }

  evaluateExpression(expr) {
    const trimmed = (expr || '').trim();
    if (trimmed === 'floodmap()') return {};
    if (trimmed === 'poolset()') return [];
    return super.evaluateExpression(expr);
  }

  getVariables() {
    return { ...this.variables };
  }

  getExports() {
    return { ...this.exports };
  }

  getInterfaces() {
    return { ...this.interfaces };
  }
}

module.exports = { ThirstOfGods };
