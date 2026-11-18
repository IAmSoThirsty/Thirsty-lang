"""
TSCG-B — TSCG Binary Protocol
Binary frame format with magic bytes, CRC32, SHA-256, and stream decoding.
"""

import hashlib
import struct
import zlib
from typing import Any

from utf.tscg.core import ALL_SYMBOLS, OPCODE_TO_SYMBOL

# Frame format constants
MAGIC = b"TSGB"
VERSION = 1
HEADER_SIZE = 8  # magic(4) + version(1) + flags(1) + payload_length(2)
CRC32_SIZE = 4
SHA256_SIZE = 32
MAX_PAYLOAD_SIZE = 0xFFFF
MIN_FRAME_SIZE = HEADER_SIZE + CRC32_SIZE + SHA256_SIZE  # 44 bytes

# Flag bits
FLAG_NONE = 0x00
FLAG_EOF = 0x01
FLAG_FRAGMENT = 0x02


def opcode_for_symbol(symbol: str) -> int:
    """Get opcode for a TSCG symbol name."""
    if symbol in ALL_SYMBOLS:
        return ALL_SYMBOLS[symbol]
    raise ValueError(f"Unknown symbol: {symbol}")


def symbol_for_opcode(opcode: int) -> str | None:
    """Get symbol name for an opcode."""
    return OPCODE_TO_SYMBOL.get(opcode)


def encode_text_to_opcodes(text: str) -> list[int]:
    """Encode each UTF-8 byte as two base-23 digits, including leading zeros."""
    data = text.encode("utf-8")
    opcodes = []
    for byte in data:
        hi = byte // 23
        lo = byte % 23
        opcodes.append(hi)
        opcodes.append(lo)
    return opcodes


def decode_opcodes_to_text(opcodes: list[int]) -> str:
    """Decode base-23 opcodes back to text (reversible)."""
    bytes_list = bytearray()
    i = 0
    while i < len(opcodes):
        op = opcodes[i]
        # If this op could be a high digit (0-11), try two-byte decode
        if op < 12 and i + 1 < len(opcodes):
            hi = op
            lo = opcodes[i + 1]
            byte_val = hi * 23 + lo
            if byte_val < 256:
                bytes_list.append(byte_val)
                i += 2
                continue
        # Single digit (byte < 23, or ambiguous low byte)
        bytes_list.append(op)
        i += 1
    return bytes(bytes_list).decode("utf-8", errors="replace")


def pack_text(text: str, flags: int = FLAG_NONE) -> bytes:
    """
    Encode text into TSCG-B binary frame.

    Frame layout:
    - magic: b'TSGB' (4 bytes)
    - version: 1 byte
    - flags: 1 byte
    - payload_length: 2 bytes big-endian
    - payload: N bytes
    - crc32: 4 bytes big-endian
    - sha256: 32 bytes
    """
    if not isinstance(text, str):
        raise TypeError("TSCG-B text must be a string")
    if len(text) > MAX_PAYLOAD_SIZE:
        raise ValueError("TSCG-B payload exceeds 65535 bytes")
    text_bytes = text.encode("utf-8")
    if len(text_bytes) > MAX_PAYLOAD_SIZE:
        raise ValueError("TSCG-B payload exceeds 65535 bytes")

    # Build header
    header = struct.pack("!4sBBH", MAGIC, VERSION, flags, len(text_bytes))

    # Payload is the raw text bytes
    payload = text_bytes

    # CRC32 of header + payload
    crc32_val = zlib.crc32(header + payload) & 0xFFFFFFFF
    crc32_bytes = struct.pack("!I", crc32_val)

    # SHA-256 of header + payload + crc32
    sha256_val = hashlib.sha256(header + payload + crc32_bytes).digest()

    return header + payload + crc32_bytes + sha256_val


