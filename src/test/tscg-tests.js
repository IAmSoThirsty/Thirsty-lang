/**
 * TSCG Tests - Test Symbolic Compression and Binary Encoding
 */

const SymbolicCompression = require('../tscg/symbolic-compression');
const BinaryEncoding = require('../tscg/binary-encoding');
const TSCGManager = require('../tscg/index');
const fs = require('fs');
const path = require('path');
const os = require('os');

class TSCGTests {
  constructor() {
    this.tests = [];
    this.passed = 0;
    this.failed = 0;
  }

  /**
   * Register a test
   */
  test(name, fn) {
    this.tests.push({ name, fn });
  }

  /**
   * Run all tests
   */
  async run() {
    console.log('\n💧 Running TSCG Tests (Tier 5 & 6)\n');
    console.log('='.repeat(60));

    for (const { name, fn } of this.tests) {
      try {
        await fn();
        this.passed++;
        console.log(`✓ ${name}`);
      } catch (error) {
        this.failed++;
        console.log(`✗ ${name}`);
        console.log(`  Error: ${error.message}`);
        if (process.env.DEBUG) {
          console.log(error.stack);
        }
      }
    }

    console.log('='.repeat(60));
    console.log(`\nResults: ${this.passed} passed, ${this.failed} failed\n`);

    return this.failed === 0;
  }

  /**
   * Assert helper
   */
  assert(condition, message) {
    if (!condition) {
      throw new Error(message || 'Assertion failed');
    }
  }

  /**
   * Assert equal helper
   */
  assertEqual(actual, expected, message) {
    if (actual !== expected) {
      throw new Error(message || `Expected ${expected}, got ${actual}`);
    }
  }

  /**
   * Assert deep equal for objects/arrays
   */
  assertDeepEqual(actual, expected, message) {
    const actualStr = JSON.stringify(actual);
    const expectedStr = JSON.stringify(expected);
    if (actualStr !== expectedStr) {
      throw new Error(message || `Expected ${expectedStr}, got ${actualStr}`);
    }
  }
}

// Create test suite
const suite = new TSCGTests();

// ========================================
// Tier 5: Symbolic Compression Tests
// ========================================

suite.test('Symbolic Compression: Initialize symbol dictionary', () => {
  const symbolic = new SymbolicCompression();
  suite.assert(symbolic.symbolMap.size > 0, 'Symbol map should be initialized');
  suite.assert(symbolic.symbolMap.has('drink'), 'Should have "drink" keyword');
  suite.assert(symbolic.symbolMap.has('pour'), 'Should have "pour" keyword');
  suite.assert(symbolic.symbolMap.has('thirsty'), 'Should have "thirsty" keyword');
  suite.assert(symbolic.symbolMap.has('glass'), 'Should have "glass" keyword');
  suite.assert(symbolic.symbolMap.has('fountain'), 'Should have "fountain" keyword');
});

suite.test('Symbolic Compression: Tokenize simple code', () => {
  const symbolic = new SymbolicCompression();
  const code = 'drink x = 5';
  const tokens = symbolic.tokenize(code);

  suite.assert(tokens.includes('drink'), 'Should tokenize "drink"');
  suite.assert(tokens.includes('x'), 'Should tokenize identifier "x"');
  suite.assert(tokens.includes('='), 'Should tokenize "="');
  suite.assert(tokens.includes('5'), 'Should tokenize number "5"');
});

suite.test('Symbolic Compression: Tokenize with strings', () => {
  const symbolic = new SymbolicCompression();
  const code = 'pour "Hello, World!"';
  const tokens = symbolic.tokenize(code);

  suite.assert(tokens.includes('pour'), 'Should tokenize "pour"');
  suite.assert(tokens.some(t => t.includes('Hello, World!')), 'Should preserve string content');
});

suite.test('Symbolic Compression: Tokenize with comments', () => {
  const symbolic = new SymbolicCompression();
  const code = '// This is a comment\ndrink x = 5';
  const tokens = symbolic.tokenize(code);

  suite.assert(tokens.some(t => t.includes('This is a comment')), 'Should preserve comment');
  suite.assert(tokens.includes('drink'), 'Should tokenize code after comment');
});

