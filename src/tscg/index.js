/**
 * TSCG Manager - Unified interface for Tiers 5 & 6
 *
 * Combines Symbolic Compression (Tier 5) and Binary Encoding (Tier 6)
 * for end-to-end repository compression.
 */

const fs = require('fs');
const path = require('path');
const SymbolicCompression = require('./symbolic-compression');
const BinaryEncoding = require('./binary-encoding');

class TSCGManager {
  constructor() {
    this.symbolic = new SymbolicCompression();
    this.binary = new BinaryEncoding();
  }

  /**
   * Compress entire repository to binary format
   */
  compressRepository(repoPath, outputPath, options = {}) {
    console.log(`\n💧 TSCG Compression Pipeline Starting...`);
    console.log(`📁 Repository: ${repoPath}`);

    // Step 1: Symbolic Compression (Tier 5)
    console.log(`\n⚡ [Tier 5] Symbolic Compression`);
    const startSymbolic = Date.now();

    const tscgData = this.symbolic.compressDirectory(repoPath, {
      includeHidden: options.includeHidden || false,
      gitAware: options.gitAware !== false, // Default true
      extensions: options.extensions || null,
    });

    // Ensure tier is set to 6 for binary encoding
    if (!tscgData.metadata) {
      tscgData.metadata = {};
    }
    tscgData.metadata.tier = 6;
    tscgData.metadata.version = 1;

    const symbolicTime = Date.now() - startSymbolic;
    console.log(`   ✓ Files processed: ${tscgData.files.length}`);
    console.log(`   ✓ Symbols mapped: ${Object.keys(tscgData.symbolDictionary).length}`);
    console.log(`   ✓ Time: ${symbolicTime}ms`);

    // Step 2: Binary Encoding (Tier 6)
    console.log(`\n⚡ [Tier 6] Binary Encoding`);
    const startBinary = Date.now();

    const encoded = this.binary.encode(tscgData);

    const binaryTime = Date.now() - startBinary;
    console.log(`   ✓ Binary size: ${encoded.binary.length} bytes`);
    console.log(`   ✓ Compression ratio: ${encoded.stats.compressionRatio}`);
    console.log(`   ✓ Hash: ${encoded.hash.substring(0, 16)}...`);
    console.log(`   ✓ Time: ${binaryTime}ms`);

    // Step 3: Write output
    fs.writeFileSync(outputPath, encoded.binary);
    console.log(`\n💾 Compressed repository saved to: ${outputPath}`);

    // Final stats
    const totalTime = symbolicTime + binaryTime;
    console.log(`\n📊 Compression Summary:`);
    console.log(`   Files: ${tscgData.files.length}`);
    console.log(`   Symbols: ${Object.keys(tscgData.symbolDictionary).length}`);
    console.log(`   Output size: ${this.formatBytes(encoded.binary.length)}`);
    console.log(`   Compression: ${encoded.stats.compressionRatio}`);
    console.log(`   Total time: ${totalTime}ms`);
    console.log(`   Hash: ${encoded.hash}`);

    return {
      outputPath,
      stats: {
        files: tscgData.files.length,
        symbols: Object.keys(tscgData.symbolDictionary).length,
        size: encoded.binary.length,
        compressionRatio: encoded.stats.compressionRatio,
        hash: encoded.hash,
        time: totalTime,
      },
    };
  }

  /**
   * Decompress binary format back to repository structure
   */
  decompressRepository(inputPath, outputPath, options = {}) {
    console.log(`\n💧 TSCG Decompression Pipeline Starting...`);
    console.log(`📁 Input: ${inputPath}`);
    console.log(`📁 Output: ${outputPath}`);

    // Step 1: Read binary data
    console.log(`\n⚡ Reading binary file...`);
    const binaryData = fs.readFileSync(inputPath);
    console.log(`   ✓ Size: ${this.formatBytes(binaryData.length)}`);

    // Step 2: Binary Decoding (Tier 6)
    console.log(`\n⚡ [Tier 6] Binary Decoding`);
    const startDecode = Date.now();

    const tscgData = this.binary.decode(binaryData);

    const decodeTime = Date.now() - startDecode;
    console.log(`   ✓ Files: ${tscgData.files.length}`);
    console.log(`   ✓ Symbols: ${Object.keys(tscgData.symbolDictionary).length}`);
    console.log(`   ✓ Time: ${decodeTime}ms`);

    // Step 3: Symbolic Decompression (Tier 5)
    console.log(`\n⚡ [Tier 5] Symbolic Decompression`);
    const startSymbolic = Date.now();

    // Restore symbol mappings
    Object.entries(tscgData.symbolDictionary).forEach(([id, token]) => {
      this.symbolic.symbolMap.set(token, parseInt(id));
      this.symbolic.reverseMap.set(parseInt(id), token);
    });

    // Create output directory
    if (!fs.existsSync(outputPath)) {
      fs.mkdirSync(outputPath, { recursive: true });
    }

    // Restore each file
    let filesRestored = 0;
    tscgData.files.forEach(fileData => {
      const fullPath = path.join(outputPath, fileData.path);
      const dirPath = path.dirname(fullPath);

      // Create directory if needed
      if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true });
      }

