/**
 * TSCG-B - Thirsty Symbolic Compression Grammar - Binary Encoding (Tier 6)
 *
 * Binary encoding layer that converts TSCG symbolic representations
 * into ultra-compact, hash-stable binary payloads.
 *
 * Target: Compress constitutional governance logic to payloads as small as 20 bytes
 */

const crypto = require('crypto');
const zlib = require('zlib');

class BinaryEncoding {
  constructor() {
    this.MAGIC_HEADER = Buffer.from('TSCGB', 'utf8'); // 5 bytes
    this.VERSION = 1; // 1 byte
    this.MIN_PAYLOAD_SIZE = 20; // Target minimum size
  }

  /**
   * Encode TSCG compressed data into binary format
   */
  encode(tscgData) {
    // Create encoding metadata
    const metadata = this.createMetadata(tscgData);

    // Convert symbol dictionary to binary
    const dictionaryBuffer = this.encodeDictionary(tscgData.symbolDictionary);

    // Convert file data to binary
    const filesBuffer = this.encodeFiles(tscgData.files);

    // Create hash for verification
    const contentHash = this.createContentHash(tscgData);

    // Assemble binary payload
    const payload = this.assemblePayload({
      metadata,
      dictionary: dictionaryBuffer,
      files: filesBuffer,
      hash: contentHash,
    });

    // Apply compression
    const compressed = this.compress(payload);

    return {
      binary: compressed,
      stats: this.getEncodingStats(payload, compressed),
      hash: contentHash,
    };
  }

  /**
   * Decode binary format back to TSCG data
   */
  decode(binaryData) {
    // Decompress
    const payload = this.decompress(binaryData);

    // Verify magic header
    if (!this.verifyHeader(payload)) {
      throw new Error('Invalid TSCG-B format: magic header mismatch');
    }

    // Extract components
    const { metadata, dictionary, files, hash } = this.disassemblePayload(payload);

    // Reconstruct TSCG data
    const tscgData = {
      metadata,
      symbolDictionary: this.decodeDictionary(dictionary),
      files: this.decodeFiles(files),
    };

    // Verify integrity
    const computedHash = this.createContentHash(tscgData);
    if (computedHash !== hash) {
      console.warn('Warning: Content hash mismatch. Data may be corrupted.');
    }

    return tscgData;
  }

  /**
   * Create metadata header
   */
  createMetadata(tscgData) {
    return {
      version: this.VERSION,
      timestamp: tscgData.metadata?.timestamp || Date.now(),
      tier: tscgData.metadata?.tier || 6,
      fileCount: tscgData.files.length,
      dictionarySize: Object.keys(tscgData.symbolDictionary).length,
    };
  }

  /**
   * Encode symbol dictionary using variable-length encoding
   */
  encodeDictionary(dictionary) {
    const entries = Object.entries(dictionary);
    const buffers = [];

    // Write dictionary size (2 bytes - up to 65535 symbols)
    const sizeBuffer = Buffer.allocUnsafe(2);
    sizeBuffer.writeUInt16BE(entries.length, 0);
    buffers.push(sizeBuffer);

    // Write each symbol entry
    entries.forEach(([id, token]) => {
      // Symbol ID (variable length)
      const idNum = parseInt(id);
      const idBuffer = this.encodeVarInt(idNum);

      // Token string (length-prefixed)
      const tokenBuffer = Buffer.from(token, 'utf8');
      const tokenLengthBuffer = this.encodeVarInt(tokenBuffer.length);

      buffers.push(idBuffer, tokenLengthBuffer, tokenBuffer);
    });

    return Buffer.concat(buffers);
  }

  /**
   * Decode symbol dictionary
   */
  decodeDictionary(buffer) {
    const dictionary = {};
    let offset = 0;

    // Read dictionary size
    const size = buffer.readUInt16BE(offset);
    offset += 2;

    // Read each entry
    for (let i = 0; i < size; i++) {
      // Read symbol ID
      const { value: id, bytes: idBytes } = this.decodeVarInt(buffer, offset);
      offset += idBytes;

      // Read token length
      const { value: tokenLength, bytes: lengthBytes } = this.decodeVarInt(buffer, offset);
      offset += lengthBytes;

      // Read token
      const token = buffer.toString('utf8', offset, offset + tokenLength);
      offset += tokenLength;

      dictionary[id] = token;
    }

    return dictionary;
  }

