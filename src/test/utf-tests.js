/**
 * UTF Tests — Tests for all 6 Universal Thirsty Family tiers
 */

const { UTFRegistry, ThirstyLang, ThirstOfGods, TARL, ShadowThirsty, TSCG, TSCGB } = require('../utf/index');

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✅ ${name}`);
    passed++;
  } catch (err) {
    console.log(`  ❌ ${name}: ${err.message}`);
    failed++;
  }
}

async function testAsync(name, fn) {
  try {
    await fn();
    console.log(`  ✅ ${name}`);
    passed++;
  } catch (err) {
    console.log(`  ❌ ${name}: ${err.message}`);
    failed++;
  }
}

function assert(condition, message) {
  if (!condition) throw new Error(message || 'Assertion failed');
}

function assertEqual(a, b, msg) {
  if (a !== b) throw new Error(`${msg || 'assertEqual'}: expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`);
}

console.log('\n🌊 UTF Universal Thirsty Family — Test Suite\n');

// ─── Tier 1: ThirstyLang ────────────────────────────────────────────────────
console.log('Tier 1 — Thirsty-Lang');

test('ThirstyLang instantiates', () => {
  const lang = new ThirstyLang();
  assert(lang.tier === 1);
  assert(lang.name === 'Thirsty-Lang');
});

test('ThirstyLang executes basic code', () => {
  const lang = new ThirstyLang({ security: false });
  lang.execute('drink x = 42');
  assertEqual(lang.getVariables().x, 42, 'variable x');
});

test('ThirstyLang getVariables returns variables', () => {
  const lang = new ThirstyLang({ security: false });
  lang.execute('drink name = "hydration"');
  assert(lang.getVariables().name === 'hydration');
});

test('UTFRegistry creates Tier 1', () => {
  const registry = new UTFRegistry();
  const t1 = registry.createTier1();
  assert(t1 instanceof ThirstyLang);
});

// ─── Tier 2: ThirstOfGods ───────────────────────────────────────────────────
console.log('\nTier 2 — Thirst of Gods');

test('ThirstOfGods instantiates', () => {
  const tog = new ThirstOfGods();
  assert(tog.tier === 2);
  assert(tog.name === 'Thirst of Gods');
});

test('ThirstOfGods executes base Thirsty-Lang code', () => {
  const tog = new ThirstOfGods({ security: false });
  tog.execute('drink x = 100');
  assertEqual(tog.getVariables().x, 100, 'variable x');
});

test('ThirstOfGods handles cascade syntax (async function)', () => {
  const tog = new ThirstOfGods({ security: false });
  tog.execute(`