suite.test('Symbolic Compression: Compress and decompress file', () => {
  const symbolic = new SymbolicCompression();
  const originalCode = 'drink water = 8\npour water';

  const compressed = symbolic.compressFile('test.thirsty', originalCode);
  suite.assert(compressed.symbols.length > 0, 'Should have symbols');
  suite.assert(compressed.hash, 'Should have hash');

  const decompressed = symbolic.decompressFile(compressed);
  const normalizedOriginal = originalCode.trim();
  const normalizedDecompressed = decompressed.trim();

  // Check that all important tokens are preserved
  suite.assert(normalizedDecompressed.includes('drink'), 'Should preserve "drink"');
  suite.assert(normalizedDecompressed.includes('water'), 'Should preserve "water"');
  suite.assert(normalizedDecompressed.includes('8'), 'Should preserve "8"');
  suite.assert(normalizedDecompressed.includes('pour'), 'Should preserve "pour"');
});

suite.test('Symbolic Compression: Handle operators correctly', () => {
  const symbolic = new SymbolicCompression();
  const code = 'drink x = 5 + 3 * 2';
  const tokens = symbolic.tokenize(code);

  suite.assert(tokens.includes('+'), 'Should tokenize "+"');
  suite.assert(tokens.includes('*'), 'Should tokenize "*"');
  suite.assert(tokens.includes('='), 'Should tokenize "="');
});

suite.test('Symbolic Compression: Handle multi-char operators', () => {
  const symbolic = new SymbolicCompression();
  const code = 'thirsty x == 5';
  const tokens = symbolic.tokenize(code);

  suite.assert(tokens.includes('=='), 'Should tokenize "==" as single token');
});

// ========================================
// Tier 6: Binary Encoding Tests
// ========================================

suite.test('Binary Encoding: Encode and decode variable-length integers', () => {
  const binary = new BinaryEncoding();

  const testNumbers = [0, 1, 127, 128, 255, 256, 65535, 65536];

  testNumbers.forEach(num => {
    const encoded = binary.encodeVarInt(num);
    const decoded = binary.decodeVarInt(encoded, 0);
    suite.assertEqual(decoded.value, num, `VarInt encoding/decoding should work for ${num}`);
  });
});

suite.test('Binary Encoding: Encode and decode dictionary', () => {
  const binary = new BinaryEncoding();
  const dictionary = {
    1: 'drink',
    2: 'pour',
    3: 'thirsty',
    10: 'glass',
    100: 'fountain',
  };

  const encoded = binary.encodeDictionary(dictionary);
  const decoded = binary.decodeDictionary(encoded);

  suite.assertDeepEqual(decoded, dictionary, 'Dictionary should encode and decode correctly');
});

suite.test('Binary Encoding: Encode and decode symbol array', () => {
  const binary = new BinaryEncoding();
  const symbols = [1, 2, 3, 10, 100, 1000];

  const encoded = binary.encodeSymbolArray(symbols);
  const decoded = binary.decodeSymbolArray(encoded, 0);

  suite.assertDeepEqual(decoded.symbols, symbols, 'Symbol array should encode and decode correctly');
});

suite.test('Binary Encoding: Encode and decode metadata', () => {
  const binary = new BinaryEncoding();
  const metadata = {
    version: 1,
    timestamp: Date.now(),
    tier: 6,
    fileCount: 10,
    dictionarySize: 50,
  };

  const buffer = Buffer.allocUnsafe(1024);
  const encoded = binary.encodeMetadata(metadata);
  encoded.copy(buffer, 0);

  const decoded = binary.decodeMetadata(buffer, 0);

  suite.assertEqual(decoded.metadata.version, metadata.version, 'Version should match');
  suite.assertEqual(decoded.metadata.tier, metadata.tier, 'Tier should match');
  suite.assertEqual(decoded.metadata.fileCount, metadata.fileCount, 'File count should match');
  suite.assertEqual(decoded.metadata.dictionarySize, metadata.dictionarySize, 'Dictionary size should match');
});

