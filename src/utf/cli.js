#!/usr/bin/env node
/**
 * UTF CLI — Universal Thirsty Family command-line interface
 * Supports all 6 UTF tiers.
 */

const path = require('path');
const fs = require('fs');

const { UTFRegistry, TSCG, TSCGB, ShadowThirsty } = require('./index');

const args = process.argv.slice(2);

function printHelp() {
  console.log(`
UTF CLI — Universal Thirsty Family

Usage:
  node src/utf/cli.js [options] [file]

Options:
  --tier <name>     Select UTF tier: thirsty-lang, thirst-of-gods, tarl, shadow-thirsty, tscg, tscg-b
  --compress        Run TSCG compression on the given file
  --verify          Run Shadow Thirsty verification on the given file
  --help            Show this help

Tiers:
  thirsty-lang      Tier 1 — Core language (.thirsty files)
  thirst-of-gods    Tier 2 — OOP/async (.thirstofgods files)
  tarl              Tier 3 — Defensive policy VM
  shadow-thirsty    Tier 4 — Dual-plane compiler
  tscg              Tier 5 — Symbolic compression
  tscg-b            Tier 6 — Binary encoding

Examples:
  node src/utf/cli.js examples/hello.thirsty
  node src/utf/cli.js --tier thirst-of-gods examples/advanced/classes.thirstofgods
  node src/utf/cli.js --compress examples/hello.thirsty
  node src/utf/cli.js --verify examples/hello.thirsty
`);
}

async function main() {
  if (args.includes('--help') || args.length === 0) {
    printHelp();
    process.exit(0);
  }

  const compress = args.includes('--compress');
  const verify = args.includes('--verify');
  const tierIndex = args.indexOf('--tier');
  const tierName = tierIndex !== -1 ? args[tierIndex + 1] : null;

  const file = args.find(a => !a.startsWith('--') && a !== tierName);

  const registry = new UTFRegistry();

  if (compress) {
    const source = file ? fs.readFileSync(file, 'utf8') : '';
    const tscg = new TSCG();
    const result = tscg.compress(source);
    console.log(`TSCG Compression Results:`);
    console.log(`  Original:    ${result.originalLength} bytes`);
    console.log(`  Compressed:  ${result.compressedLength} bytes`);
    console.log(`  Ratio:       ${result.ratio}%`);
    console.log(`  Symbols:     ${result.symbolCount}`);
    console.log(`\nCompressed output:\n${result.compressed}`);
    return;
  }

  if (verify) {
    const source = file ? fs.readFileSync(file, 'utf8') : '';
    const shadow = new ShadowThirsty();
    const compiled = shadow.compile(source);
    const result = shadow.verify(compiled);
    console.log(`Shadow Thirsty Verification:`);
    console.log(`  Valid:    ${result.valid}`);
    console.log(`  Checksum: ${result.checksum || 'N/A'}`);
    if (!result.valid) console.log(`  Reason: ${result.reason}`);
    return;
  }

  if (!file) {
    console.error('Error: No file specified. Use --help for usage.');
    process.exit(1);
  }

  if (!fs.existsSync(file)) {
    console.error(`Error: File not found: ${file}`);
    process.exit(1);
  }

  let tier = tierName;
  if (!tier) {
    if (file.endsWith('.thirstofgods')) tier = 'thirst-of-gods';
    else tier = 'thirsty-lang';
  }

  if (tier === 'tarl') {
    const { TARL } = require('./components/tarl');
    const tarl = new TARL();
    const source = fs.readFileSync(file, 'utf8');
    const result = await tarl.evaluate({ input: source, role: 'user', resource: 'file', action: 'execute' });
    console.log(`T.A.R.L. Policy Evaluation: ${result.verdict}`);
    if (result.reason) console.log(`Reason: ${result.reason}`);
    return;
  }

  if (tier === 'shadow-thirsty') {
    const source = fs.readFileSync(file, 'utf8');
    const shadow = new ShadowThirsty();
    const compiled = shadow.compile(source);
    const vResult = shadow.verify(compiled);
    if (!vResult.valid) {
      console.error(`Verification failed: ${vResult.reason}`);
      process.exit(1);
    }
    shadow.execute(compiled);
    return;
  }

  if (tier === 'tscg') {
    const source = fs.readFileSync(file, 'utf8');
    const tscg = new TSCG();
    const result = tscg.compress(source);
    console.log(`Compressed (${result.ratio}% reduction):\n${result.compressed}`);
    return;
  }

  if (tier === 'tscg-b') {
    const source = fs.readFileSync(file, 'utf8');
    const tscg = new TSCG();
    const tscgb = new TSCGB();
    const compressed = tscg.compress(source);
    const binary = tscgb.encode(compressed.compressed);
    console.log(`TSCG-B encoded: ${binary.length} bytes`);
    const decoded = tscgb.decode(binary);
    const restored = tscg.decompress(decoded);
    console.log(`Round-trip verified: ${restored.trim() === source.trim() ? 'OK' : 'MISMATCH'}`);
    return;
  }

  const component = registry.create(tier);
  component.executeFile(file);
}

main().catch(err => {
  console.error('UTF CLI error:', err.message);
  process.exit(1);
});
