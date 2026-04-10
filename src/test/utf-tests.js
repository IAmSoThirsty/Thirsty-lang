/**
 * UTF Tests — Tests for all 6 Universal Thirsty Family tiers
 */

const { UTFRegistry, ThirstyLang, ThirstOfGods, TARL, ShadowThirsty, TSCG, TSCGB } = require('../utf/index');
const { TARLLexer, TARLParser, TARLVirtualMachine, ResourceLimitError } = require('../utf/components/tarl');

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

// Updated: magic is now 0x54534742 ('TSGB') per spec
test('TSCGB encode produces a Buffer with magic header', () => {
  const tscgb = new TSCGB();
  const encoded = tscgb.encode('hello world');
  assert(Buffer.isBuffer(encoded));
  assertEqual(encoded.readUInt32BE(0), 0x54534742, 'magic header');
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

// ─── New: TSCG-B spec-accurate tests ────────────────────────────────────────
console.log('\nTSCG-B — spec-accurate wire format');

test("TSCGB magic bytes are 0x54534742 ('TSGB')", () => {
  const tscgb = new TSCGB();
  assertEqual(tscgb.getMagic(), 0x54534742, 'getMagic');
});

test('TSCGB wire format has CRC32 verification', () => {
  const tscgb   = new TSCGB();
  const encoded = tscgb.encode('hello');
  // Tamper with the first payload byte (at offset 16).
  encoded[16] ^= 0xFF;
  let threw = false;
  try {
    tscgb.decode(encoded);
  } catch (e) {
    threw = true;
    assert(e.message.includes('CRC32') || e.message.includes('SHA-256'), `unexpected error: ${e.message}`);
  }
  assert(threw, 'decode should throw on tampered payload');
});

test('TSCGB wire format has SHA-256 verification', () => {
  const tscgb   = new TSCGB();
  const encoded = tscgb.encode('hello');
  // Tamper with the last byte of the SHA-256 hash.
  encoded[encoded.length - 1] ^= 0xFF;
  let threw = false;
  try {
    tscgb.decode(encoded);
  } catch (e) {
    threw = true;
    assert(e.message.includes('SHA-256'), `unexpected error: ${e.message}`);
  }
  assert(threw, 'decode should throw on tampered SHA-256');
});

test('TSCGB opcode encode/decode round-trip', () => {
  const tscgb  = new TSCGB();
  const text   = 'COG → SHD → COM';
  const opcodes = tscgb.encodeOpcodes(text);
  assert(Buffer.isBuffer(opcodes), 'encodeOpcodes should return a Buffer');
  const decoded = tscgb.decodeOpcodes(opcodes);
  assertEqual(decoded, text, 'opcode round-trip');
});

test('TSCGB wire overhead is 48 bytes for empty payload', () => {
  const tscgb   = new TSCGB();
  const encoded = tscgb.encode('');
  assertEqual(encoded.length, 48, 'empty payload overhead should be 48 bytes');
});

// ─── New: TSCG governance dictionary tests ──────────────────────────────────
console.log('\nTSCG — governance dictionary');

test('TSCG governance dictionary compresses COG pipeline', () => {
  const tscg     = new TSCG();
  const pipeline = 'COG → Δ_NT → SHD(v) → INV(I) ∧ CAP → QRM(3f+1,2f+1) → COM → ANC';
  const result   = tscg.compress(pipeline);
  // The canonical pipeline is registered as a single §GCPIPE symbol.
  assert(result.ratio > 60, `Expected > 60% compression, got ${result.ratio}%`);
  assert(result.compressed.includes('§GCPIPE'), 'compressed should contain §GCPIPE');
});

test('TSCG verify() proves bijective guarantee', () => {
  const tscg   = new TSCG();
  const source = 'COG → Δ_NT → SHD(v) → INV(I) ∧ CAP → QRM(3f+1,2f+1) → COM → ANC\nCOG → COM';
  const result = tscg.verify(source);
  assertEqual(result.valid, true, 'verify should return valid: true');
  assertEqual(result.original, source, 'original should match input');
  assertEqual(result.roundTripped, source, 'roundTripped should equal original');
});

// ─── New: ShadowThirsty analyzer tests ──────────────────────────────────────
console.log('\nShadow Thirsty — static analyzers');

test('ShadowThirsty has 6 static analyzers', () => {
  const shadow    = new ShadowThirsty({ secret: 'test-secret' });
  const analyzers = shadow.getAnalyzers();
  assert(Array.isArray(analyzers), 'getAnalyzers should return an array');
  assertEqual(analyzers.length, 6, 'should have 6 analyzers');
});

test('ShadowThirsty PlaneIsolationAnalyzer runs on compile', () => {
  const shadow   = new ShadowThirsty({ secret: 'test-secret' });
  const compiled = shadow.compile('drink x = 42');
  assert(compiled.analysis !== undefined, 'should have analysis');
  assert(
    compiled.analysis.analyzers['PlaneIsolationAnalyzer'] !== undefined,
    'PlaneIsolationAnalyzer result should be present'
  );
  assertEqual(
    compiled.analysis.analyzers['PlaneIsolationAnalyzer'].passed,
    true,
    'PlaneIsolationAnalyzer should pass for plain code'
  );
});

test('ShadowThirsty quarantine() returns quarantine record', () => {
  const shadow = new ShadowThirsty({ secret: 'test-secret' });
  const record = shadow.quarantine('bad code', 'test reason');
  assertEqual(record.quarantined, true, 'quarantined should be true');
  assertEqual(record.reason, 'test reason', 'reason should match');
  assertEqual(record.code, 'bad code', 'code should match');
  assert(typeof record.timestamp === 'number', 'timestamp should be a number');
});

// ─── New: TARL subsystem tests ───────────────────────────────────────────────
console.log('\nT.A.R.L. — subsystems');

test('TARL has 8 subsystems', () => {
  const tarl       = new TARL();
  const subsystems = tarl.getSubsystems();
  assert(typeof subsystems === 'object', 'getSubsystems should return an object');
  assertEqual(Object.keys(subsystems).length, 8, 'should have 8 subsystems');
  assert('TARLLexer'          in subsystems, 'TARLLexer missing');
  assert('TARLParser'         in subsystems, 'TARLParser missing');
  assert('TARLAST'            in subsystems, 'TARLAST missing');
  assert('TARLCompiler'       in subsystems, 'TARLCompiler missing');
  assert('TARLVirtualMachine' in subsystems, 'TARLVirtualMachine missing');
  assert('TARLJit'            in subsystems, 'TARLJit missing');
  assert('TARLStdLib'         in subsystems, 'TARLStdLib missing');
  assert('TARLDevTooling'     in subsystems, 'TARLDevTooling missing');
});

test('TARL TARLLexer tokenizes rule syntax', () => {
  const tokens = new TARLLexer('rule test { }').tokenize();
  const types  = tokens.map(t => t.type);
  assert(types.includes('RULE'),       'should have RULE token');
  assert(types.includes('IDENTIFIER'), 'should have IDENTIFIER token');
  assert(types.includes('LBRACE'),     'should have LBRACE token');
  assert(types.includes('RBRACE'),     'should have RBRACE token');
  assert(types.includes('EOF'),        'should have EOF token');
  const ruleToken = tokens.find(t => t.type === 'RULE');
  assertEqual(ruleToken.value, 'rule', 'RULE token value should be "rule"');
  const identToken = tokens.find(t => t.type === 'IDENTIFIER');
  assertEqual(identToken.value, 'test', 'IDENTIFIER token value should be "test"');
});

test('TARL TARLParser parses rule syntax', () => {
  const source = 'rule check { if (user.role == "admin") { allow("ok"); } }';
  const tokens = new TARLLexer(source).tokenize();
  const ast    = new TARLParser(tokens).parse();
  assertEqual(ast.type, 'Program', 'root should be Program');
  assert(Array.isArray(ast.rules), 'should have rules array');
  assertEqual(ast.rules.length, 1, 'should have 1 rule');
  assertEqual(ast.rules[0].type, 'Rule', 'rule node type');
  assertEqual(ast.rules[0].name, 'check', 'rule name');
});

test('TARL TARLVirtualMachine enforces stack depth limit', () => {
  const vm = new TARLVirtualMachine({ maxStackDepth: 3 });
  // Build bytecode that pushes more items than the limit allows.
  const bytecode = Array.from({ length: 10 }, (_, i) => ({ op: 'LOAD_CONST', value: i }));
  let threw = false;
  try {
    vm.execute(bytecode, {});
  } catch (e) {
    threw = true;
    assert(e instanceof ResourceLimitError, `expected ResourceLimitError, got ${e.constructor.name}`);
    assert(e.message.includes('Stack depth'), `unexpected message: ${e.message}`);
  }
  assert(threw, 'VM should throw ResourceLimitError when stack depth is exceeded');
});

test('TARL parseRule adds policy from TARL source syntax', () => {
  const tarl   = new TARL();
  const source = 'rule my-rule { if (user.role == "admin") { allow("Admin access granted"); } }';
  tarl.addRuleFromSource('my-rule', source);
  assert(tarl.listPolicies().includes('my-rule'), 'my-rule should be registered as a policy');
});

// ─── Async tests then summary ────────────────────────────────────────────────
async function runAsyncTests() {
  const asyncTests = [
    async () => testAsync('TARL evaluate ALLOW (async)', async () => {
      const tarl = new TARL();
      tarl.policies.clear();
      tarl.addPolicy('allow-all', () => ({ verdict: 'ALLOW', reason: 'ok' }));
      const r = await tarl.evaluate({ input: 'safe' });
      assertEqual(r.verdict, 'ALLOW', 'verdict');
    }),
    async () => testAsync('TARL evaluate ALLOW for valid context', async () => {
      const tarl = new TARL();
      tarl.policies.clear();
      tarl.addPolicy('access-control', (ctx) => {
        if (ctx.role === 'admin') return { verdict: 'ALLOW', reason: 'admin' };
        return { verdict: 'DENY', reason: 'no access' };
      });
      const result = await tarl.evaluate({ role: 'admin', resource: 'file', action: 'read' });
      assertEqual(result.verdict, 'ALLOW', 'verdict');
    }),
    async () => testAsync('TARL evaluate DENY for dangerous input', async () => {
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
    }),
  ];

  for (const fn of asyncTests) {
    await fn();
  }

  console.log(`\n${'─'.repeat(50)}`);
  console.log(`Results: ${passed} passed, ${failed} failed`);
  if (failed > 0) process.exit(1);
}

runAsyncTests().catch(err => {
  console.error('Async test runner failed:', err);
  process.exit(1);
});

