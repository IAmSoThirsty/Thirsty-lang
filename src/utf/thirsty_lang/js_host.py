"""Runtime support for Node artifacts built with a host-selected TARL policy."""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def list_contract(annotation: str | None) -> str | None:
    """Return the flat writable element type supported by the Node host."""
    if annotation is None or annotation in (
        "Any",
        "Int",
        "Float",
        "Bool",
        "String",
        "Void",
    ):
        return None
    match = re.fullmatch(r"Reservoir\[(Int|Float|Bool|String|Void|Any)\]", annotation)
    if match is None:
        raise ValueError(f"Governed JS does not support annotation {annotation!r}")
    return match.group(1)


def bind_expression(value: str, element: str | None, span: tuple) -> str:
    if element is None:
        return value
    return f"__bindList({value}, {json.dumps(element)}, '{span[0]}:{span[1]}')"


def host_prelude(policy: str) -> str:
    from utf.thirsty_lang.js_policy import validate_js_policy

    validate_js_policy(policy)
    return "const __policy = " + json.dumps(policy) + ";\n" + _NODE_HOST


def launch_verified(artifact: Path, expected: str, authority: str) -> int:
    """Execute the compared bytes. Node never reopens a replaceable script path."""
    if not authority.strip():
        raise ValueError("Governance denied: a nonempty host authority is required")
    code = expected.encode("utf-8")
    with artifact.open("rb") as stream:
        if stream.read(len(code) + 1) != code:
            raise ValueError(
                "JS artifact does not match its source and host-selected policy"
            )
    # Resolve the host tool only in absolute PATH entries, excluding the guest directory.
    executable = "node.exe" if os.name == "nt" else "node"
    node = None
    guest_directories = {Path.cwd(), artifact.resolve().parent}
    for entry in os.get_exec_path():
        directory = Path(entry)
        if directory.is_absolute() and directory.resolve() not in guest_directories:
            node = shutil.which(str(directory / executable))
            if node is not None:
                break
    if node is None:
        raise ValueError("Node.js is required to execute a governed JavaScript build")
    env = dict(
        os.environ, THIRSTY_JS_PYTHON=sys.executable, THIRSTY_JS_AUTHORITY=authority
    )
    # A project-local JS preload must not run ahead of the verified program.
    env.pop("NODE_OPTIONS", None)
    return subprocess.run(
        [node, "--input-type=commonjs", "-"], input=code, env=env, check=False
    ).returncode


_NODE_HOST = r"""
const {spawnSync: __invoke} = require('node:child_process');
const __python = process.env.THIRSTY_JS_PYTHON;
const __authority = process.env.THIRSTY_JS_AUTHORITY;
function __broker(op, text) {
  if (!__python || !__authority || !__authority.trim()) {
    throw Object.assign(new Error('Governance denied: launch with thirsty run-js and a host authority'), {status: 2});
  }
  const request = {op, authority: __authority, policy: __policy};
  if (text !== undefined) request.text = text;
  const result = __invoke(__python, ['-I', '-B', '-m', 'utf.thirsty_lang.js_policy'], {
    input: Buffer.from(JSON.stringify(request), 'utf8'),
    stdio: ['pipe', 'inherit', 'pipe'],
    windowsHide: true,
  });
  if (result.status !== 0 || result.error) {
    const message = result.stderr && result.stderr.toString('utf8').trim();
    throw Object.assign(new Error(message || 'Governance broker unavailable'), {status: result.status === 2 ? 2 : 1});
  }
}

const __contracts = new WeakMap();
function __matches(value, type) {
  switch (type) {
    case 'Any': return true;
    case 'Int': return typeof value === 'bigint';
    case 'Float': return typeof value === 'number' || typeof value === 'bigint';
    case 'String': return typeof value === 'string';
    case 'Bool': return typeof value === 'boolean';
    case 'Void': return value === null;
    default: throw new TypeError('Unknown list contract');
  }
}
function __bindList(list, element, loc) {
  if (!Array.isArray(list)) throw new TypeError(loc + ': typed value requires Reservoir');
  const previous = __contracts.get(list);
  if (previous && previous !== 'Any' && element !== 'Any' && element !== previous) {
    throw new TypeError(loc + ': incompatible writable contracts ' + previous + ' and ' + element);
  }
  if (list.length >= 100000) throw new RangeError(loc + ': mutable contract validation limit exceeded');
  const expected = previous && element === 'Any' ? previous : element;
  if (!list.every(item => __matches(item, expected))) throw new TypeError(loc + ': typed value requires ' + expected);
  __contracts.set(list, expected);
  return list;
}
function __position(index, length, loc) {
  if (typeof index !== 'bigint') throw new TypeError(loc + ': sequence index must be an Int');
  const size = BigInt(length);
  if (index < 0n) index += size;
  if (index < 0n || index >= size) throw new RangeError(loc + ': index out of bounds');
  return Number(index);
}
function __get(sequence, index, loc) {
  if (typeof sequence === 'string') sequence = Array.from(sequence);
  if (!Array.isArray(sequence)) throw new TypeError(loc + ': expected an indexable list or string');
  return sequence[__position(index, sequence.length, loc)];
}
function __set(value, list, index, loc) {
  if (!Array.isArray(list)) throw new TypeError(loc + ': indexed assignment requires a list');
  const slot = __position(index, list.length, loc);
  const expected = __contracts.get(list);
  if (expected && !__matches(value, expected)) throw new TypeError(loc + ': typed value requires ' + expected);
  list[slot] = value;
}
"""
