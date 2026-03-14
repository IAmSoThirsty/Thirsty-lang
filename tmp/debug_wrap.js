const { Tokenizer } = require('c:/Users/Quencher/.gemini/antigravity/scratch/sovereign-repos/Thirsty-Lang/src/engine/tokenizer');
const { Parser } = require('c:/Users/Quencher/.gemini/antigravity/scratch/sovereign-repos/Thirsty-Lang/src/engine/parser');
const { ASTInterpreter } = require('c:/Users/Quencher/.gemini/antigravity/scratch/sovereign-repos/Thirsty-Lang/src/engine/ast-interpreter');
const fs = require('fs');

const source = `
import { SovereignServer } from "c:/Users/Quencher/.gemini/antigravity/scratch/sovereign-repos/Thirsty-Lang/src/lib/server.thirsty"
drink app = new SovereignServer({ port: 9999 })
app.route("/test", glass(req) { return { status: 200, body: "OK" } })
Console.log("onHandle type: " + (typeof app.server.onHandle))
`;

const tokenizer = new Tokenizer(source);
const tokens = tokenizer.tokenize();
const parser = new Parser(tokens);
const ast = parser.parse();
const interpreter = new ASTInterpreter();
interpreter.interpret(ast);