cascade greet(name) {
  return "Hello " + name
}
drink result = greet("World")
  `);
  assert(tog.getVariables().result === 'Hello World');
});

test('ThirstOfGods handles floodmap syntax', () => {
  const tog = new ThirstOfGods({ security: false });
  tog.execute('drink m = floodmap()');
  assert(tog.getVariables().m !== undefined);
});

test('ThirstOfGods handles poolset syntax', () => {
  const tog = new ThirstOfGods({ security: false });
  tog.execute('drink s = poolset()');
  assert(tog.getVariables().s !== undefined);
});

test('ThirstOfGods getInterfaces returns interfaces map', () => {
  const tog = new ThirstOfGods({ security: false });
  assert(typeof tog.getInterfaces() === 'object');
});

// ─── Tier 3: TARL ───────────────────────────────────────────────────────────
console.log('\nTier 3 — T.A.R.L.');

test('TARL instantiates', () => {
  const tarl = new TARL();
  assert(tarl.tier === 3);
  assert(tarl.name === 'T.A.R.L.');
});

test('TARL has built-in policies', () => {
  const tarl = new TARL();
  const policies = tarl.listPolicies();
  assert(policies.includes('input-sanitization'));
  assert(policies.includes('rate-limiting'));
  assert(policies.includes('access-control'));
});

test('TARL addPolicy adds a policy', () => {
  const tarl = new TARL();
  tarl.addPolicy('custom', (ctx) => ({ verdict: 'ALLOW', reason: 'custom policy' }));
  assert(tarl.listPolicies().includes('custom'));
});

test('TARL getMetrics returns metrics object', () => {
  const tarl = new TARL();
  const m = tarl.getMetrics();
  assert(typeof m.evaluations === 'number');
  assert(typeof m.policyCount === 'number');
});

// ─── Tier 4: ShadowThirsty ──────────────────────────────────────────────────
console.log('\nTier 4 — Shadow Thirsty');

test('ShadowThirsty instantiates', () => {
  const shadow = new ShadowThirsty();
  assert(shadow.tier === 4);
  assert(shadow.name === 'Shadow Thirsty');
});

test('ShadowThirsty compile produces dual planes', () => {
  const shadow = new ShadowThirsty();
  const result = shadow.compile('drink x = 42\npour x');
  assert(result.planeA && result.planeB);
  assertEqual(result.planeA.plane, 'A');
  assertEqual(result.planeB.plane, 'B');
});

test('ShadowThirsty verify accepts valid compiled code', () => {
  const shadow = new ShadowThirsty();
  const compiled = shadow.compile('drink x = 1\npour x');
  const result = shadow.verify(compiled);
  assertEqual(result.valid, true, 'valid');
});

test('ShadowThirsty verify rejects tampered plane A', () => {
  const shadow = new ShadowThirsty();
  const compiled = shadow.compile('drink x = 1');
  compiled.planeA.checksum = 'tampered';
  const result = shadow.verify(compiled);
  assertEqual(result.valid, false, 'should be invalid');
});

test('ShadowThirsty execute runs verified code', () => {
  const shadow = new ShadowThirsty();
  const compiled = shadow.compile('drink value = 99');
  shadow.execute(compiled);
});

// ─── Tier 5: TSCG ───────────────────────────────────────────────────────────
console.log('\nTier 5 — TSCG');

test('TSCG instantiates', () => {
  const tscg = new TSCG();
  assert(tscg.tier === 5);
  assert(tscg.name === 'TSCG');
});

test('TSCG compress returns result object', () => {
  const tscg = new TSCG();
  const result = tscg.compress('drink x = 42\npour x');
  assert(result.compressed !== undefined);
  assert(typeof result.originalLength === 'number');
  assert(typeof result.compressedLength === 'number');
});

test('TSCG decompress restores original', () => {
  const tscg = new TSCG();
  const source = 'drink x = 42\npour x';
  const compressed = tscg.compress(source);
  const restored = tscg.decompress(compressed.compressed);
  assertEqual(restored, source, 'round-trip');
});

test('TSCG getSymbolTable returns symbol table', () => {
  const tscg = new TSCG();
  const table = tscg.getSymbolTable();
  assert(typeof table === 'object');
  assert(Object.keys(table).length > 0);
});

test('TSCG reset clears and re-initializes', () => {
  const tscg = new TSCG();
  tscg.reset();
  const table = tscg.getSymbolTable();
  assert(Object.keys(table).length > 0);
});

// ─── Tier 6: TSCG-B ─────────────────────────────────────────────────────────
console.log('\nTier 6 — TSCG-B');

test('TSCGB instantiates', () => {
  const tscgb = new TSCGB();
  assert(tscgb.tier === 6);
  assert(tscgb.name === 'TSCG-B');
});

test('TSCGB encode produces a Buffer with magic header', () => {
  const tscgb = new TSCGB();
  const encoded = tscgb.encode('hello world');
  assert(Buffer.isBuffer(encoded));
  assertEqual(encoded.readUInt32BE(0), 0x54534347, 'magic header');
});

test('TSCGB decode restores string', () => {
  const tscgb = new TSCGB();
  const content = 'drink x = 42\npour x';
  const encoded = tscgb.encode(content);
  const decoded = tscgb.decode(encoded);
  assertEqual(decoded, content, 'round-trip');
});

test('TSCGB decode rejects invalid magic', () => {
  const tscgb = new TSCGB();
  const bad = Buffer.alloc(20);
  bad.writeUInt32BE(0xDEADBEEF, 0);
  try {
    tscgb.decode(bad);
    assert(false, 'should have thrown');
  } catch (e) {
    assert(e.message.includes('magic header'));
  }
});

test('TSCGB full pipeline: compress then encode then decode then decompress', () => {
  const tscg = new TSCG();
  const tscgb = new TSCGB();
  const source = 'drink x = 42\npour x\ndrink y = x + 1\npour y';
  const compressed = tscg.compress(source);
  const encoded = tscgb.encode(compressed.compressed);
  const decoded = tscgb.decode(encoded);
  const restored = tscg.decompress(decoded);
  assertEqual(restored, source, 'full pipeline round-trip');
});

// ─── UTFRegistry ────────────────────────────────────────────────────────────
console.log('\nUTF Registry');

test('UTFRegistry.create() works for all tiers', () => {
  const reg = new UTFRegistry();
  assert(reg.create(1) instanceof ThirstyLang);
  assert(reg.create(2) instanceof ThirstOfGods);
  assert(reg.create(3) instanceof TARL);
  assert(reg.create(4) instanceof ShadowThirsty);
  assert(reg.create(5) instanceof TSCG);
  assert(reg.create(6) instanceof TSCGB);
});

test('UTFRegistry.create() works with tier names', () => {
  const reg = new UTFRegistry();
  assert(reg.create('thirsty-lang') instanceof ThirstyLang);
  assert(reg.create('thirst-of-gods') instanceof ThirstOfGods);
  assert(reg.create('tarl') instanceof TARL);
  assert(reg.create('shadow-thirsty') instanceof ShadowThirsty);
  assert(reg.create('tscg') instanceof TSCG);
  assert(reg.create('tscg-b') instanceof TSCGB);
});

test('UTFRegistry.getTierInfo returns 6 tiers', () => {
  const reg = new UTFRegistry();
  assertEqual(reg.getTierInfo().length, 6, 'tier count');
});

// ─── Async tests then summary ────────────────────────────────────────────────
Promise.resolve()
  .then(() => testAsync('TARL evaluate ALLOW (async)', async () => {
    const tarl = new TARL();
    tarl.policies.clear();
    tarl.addPolicy('allow-all', () => ({ verdict: 'ALLOW', reason: 'ok' }));
    const r = await tarl.evaluate({ input: 'safe' });
    assertEqual(r.verdict, 'ALLOW', 'verdict');
  }))
  .then(() => testAsync('TARL evaluate ALLOW for valid context', async () => {
    const tarl = new TARL();
    tarl.policies.clear();
    tarl.addPolicy('access-control', (ctx) => {
      if (ctx.role === 'admin') return { verdict: 'ALLOW', reason: 'admin' };
      return { verdict: 'DENY', reason: 'no access' };
    });
    const result = await tarl.evaluate({ role: 'admin', resource: 'file', action: 'read' });
    assertEqual(result.verdict, 'ALLOW', 'verdict');
  }))
  .then(() => testAsync('TARL evaluate DENY for dangerous input', async () => {
    const tarl = new TARL();
    tarl.policies.clear();
    tarl.policies.set('input-sanitization', {
      name: 'input-sanitization',
      evaluate: (ctx) => {
        if (typeof ctx.input === 'string' && /<script/i.test(ctx.input)) {
          return { verdict: 'DENY', reason: 'XSS detected' };
        }
        return { verdict: 'ALLOW', reason: 'OK' };
      }
    });
    const result = await tarl.evaluate({ input: '<script>alert(1)</script>' });
    assertEqual(result.verdict, 'DENY', 'verdict');
  }))
  .then(() => {
    console.log(`\n${'─'.repeat(50)}`);
    console.log(`Results: ${passed} passed, ${failed} failed`);
    if (failed > 0) process.exit(1);
  });