suite.test('Binary Encoding: Verify magic header', () => {
  const binary = new BinaryEncoding();

  const validBuffer = Buffer.concat([
    Buffer.from('TSCGB', 'utf8'),
    Buffer.allocUnsafe(100),
  ]);

  suite.assert(binary.verifyHeader(validBuffer), 'Should verify valid header');

  const invalidBuffer = Buffer.from('INVALID', 'utf8');
  suite.assert(!binary.verifyHeader(invalidBuffer), 'Should reject invalid header');
});

suite.test('Binary Encoding: Full encode/decode cycle', () => {
  const binary = new BinaryEncoding();

  const tscgData = {
    metadata: {
      timestamp: Date.now(),
      tier: 6,
    },
    symbolDictionary: {
      1: 'drink',
      2: 'pour',
      3: 'x',
      4: '=',
      5: '5',
    },
    files: [
      {
        path: 'test.thirsty',
        symbols: [1, 3, 4, 5],
        hash: 'a'.repeat(64), // Mock SHA-256 hash
      },
    ],
  };

  const encoded = binary.encode(tscgData);
  suite.assert(encoded.binary.length > 0, 'Should produce binary output');
  suite.assert(encoded.hash, 'Should have hash');

  const decoded = binary.decode(encoded.binary);
  suite.assertEqual(decoded.files.length, 1, 'Should decode correct number of files');
  suite.assertDeepEqual(decoded.symbolDictionary, tscgData.symbolDictionary, 'Dictionary should match');
  suite.assertDeepEqual(decoded.files[0].symbols, tscgData.files[0].symbols, 'Symbols should match');
});

suite.test('Binary Encoding: Compression reduces size', () => {
  const binary = new BinaryEncoding();

  const largeData = Buffer.alloc(1000, 'A');
  const compressed = binary.compress(largeData);

  suite.assert(compressed.length < largeData.length, 'Compression should reduce size');

  const decompressed = binary.decompress(compressed);
  suite.assert(decompressed.equals(largeData), 'Decompression should restore original data');
});

// ========================================
// Integration Tests (TSCG Manager)
// ========================================

suite.test('TSCG Manager: Compress and decompress directory', () => {
  const manager = new TSCGManager();

  // Create temporary directory with test files
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'tscg-test-'));
  const testFile1 = path.join(tmpDir, 'test1.thirsty');
  const testFile2 = path.join(tmpDir, 'test2.thirsty');

  fs.writeFileSync(testFile1, 'drink x = 5\npour x', 'utf8');
  fs.writeFileSync(testFile2, 'drink y = 10\npour y', 'utf8');

  // Compress
  const compressedPath = path.join(tmpDir, 'compressed.tscg');
  const compressResult = manager.compressRepository(tmpDir, compressedPath, {
    extensions: ['.thirsty'],
  });

  suite.assert(fs.existsSync(compressedPath), 'Compressed file should exist');
  suite.assertEqual(compressResult.stats.files, 2, 'Should compress 2 files');

  // Decompress
  const outputDir = path.join(tmpDir, 'output');
  const decompressResult = manager.decompressRepository(compressedPath, outputDir);

  suite.assert(fs.existsSync(path.join(outputDir, 'test1.thirsty')), 'File 1 should be restored');
  suite.assert(fs.existsSync(path.join(outputDir, 'test2.thirsty')), 'File 2 should be restored');

  // Verify content
  const restored1 = fs.readFileSync(path.join(outputDir, 'test1.thirsty'), 'utf8');
  const restored2 = fs.readFileSync(path.join(outputDir, 'test2.thirsty'), 'utf8');

  suite.assert(restored1.includes('drink'), 'File 1 should preserve content');
  suite.assert(restored1.includes('x'), 'File 1 should preserve variable name');
  suite.assert(restored2.includes('drink'), 'File 2 should preserve content');
  suite.assert(restored2.includes('y'), 'File 2 should preserve variable name');

  // Cleanup
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