      // Decompress and write file
      const content = this.symbolic.decompressFile(fileData);
      fs.writeFileSync(fullPath, content, 'utf8');
      filesRestored++;
    });

    const symbolicTime = Date.now() - startSymbolic;
    console.log(`   ✓ Files restored: ${filesRestored}`);
    console.log(`   ✓ Time: ${symbolicTime}ms`);

    // Final stats
    const totalTime = decodeTime + symbolicTime;
    console.log(`\n📊 Decompression Summary:`);
    console.log(`   Files: ${filesRestored}`);
    console.log(`   Output: ${outputPath}`);
    console.log(`   Total time: ${totalTime}ms`);

    return {
      outputPath,
      stats: {
        files: filesRestored,
        time: totalTime,
      },
    };
  }

  /**
   * Compress single file to micro payload (~20 bytes)
   */
  compressMicroPayload(filePath, outputPath) {
    console.log(`\n💧 TSCG Micro Payload Compression`);
    console.log(`📄 File: ${filePath}`);

    // Read file
    const content = fs.readFileSync(filePath, 'utf8');
    const fileName = path.basename(filePath);

    // Symbolic compression
    const tscgFile = this.symbolic.compressFile(fileName, content);
    const tscgData = {
      files: [tscgFile],
      symbolDictionary: {},
      metadata: { tier: 6, timestamp: Date.now(), version: 1 },
    };

    // Export dictionary
    this.symbolic.symbolMap.forEach((id, token) => {
      tscgData.symbolDictionary[id] = token;
    });

    // Create micro payload
    const microPayload = this.binary.createMicroPayload(tscgData);

    // Write output
    fs.writeFileSync(outputPath, microPayload);

    console.log(`   ✓ Original: ${content.length} bytes`);
    console.log(`   ✓ Compressed: ${microPayload.length} bytes`);
    console.log(`   ✓ Ratio: ${((1 - microPayload.length / content.length) * 100).toFixed(2)}%`);
    console.log(`   💾 Saved to: ${outputPath}`);

    return {
      originalSize: content.length,
      compressedSize: microPayload.length,
      outputPath,
    };
  }

  /**
   * Get repository compression stats without actually compressing
   */
  analyzeRepository(repoPath, options = {}) {
    console.log(`\n💧 TSCG Repository Analysis`);
    console.log(`📁 Repository: ${repoPath}`);

    const files = this.symbolic.scanDirectory(
      repoPath,
      options.includeHidden || false,
      options.gitAware !== false,
      options.extensions || null
    );

    let totalSize = 0;
    const filesByExtension = {};

    files.forEach(filePath => {
      const stats = fs.statSync(filePath);
      totalSize += stats.size;

      const ext = path.extname(filePath) || 'no-extension';
      if (!filesByExtension[ext]) {
        filesByExtension[ext] = { count: 0, size: 0 };
      }
      filesByExtension[ext].count++;
      filesByExtension[ext].size += stats.size;
    });

    console.log(`\n📊 Analysis Results:`);
    console.log(`   Total files: ${files.length}`);
    console.log(`   Total size: ${this.formatBytes(totalSize)}`);
    console.log(`\n   Files by extension:`);

    Object.entries(filesByExtension)
      .sort((a, b) => b[1].size - a[1].size)
      .forEach(([ext, stats]) => {
        console.log(`     ${ext.padEnd(15)} ${stats.count.toString().padStart(5)} files  ${this.formatBytes(stats.size).padStart(10)}`);
      });

    return {
      files: files.length,
      totalSize,
      filesByExtension,
    };
  }

  /**
   * Verify compressed repository integrity
   */
  verifyCompressed(compressedPath) {
    console.log(`\n💧 TSCG Integrity Verification`);
    console.log(`📁 File: ${compressedPath}`);

    try {
      const binaryData = fs.readFileSync(compressedPath);
      const tscgData = this.binary.decode(binaryData);

      console.log(`   ✓ Format: Valid TSCG-B`);
      console.log(`   ✓ Version: ${tscgData.metadata.version}`);
      console.log(`   ✓ Tier: ${tscgData.metadata.tier}`);
      console.log(`   ✓ Files: ${tscgData.files.length}`);
      console.log(`   ✓ Symbols: ${Object.keys(tscgData.symbolDictionary).length}`);
      console.log(`   ✓ Timestamp: ${new Date(tscgData.metadata.timestamp).toISOString()}`);

      return {
        valid: true,
        metadata: tscgData.metadata,
        files: tscgData.files.length,
        symbols: Object.keys(tscgData.symbolDictionary).length,
      };
    } catch (error) {
      console.log(`   ✗ Error: ${error.message}`);
      return {
        valid: false,
        error: error.message,
      };
    }
  }

  /**
   * Format bytes for display
   */
  formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  }

  /**
   * Export TSCG data as JSON for inspection
   */
  exportJSON(compressedPath, outputPath) {
    console.log(`\n💧 TSCG Export to JSON`);

    const binaryData = fs.readFileSync(compressedPath);
    const tscgData = this.binary.decode(binaryData);

    fs.writeFileSync(outputPath, JSON.stringify(tscgData, null, 2), 'utf8');

    console.log(`   ✓ Exported to: ${outputPath}`);

    return outputPath;
  }

  /**
   * Import TSCG data from JSON
   */
  importJSON(jsonPath, outputPath) {
    console.log(`\n💧 TSCG Import from JSON`);

    const tscgData = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
    const encoded = this.binary.encode(tscgData);

    fs.writeFileSync(outputPath, encoded.binary);

    console.log(`   ✓ Imported to: ${outputPath}`);
    console.log(`   ✓ Size: ${this.formatBytes(encoded.binary.length)}`);

    return outputPath;
  }
}

module.exports = TSCGManager;
