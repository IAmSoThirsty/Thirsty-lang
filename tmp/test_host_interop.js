const { Tokenizer } = require('c:/Users/Quencher/.gemini/antigravity/scratch/sovereign-repos/Thirsty-Lang/src/engine/tokenizer');
const { Parser } = require('c:/Users/Quencher/.gemini/antigravity/scratch/sovereign-repos/Thirsty-Lang/src/engine/parser');
const { ASTInterpreter } = require('c:/Users/Quencher/.gemini/antigravity/scratch/sovereign-repos/Thirsty-Lang/src/engine/ast-interpreter');
const { initializeStandardLibrary } = require('c:/Users/Quencher/.gemini/antigravity/scratch/sovereign-repos/Thirsty-Lang/src/interpreter/stdlib');

const source = `
drink host = Http.createServer()
host.onHandle = glass(req) { return "HELLO" }
Console.log("Result: " + host.onHandle({}))
`;

const tokenizer = new Tokenizer(source);
const tokens = tokenizer.tokenize();
const parser = new Parser(tokens);
const ast = parser.parse();

const host = { 
    variables: {}, 
    MAX_LOOP_ITERATIONS: 10000,
    securityManager: { verifyAccess: () => true },
    logger: { info: console.log, security: console.error, warn: console.warn, error: console.error }
};
// Mock allVariables for syncToHost
host.variables.allVariables = () => ({});

const interpreter = new ASTInterpreter(host);
interpreter.run(ast);