  /**
   * Encode files array
   */
  encodeFiles(files) {
    const buffers = [];

    // Write file count (2 bytes)
    const countBuffer = Buffer.allocUnsafe(2);
    countBuffer.writeUInt16BE(files.length, 0);
    buffers.push(countBuffer);

    // Write each file
    files.forEach(file => {
      // File path (length-prefixed)
      const pathBuffer = Buffer.from(file.path, 'utf8');
      const pathLengthBuffer = this.encodeVarInt(pathBuffer.length);

      // Symbols array (length-prefixed variable-int array)
      const symbolsBuffer = this.encodeSymbolArray(file.symbols);

      // File hash (32 bytes for SHA-256)
      const hashBuffer = Buffer.from(file.hash, 'hex');

      buffers.push(pathLengthBuffer, pathBuffer, symbolsBuffer, hashBuffer);
    });

    return Buffer.concat(buffers);
  }

  /**
   * Decode files array
   */
  decodeFiles(buffer) {
    const files = [];
    let offset = 0;

    // Read file count
    const fileCount = buffer.readUInt16BE(offset);
    offset += 2;

    // Read each file
    for (let i = 0; i < fileCount; i++) {
      // Read path length
      const { value: pathLength, bytes: pathLengthBytes } = this.decodeVarInt(buffer, offset);
      offset += pathLengthBytes;

      // Read path
      const path = buffer.toString('utf8', offset, offset + pathLength);
      offset += pathLength;

      // Read symbols array
      const { symbols, bytes: symbolsBytes } = this.decodeSymbolArray(buffer, offset);
      offset += symbolsBytes;

      // Read hash
      const hash = buffer.toString('hex', offset, offset + 32);
      offset += 32;

      files.push({ path, symbols, hash });
    }

    return files;
  }

  /**
   * Encode array of symbol IDs using variable-length integers
   */
  encodeSymbolArray(symbols) {
    const buffers = [];

    // Array length
    const lengthBuffer = this.encodeVarInt(symbols.length);
    buffers.push(lengthBuffer);

    // Each symbol ID
    symbols.forEach(symbolId => {
      buffers.push(this.encodeVarInt(symbolId));
    });

    return Buffer.concat(buffers);
  }

  /**
   * Decode array of symbol IDs
   */
  decodeSymbolArray(buffer, offset) {
    const symbols = [];
    let currentOffset = offset;

    // Read array length
    const { value: length, bytes: lengthBytes } = this.decodeVarInt(buffer, currentOffset);
    currentOffset += lengthBytes;

    // Read each symbol ID
    for (let i = 0; i < length; i++) {
      const { value: symbolId, bytes: symbolBytes } = this.decodeVarInt(buffer, currentOffset);
      currentOffset += symbolBytes;
      symbols.push(symbolId);
    }

    return { symbols, bytes: currentOffset - offset };
  }

  /**
   * Variable-length integer encoding (VarInt)
   * More compact for small numbers, efficient for large ones
   */
  encodeVarInt(num) {
    const buffers = [];

    while (num > 0x7F) {
      buffers.push(Buffer.from([(num & 0x7F) | 0x80]));
      num >>>= 7;
    }
    buffers.push(Buffer.from([num & 0x7F]));

    return Buffer.concat(buffers);
  }

  /**
   * Decode variable-length integer
   */
  decodeVarInt(buffer, offset) {
    let num = 0;
    let shift = 0;
    let bytes = 0;

    while (true) {
      const byte = buffer.readUInt8(offset + bytes);
      num |= (byte & 0x7F) << shift;
      bytes++;

      if ((byte & 0x80) === 0) {
        break;
      }

      shift += 7;
    }

    return { value: num, bytes };
  }

  /**
   * Create content hash for verification
   */
  createContentHash(tscgData) {
    const hashContent = JSON.stringify({
      files: tscgData.files,
      dictionary: tscgData.symbolDictionary,
    });
    return crypto.createHash('sha256').update(hashContent).digest('hex');
  }

  /**
   * Assemble complete binary payload
   */
  assemblePayload(components) {
    const buffers = [];

    // Magic header (5 bytes)
    buffers.push(this.MAGIC_HEADER);

    // Version (1 byte)
    buffers.push(Buffer.from([this.VERSION]));

    // Metadata (variable)
    const metadataBuffer = this.encodeMetadata(components.metadata);
    buffers.push(metadataBuffer);

    // Dictionary length (4 bytes)
    const dictLengthBuffer = Buffer.allocUnsafe(4);
    dictLengthBuffer.writeUInt32BE(components.dictionary.length, 0);
    buffers.push(dictLengthBuffer);

    // Dictionary
    buffers.push(components.dictionary);

    // Files length (4 bytes)
    const filesLengthBuffer = Buffer.allocUnsafe(4);
    filesLengthBuffer.writeUInt32BE(components.files.length, 0);
    buffers.push(filesLengthBuffer);

    // Files
    buffers.push(components.files);

    // Content hash (32 bytes)
    buffers.push(Buffer.from(components.hash, 'hex'));

    return Buffer.concat(buffers);
  }

