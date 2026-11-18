"""Private synchronous Node transport for the trusted shield supervisor."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping
from contextlib import suppress
from threading import Timer
from time import monotonic

from utf.thirsty_lang.shield import MAX_RECORD_BYTES, ShieldDenied, ShieldRun

_MAX_CODE_BYTES = 8 * 1024 * 1024
_MAX_REQUESTS = 1024
_TIMEOUT_SECONDS = 30

# Node reads the verified script by length so subsequent stdin bytes are
# acknowledgements. The command line contains only this fixed bootstrap.
_BOOTSTRAP = r"""
const fs = require('node:fs');
function readExactly(n) {
  const b = Buffer.alloc(n);
  let i = 0;
  while (i < n) {
    const count = fs.readSync(0, b, i, n - i, null);
    if (!count) throw Error('incomplete shield program');
    i += count;
  }
  return b;
}
const size = readExactly(4).readUInt32BE(0);
const code = readExactly(size).toString('utf8');
Object.defineProperty(globalThis, Symbol.for('thirsty.shield.exchange.v1'), {
  value(frame) {
    for (let sent = 0; sent < frame.length;) {
      const count = fs.writeSync(1, frame, sent, frame.length - sent);
      if (!count) throw Error('shield channel closed');
      sent += count;
    }
    return readExactly(1)[0];
  },
});
new (require('node:module').Module)('thirsty-shield')._compile(code, 'thirsty-shield.cjs');
"""

# Frame layout: one operation byte, two big-endian length bytes, UTF-8
# payload without the final LF. A one-byte acknowledgement follows each frame.
JS_CHANNEL = r"""
function __shield(op, text) {
  const exchange = globalThis[Symbol.for('thirsty.shield.exchange.v1')];
  if (typeof exchange !== 'function') {
    throw Object.assign(new Error('Governance denied: private shield channel required'), {status: 2});
  }
  const id = op === 'check' ? 1 : op === 'write' ? 2 : op === 'surrender' ? 3 : 0;
  if (!id || (id === 3 ? text !== undefined : typeof text !== 'string')) {
    throw Error('invalid shield operation');
  }
  if (text !== undefined && (text.length >= __shieldLimit ||
      Buffer.byteLength(text, 'utf8') >= __shieldLimit)) {
    throw Error('invalid shield record');
  }
  const payload = Buffer.from(text || '', 'utf8');
  if (text !== undefined && payload.toString('utf8') !== text) {
    throw Error('invalid shield record');
  }
  const frame = Buffer.alloc(3 + payload.length);
  frame[0] = id;
  frame.writeUInt16BE(payload.length, 1);
  payload.copy(frame, 3);
  if (exchange(frame) !== 0) {
    throw Object.assign(new Error('Governance denied: shield operation'), {status: 2});
  }
}
"""
JS_CHANNEL = f"const __shieldLimit = {MAX_RECORD_BYTES};\n" + JS_CHANNEL


def invoke_node(
    node: str,
    code: bytes,
    run: ShieldRun,
    authorize: Callable[[], object],
    env: Mapping[str, str],
) -> int:
    """Execute caller-verified bytes with private child stdio and bounded frames."""
    if type(code) is not bytes or len(code) > _MAX_CODE_BYTES:
        return 1
    # The trusted launcher selects Node and compares the program bytes. Never
    # let environment preloads replace the fixed bootstrap or its imports.
    child_env = {
        k: v for k, v in env.items() if k.upper() not in {"NODE_OPTIONS", "NODE_PATH"}
    }
    channel = run._channel_handle()
    try:
        child = subprocess.Popen(
            [node, "--input-type=commonjs", "-e", _BOOTSTRAP],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=child_env,
        )
    except OSError:
        channel.close()
        return 1

    def terminate() -> None:
        # Serialize loss of this private channel with its pending handoff.
        # Other invocations can still spend the caller's remaining grant.
        channel.close()
        with suppress(OSError):
            child.kill()

    deadline = monotonic() + _TIMEOUT_SECONDS

    def authorize_live() -> object:
        decision = authorize()
        if monotonic() >= deadline or child.poll() is not None:
            channel.close()
            raise ShieldDenied("shield worker is no longer live")
        return decision

    watchdog = Timer(_TIMEOUT_SECONDS, terminate)
    watchdog.daemon = True
    with child:
        assert child.stdin is not None and child.stdout is not None
        watchdog.start()
        try:
            child.stdin.write(len(code).to_bytes(4, "big"))
            child.stdin.write(code)
            child.stdin.flush()
            count = 0
            while True:
                header = child.stdout.read(3)
                if not header:
                    status = child.wait()
                    return status if status in (0, 2) else 1
                count += 1
                if len(header) != 3 or count > _MAX_REQUESTS:
                    return 1
                op = header[0]
                size = int.from_bytes(header[1:], "big")
                if (
                    op not in (1, 2, 3)
                    or size >= MAX_RECORD_BYTES
                    or (op == 3 and size)
                ):
                    return 1
                payload = child.stdout.read(size)
                if len(payload) != size:
                    return 1
                if op == 3:
                    # A voluntary surrender is for the guest's actual lineage.
                    run.surrender()
                else:
                    text = payload.decode("utf-8")
                    if op == 1:
                        channel.check(text, authorize_live)
                    else:
                        channel.dispatch(text, authorize_live)
                child.stdin.write(b"\x00")
                child.stdin.flush()
        except ShieldDenied:
            # Terminal refusal. Neither closing this private pipe nor a lost
            # acknowledgement can refund a write already handed to the sink.
            with suppress(OSError):
                child.stdin.write(b"\x02")
                child.stdin.flush()
            raise
        except (OSError, UnicodeError):
            return 1
        finally:
            terminate()
            watchdog.cancel()
            watchdog.join()
            with suppress(OSError):
                child.stdin.close()
