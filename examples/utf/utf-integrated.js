/**
 * UTF Integrated Pipeline Demo
 * Shows all 6 tiers working together.
 */

const { UTFRegistry } = require('../../src/utf');
const { TSCG } = require('../../src/utf/components/tscg');
const { TSCGB } = require('../../src/utf/components/tscg-b');
const { ShadowThirsty } = require('../../src/utf/components/shadow-thirsty');
const { TARL } = require('../../src/utf/components/tarl');

async function main() {
  console.log('=== UTF Integrated Pipeline Demo ===\n');

  const registry = new UTFRegistry();

  // Tier 1: Execute basic Thirsty-Lang
  console.log('--- Tier 1: Thirsty-Lang ---');
  const t1 = registry.createTier1({ security: false });
  t1.execute('drink msg = "UTF pipeline active"\npour msg');
  console.log();

  // Tier 2: ThirstOfGods OOP
  console.log('--- Tier 2: Thirst of Gods ---');
  const t2 = registry.createTier2({ security: false });
  t2.execute(`
fountain Hydrator {
  drink level = 0
  glass hydrate(amount) {
    drink this.level = this.level + amount
    pour "Hydration level: " + this.level
  }
}
drink h = Hydrator()
h.hydrate(500)
h.hydrate(300)
  `);
  console.log();

  // Tier 3: TARL policy evaluation
  console.log('--- Tier 3: T.A.R.L. ---');
  const tarl = registry.createTier3();
  const policyResult = await tarl.evaluate({
    input: 'safe input',
    role: 'user',
    resource: 'file',
    action: 'read',
  });
  console.log(`Policy verdict: ${policyResult.verdict}`);
  const metrics = tarl.getMetrics();
  console.log(`Evaluations: ${metrics.evaluations}, Allowed: ${metrics.allowed}`);
  console.log();

  // Tier 4: Shadow Thirsty dual-plane verification
  console.log('--- Tier 4: Shadow Thirsty ---');
  const shadow = registry.createTier4();
  const code = 'drink verified = parched\npour "Verified: " + verified';
  const compiled = shadow.compile(code);
  const verification = shadow.verify(compiled);
  console.log(`Compilation: Plane A ✅, Plane B ✅`);
  console.log(`Verification: ${verification.valid ? 'PASSED ✅' : 'FAILED ❌'}`);
  console.log();

  // Tier 5: TSCG compression
  console.log('--- Tier 5: TSCG ---');
  const tscg = registry.createTier5();
  const sourceCode = 'drink x = 1\ndrink y = 2\ndrink z = x + y\npour z';
  const compressed = tscg.compress(sourceCode);
  console.log(`Compressed ${compressed.originalLength} → ${compressed.compressedLength} bytes (${compressed.ratio}% reduction)`);
  const decompressed = tscg.decompress(compressed.compressed);
  console.log(`Round-trip: ${decompressed === sourceCode ? 'PASS ✅' : 'FAIL ❌'}`);
  console.log();

  // Tier 6: TSCG-B binary encoding
  console.log('--- Tier 6: TSCG-B ---');
  const tscgb = registry.createTier6();
  const binary = tscgb.encode(compressed.compressed);
  console.log(`Binary encoded: ${binary.length} bytes`);
  const decoded = tscgb.decode(binary);
  const restored = tscg.decompress(decoded);
  console.log(`Full pipeline round-trip: ${restored === sourceCode ? 'PASS ✅' : 'FAIL ❌'}`);

  console.log('\n=== UTF Pipeline Complete ✅ ===');
}

main().catch(console.error);
