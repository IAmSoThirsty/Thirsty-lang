"""Edge/error coverage for the TSCG-B binary protocol core."""

import struct

import pytest

from utf.tscg_b import core
from utf.tscg_b.core import (
    StreamDecoder,
    opcode_for_symbol,
    pack_text,
    unpack_frame,
)


def test_opcode_for_symbol():
    name = next(iter(core.ALL_SYMBOLS))
    assert isinstance(opcode_for_symbol(name), int)
    with pytest.raises(ValueError, match="Unknown symbol"):
        opcode_for_symbol("NOPE")


def test_roundtrip():
    frame = pack_text("hello")
    assert unpack_frame(frame)["text"] == "hello"


def test_frame_too_short():
    with pytest.raises(ValueError, match="too short"):
        unpack_frame(b"\x00")


def test_bad_magic():
    frame = bytearray(pack_text("hi"))
    frame[0] ^= 0xFF
    with pytest.raises(ValueError, match="magic"):
        unpack_frame(bytes(frame))


def test_bad_version():
    frame = bytearray(pack_text("hi"))
    frame[4] = 0xEE  # version byte after the 4-byte magic
    with pytest.raises(ValueError, match="version"):
        unpack_frame(bytes(frame))


def test_payload_length_overflow():
    data = core.MAGIC + bytes([core.VERSION, 0]) + struct.pack("!H", 255) + b"\x00" * 36
    with pytest.raises(ValueError, match="too short for payload"):
        unpack_frame(data)


def test_crc_mismatch():
    frame = bytearray(pack_text("hi"))
    crc_start = core.HEADER_SIZE + 2  # payload "hi" is 2 bytes
    frame[crc_start] ^= 0xFF
    with pytest.raises(ValueError, match="CRC32 mismatch"):
        unpack_frame(bytes(frame))


def test_sha_mismatch():
    frame = bytearray(pack_text("hi"))
    frame[-1] ^= 0xFF  # corrupt SHA (CRC does not cover the SHA region)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        unpack_frame(bytes(frame))


def test_no_verify_skips_checks():
    frame = bytearray(pack_text("hi"))
    frame[-1] ^= 0xFF
    # verify=False tolerates the corrupt SHA.
    assert unpack_frame(bytes(frame), verify=False)["text"] == "hi"


def test_stream_decoder_single_and_partial():
    dec = StreamDecoder()
    frame = pack_text("one")
    assert dec.feed(frame[:5]) == []  # partial → buffered
    rest = dec.feed(frame[5:])
    assert rest and rest[0]["text"] == "one"


def test_stream_decoder_resync_after_garbage():
    dec = StreamDecoder()
    frame = pack_text("sync")
    frames = dec.feed(b"\x01\x02\x03" + frame)
    assert frames and frames[0]["text"] == "sync"


def test_stream_decoder_discards_huge_garbage():
    dec = StreamDecoder()
    dec.feed(b"\x00" * 70000)  # no magic, >64KB → buffer cleared
    assert len(dec.buffer) == 0


def test_stream_decoder_corrupt_frame_skipped():
    dec = StreamDecoder()
    frame = bytearray(pack_text("x"))
    frame[-1] ^= 0xFF  # corrupt SHA → frame dropped
    assert dec.feed(bytes(frame)) == []


@pytest.mark.parametrize(
    "value",
    ["", "  hello\r\n", "λ🌊", "\x00\x01\x16A", "x" * 65535],
    ids=["empty", "whitespace", "unicode", "controls", "maximum"],
)
def test_text_profile_and_opcode_round_trips(value):
    assert core.decode_text(core.encode_text(value)) == value
    assert core.decode_opcodes_to_text(core.encode_text_to_opcodes(value)) == value


@pytest.mark.parametrize("value", ["x" * 65536, "λ" * 32768], ids=["ascii", "utf8"])
def test_text_profile_bounds_utf8_bytes(value):
    with pytest.raises(ValueError, match="65535"):
        core.encode_text(value)


def test_text_profile_requires_one_verified_unflagged_utf8_frame():
    import hashlib
    import zlib

    header_payload = struct.pack("!4sBBH", core.MAGIC, 1, 0, 1) + b"\xff"
    checked = header_payload + struct.pack("!I", zlib.crc32(header_payload))
    invalid_utf8 = checked + hashlib.sha256(checked).digest()
    good = core.encode_text("hi")
    assert core.decode_text(list(good)) == "hi"
    for octets in ([True], [-1], [256], [1.0], [0] * 65580):
        with pytest.raises(ValueError):
            core.decode_text(octets)
    for frame in (good + good, good + b"x", good[:-1], pack_text("hi", flags=1)):
        with pytest.raises(ValueError):
            core.decode_text(frame)
    for index in (-1, -33):
        damaged = bytearray(good)
        damaged[index] ^= 1
        with pytest.raises(ValueError):
            core.decode_text(bytes(damaged))
    with pytest.raises(UnicodeDecodeError):
        core.decode_text(invalid_utf8)
    with pytest.raises(TypeError):
        core.encode_text(b"text")
    with pytest.raises(TypeError):
        core.decode_text("text")


def test_stream_resumes_after_damaged_frame_and_split_magic():
    good = pack_text("next")
    damaged = bytearray(pack_text("lost"))
    damaged[-1] ^= 1
    stream = StreamDecoder()
    assert stream.feed(b"x" * 70000 + good[:3]) == []
    assert stream.buffered_bytes == 3
    assert [f["text"] for f in stream.feed(good[3:] + damaged + good)] == [
        "next",
        "next",
    ]
