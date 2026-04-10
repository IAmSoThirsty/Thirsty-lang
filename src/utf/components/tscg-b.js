/**
 * Tier 6 - TSCG-B (Binary Encoding)
 * Encodes TSCG-compressed output to binary (Buffer/Uint8Array).
 * Magic header: 0x54534347 ('TSCG')
 */

const fs = require('fs');

const MAGIC = 0x54534347; // 'TSCG' in ASCII
const VERSION = 1;

class TSCGB {
  constructor(options = {}) {
    this.tier = 6;
    this.name = 'TSCG-B';
    this.options = options;
  }

  encode(tscgOutput) {
    const content = typeof tscgOutput === 'string'
      ? tscgOutput
      : (tscgOutput.compressed || JSON.stringify(tscgOutput));

    const contentBuf = Buffer.from(content, 'utf8');
    const headerSize = 12; // magic(4) + version(2) + flags(2) + contentLength(4)
    const buf = Buffer.alloc(headerSize + contentBuf.length);

    buf.writeUInt32BE(MAGIC, 0);
    buf.writeUInt16BE(VERSION, 4);
    buf.writeUInt16BE(0, 6);             // Flags (reserved)
    buf.writeUInt32BE(contentBuf.length, 8);
    contentBuf.copy(buf, headerSize);

    return buf;
  }

  decode(binary) {
    const buf = Buffer.isBuffer(binary) ? binary : Buffer.from(binary);

    if (buf.length < 12) throw new Error('Invalid TSCG-B: buffer too small');

    const magic = buf.readUInt32BE(0);
    if (magic !== MAGIC) {
      throw new Error(`Invalid TSCG-B: bad magic header (got 0x${magic.toString(16).toUpperCase()})`);
    }

    const version = buf.readUInt16BE(4);
    if (version !== VERSION) throw new Error(`Unsupported TSCG-B version: ${version}`);

    const contentLength = buf.readUInt32BE(8);
    if (buf.length < 12 + contentLength) throw new Error('Invalid TSCG-B: truncated content');

    return buf.slice(12, 12 + contentLength).toString('utf8');
  }

  encodeToFile(tscgOutput, filePath) {
    const encoded = this.encode(tscgOutput);
    fs.writeFileSync(filePath, encoded);
    return { written: encoded.length, path: filePath };
  }

  decodeFromFile(filePath) {
    const buf = fs.readFileSync(filePath);
    return this.decode(buf);
  }

  getMagic() {
    return MAGIC;
  }
}

module.exports = { TSCGB };