  /**
   * Disassemble binary payload into components
   */
  disassemblePayload(buffer) {
    let offset = 0;

    // Skip magic header (5 bytes)
    offset += 5;

    // Read version (1 byte)
    const version = buffer.readUInt8(offset);
    offset += 1;

    // Read metadata
    const { metadata, bytes: metadataBytes } = this.decodeMetadata(buffer, offset);
    offset += metadataBytes;

    // Read dictionary length
    const dictLength = buffer.readUInt32BE(offset);
    offset += 4;

    // Read dictionary
    const dictionary = buffer.slice(offset, offset + dictLength);
    offset += dictLength;

    // Read files length
    const filesLength = buffer.readUInt32BE(offset);
    offset += 4;

    // Read files
    const files = buffer.slice(offset, offset + filesLength);
    offset += filesLength;

    // Read hash
    const hash = buffer.toString('hex', offset, offset + 32);

    return { metadata, dictionary, files, hash };
  }

  /**
   * Encode metadata
   */
  encodeMetadata(metadata) {
    const buffers = [];

    // Timestamp (8 bytes)
    const timestampBuffer = Buffer.allocUnsafe(8);
    timestampBuffer.writeBigUInt64BE(BigInt(metadata.timestamp), 0);
    buffers.push(timestampBuffer);

    // Tier (1 byte)
    buffers.push(Buffer.from([metadata.tier]));

    // File count (2 bytes)
    const fileCountBuffer = Buffer.allocUnsafe(2);
    fileCountBuffer.writeUInt16BE(metadata.fileCount, 0);
    buffers.push(fileCountBuffer);

    // Dictionary size (2 bytes)
    const dictSizeBuffer = Buffer.allocUnsafe(2);
    dictSizeBuffer.writeUInt16BE(metadata.dictionarySize, 0);
    buffers.push(dictSizeBuffer);

    return Buffer.concat(buffers);
  }

  /**
   * Decode metadata
   */
  decodeMetadata(buffer, offset) {
    let currentOffset = offset;

    // Timestamp (8 bytes)
    const timestamp = Number(buffer.readBigUInt64BE(currentOffset));
    currentOffset += 8;

    // Tier (1 byte)
    const tier = buffer.readUInt8(currentOffset);
    currentOffset += 1;

    // File count (2 bytes)
    const fileCount = buffer.readUInt16BE(currentOffset);
    currentOffset += 2;

    // Dictionary size (2 bytes)
    const dictionarySize = buffer.readUInt16BE(currentOffset);
    currentOffset += 2;

    return {
      metadata: { timestamp, tier, fileCount, dictionarySize, version: this.VERSION },
      bytes: currentOffset - offset,
    };
  }

  /**
   * Verify magic header
   */
  verifyHeader(buffer) {
    return buffer.slice(0, 5).equals(this.MAGIC_HEADER);
  }

  /**
   * Compress binary payload using gzip
   */
  compress(buffer) {
    return zlib.gzipSync(buffer, { level: 9 });
  }

  /**
   * Decompress binary payload
   */
  decompress(buffer) {
    return zlib.gunzipSync(buffer);
  }

  /**
   * Get encoding statistics
   */
  getEncodingStats(uncompressed, compressed) {
    const ratio = ((1 - compressed.length / uncompressed.length) * 100).toFixed(2);

    return {
      uncompressedSize: uncompressed.length,
      compressedSize: compressed.length,
      compressionRatio: ratio + '%',
      hashStable: true,
      tier: 6,
    };
  }

  /**
   * Create ultra-compact payload (target: ~20 bytes)
   * For extremely small code snippets or single-file compression
   */
  createMicroPayload(tscgData) {
    // This creates an even more aggressive compression for single files
    // Trade-off: Less metadata, optimized for minimal size

    if (tscgData.files.length !== 1) {
      throw new Error('Micro payload only supports single file compression');
    }

    const file = tscgData.files[0];

    // Create minimal representation
    const symbolHash = this.hashSymbolSequence(file.symbols);
    const contentHash = Buffer.from(file.hash, 'hex').slice(0, 8); // First 8 bytes of SHA-256

    // Combine hashes (16 bytes) + version (1 byte) + tier (1 byte) + file count (1 byte) = ~19 bytes minimum
    const microPayload = Buffer.concat([
      Buffer.from([this.VERSION]),
      Buffer.from([6]), // Tier 6
      Buffer.from([1]), // Single file
      symbolHash,
      contentHash,
    ]);

    return this.compress(microPayload);
  }

  /**
   * Hash a sequence of symbols for ultra-compact representation
   */
  hashSymbolSequence(symbols) {
    const symbolString = symbols.join(',');
    const hash = crypto.createHash('sha256').update(symbolString).digest();
    return hash.slice(0, 8); // 8 bytes
  }
}

module.exports = BinaryEncoding;
