const { Tokenizer } = require('c:/Users/Quencher/.gemini/antigravity/scratch/sovereign-repos/Thirsty-Lang/src/engine/tokenizer');
const fs = require('fs');
const source = fs.readFileSync('c:/Users/Quencher/.gemini/antigravity/scratch/sovereign-repos/Thirsty-Lang/src/lib/server.thirsty', 'utf8');
const tokenizer = new Tokenizer(source);
const tokens = tokenizer.tokenize();
tokens.forEach(t => console.log(`${t.line}:${t.column} [${t.type}] ${t.value}`));
