/**
 * Tier 6 - TSCG-B (Binary Encoding)
 * Encodes TSCG-compressed output to binary (Buffer/Uint8Array).
 *
 * Wire format: [12-byte header][4-byte CRC32][payload bytes][32-byte SHA-256]
 * Total overhead = 48 bytes.
 *
 * Header layout (12 bytes):
 *   Bytes 0-3:  Magic 0x54534742 ('TSGB') as UInt32BE
 *   Bytes 4-5:  Version 0x0001 as UInt16BE
 *   Bytes 6-7:  Flags (reserved = 0) as UInt16BE
 *   Bytes 8-11: Payload length in bytes as UInt32BE
 *
 * CRC32 covers the payload only.
 * SHA-256 covers header + CRC32 + payload (everything before the hash).
 */

const crypto = require('crypto');
const fs = require('fs');

const MAGIC = 0x54534742; // 'TSGB' in ASCII (T=0x54, S=0x53, G=0x47, B=0x42)
const VERSION = 1;
const HEADER_SIZE = 12;
const CRC32_SIZE = 4;
const SHA256_SIZE = 32;
const OVERHEAD = HEADER_SIZE + CRC32_SIZE + SHA256_SIZE; // 48

// ── CRC32 (IEEE 802.3 polynomial 0xEDB88320, standard CRC-32/ISO-HDLC) ──────

const _CRC32_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let j = 0; j < 8; j++) {
      c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    }
    t[i] = c;
  }
  return t;
})();

function _crc32(buf) {
  let crc = 0xFFFFFFFF;
  for (let i = 0; i < buf.length; i++) {
    crc = (crc >>> 8) ^ _CRC32_TABLE[(crc ^ buf[i]) & 0xFF];
  }
  return (crc ^ 0xFFFFFFFF) >>> 0;
}

// ── TSCG Opcode Table (1-byte opcodes, 0x00–0x1F core primitives) ───────────
//
// Order: longest symbols first so the greedy encoder always matches the most
// specific symbol (e.g. Δ_NT before Δ).

const _OPCODE_DEFS = [
  [0x03, 'Δ_NT'],  // non-trivial delta  — must precede Δ
  [0x00, 'NUL'],
  [0x02, 'COG'],
  [0x04, 'SHD'],
  [0x05, 'INV'],
  [0x06, 'CAP'],
  [0x07, 'QRM'],
  [0x08, 'COM'],
  [0x09, 'ANC'],
  [0x0A, 'PRO'],
  [0x0B, 'VER'],
  [0x0C, 'REJ'],
  [0x0D, 'ESC'],
  [0x0E, 'HAL'],
  [0x0F, 'QRN'],
  [0x01, 'Ω'],
  [0x10, '→'],
  [0x11, '∧'],
  [0x12, '∨'],
  [0x13, '¬'],
  [0x14, '⊕'],
  [0x15, '⊢'],
  [0x16, '⊨'],
  [0x17, '∀'],
  [0x18, '∃'],
  [0x19, 'Δ'],   // generic delta — must follow Δ_NT
  [0x1A, '∑'],
  [0x1B, '∏'],
  [0x1C, '∈'],
  [0x1D, '⊂'],
  [0x1E, '∅'],
  [0x1F, '⊥'],
];

// Sorted by symbol length descending for greedy left-to-right matching.
const _ENCODE_LIST = [..._OPCODE_DEFS].sort((a, b) => b[1].length - a[1].length);
const _DECODE_MAP  = new Map(_OPCODE_DEFS.map(([op, sym]) => [op, sym]));
const _ENCODE_MAP  = new Map(_OPCODE_DEFS.map(([op, sym]) => [sym, op]));

// ── TSCGB Class ──────────────────────────────────────────────────────────────

class TSCGB {
  constructor(options = {}) {
    this.tier = 6;
    this.name = 'TSCG-B';
    this.options = options;
  }

  /**
   * Encodes a TSCG string (or TSCG result object) to the TSCG-B wire format.
   * Layout: header(12) + CRC32(4) + payload + SHA-256(32)
   * @param {string|object} tscgOutput
   * @returns {Buffer}
   */
  encode(tscgOutput) {
    const content = typeof tscgOutput === 'string'
      ? tscgOutput
      : (tscgOutput.compressed || JSON.stringify(tscgOutput));

    const payload = Buffer.from(content, 'utf8');

    // Build 12-byte header.
    const header = Buffer.alloc(HEADER_SIZE);
    header.writeUInt32BE(MAGIC, 0);
    header.writeUInt16BE(VERSION, 4);
    header.writeUInt16BE(0, 6);                // flags (reserved)
    header.writeUInt32BE(payload.length, 8);

    // 4-byte CRC32 of the payload.
    const crcBuf = Buffer.alloc(CRC32_SIZE);
    crcBuf.writeUInt32BE(_crc32(payload), 0);

    // Concatenate header + CRC32 + payload for the SHA-256 input.
    const preHash = Buffer.concat([header, crcBuf, payload]);

    // 32-byte SHA-256 over everything before the hash.
    const hash = crypto.createHash('sha256').update(preHash).digest();

    return Buffer.concat([preHash, hash]);
  }