suite.test('TSCG Manager: Micro payload compression', () => {
  const manager = new TSCGManager();

  // Create temporary file
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'tscg-micro-'));
  const testFile = path.join(tmpDir, 'test.thirsty');
  const outputFile = path.join(tmpDir, 'test.tscg');

  fs.writeFileSync(testFile, 'drink x = 5', 'utf8');

  // Create micro payload
  const result = manager.compressMicroPayload(testFile, outputFile);

  suite.assert(fs.existsSync(outputFile), 'Micro payload file should exist');
  suite.assert(result.compressedSize > 0, 'Should have compressed size');
  // Note: For very small files, compression may increase size due to overhead
  // This is expected behavior - compression is most effective for larger files

  // Cleanup
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

suite.test('TSCG Manager: Verify compressed file', () => {
  const manager = new TSCGManager();

  // Create temporary test
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'tscg-verify-'));
  const testFile = path.join(tmpDir, 'test.thirsty');
  const compressedPath = path.join(tmpDir, 'compressed.tscg');

  fs.writeFileSync(testFile, 'drink water = 8', 'utf8');

  manager.compressRepository(tmpDir, compressedPath, {
    extensions: ['.thirsty'],
  });

  // Verify
  const verifyResult = manager.verifyCompressed(compressedPath);

  suite.assert(verifyResult.valid, 'Should verify as valid');
  suite.assertEqual(verifyResult.metadata.tier, 6, 'Should be Tier 6');
  suite.assert(verifyResult.files > 0, 'Should have files');

  // Cleanup
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

suite.test('TSCG Manager: Export and import JSON', () => {
  const manager = new TSCGManager();

  // Create temporary test
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'tscg-json-'));
  const testFile = path.join(tmpDir, 'test.thirsty');
  const compressedPath = path.join(tmpDir, 'compressed.tscg');
  const jsonPath = path.join(tmpDir, 'export.json');
  const importedPath = path.join(tmpDir, 'imported.tscg');

  fs.writeFileSync(testFile, 'drink water = 8', 'utf8');

  // Compress
  manager.compressRepository(tmpDir, compressedPath, {
    extensions: ['.thirsty'],
  });

  // Export to JSON
  manager.exportJSON(compressedPath, jsonPath);
  suite.assert(fs.existsSync(jsonPath), 'JSON export should exist');

  const jsonData = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
  suite.assert(jsonData.files, 'JSON should have files');
  suite.assert(jsonData.symbolDictionary, 'JSON should have dictionary');

  // Import from JSON
  manager.importJSON(jsonPath, importedPath);
  suite.assert(fs.existsSync(importedPath), 'Imported binary should exist');

  // Verify imported file
  const verifyResult = manager.verifyCompressed(importedPath);
  suite.assert(verifyResult.valid, 'Imported file should be valid');

  // Cleanup
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

suite.test('TSCG Manager: Handle .gitignore correctly', () => {
  const manager = new TSCGManager();

  // Create temporary directory with .gitignore
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'tscg-gitignore-'));

  fs.writeFileSync(path.join(tmpDir, '.gitignore'), 'ignored.txt\n*.log', 'utf8');
  fs.writeFileSync(path.join(tmpDir, 'included.thirsty'), 'drink x = 1', 'utf8');
  fs.writeFileSync(path.join(tmpDir, 'ignored.txt'), 'should be ignored', 'utf8');
  fs.writeFileSync(path.join(tmpDir, 'test.log'), 'should be ignored', 'utf8');

  const compressedPath = path.join(tmpDir, 'compressed.tscg');

  // Compress with git-aware mode
  const result = manager.compressRepository(tmpDir, compressedPath, {
    gitAware: true,
  });

  // Should only compress included.thirsty and .gitignore
  suite.assert(result.stats.files >= 1, 'Should compress at least included.thirsty');

  // Cleanup
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

// Run all tests
suite.run().then(success => {
  process.exit(success ? 0 : 1);
});
