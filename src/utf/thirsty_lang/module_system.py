"""
Thirsty-Lang Module System
Import resolution, 16 stdlib namespaces, and 16 global builtins.
"""

import hashlib
import hmac as standard_hmac
import json
import os
import secrets
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

# Module cache: store resolved modules by import path
ModuleCache: dict[str, object] = {}


# ============================================================
# Sensitive stdlib capability metadata (single source of truth)
# ============================================================
#
# Maps each sensitive stdlib namespace to the explicit capability *action* of
# every side-effecting function it exposes. Actions are constrained to a closed
# vocabulary — {"read", "write", "network", "execute"} — so the governed-runtime
# capability broker can gate imported stdlib calls without per-call guesswork.
# The interpreter wraps these callables in governed mode and routes each through
# the capability gate with the action declared here.
SENSITIVE_STDLIB_CAPABILITIES: dict[str, dict[str, str]] = {
    "thirst::time": {"now": "read", "epoch_ms": "read", "sleep": "execute"},
    "thirst::crypto": {"random_bytes": "read", "uuid4": "read"},
    "thirst::path": {"absolute": "read", "relative": "read"},
    "thirst::fs": {
        "read_file": "read",
        "exists": "read",
        "list_dir": "read",
        "write_file": "write",
        "mkdir": "write",
        "remove": "write",
    },
    "thirst::http": {
        "get": "network",
        "post": "network",
        "put": "network",
        "delete": "network",
    },
    "thirst::net": {
        "tcp_connect": "network",
        "tcp_listen": "network",
        "tcp_accept": "network",
        "tcp_send": "network",
        "tcp_receive": "network",
        "udp_send": "network",
        "udp_bind": "network",
        "udp_receive": "network",
        "close": "network",
    },
    "thirst::env": {
        "get": "read",
        "all": "read",
        "set": "write",
    },
    "thirst::process": {
        "run": "execute",
        "exit": "execute",
        "args": "read",
        "pid": "read",
    },
    "thirst::log": {
        "info": "write",
        "warn": "write",
        "error": "write",
        "debug": "write",
    },
    "thirst::test": {
        "describe": "write",
        "it": "write",
    },
    "thirst::sqlite": {
        "connect": "write",
        "query": "read",
        "execute": "write",
        "close": "write",
    },
}


# Explicit review of exports that perform no direct ambient operation. These
# are not a claim of immutable/pure values: reservoir/JSON helpers can mutate
# guest containers, and collection/test helpers call their provided callbacks.
# Runtime wrappers retain execution restrictions for those callback paths.
NO_AMBIENT_STDLIB_EXPORTS: dict[str, frozenset[str]] = {
    "thirst::time": frozenset(),
    "thirst::crypto": frozenset(
        {
            "sha256",
            "sign",
            "ed25519_sign",
            "verify",
            "ed25519_verify",
            "public_key",
            "hmac",
            "hmac_sha256",
            "verify_hmac",
        }
    ),
    "thirst::reservoir": frozenset({"size", "push", "pop", "get", "flood"}),
    "thirst::fs": frozenset(),
    "thirst::path": frozenset({"join", "dirname", "basename", "ext"}),
    "thirst::json": frozenset({"parse", "stringify", "get", "set"}),
    "thirst::http": frozenset(),
    "thirst::env": frozenset(),
    "thirst::process": frozenset(),
    "thirst::log": frozenset(),
    "thirst::test": frozenset(
        {"assert_eq", "assert_ne", "assert_true", "assert_raises"}
    ),
    "thirst::collections": frozenset(
        {
            "map",
            "filter",
            "reduce",
            "sort",
            "unique",
            "flatten",
            "zip",
            "dict",
            "keys",
            "values",
            "items",
            "has",
            "with_item",
            "merge",
            "tuple",
            "set",
            "set_union",
            "set_intersection",
            "set_difference",
            "bytes",
            "encode_utf8",
            "decode_utf8",
            "to_list",
            "kind",
            "group_by",
            "sum",
        }
    ),
    "thirst::net": frozenset(),
    "thirst::sqlite": frozenset(),
    "thirst::yaml": frozenset({"parse", "dump"}),
    "thirst::toml": frozenset({"parse", "dump"}),
}


def validate_stdlib_exports(module_path: str, module: object) -> None:
    """Refuse stdlib exports that lack an explicit, consistent classification.

    Validate resolved and cached dictionaries before guest exposure. File module
    exports follow source execution restrictions instead of this stdlib ledger.
    """
    if (
        module_path not in STDLIB_MODULES
        or module_path not in NO_AMBIENT_STDLIB_EXPORTS
    ):
        raise ImportError(f"Unreviewed standard-library namespace: {module_path}")
    effects = SENSITIVE_STDLIB_CAPABILITIES.get(module_path, {})
    no_ambient = NO_AMBIENT_STDLIB_EXPORTS[module_path]
    if (
        not isinstance(effects, dict)
        or not isinstance(no_ambient, frozenset)
        or any(type(name) is not str for name in (*effects, *no_ambient))
        or any(
            type(action) is not str
            or action not in {"read", "write", "network", "execute"}
            for action in effects.values()
        )
        or set(effects) & no_ambient
    ):
        raise ImportError(f"Invalid standard-library classification: {module_path}")
    if not isinstance(module, dict) or any(type(name) is not str for name in module):
        raise ImportError(f"Invalid standard-library export dictionary: {module_path}")
    expected = set(effects) | no_ambient
    if set(module) != expected:
        raise ImportError(
            f"Unreviewed or missing standard-library exports: {module_path}"
        )
    if any(not callable(value) for value in module.values()):
        raise ImportError(f"Standard-library exports must be callable: {module_path}")


# ============================================================
# Stdlib Namespace Implementations
# ============================================================


def _make_time_module() -> dict:
    """thirst::time — Time utilities."""

    def now() -> str:
        return datetime.now(UTC).isoformat()

    def epoch_ms() -> int:
        return int(time.time() * 1000)

    def sleep(seconds: float) -> None:
        time.sleep(seconds)

    return {
        "now": now,
        "epoch_ms": epoch_ms,
        "sleep": sleep,
    }