  /**
   * Decodes a TSCG-B buffer back to a string, verifying CRC32 and SHA-256.
   * @param {Buffer|Uint8Array} binary
   * @returns {string}
   */
  decode(binary) {
    const buf = Buffer.isBuffer(binary) ? binary : Buffer.from(binary);

    if (buf.length < 4) {
      throw new Error('Invalid TSCG-B: buffer too small');
    }

    // Verify magic first so the caller gets a meaningful error.
    const magic = buf.readUInt32BE(0);
    if (magic !== MAGIC) {
      throw new Error(`Invalid TSCG-B: bad magic header (got 0x${magic.toString(16).toUpperCase()})`);
    }

    const minSize = OVERHEAD; // 48 bytes minimum (empty payload)
    if (buf.length < minSize) {
      throw new Error('Invalid TSCG-B: buffer too small');
    }

    // Verify version.
    const version = buf.readUInt16BE(4);
    if (version !== VERSION) {
      throw new Error(`Unsupported TSCG-B version: ${version}`);
    }

    const payloadLength = buf.readUInt32BE(8);
    const expectedTotal = OVERHEAD + payloadLength;
    if (buf.length < expectedTotal) {
      throw new Error('Invalid TSCG-B: truncated content');
    }

    // Extract regions.
    const storedCrc    = buf.readUInt32BE(HEADER_SIZE);
    const payloadStart = HEADER_SIZE + CRC32_SIZE;
    const payloadEnd   = payloadStart + payloadLength;
    const payload      = buf.slice(payloadStart, payloadEnd);
    const storedHash   = buf.slice(payloadEnd, payloadEnd + SHA256_SIZE);

    // Verify SHA-256 over header + CRC32 + payload.
    const preHash      = buf.slice(0, payloadEnd);
    const expectedHash = crypto.createHash('sha256').update(preHash).digest();
    if (!expectedHash.equals(storedHash)) {
      throw new Error('Invalid TSCG-B: SHA-256 verification failed');
    }

    // Verify CRC32 over payload.
    const computedCrc = _crc32(payload);
    if (computedCrc !== storedCrc) {
      throw new Error('Invalid TSCG-B: CRC32 verification failed');
    }

    return payload.toString('utf8');
  }

  /**
   * Encodes TSCG symbolic text to a compact binary opcode buffer.
   * Each recognized symbol becomes a 1-byte opcode; unrecognized characters
   * are escaped as [0xFF][byte].
   * @param {string} tscgText
   * @returns {Buffer}
   */
  encodeOpcodes(tscgText) {
    const text = String(tscgText);
    const bytes = [];
    let i = 0;
    while (i < text.length) {
      let matched = false;
      for (const [opcode, symbol] of _ENCODE_LIST) {
        if (text.startsWith(symbol, i)) {
          bytes.push(opcode);
          i += symbol.length;
          matched = true;
          break;
        }
      }
      if (!matched) {
        // Escape: emit 0xFF followed by each UTF-8 byte of the character.
        const charBytes = Buffer.from(text[i], 'utf8');
        bytes.push(0xFF);
        for (const b of charBytes) {
          bytes.push(b);
        }
        i++;
      }
    }
    return Buffer.from(bytes);
  }

  /**
   * Decodes a binary opcode buffer back to TSCG symbolic text.
   * @param {Buffer} buffer
   * @returns {string}
   */
  decodeOpcodes(buffer) {
    const buf = Buffer.isBuffer(buffer) ? buffer : Buffer.from(buffer);
    const parts = [];
    let i = 0;
    while (i < buf.length) {
      const byte = buf[i];
      if (byte === 0xFF) {
        // Escape sequence: one UTF-8 byte follows.
        i++;
        if (i < buf.length) {
          parts.push(Buffer.from([buf[i]]).toString('utf8'));
          i++;
        }
      } else if (_DECODE_MAP.has(byte)) {
        parts.push(_DECODE_MAP.get(byte));
        i++;
      } else {
        // Unknown byte: treat as a raw ASCII character.
        parts.push(String.fromCharCode(byte));
        i++;
      }
    }
    return parts.join('');
  }

  /**
   * Encodes TSCG output and writes it to a file.
   * @param {string|object} tscgOutput
   * @param {string} filePath
   * @returns {{ written: number, path: string }}
   */
  encodeToFile(tscgOutput, filePath) {
    const encoded = this.encode(tscgOutput);
    fs.writeFileSync(filePath, encoded);
    return { written: encoded.length, path: filePath };
  }

  /**
   * Reads a TSCG-B file and decodes it.
   * @param {string} filePath
   * @returns {string}
   */
  decodeFromFile(filePath) {
    const buf = fs.readFileSync(filePath);
    return this.decode(buf);
  }

  /**
   * Returns the TSCG-B magic number (0x54534742).
   * @returns {number}
   */
  getMagic() {
    return MAGIC;
  }
}

module.exports = { TSCGB };