def unpack_frame(
    data: bytes, verify: bool = True, *, exact_text: bool = False
) -> dict[str, Any]:
    """
    Unpack a TSCG-B binary frame.

    Returns dict with keys: magic, version, flags, payload_length, payload, crc32, sha256
    Raises ValueError on verification failure.
    """
    if len(data) < MIN_FRAME_SIZE:
        raise ValueError(
            f"Frame too short: {len(data)} bytes, minimum {MIN_FRAME_SIZE}"
        )

    # Parse header
    magic, version, flags, payload_length = struct.unpack("!4sBBH", data[:HEADER_SIZE])

    if magic != MAGIC:
        raise ValueError(f"Invalid magic: {magic!r}, expected {MAGIC!r}")
    if version != VERSION:
        raise ValueError(f"Unsupported version: {version}, expected {VERSION}")

    # Extract payload
    payload_start = HEADER_SIZE
    payload_end = payload_start + payload_length
    if payload_end + CRC32_SIZE + SHA256_SIZE > len(data):
        raise ValueError(
            f"Frame too short for payload: need {payload_end + CRC32_SIZE + SHA256_SIZE}, "
            f"got {len(data)}"
        )

    if exact_text and len(data) != payload_end + CRC32_SIZE + SHA256_SIZE:
        raise ValueError("Expected exactly one TSCG-B frame")
    payload = data[payload_start:payload_end]

    # Extract CRC32
    crc32_start = payload_end
    crc32_end = crc32_start + CRC32_SIZE
    stored_crc32 = struct.unpack("!I", data[crc32_start:crc32_end])[0]

    # Extract SHA-256
    sha256_start = crc32_end
    sha256_end = sha256_start + SHA256_SIZE
    stored_sha256 = data[sha256_start:sha256_end]

    if verify:
        # Verify CRC32
        computed_crc32 = zlib.crc32(data[:HEADER_SIZE] + payload) & 0xFFFFFFFF
        if computed_crc32 != stored_crc32:
            raise ValueError(
                f"CRC32 mismatch: computed {computed_crc32:#010x}, "
                f"stored {stored_crc32:#010x}"
            )

        # Verify SHA-256
        computed_sha256 = hashlib.sha256(
            data[:HEADER_SIZE] + payload + data[crc32_start:crc32_end]
        ).digest()
        if computed_sha256 != stored_sha256:
            raise ValueError(
                f"SHA-256 mismatch: computed {computed_sha256.hex()}, "
                f"stored {stored_sha256.hex()}"
            )

    text = payload.decode("utf-8", errors="strict" if exact_text else "replace")

    return {
        "magic": magic,
        "version": version,
        "flags": flags,
        "payload_length": payload_length,
        "payload": payload,
        "text": text,
        "crc32": stored_crc32,
        "sha256": stored_sha256,
        "crc32_hex": f"{stored_crc32:#010x}",
        "sha256_hex": stored_sha256.hex(),
    }


def encode_text(text: str) -> bytes:
    """Encode one unflagged UTF-8 text frame."""
    return pack_text(text)


def decode_text(data: bytes | list[int]) -> str:
    """Verify exactly one unflagged UTF-8 text frame."""
    if type(data) not in (bytes, list):
        raise TypeError("TSCG-B frame must be bytes or a list of octets")
    if len(data) > MIN_FRAME_SIZE + MAX_PAYLOAD_SIZE:
        raise ValueError("TSCG-B text frame exceeds the maximum length")
    if isinstance(data, list):
        if any(type(octet) is not int or not 0 <= octet <= 255 for octet in data):
            raise ValueError("TSCG-B octets must be integers from 0 to 255")
        data = bytes(data)
    frame = unpack_frame(data, exact_text=True)
    if frame["flags"] != FLAG_NONE:
        raise ValueError("TSCG-B text frames require zero flags")
    text: str = frame["text"]
    return text


class StreamDecoder:
    """
    Buffered multi-frame TSCG-B decoder with magic-byte resynchronization.

    Handles streams where frames may be concatenated or interrupted.
    Maintains internal buffer and yields complete frames as they arrive.
    """

    def __init__(self):
        self.buffer = bytearray()
        self.frames_decoded = 0

    def feed(self, data: bytes) -> list[dict[str, Any]]:
        """
        Feed raw bytes into the decoder.
        Returns list of fully decoded frames found in the data.
        """
        self.buffer.extend(data)
        frames = []

        while self.buffer:
            start = self.buffer.find(MAGIC)
            if start < 0:
                # A chunk can end in the first one to three bytes of the magic.
                keep = next(
                    (n for n in (3, 2, 1) if self.buffer.endswith(MAGIC[:n])), 0
                )
                del self.buffer[: len(self.buffer) - keep]
                break
            del self.buffer[:start]
            if len(self.buffer) < HEADER_SIZE:
                break
            if self.buffer[4] != VERSION:
                del self.buffer[:1]
                continue
            size = MIN_FRAME_SIZE + int.from_bytes(self.buffer[6:8], "big")
            if len(self.buffer) < size:
                break
            try:
                frame = unpack_frame(bytes(self.buffer[:size]))
            except ValueError:
                del self.buffer[:1]
                continue
            del self.buffer[:size]
            frames.append(frame)
            self.frames_decoded += 1
        return frames

    def flush(self) -> list[dict[str, Any]]:
        """Flush any remaining frames. Returns empty list (incomplete frames discarded)."""
        self.buffer.clear()
        return []

    @property
    def buffered_bytes(self) -> int:
        return len(self.buffer)
