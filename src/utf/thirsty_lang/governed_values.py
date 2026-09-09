"""Bounded, owned JSON projections of values entering governed calls.

The native profile identifies declarations within a live interpreter session;
it is not a portable code signature or an operating-system security boundary.
"""

import math
import weakref
from dataclasses import dataclass
from threading import RLock
from typing import Any, cast
from uuid import uuid4

NATIVE_MARKER = "__thirsty_native__"
NATIVE_PROFILE = "thirsty.native-value.v1"
MAX_DEPTH = 32
MAX_NODES = 10_000
MAX_UTF8_BYTES = 1_048_576
MAX_INTEGER_BITS = 4096


class GovernedValueError(ValueError):
    """A value cannot be represented by the governed native-value profile."""


@dataclass(frozen=True, eq=False)
class _NativeIdentity:
    registry: "NativeValueRegistry"
    key: Any
    declaration_id: str
    kind: str
    name: str
    fields: tuple[str, ...]


class NativeValueRegistry:
    """Runtime-owned declaration identities, shared with imported modules."""

    def __init__(self) -> None:
        self.scope_id = uuid4().hex
        self._entries: dict[int, _NativeIdentity] = {}
        self._next_id = 0
        self._lock = RLock()

    def register(
        self, key: Any, kind: str, name: str, fields: tuple[str, ...] = ()
    ) -> _NativeIdentity:
        address = id(key)
        with self._lock:
            previous = self._entries.get(address)
            if previous is not None and previous.key() is key:
                if (previous.kind, previous.name, previous.fields) != (
                    kind,
                    name,
                    fields,
                ):
                    raise GovernedValueError(
                        "native declaration changed after registration"
                    )
                return previous
            self._next_id += 1

            def discard(reference: Any) -> None:
                with self._lock:
                    current = self._entries.get(address)
                    if current is not None and current.key is reference:
                        del self._entries[address]

            identity = _NativeIdentity(
                self, weakref.ref(key, discard), str(self._next_id), kind, name, fields
            )
            self._entries[address] = identity
            return identity

    def contains(self, identity: _NativeIdentity, key: Any) -> bool:
        with self._lock:
            return (
                identity.key() is key
                and self._entries.get(id(key)) is identity
                and identity.registry is self
            )


def project_governed_context(context: dict[str, Any]) -> dict[str, Any]:
    """Copy exact JSON values and runtime native values, without host hooks.

    Object keys count as nodes. The UTF-8 budget counts strings and keys,
    including generated metadata, rather than JSON punctuation. Depth starts
    at zero and includes the native envelope. Repeated aliases count again.
    """
    # Local import avoids an interpreter/module initialization cycle.
    from utf.thirsty_lang.interpreter import FountainInstance, StructInstance

    if type(context) is not dict:
        raise GovernedValueError("governed context must be an exact dict")
    nodes = 0
    utf8_bytes = 0
    active: set[int] = set()

    def node() -> None:
        nonlocal nodes
        nodes += 1
        if nodes > MAX_NODES:
            raise GovernedValueError("governed value exceeds node budget")

    def string(value: str) -> str:
        nonlocal utf8_bytes
        # Bound the allocation before encoding; every code point uses >=1 byte.
        if len(value) > MAX_UTF8_BYTES - utf8_bytes:
            raise GovernedValueError("governed value exceeds UTF-8 budget")
        try:
            utf8_bytes += len(value.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise GovernedValueError("governed value contains invalid Unicode") from exc
        if utf8_bytes > MAX_UTF8_BYTES:
            raise GovernedValueError("governed value exceeds UTF-8 budget")
        return value

    def object_key(value: Any, *, generated: bool = False) -> str:
        node()
        if type(value) is not str:
            raise GovernedValueError("governed object keys must be exact strings")
        string(value)
        if not generated and NATIVE_MARKER in value.split("."):
            raise GovernedValueError("reserved native metadata key in governed value")
        return value

    def walk(value: Any, depth: int) -> Any:
        if depth > MAX_DEPTH:
            raise GovernedValueError("governed value exceeds depth budget")
        node()
        value_type = type(value)
        if value is None or value_type is bool:
            return value
        if value_type is int:
            if value.bit_length() > MAX_INTEGER_BITS:
                raise GovernedValueError("governed integer exceeds bit budget")
            return value
        if value_type is float:
            if not math.isfinite(value):
                raise GovernedValueError("governed floats must be finite")
            return value
        if value_type is str:
            return string(value)
        address = id(value)
        if address in active:
            raise GovernedValueError("cyclic governed value")
        active.add(address)
        try:
            if value_type is list:
                if len(value) > MAX_NODES - nodes:
                    raise GovernedValueError("governed value exceeds node budget")
                return [walk(item, depth + 1) for item in value]
            if value_type is dict:
                if len(value) * 2 > MAX_NODES - nodes:
                    raise GovernedValueError("governed value exceeds node budget")
                return {
                    object_key(key): walk(item, depth + 1)
                    for key, item in value.items()
                }
            if value_type is StructInstance:
                identity = object.__getattribute__(value, "native_identity")
                declaration = object.__getattribute__(value, "declaration")
                expected_kind = "struct"
            elif value_type is FountainInstance:
                identity = object.__getattribute__(value, "native_identity")
                declaration = object.__getattribute__(value, "cls_decl")
                expected_kind = "fountain"
            else:
                identity = type.__getattribute__(value_type, "__dict__").get(
                    "_thirsty_native_identity"
                )
                declaration = value_type
                expected_kind = "enum"
            if (
                type(identity) is not _NativeIdentity
                or identity.kind != expected_kind
                or not identity.registry.contains(identity, declaration)
            ):
                raise GovernedValueError("unsupported or unregistered governed value")
            metadata = {
                "profile": NATIVE_PROFILE,
                "scope_id": identity.registry.scope_id,
                "declaration_id": identity.declaration_id,
                "kind": identity.kind,
                "name": identity.name,
            }
            result = {
                object_key(NATIVE_MARKER, generated=True): walk(metadata, depth + 1)
            }
            if expected_kind == "enum":
                variant = object.__getattribute__(value, "_name_")
                members = type.__getattribute__(value_type, "_member_map_")
                if type(variant) is not str or members.get(variant) is not value:
                    raise GovernedValueError("invalid native enum variant")
                result[object_key("variant")] = walk(variant, depth + 1)
            else:
                fields = object.__getattribute__(value, "fields")
                if (
                    type(fields) is not dict
                    or len(fields) > MAX_NODES
                    or len(fields) != len(identity.fields)
                    or any(type(key) is not str for key in fields)
                    or set(fields) != set(identity.fields)
                ):
                    raise GovernedValueError("native field inventory changed")
                result[object_key("fields")] = walk(fields, depth + 1)
            return result
        except (RuntimeError, AttributeError) as exc:
            raise GovernedValueError(
                "governed value changed during projection"
            ) from exc
        finally:
            active.remove(address)

    return cast(dict[str, Any], walk(context, 0))