def _make_crypto_module() -> dict:
    """SHA-256, HMAC-SHA256, Ed25519, and operating-system entropy.

    Signing keys are hex-encoded 32-byte Ed25519 seeds; public keys are
    hex-encoded 32-byte values. Signatures carry an explicit algorithm prefix.
    The previous concatenation digests are not signatures and are not accepted.
    """
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )

    def sha256(data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    def sign(data: str, key: str) -> str:
        private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(key))
        return "ed25519:" + private_key.sign(data.encode("utf-8")).hex()

    def public_key(key: str) -> str:
        private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(key))
        return (
            private_key.public_key()
            .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
            .hex()
        )

    def verify(data: str, signature: str, key: str) -> bool:
        try:
            verifier = Ed25519PublicKey.from_public_bytes(bytes.fromhex(key))
            if not signature.startswith("ed25519:"):
                return False
            verifier.verify(bytes.fromhex(signature[8:]), data.encode("utf-8"))
            return True
        except (ValueError, InvalidSignature):
            return False

    def hmac(key: str, data: str) -> str:
        if not key:
            raise ValueError("HMAC requires a nonempty key")
        return standard_hmac.new(
            key.encode(), data.encode(), hashlib.sha256
        ).hexdigest()

    def verify_hmac(key: str, data: str, mac: str) -> bool:
        expected = hmac(key, data)
        if not isinstance(mac, str) or not mac.isascii():
            return False
        return standard_hmac.compare_digest(expected, mac)

    def random_bytes(n: int) -> str:
        if type(n) is not int or not 0 <= n <= 1024 * 1024:
            raise ValueError("random_bytes length must be an integer from 0 to 1048576")
        return secrets.token_bytes(n).hex()

    def uuid4() -> str:
        return str(uuid.uuid4())

    return {
        "sha256": sha256,
        "sign": sign,
        "ed25519_sign": sign,
        "verify": verify,
        "ed25519_verify": verify,
        "public_key": public_key,
        "hmac": hmac,
        "hmac_sha256": hmac,
        "verify_hmac": verify_hmac,
        "random_bytes": random_bytes,
        "uuid4": uuid4,
    }


def _make_reservoir_module() -> dict:
    """thirst::reservoir — Reservoir (list) operations."""

    def size(r: list) -> int:
        if not isinstance(r, list):
            raise TypeError("reservoir.size requires a list")
        return len(r)

    def push(r: list, v: object) -> int:
        return _list_push(r, v)

    def pop(r: list) -> object:
        return _list_pop(r)

    def get(r: list, i: int) -> object:
        if not isinstance(r, list) or type(i) is not int:
            raise TypeError("reservoir.get requires a list and integer index")
        return r[i] if 0 <= i < len(r) else None

    def flood(r: list, v: object) -> list:
        return _list_flood(r, v)

    return {
        "size": size,
        "push": push,
        "pop": pop,
        "get": get,
        "flood": flood,
    }


def _make_fs_module() -> dict:
    """thirst::fs — File system operations."""

    def read_file(path: str, max_bytes: int | None = None) -> str:
        """Read UTF-8 text, optionally bounding bytes before allocation/parsing."""
        if max_bytes is not None and (
            type(max_bytes) is not int or not 0 <= max_bytes <= 64 * 1024 * 1024
        ):
            raise ValueError("max_bytes must be an integer from 0 to 67108864")
        with open(path, "rb") as f:
            data = f.read() if max_bytes is None else f.read(max_bytes + 1)
        if max_bytes is not None and len(data) > max_bytes:
            raise ValueError("read_file input exceeds max_bytes")
        return data.decode("utf-8")

    def write_file(path: str, data: str) -> int:
        with open(path, "w") as f:
            return f.write(data)

    def exists(path: str) -> bool:
        return os.path.exists(path)

    def list_dir(path: str) -> list[str]:
        return os.listdir(path)

    def mkdir(path: str) -> bool:
        os.makedirs(path, exist_ok=True)
        return True

    def remove(path: str) -> bool:
        if os.path.isfile(path):
            os.remove(path)
            return True
        elif os.path.isdir(path):
            os.rmdir(path)
            return True
        return False

    return {
        "read_file": read_file,
        "write_file": write_file,
        "exists": exists,
        "list_dir": list_dir,
        "mkdir": mkdir,
        "remove": remove,
    }


def _make_path_module() -> dict:
    """thirst::path — Path manipulation."""

    def join(*parts: str) -> str:
        return os.path.join(*parts)

    def dirname(p: str) -> str:
        return os.path.dirname(p)

    def basename(p: str) -> str:
        return os.path.basename(p)

    def ext(p: str) -> str:
        _, extension = os.path.splitext(p)
        return extension

    def absolute(p: str) -> str:
        return os.path.abspath(p)

    def relative(p: str, start: str = ".") -> str:
        return os.path.relpath(p, start)

    return {
        "join": join,
        "dirname": dirname,
        "basename": basename,
        "ext": ext,
        "absolute": absolute,
        "relative": relative,
    }


