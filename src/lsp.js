/**
 * Thirsty-Lang Language Server Protocol (LSP) Engine
 * Providing Sovereign-grade IntelliSense, Diagnostics, and Navigation.
 */

const { Tokenizer } = require('./engine/tokenizer');
const { Parser } = require('./engine/parser');

class ThirstyLSP {
  constructor() {
    this.documents = new Map();
  }

  /**
   * Open or update a document
   */
  updateDocument(uri, text) {
    this.documents.set(uri, text);
    return this.validateDocument(uri);
  }

  /**
   * Run diagnostics on a document
   */
  validateDocument(uri) {
    const text = this.documents.get(uri);
    const diagnostics = [];

    try {
      const tokenizer = new Tokenizer(text);
      const tokens = tokenizer.tokenize();
      const parser = new Parser(tokens);
      parser.parse();
    } catch (err) {
      // Extract position if available
      const match = err.message.match(/line (\d+)/);
      const line = match ? parseInt(match[1]) - 1 : 0;
      
      diagnostics.push({
        severity: 'error',
        range: {
          start: { line: line, character: 0 },
          end: { line: line, character: 100 }
        },
        message: err.message,
        source: 'Thirsty-Lang'
      });
    }

    return diagnostics;
  }

  /**
   * Find symbol references or definitions by walking the AST
   */
  findSymbolUnderCursor(uri, line, character) {
    const text = this.documents.get(uri);
    if (!text) return null;

    try {
      const tokenizer = new Tokenizer(text);
      const tokens = tokenizer.tokenize();
      const parser = new Parser(tokens);
      const ast = parser.parse();

      const symbols = [];
      this.walkAST(ast, (node) => {
        if (node.line === line + 1) { // LSP is 0-indexed, AST is 1-indexed
          if (node.type === 'Identifier' || (node.name && typeof node.name === 'string')) {
              // Narrow check for exact character range if needed
              symbols.push(node);
          }
        }
      });

      // Find the specific node under the cursor
      const target = symbols.find(s => character >= (s.column - 1) && character <= (s.column - 1 + (s.name || s.value || "").length));
      if (!target) return null;

      const results = [];
      const symbolName = target.name || target.value;

      this.walkAST(ast, (node) => {
        if (node.type === 'Identifier' && node.name === symbolName) {
          results.push({
            uri,
            range: {
              start: { line: node.line - 1, character: node.column - 1 },
              end: { line: node.line - 1, character: node.column - 1 + symbolName.length }
            }
          });
        }
        // Also check declarations
        if ((node.type === 'VariableDeclaration' || node.type === 'FunctionDeclaration' || node.type === 'ClassDeclaration') && node.name === symbolName) {
            results.push({
                uri,
                range: {
                  start: { line: node.line - 1, character: node.column - 1 },
                  end: { line: node.line - 1, character: node.column - 1 + symbolName.length }
                }
              });
        }
      });

      return results;
    } catch (err) {
      console.error("LSP symbol search failed:", err);
      return null;
    }
  }

  /**
   * Recursive AST Walker
   */
  walkAST(node, callback) {
    if (!node) return;
    callback(node);

    if (Array.isArray(node)) {
      node.forEach(child => this.walkAST(child, callback));
      return;
    }

    // Traverse children based on node type
    switch (node.type) {
      case 'Program':
      case 'BlockStatement':
        this.walkAST(node.body, callback);
        break;
      case 'VariableDeclaration':
        this.walkAST(node.target, callback);
        this.walkAST(node.value, callback);
        break;
      case 'FunctionDeclaration':
      case 'CascadeDeclaration':
        this.walkAST(node.body, callback);
        break;
      case 'ClassDeclaration':
        this.walkAST(node.methods, callback);
        this.walkAST(node.properties, callback);
        break;
      case 'IfStatement':
        this.walkAST(node.condition, callback);
        this.walkAST(node.consequent, callback);
        this.walkAST(node.alternate, callback);
        break;
      case 'WhileStatement':
        this.walkAST(node.condition, callback);
        this.walkAST(node.body, callback);
        break;
      case 'BinaryExpression':
        this.walkAST(node.left, callback);
        this.walkAST(node.right, callback);
        break;
      case 'UnaryExpression':
        this.walkAST(node.operand, callback);
        break;
      case 'CallExpression':
        this.walkAST(node.callee, callback);
        this.walkAST(node.arguments, callback);
        break;
      case 'MemberExpression':
        this.walkAST(node.object, callback);
        break;
      case 'ReturnStatement':
      case 'ThrowStatement':
      case 'ExpressionStatement':
      case 'PourStatement':
        this.walkAST(node.expression || node.value, callback);
        break;
      default:
        break;
    }
  }
}

function startLSP() {
  const lsp = new ThirstyLSP();
  console.log("Sovereign LSP Engine Active.");
  
  process.on('message', (msg) => {
    if (msg.method === 'textDocument/didChange') {
      const diagnostics = lsp.updateDocument(msg.params.textDocument.uri, msg.params.contentChanges[0].text);
      process.send({ method: 'textDocument/publishDiagnostics', params: { uri: msg.params.textDocument.uri, diagnostics } });
    }
    
    if (msg.method === 'textDocument/references') {
      const refs = lsp.findSymbolUnderCursor(msg.params.textDocument.uri, msg.params.position.line, msg.params.position.character);
      process.send({ id: msg.id, result: refs });
    }

    if (msg.method === 'textDocument/definition') {
      const refs = lsp.findSymbolUnderCursor(msg.params.textDocument.uri, msg.params.position.line, msg.params.position.character);
      // For Go-to-Definition, we usually just want the first result (the declaration)
      // but returning all matches is also valid in some clients.
      // A more complex implementation would distinguish between decl and ref.
      process.send({ id: msg.id, result: refs ? refs[0] : null });
    }
  });
}

if (require.main === module) {
  startLSP();
}

module.exports = { ThirstyLSP };
