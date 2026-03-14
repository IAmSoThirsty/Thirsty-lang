const { Tokenizer } = require('c:/Users/Quencher/.gemini/antigravity/scratch/sovereign-repos/Thirsty-Lang/src/engine/tokenizer');
const { Parser } = require('c:/Users/Quencher/.gemini/antigravity/scratch/sovereign-repos/Thirsty-Lang/src/engine/parser');
const fs = require('fs');
const source = fs.readFileSync('c:/Users/Quencher/.gemini/antigravity/scratch/sovereign-repos/Thirsty-Lang/examples/server_demo.thirsty', 'utf8');
const tokenizer = new Tokenizer(source);
const tokens = tokenizer.tokenize();
const parser = new Parser(tokens);
try {
    const ast = parser.parse();
    console.log(JSON.stringify(ast, null, 2));
} catch (e) {
    console.error(e.message);
}