def _make_json_module() -> dict:
    """thirst::json — JSON parsing and serialization."""
    import math

    def finite_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("JSON numbers must be finite")
        return parsed

    def reject_constant(value: str) -> object:
        raise ValueError(f"Invalid JSON constant: {value}")

    def parse(s: str) -> object:
        return json.loads(
            s,
            object_pairs_hook=_unique_json_object,
            parse_float=finite_float,
            parse_constant=reject_constant,
        )

    def stringify(v: object) -> str:
        def validate(value: object) -> None:
            if isinstance(value, dict):
                if any(not isinstance(key, str) for key in value):
                    raise TypeError("JSON object keys must be strings")
                for item in value.values():
                    validate(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    validate(item)

        validate(v)
        return json.dumps(v, allow_nan=False)

    def get(d: dict, k: str, default=None) -> object:
        return d.get(k, default)

    def set(d: dict, k: str, v: object) -> dict:
        d[k] = v
        return d

    return {
        "parse": parse,
        "stringify": stringify,
        "get": get,
        "set": set,
    }


def _make_http_module() -> dict:
    """HTTP(S) client with byte limits, verified TLS, and explicit failures.

    Timeout bounds socket inactivity, not DNS lookup or total elapsed response
    time. Redirects require a separate request and capability decision.
    """
    import math
    import urllib.error
    import urllib.parse
    import urllib.request

    class ExplicitRedirects(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise urllib.error.HTTPError(
                req.full_url, code, "Redirect requires an explicit request", headers, fp
            )

    def request(
        method: str, url: str, data: object, timeout: float, max_bytes: int
    ) -> str:
        if not isinstance(url, str):
            raise TypeError("HTTP URL must be a string")
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("Only absolute HTTP and HTTPS URLs are supported")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials embedded in HTTP URLs are unsupported")
        if (
            type(timeout) not in (int, float)
            or not math.isfinite(timeout)
            or not 0 < timeout <= 60
        ):
            raise ValueError(
                "HTTP timeout must be greater than 0 and at most 60 seconds"
            )
        if type(max_bytes) is not int or not 0 <= max_bytes <= 64 * 1024 * 1024:
            raise ValueError("max_bytes must be an integer from 0 to 67108864")
        encoded = None
        headers = {}
        if method in ("POST", "PUT"):
            # Preserve false/zero/empty-container payloads; only None means no
            # body. Bound the encoded body independently of response limits.
            if data is None:
                encoded = b""
            else:
                encoded = _make_json_module()["stringify"](data).encode("utf-8")
                if len(encoded) > 1024 * 1024:
                    raise ValueError("HTTP request body exceeds the 1 MiB limit")
            headers["Content-Type"] = "application/json; charset=utf-8"
        req = urllib.request.Request(url, data=encoded, headers=headers, method=method)
        opener = urllib.request.build_opener(ExplicitRedirects())
        try:
            with opener.open(req, timeout=float(timeout)) as response:
                body = response.read(max_bytes + 1)
                if len(body) > max_bytes:
                    raise ValueError("HTTP response exceeds max_bytes")
                return str(body.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            exc.close()
            raise

    def get(url: str, timeout: float = 10, max_bytes: int = 1024 * 1024) -> str:
        return request("GET", url, None, timeout, max_bytes)

    def post(
        url: str, data: object = None, timeout: float = 10, max_bytes: int = 1024 * 1024
    ) -> str:
        return request("POST", url, data, timeout, max_bytes)

    def put(
        url: str, data: object = None, timeout: float = 10, max_bytes: int = 1024 * 1024
    ) -> str:
        return request("PUT", url, data, timeout, max_bytes)

    def delete(url: str, timeout: float = 10, max_bytes: int = 1024 * 1024) -> str:
        return request("DELETE", url, None, timeout, max_bytes)

    return {"get": get, "post": post, "put": put, "delete": delete}


def _make_env_module() -> dict:
    """thirst::env — Environment variables."""

    def get(k: str, default: str = "") -> str:
        return os.environ.get(k, default)

    def set(k: str, v: str) -> None:
        os.environ[k] = v

    def all() -> dict:
        return dict(os.environ)

    return {
        "get": get,
        "set": set,
        "all": all,
    }


def _make_process_module() -> dict:
    """Explicit argv execution with bounded captured output and direct-child timeout.

    No implicit shell or batch-file interpretation. This is a process adapter,
    not a sandbox or descendant-process containment mechanism.
    """
    import math
    import shutil
    import subprocess
    import sys

    def available_bytes(pipe) -> int:
        if sys.platform == "win32":
            import ctypes
            import msvcrt
            from ctypes import wintypes

            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            peek = kernel.PeekNamedPipe
            peek.argtypes = [
                wintypes.HANDLE,
                wintypes.LPVOID,
                wintypes.DWORD,
                wintypes.LPVOID,
                ctypes.POINTER(wintypes.DWORD),
                wintypes.LPVOID,
            ]
            peek.restype = wintypes.BOOL
            available = wintypes.DWORD()
            if not peek(
                msvcrt.get_osfhandle(pipe.fileno()),
                None,
                0,
                None,
                ctypes.byref(available),
                None,
            ):
                error = ctypes.get_last_error()
                if error == 109:  # ERROR_BROKEN_PIPE: child closed its output.
                    return 0
                raise ctypes.WinError(error)
            return int(available.value)
        import select

        return 65536 if select.select([pipe], [], [], 0)[0] else 0

    def run(
        argv: list[str] | tuple[str, ...],
        timeout: float = 30,
        max_output_bytes: int = 1024 * 1024,
    ) -> str:
        if not isinstance(argv, (list, tuple)) or not argv or len(argv) > 1024:
            raise TypeError(
                "process.run requires a nonempty argv array (at most 1024 arguments); command strings are unsupported"
            )
        if (
            any(not isinstance(arg, str) or "\x00" in arg for arg in argv)
            or not argv[0]
        ):
            raise TypeError("argv entries must be strings without null bytes")
        if sum(len(arg) for arg in argv) > 1024 * 1024:
            raise ValueError("argv exceeds the 1 MiB character limit")
        if (
            type(timeout) not in (int, float)
            or not math.isfinite(timeout)
            or not 0 < timeout <= 60
        ):
            raise ValueError(
                "process timeout must be greater than 0 and at most 60 seconds"
            )
        if (
            type(max_output_bytes) is not int
            or not 0 <= max_output_bytes <= 64 * 1024 * 1024
        ):
            raise ValueError("max_output_bytes must be an integer from 0 to 67108864")
        executable = shutil.which(argv[0]) or argv[0]
        if sys.platform == "win32" and executable.lower().endswith((".bat", ".cmd")):
            raise ValueError(
                "Batch files require an explicit shell executable; implicit shell execution is disabled"
            )
        command = [executable, *argv[1:]]
        deadline = time.monotonic() + timeout
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NO_WINDOW
        process = subprocess.Popen(
            command,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            creationflags=creation_flags,
        )
        output = bytearray()
        pipe = process.stdout
        if pipe is None:
            process.kill()
            process.wait()
            raise RuntimeError("Process output pipe unavailable")
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(
                        command[:1], timeout, output=bytes(output)
                    )
                eof = False
                available = available_bytes(pipe)
                if available:
                    chunk = os.read(
                        pipe.fileno(),
                        min(available, 65536, max_output_bytes - len(output) + 1),
                    )
                    output.extend(chunk)
                    if len(output) > max_output_bytes:
                        raise ValueError("Process output exceeds max_output_bytes")
                    if chunk:
                        continue
                    eof = True
                returncode = process.poll()
                if returncode is not None:
                    # Once the launched process exits and available bytes are
                    # drained, do not wait on inherited descendant pipe handles.
                    if not eof and available_bytes(pipe):
                        continue
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(
                        command[:1], timeout, output=bytes(output)
                    )
                time.sleep(min(0.005, remaining))
            if returncode:
                raise subprocess.CalledProcessError(
                    returncode, command[:1], output=bytes(output)
                )
            return output.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=1)
            pipe.close()

    def exit(code: int = 0) -> None:
        if type(code) is not int:
            raise TypeError("exit status must be an Int")
        sys.exit(code)

    def args() -> list[str]:
        return list(sys.argv)

    def pid() -> int:
        return os.getpid()

    return {"run": run, "exit": exit, "args": args, "pid": pid}


def _make_log_module() -> dict:
    """thirst::log — Logging utilities."""

    def info(msg: str) -> None:
        print(f"[INFO] {msg}")

    def warn(msg: str) -> None:
        print(f"[WARN] {msg}")

    def error(msg: str) -> None:
        print(f"[ERROR] {msg}")

    def debug(msg: str) -> None:
        print(f"[DEBUG] {msg}")

    return {
        "info": info,
        "warn": warn,
        "error": error,
        "debug": debug,
    }


def _make_test_module() -> dict:
    """thirst::test — Testing utilities."""

    def assert_eq(a: object, b: object) -> None:
        if a != b:
            raise AssertionError(f"AssertionError: {a!r} != {b!r}")

    def assert_ne(a: object, b: object) -> None:
        if a == b:
            raise AssertionError(f"AssertionError: {a!r} == {b!r}")

    def assert_true(v: object) -> None:
        if not v:
            raise AssertionError(f"AssertionError: {v!r} is not truthy")

    def assert_raises(fn: Callable[..., Any], *args, **kwargs) -> None:
        from utf.thirsty_lang.interpreter import GovernanceViolation

        try:
            fn(*args, **kwargs)
        except GovernanceViolation:
            raise
        except Exception:
            return
        raise AssertionError("Expected exception but none raised")

    describe_results = {}

    def describe(name: str) -> None:
        describe_results["current"] = name
        print(f"\n  {name}")

    def it(name: str) -> None:
        print(f"    ✓ {name}")

    return {
        "assert_eq": assert_eq,
        "assert_ne": assert_ne,
        "assert_true": assert_true,
        "assert_raises": assert_raises,
        "describe": describe,
        "it": it,
    }


def _hashable_guest(value: object) -> None:
    """Restrict collection keys to immutable guest values with stable equality."""
    import math

    if value is None or type(value) in (bool, int, str, bytes):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("Collection keys must be finite")
        return
    if isinstance(value, tuple):
        for item in value:
            _hashable_guest(item)
        return
    if isinstance(value, _OrderedSet):
        return
    raise TypeError("Collection keys and set members must be immutable guest values")


class _OrderedSet:
    """Immutable set membership with deterministic first-occurrence iteration."""

    __slots__ = ("__values", "__members")

    def __init__(self, values):
        ordered: dict[Any, None] = {}
        for value in values:
            _hashable_guest(value)
            ordered[value] = None
        self.__values = tuple(ordered)
        self.__members = frozenset(ordered)

    def __iter__(self):
        return iter(self.__values)

    def __len__(self) -> int:
        return len(self.__values)

    def __contains__(self, value: object) -> bool:
        _hashable_guest(value)
        return value in self.__members

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _OrderedSet) and self.__members == other.__members

    def __hash__(self) -> int:
        return hash(self.__members)

    def __repr__(self) -> str:
        return "set(" + repr(list(self.__values)) + ")"


def _make_collections_module() -> dict:
    """Validated collections, functional transforms, and explicit binary values.

    Dictionary and set iteration preserves insertion order. Copy operations are
    shallow; tuples and sets prevent structural mutation of those containers.
    """
    import builtins
    import math
    from functools import reduce as _reduce

    no_initial = object()

    def sequence(value):
        if not isinstance(value, (list, tuple, bytes, _OrderedSet)):
            raise TypeError("Expected a list, tuple, bytes, or ordered set")
        return value

    def mapping(value):
        if not isinstance(value, dict):
            raise TypeError("Expected a dictionary")
        return value

    def callback(fn):
        if not callable(fn):
            raise TypeError("Expected a callable")
        return fn

    def map(fn: Callable[..., Any], values) -> list:
        callback(fn)
        return [fn(item) for item in sequence(values)]

    def filter(fn: Callable[..., Any], values) -> list:
        callback(fn)
        return [item for item in sequence(values) if fn(item)]

    def reduce(fn: Callable[..., Any], values, init: object = no_initial) -> object:
        callback(fn)
        items = sequence(values)
        if init is no_initial:
            return _reduce(fn, items)
        return _reduce(fn, items, init)

    def sort(
        values, reverse: bool = False, key: Callable[..., Any] | None = None
    ) -> list:
        if type(reverse) is not bool:
            raise TypeError("reverse must be a Bool")
        if key is not None:
            callback(key)
        return sorted(sequence(values), reverse=reverse, key=key)

    def unique(values) -> list:
        return list(_OrderedSet(sequence(values)))

    def flatten(values) -> list:
        result = []
        for value in sequence(values):
            if isinstance(value, (list, tuple)):
                result.extend(flatten(value))
            else:
                result.append(value)
        return result

    def zip(*values) -> list:
        return list(builtins.zip(*(sequence(value) for value in values), strict=False))

    def make_dict(pairs=()) -> dict:
        result = {}
        for pair in sequence(pairs):
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise ValueError("Dictionary entries must be key/value pairs")
            key, value = pair
            _hashable_guest(key)
            if key in result:
                raise ValueError(f"Duplicate dictionary key: {key!r}")
            result[key] = value
        return result

    def keys(value) -> list:
        return list(mapping(value))

    def values(value) -> list:
        return list(mapping(value).values())

    def items(value) -> list:
        return list(mapping(value).items())

    def has(value, key) -> bool:
        _hashable_guest(key)
        return key in mapping(value)

    def with_item(value, key, item) -> dict:
        _hashable_guest(key)
        result = dict(mapping(value))
        result[key] = item
        return result

    def merge(left, right, overwrite: bool = False) -> dict:
        if type(overwrite) is not bool:
            raise TypeError("overwrite must be a Bool")
        result = dict(mapping(left))
        for key, value in mapping(right).items():
            _hashable_guest(key)
            if not overwrite and key in result:
                raise ValueError(f"Duplicate dictionary key: {key!r}")
            result[key] = value
        return result

    def make_tuple(value=()) -> tuple:
        return tuple(sequence(value))

    def make_set(value=()) -> _OrderedSet:
        return _OrderedSet(sequence(value))

    def set_pair(left, right):
        if not isinstance(left, _OrderedSet) or not isinstance(right, _OrderedSet):
            raise TypeError("Set operations require ordered set values")

    def set_union(left, right) -> _OrderedSet:
        set_pair(left, right)
        return _OrderedSet((*left, *right))

    def set_intersection(left, right) -> _OrderedSet:
        set_pair(left, right)
        return _OrderedSet(value for value in left if value in right)

    def set_difference(left, right) -> _OrderedSet:
        set_pair(left, right)
        return _OrderedSet(value for value in left if value not in right)

    def make_bytes(value=()) -> bytes:
        items = sequence(value)
        if any(type(item) is not int or not 0 <= item <= 255 for item in items):
            raise ValueError("Bytes require integers from 0 to 255")
        return bytes(items)

    def encode_utf8(value: str) -> bytes:
        if not isinstance(value, str):
            raise TypeError("encode_utf8 requires a String")
        return value.encode("utf-8")

    def decode_utf8(value) -> str:
        return make_bytes(value).decode("utf-8", errors="strict")

    def to_list(value) -> list:
        return list(sequence(value))

    def kind(value: object) -> str:
        names = {
            type(None): "none",
            bool: "bool",
            int: "int",
            float: "float",
            str: "string",
            list: "list",
            dict: "dict",
            tuple: "tuple",
            bytes: "bytes",
            _OrderedSet: "set",
        }
        return names.get(type(value), "function" if callable(value) else "object")

    def group_by(fn: Callable[..., Any], value) -> dict:
        callback(fn)
        groups: dict[Any, list] = {}
        for item in sequence(value):
            key = fn(item)
            _hashable_guest(key)
            groups.setdefault(key, []).append(item)
        return groups

    def sum(value) -> int | float:
        result: int | float = 0
        for item in sequence(value):
            if type(item) not in (int, float):
                raise TypeError("sum requires finite Int or Float values")
            if type(item) is float and not math.isfinite(item):
                raise ValueError("sum requires finite numbers")
            result += item
            if isinstance(result, float) and not math.isfinite(result):
                raise ValueError("sum produced a non-finite result")
        return result

    return {
        "map": map,
        "filter": filter,
        "reduce": reduce,
        "sort": sort,
        "unique": unique,
        "flatten": flatten,
        "zip": zip,
        "dict": make_dict,
        "keys": keys,
        "values": values,
        "items": items,
        "has": has,
        "with_item": with_item,
        "merge": merge,
        "tuple": make_tuple,
        "set": make_set,
        "set_union": set_union,
        "set_intersection": set_intersection,
        "set_difference": set_difference,
        "bytes": make_bytes,
        "encode_utf8": encode_utf8,
        "decode_utf8": decode_utf8,
        "to_list": to_list,
        "kind": kind,
        "group_by": group_by,
        "sum": sum,
    }


def _make_net_module() -> dict:
    """Bounded TCP/UDP sockets with opaque handles and explicit lifecycle.

    Addresses must be numeric IPv4/IPv6 literals: hostname resolution is not
    claimed to obey socket deadlines. Receive returns a list of byte integers,
    preserving arbitrary binary data and split UTF-8 sequences. Sent counts
    report local transport acceptance, never remote application completion.
    """
    import ipaddress
    import math
    import socket
    import threading
    from contextlib import contextmanager

    sockets: dict[str, tuple[socket.socket, str, Any, float]] = {}
    registry_lock = threading.RLock()
    max_transfer = 1024 * 1024
    max_datagram = 65507

    def bounded_int(value: int, minimum: int, maximum: int, label: str) -> int:
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError(f"{label} must be an integer from {minimum} to {maximum}")
        return value

    def address(host: str, port: int, *, binding: bool = False):
        if not isinstance(host, str):
            raise TypeError("host must be a numeric IP address string")
        try:
            ip = ipaddress.ip_address(host)
        except ValueError as exc:
            raise ValueError(
                "Numeric IPv4/IPv6 addresses are required; hostname resolution is unavailable"
            ) from exc
        bounded_int(port, 0 if binding else 1, 65535, "port")
        return socket.AF_INET6 if ip.version == 6 else socket.AF_INET, (str(ip), port)

    def deadline(timeout: float) -> float:
        if (
            type(timeout) not in (int, float)
            or not math.isfinite(timeout)
            or not 0 < timeout <= 60
        ):
            raise ValueError(
                "timeout must be a finite number greater than 0 and at most 60 seconds"
            )
        return float(timeout)

    def payload(data: str | list[int] | bytes, maximum: int = max_transfer) -> bytes:
        if isinstance(data, str):
            # Check characters first to reject clearly oversized inputs before
            # allocating a potentially larger UTF-8 representation.
            if len(data) > maximum:
                raise ValueError("Network payload exceeds transfer limit")
            encoded = data.encode("utf-8")
        elif isinstance(data, bytes):
            encoded = data
        elif isinstance(data, list):
            if len(data) > maximum:
                raise ValueError("Network payload exceeds transfer limit")
            if any(type(value) is not int or not 0 <= value <= 255 for value in data):
                raise ValueError("Byte arrays must contain integers from 0 to 255")
            encoded = bytes(data)
        else:
            raise TypeError(
                "Network payload must be UTF-8 text, bytes, or a list of bytes"
            )
        if len(encoded) > maximum:
            raise ValueError("Network payload exceeds transfer limit")
        return encoded

    def register(sock: socket.socket, kind: str) -> str:
        seconds = sock.gettimeout()
        if seconds is None:
            raise ValueError("Network handles require an explicit timeout")
        with registry_lock:
            if len(sockets) >= 256:
                sock.close()
                raise OSError("Network handle limit (256) reached")
            handle = "net_" + secrets.token_hex(32)
            sockets[handle] = (sock, kind, threading.RLock(), seconds)
            return handle

    def lookup(handle: str, kind: str):
        if not isinstance(handle, str):
            raise TypeError("Network handle must be a string")
        with registry_lock:
            record = sockets.get(handle)
        if record is None:
            raise ValueError("Unknown or closed network handle")
        if record[1] != kind:
            raise ValueError(f"Operation requires a {kind} handle")
        return record

    @contextmanager
    def operation(handle: str, kind: str):
        sock, _, lock, seconds = lookup(handle, kind)
        start = time.monotonic()
        if not lock.acquire(timeout=seconds):
            raise TimeoutError("Network operation timed out waiting for its handle")
        try:
            remaining = seconds - (time.monotonic() - start)
            if remaining <= 0:
                raise TimeoutError("Network operation deadline expired")
            if sock.fileno() < 0:
                raise ValueError("Unknown or closed network handle")
            sock.settimeout(remaining)
            yield sock, seconds
        finally:
            if sock.fileno() >= 0:
                sock.settimeout(seconds)
            lock.release()

    def tcp_connect(host: str, port: int, timeout: float = 10) -> dict:
        family, endpoint = address(host, port)
        seconds = deadline(timeout)
        sock = socket.socket(family, socket.SOCK_STREAM)
        try:
            sock.settimeout(seconds)
            sock.connect(endpoint)
            handle = register(sock, "tcp")
        except BaseException:
            sock.close()
            raise
        return {
            "type": "tcp",
            "host": endpoint[0],
            "port": port,
            "connected": True,
            "handle": handle,
        }

    def tcp_listen(
        port: int, host: str = "127.0.0.1", backlog: int = 16, timeout: float = 10
    ) -> dict:
        family, endpoint = address(host, port, binding=True)
        seconds = deadline(timeout)
        bounded_int(backlog, 1, 128, "backlog")
        sock = socket.socket(family, socket.SOCK_STREAM)
        try:
            sock.settimeout(seconds)
            sock.bind(endpoint)
            sock.listen(backlog)
            handle = register(sock, "listener")
        except BaseException:
            sock.close()
            raise
        return {
            "type": "tcp_listener",
            "host": endpoint[0],
            "port": sock.getsockname()[1],
            "listening": True,
            "handle": handle,
        }

    def tcp_accept(handle: str) -> dict:
        with operation(handle, "listener") as (listener, seconds):
            accepted, peer = listener.accept()
            try:
                accepted.settimeout(seconds)
                child = register(accepted, "tcp")
            except BaseException:
                accepted.close()
                raise
        return {
            "type": "tcp",
            "host": peer[0],
            "port": peer[1],
            "connected": True,
            "handle": child,
        }

    def tcp_send(handle: str, data: str | list[int] | bytes) -> dict:
        encoded = payload(data)
        with operation(handle, "tcp") as (sock, _):
            sock.sendall(encoded)
        return {"sent": len(encoded)}

    def tcp_receive(handle: str, max_bytes: int = 65536) -> dict:
        bounded_int(max_bytes, 1, max_transfer, "max_bytes")
        with operation(handle, "tcp") as (sock, _):
            data = sock.recv(max_bytes)
        return {"data": list(data), "received": len(data), "eof": not data}

    def udp_bind(port: int, host: str = "127.0.0.1", timeout: float = 10) -> dict:
        family, endpoint = address(host, port, binding=True)
        seconds = deadline(timeout)
        sock = socket.socket(family, socket.SOCK_DGRAM)
        try:
            sock.settimeout(seconds)
            sock.bind(endpoint)
            handle = register(sock, "udp")
        except BaseException:
            sock.close()
            raise
        return {
            "type": "udp_listener",
            "host": endpoint[0],
            "port": sock.getsockname()[1],
            "listening": True,
            "handle": handle,
        }

    def udp_send(
        host: str, port: int, data: str | list[int] | bytes, timeout: float = 10
    ) -> dict:
        family, endpoint = address(host, port)
        seconds = deadline(timeout)
        encoded = payload(data, max_datagram)
        with socket.socket(family, socket.SOCK_DGRAM) as sock:
            sock.settimeout(seconds)
            sent = sock.sendto(encoded, endpoint)
        return {"type": "udp", "host": endpoint[0], "port": port, "sent": sent}

    def udp_receive(handle: str, max_bytes: int = max_datagram) -> dict:
        bounded_int(max_bytes, 1, max_datagram, "max_bytes")
        with operation(handle, "udp") as (sock, _):
            # One extra byte detects truncation instead of returning incomplete
            # data as a successful full datagram. Windows may raise WSAEMSGSIZE.
            data, peer = sock.recvfrom(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("UDP datagram exceeds max_bytes; datagram discarded")
        return {
            "data": list(data),
            "received": len(data),
            "host": peer[0],
            "port": peer[1],
        }

    def close(handle: str) -> bool:
        if not isinstance(handle, str):
            raise TypeError("Network handle must be a string")
        with registry_lock:
            record = sockets.get(handle)
        if record is None:
            return False
        sock, kind, lock, seconds = record
        if not lock.acquire(timeout=seconds):
            raise TimeoutError(
                "Closing network handle timed out waiting for active operation"
            )
        try:
            with registry_lock:
                if sockets.pop(handle, None) is None:
                    return False
            sock.close()
            return True
        finally:
            lock.release()

    return {
        "tcp_connect": tcp_connect,
        "tcp_listen": tcp_listen,
        "tcp_accept": tcp_accept,
        "tcp_send": tcp_send,
        "tcp_receive": tcp_receive,
        "udp_send": udp_send,
        "udp_bind": udp_bind,
        "udp_receive": udp_receive,
        "close": close,
    }


def _make_sqlite_module() -> dict:
    """thirst::sqlite — SQLite database operations (built-in sqlite3)."""
    import sqlite3
    import threading

    _connections: dict[str, tuple[sqlite3.Connection, Any]] = {}
    _registry_lock = threading.RLock()
    # Deny unknown functions as well as extension loading: a SELECT may call
    # a function with external effects. These are SQLite's built-in readers.
    read_functions = frozenset(
        "abs avg char coalesce concat concat_ws count format glob group_concat "
        "hex ifnull iif instr julianday length like likelihood likely lower "
        "ltrim max min nullif printf quote replace round rtrim sign soundex "
        "strftime substr substring sum time date datetime total trim typeof "
        "unicode unixepoch unlikely upper zeroblob json json_array json_extract "
        "json_object json_quote json_type json_valid json_array_length "
        "json_group_array json_group_object rank dense_rank row_number lag lead "
        "first_value last_value nth_value ntile percent_rank cume_dist".split()
    )

    def authorizer(read_only: bool):
        def authorize(action, arg1, arg2, database, trigger):
            if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH):
                return sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_FUNCTION:
                name = (arg2 or "").lower()
                if name == "load_extension" or (
                    read_only and name not in read_functions
                ):
                    return sqlite3.SQLITE_DENY
            if not read_only or action in (
                sqlite3.SQLITE_SELECT,
                sqlite3.SQLITE_READ,
                sqlite3.SQLITE_RECURSIVE,
                sqlite3.SQLITE_FUNCTION,
            ):
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY

        return authorize

    def connection(conn_id: str):
        with _registry_lock:
            record = _connections.get(conn_id)
        if record is None:
            raise ValueError(f"Connection not found: {conn_id}")
        return record

    def connect(path: str) -> str:
        conn_id = "sqlite_" + secrets.token_hex(32)
        # No statement cache: authorizers must run for every operation even if
        # identical SQL was previously compiled with broader permissions.
        conn = sqlite3.connect(path, check_same_thread=False, cached_statements=0)
        conn.set_authorizer(authorizer(False))
        with _registry_lock:
            _connections[conn_id] = (conn, threading.RLock())
        return conn_id

    def query(conn_id: str, sql: str, params: list | dict | tuple = ()) -> list:
        conn, lock = connection(conn_id)
        with lock:
            # The lock covers preparation AND stepping/fetching; another call
            # cannot restore write permissions while a query is still running.
            conn.set_authorizer(authorizer(True))
            try:
                cursor = conn.execute(sql, params)
                columns = (
                    [desc[0] for desc in cursor.description]
                    if cursor.description
                    else []
                )
                return [
                    dict(zip(columns, row, strict=True)) for row in cursor.fetchall()
                ]
            finally:
                conn.set_authorizer(authorizer(False))

    def execute(conn_id: str, sql: str, params: list | dict | tuple = ()) -> dict:
        conn, lock = connection(conn_id)
        with lock:
            try:
                cursor = conn.execute(sql, params)
                conn.commit()
                return {"rows_affected": cursor.rowcount}
            except Exception:
                conn.rollback()
                raise

    def close(conn_id: str) -> bool:
        with _registry_lock:
            record = _connections.pop(conn_id, None)
        if record:
            conn, lock = record
            with lock:
                conn.close()
            return True
        return False

    return {
        "connect": connect,
        "query": query,
        "execute": execute,
        "close": close,
    }


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate key: {key}")
        result[key] = value
    return result


def _make_yaml_module() -> dict:
    """A strict YAML 1.2 subset: JSON or a flat scalar mapping.

    Nested block YAML, tags, anchors, aliases, folded strings, and ambiguous
    scalars are rejected. dump emits JSON, which is a YAML 1.2 subset.
    """
    import math
    import re

    def scalar(value: str) -> object:
        if value.startswith('"'):
            parsed = json.loads(value)
            if not isinstance(parsed, str):
                raise ValueError("Expected a quoted YAML string")
            return parsed
        if value.startswith("'"):
            if not re.fullmatch(r"'(?:[^']|'')*'", value):
                raise ValueError("Invalid YAML quoted string")
            return value[1:-1].replace("''", "'")
        if value in ("true", "false", "null", "~"):
            return {"true": True, "false": False, "null": None, "~": None}[value]
        if re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", value):
            number = json.loads(value)
            if isinstance(number, float) and not math.isfinite(number):
                raise ValueError("Non-finite YAML number")
            return number
        if not value or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9 ./-]*", value):
            raise ValueError("Unsupported or ambiguous YAML scalar; use quoted JSON")
        return value

    def finite_float(value: str) -> float:
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("Non-finite YAML number")
        return result

    def reject_constant(value: str) -> object:
        raise ValueError(f"Unsupported YAML constant: {value}")

    def parse(s: str) -> object:
        stripped = s.strip()
        if stripped and (
            stripped[0] in '{["-0123456789' or stripped in ("true", "false", "null")
        ):
            return json.loads(
                stripped,
                object_pairs_hook=_unique_json_object,
                parse_constant=reject_constant,
                parse_float=finite_float,
            )
        result = {}
        for line in s.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if line[0].isspace() or ": " not in line:
                raise ValueError("Only flat YAML scalar mappings or JSON are supported")
            key, value = line.split(": ", 1)
            if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9-]*", key):
                raise ValueError("Unsupported YAML key; use JSON for complex keys")
            if key in result:
                raise ValueError(f"Duplicate key: {key}")
            result[key] = scalar(value.strip())
        return result

    def dump(v: object) -> str:
        def validate(value: object) -> None:
            if isinstance(value, dict):
                if any(not isinstance(key, str) for key in value):
                    raise TypeError("YAML JSON subset requires string mapping keys")
                for item in value.values():
                    validate(item)
            elif isinstance(value, list):
                for item in value:
                    validate(item)
            elif value is not None and type(value) not in (str, int, float, bool):
                raise TypeError("Unsupported YAML value")

        validate(v)
        return json.dumps(v, ensure_ascii=False, allow_nan=False)

    return {"parse": parse, "dump": dump}


