/**
 * Tier 6: TSCG-B — Binary Encoding Demo
 */

const { TSCG } = require('../../src/utf/components/tscg');
const { TSCGB } = require('../../src/utf/components/tscg-b');
const path = require('path');
const fs = require('fs');

const tscg = new TSCG();
const tscgb = new TSCGB();

const source = `
drink message = "Binary encoded by TSCG-B"
pour message
drink count = 0
refill count < 3 {
  pour "Iteration: " + count
  drink count = count + 1
}
`.trim();

console.log('=== TSCG-B Binary Encoding Demo ===\n');
console.log(`Source (${source.length} bytes):\n${source}\n`);

// Step 1: TSCG compress
const compressed = tscg.compress(source);
console.log(`TSCG compressed to ${compressed.compressedLength} bytes (${compressed.ratio}% reduction)`);

// Step 2: TSCG-B encode to binary
const binary = tscgb.encode(compressed.compressed);
console.log(`TSCG-B encoded to ${binary.length} bytes`);
console.log(`Magic header: 0x${binary.readUInt32BE(0).toString(16).toUpperCase()}`);
console.log(`Version: ${binary.readUInt16BE(4)}`);

// Step 3: TSCG-B decode
const decoded = tscgb.decode(binary);
console.log(`\nDecoded back: ${decoded.length} bytes`);

// Step 4: TSCG decompress
const restored = tscg.decompress(decoded);
console.log(`Decompressed: ${restored.length} bytes`);
console.log(`Round-trip match: ${restored === source ? '✅ PASS' : '❌ FAIL'}`);

// File round-trip demo
const outFile = path.join(__dirname, '_demo_output.tscgb');
try {
  tscgb.encodeToFile(compressed.compressed, outFile);
  console.log(`\nWritten to file: ${outFile}`);
  const fromFile = tscgb.decodeFromFile(outFile);
  const restoredFromFile = tscg.decompress(fromFile);
  console.log(`File round-trip match: ${restoredFromFile === source ? '✅ PASS' : '❌ FAIL'}`);
} finally {
  if (fs.existsSync(outFile)) fs.unlinkSync(outFile);
  console.log('Cleanup complete.');
}
