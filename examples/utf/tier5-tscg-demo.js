/**
 * Tier 5: TSCG — Symbolic Compression Grammar Demo
 */

const { TSCG } = require('../../src/utf/components/tscg');

const tscg = new TSCG();

const source = `
drink greeting = "Hello from TSCG!"
pour greeting
drink x = 10
drink y = 20
drink sum = x + y
pour "Sum: " + sum
glass square(n) {
  return n * n
}
drink result = square(7)
pour "7 squared = " + result
`.trim();

console.log('=== TSCG Compression Demo ===\n');
console.log('Original source:');
console.log(source);
console.log(`\nLength: ${source.length} bytes`);

const compressed = tscg.compress(source);
console.log('\n--- Compressed ---');
console.log(compressed.compressed);
console.log(`\nCompressed length: ${compressed.compressedLength} bytes`);
console.log(`Compression ratio: ${compressed.ratio}%`);
console.log(`Symbols used: ${compressed.symbolCount}`);

const restored = tscg.decompress(compressed.compressed);
console.log('\n--- Decompressed ---');
console.log(restored);
console.log(`\nRound-trip match: ${restored === source ? '✅ PASS' : '❌ FAIL'}`);

console.log('\n--- Symbol Table ---');
const table = tscg.getSymbolTable();
for (const [sym, pattern] of Object.entries(table)) {
  console.log(`  ${sym} => "${pattern}"`);
}