def dump_toml(data: dict) -> str:
    """Serialize TOML values with explicit rejection of unsupported types."""
    import re
    import tomllib
    from datetime import date
    from datetime import time as datetime_time

    def key(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("TOML keys must be strings")
        return (
            value
            if re.fullmatch(r"[A-Za-z0-9_-]+", value)
            else json.dumps(value, ensure_ascii=False)
        )

    def scalar(value: object) -> str:
        if isinstance(value, str):
            return json.dumps(value, ensure_ascii=False)
        if type(value) is bool:
            return "true" if value else "false"
        if type(value) in (int, float):
            return repr(value)
        if isinstance(value, (datetime, date, datetime_time)):
            return value.isoformat()
        if isinstance(value, list):
            return "[" + ", ".join(scalar(item) for item in value) + "]"
        if isinstance(value, dict):
            return (
                "{ "
                + ", ".join(f"{key(k)} = {scalar(v)}" for k, v in value.items())
                + " }"
            )
        raise TypeError(f"TOML cannot represent {type(value).__name__}")

    lines: list[str] = []

    def table(value: dict, path: tuple[str, ...]) -> None:
        if path:
            lines.append("[" + ".".join(key(part) for part in path) + "]")
        for name, item in value.items():
            if not isinstance(item, dict):
                lines.append(f"{key(name)} = {scalar(item)}")
        for name, item in value.items():
            if isinstance(item, dict):
                table(item, (*path, name))

    if not isinstance(data, dict):
        raise TypeError("TOML document must be a mapping")
    table(data, ())
    result = "\n".join(lines)
    tomllib.loads(result)  # Never return a malformed document.
    return result


def _make_toml_module() -> dict:
    """thirst::toml — Standard TOML parsing and strict serialization."""
    import tomllib

    return {"parse": tomllib.loads, "dump": dump_toml}


# ============================================================
# Module Registry
# ============================================================

STDLIB_MODULES = {
    "thirst::time": _make_time_module,
    "thirst::crypto": _make_crypto_module,
    "thirst::reservoir": _make_reservoir_module,
    "thirst::fs": _make_fs_module,
    "thirst::path": _make_path_module,
    "thirst::json": _make_json_module,
    "thirst::http": _make_http_module,
    "thirst::env": _make_env_module,
    "thirst::process": _make_process_module,
    "thirst::log": _make_log_module,
    "thirst::test": _make_test_module,
    "thirst::collections": _make_collections_module,
    "thirst::net": _make_net_module,
    "thirst::sqlite": _make_sqlite_module,
    "thirst::yaml": _make_yaml_module,
    "thirst::toml": _make_toml_module,
}


# ============================================================
# Builtin Functions
# ============================================================


def _list_push(values: list, value: object) -> int:
    if not isinstance(values, list):
        raise TypeError("push requires a list")
    values.append(value)
    return len(values)


def _list_pop(values: list) -> object:
    if not isinstance(values, list):
        raise TypeError("pop requires a list")
    return values.pop() if values else None


def _list_flood(values: list, value: object) -> list:
    _list_push(values, value)
    return values


def _unsupported_builtin(*args: object) -> object:
    raise NotImplementedError(
        "This reserved transformation has no defined implementation"
    )


BUILTINS: dict[str, Callable[..., Any]] = {
    "length": len,
    "contains": lambda x, y: y in x,
    "split": lambda s, sep=None: str.split(s, sep),
    "abs": abs,
    "min": lambda *args: min(args),
    "max": lambda *args: max(args),
    "push": _list_push,
    "pop": _list_pop,
    "size": len,
    "get": lambda x, i: x[i],
    "flood": _list_flood,
    "condense": lambda q: q.get("value"),
    "evaporate": lambda q: q.pop("value", None),
    "strain": _unsupported_builtin,
    "transmute": _unsupported_builtin,
    "distill": _unsupported_builtin,
}


# ============================================================
# Lockfile-aware Module Resolution
# ============================================================


def load_lockfile(cwd: str = ".") -> dict[str, Any]:
    """
    Load and parse thirsty.lock from the given directory.
    Returns the lockfile dict, or an empty dict if not found or malformed.
    """
    lock_path = os.path.join(cwd, "thirsty.lock")
    if not os.path.exists(lock_path):
        return {}
    try:
        with open(lock_path) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


class LockedImports:
    """A project-local, content-bound import context for one execution.

    The lockfile itself is trusted project configuration, not a signature. A
    caller must read through this context immediately before parsing so checked
    bytes are the bytes executed. Files outside its inventory are rejected.
    """

    def __init__(self, project_root: str = "."):
        from pathlib import Path

        from utf.thirsty_lang.package_manager import PackageManager

        self.root = Path(project_root).resolve()
        manager = PackageManager(str(self.root))
        try:
            self.lock = manager.parse_lock()
            if not self.lock:
                raise ValueError("thirsty.lock not found or empty")
            violations = manager.verify_integrity()
            if violations:
                names = ", ".join(str(item["name"]) for item in violations)
                raise ValueError(
                    f"integrity check failed: {names}; regenerate lockfile v2"
                )
        except (OSError, ValueError, TypeError) as exc:
            raise ImportError(f"Lockfile check failed: {exc}") from exc

    def read_source(self, path: str) -> str:
        from pathlib import Path

        from utf.thirsty_lang.package_manager import content_integrity

        candidate = Path(path)
        candidate = (self.root / candidate).resolve()
        if not candidate.is_relative_to(self.root):
            raise ImportError("Locked import escapes project root")
        name = candidate.relative_to(self.root).as_posix()
        expected = self.lock["sources"].get(name)
        if expected is None:
            raise ImportError(f"Source '{name}' is not in thirsty.lock")
        try:
            content = candidate.read_bytes()
            if content_integrity(content) != expected:
                raise ImportError(f"Lockfile integrity check failed: '{name}' changed")
            return content.decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise ImportError(f"Cannot read locked source '{name}': {exc}") from exc

    def verify_stdlib(self, path_str: str) -> None:
        from utf.thirsty_lang.package_manager import runtime_integrity

        if path_str not in STDLIB_MODULES:
            raise ImportError(f"Module not found: {path_str}")
        if self.lock["runtime_integrity"] != runtime_integrity():
            raise ImportError(
                "Lockfile integrity check failed: bundled runtime changed"
            )


def check_lock_integrity(dep_name: str, dep_version: str, lock: dict) -> bool:
    """Verify a named dependency's content using the current project root."""
    from utf.thirsty_lang.package_manager import PackageManager

    manager = PackageManager()
    manager.lock = lock
    if manager.verify_integrity():
        return False
    entry = lock.get("dependencies", {}).get(dep_name)
    return isinstance(entry, dict) and (
        dep_version in ("*", "") or entry.get("version") == dep_version
    )


# ============================================================
# Public API
# ============================================================


def resolve_import(path_str: str, locked: bool = False) -> object:
    """
    Resolve an import path string to a module object.
    Handles 'thirst::module' syntax for stdlib modules.
    When locked=True, verifies a v2 content lock before resolving and carries
    the lock context through transitive source imports.
    """
    lock_context = LockedImports(".") if locked else None
    if lock_context and path_str.startswith("thirst::"):
        lock_context.verify_stdlib(path_str)

    # Check cache first
    if path_str in ModuleCache and not (locked and path_str.endswith(".thirsty")):
        return ModuleCache[path_str]

    # Check stdlib modules
    if path_str in STDLIB_MODULES:
        module = STDLIB_MODULES[path_str]()
        ModuleCache[path_str] = module
        return module

    # A 'thirst::' path not matched in STDLIB_MODULES above is an unknown module.
    if path_str.startswith("thirst::"):
        raise ImportError(f"Module not found: {path_str}")

    # Try to load from a .thirsty source file: parse, interpret, and expose its
    # top-level bindings (functions and `drink` values) as a module dict — the
    # same shape stdlib modules use, so `import "x.thirsty" as m; m.fn(...)`
    # works through the interpreter's dict member access.
    if path_str.endswith(".thirsty"):
        if not os.path.exists(path_str):
            raise ImportError(f"File not found: {path_str}")
        # Lazy imports: the interpreter imports this module at top level.
        from utf.thirsty_lang.interpreter import Interpreter
        from utf.thirsty_lang.lexer import Lexer
        from utf.thirsty_lang.parser import Parser

        if lock_context:
            source = lock_context.read_source(path_str)
        else:
            with open(path_str, encoding="utf-8") as f:
                source = f.read()
        lexer = Lexer(source)
        tokens = lexer.lex()
        if lexer.errors:
            raise ImportError(f"Failed to import '{path_str}': {lexer.errors[0]}")
        parser = Parser(tokens)
        ast = parser.parse()
        if parser.errors:
            raise ImportError(f"Failed to import '{path_str}': {parser.errors[0]}")
        interp = Interpreter()
        from pathlib import Path

        interp.source_directory = Path(path_str).resolve().parent
        if lock_context:
            interp.set_locked(lock_context)
        baseline = set(interp.env.vars)  # builtins to exclude from the module
        interp.interpret(ast)
        module = {
            name: value
            for name, value in interp.env.vars.items()
            if name not in baseline
        }
        ModuleCache[path_str] = module
        return module

    raise ImportError(f"Module not found: {path_str}")


def get_builtin(name: str) -> Callable[..., Any]:
    """Get a builtin function by name."""
    if name in BUILTINS:
        return BUILTINS[name]
    raise KeyError(f"Builtin not found: {name}")


def list_stdlib_modules() -> list[str]:
    """List all available stdlib module paths."""
    return sorted(STDLIB_MODULES.keys())


def list_builtins() -> list[str]:
    """List all builtin function names."""
    return sorted(BUILTINS.keys())
