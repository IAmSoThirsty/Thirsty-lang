"""Authoritative TARL context preparation and typed path resolution.

The policy language uses dotted *paths* (``user.role``), while the runtime
evaluates one nested mapping (``{"user": {"role": ...}}``).  Input may use a
dotted key, a nested object, or an equivalent mixture of both; all accepted
forms are normalized to the same nested representation.  Contradictory or
malformed mixtures are rejected instead of choosing one value silently.

Most importantly, resolution does not use a boolean sentinel.  Missing paths,
wrong intermediate types, and representation conflicts are distinct states
that callers must handle explicitly and fail closed on.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

CONTEXT_REPRESENTATION_ID = "tarl.context.nested-json.v1"
NORMALIZATION_ALGORITHM_ID = "tarl.context.dotted-path-expansion"
NORMALIZATION_VERSION = "1"
SOURCE_INJECTION_ALGORITHM_ID = (
    "tarl.context.dotted-path-expansion+registered-source-injection"
)
RESERVED_CONTEXT_IDENTIFIERS = frozenset({
    "true",
    "false",
    "CURRENT_HOUR",
    "CURRENT_DAY",
    "CURRENT_WEEKDAY",
    "CURRENT_MONTH",
    "CURRENT_YEAR",
    "CURRENT_TIMESTAMP",
})


class ContextResolutionState(StrEnum):
    """The complete state space for a context-path lookup."""

    RESOLVED = "resolved"
    MISSING = "missing"
    TYPE_ERROR = "type_error"
    REPRESENTATION_CONFLICT = "representation_conflict"


class ContextResolutionError(ValueError):
    """Raised when a path cannot produce an ordinary expression value."""

    def __init__(
        self,
        message: str,
        *,
        state: ContextResolutionState,
        path: str = "",
        conflict_status: str = "invalid",
    ) -> None:
        super().__init__(message)
        self.state = state
        self.path = path
        self.conflict_status = conflict_status


class ContextRepresentationError(ContextResolutionError):
    """Raised when a context is not an unambiguous nested mapping."""


@dataclass(frozen=True)
class ContextResolution:
    """A typed path-resolution result; only ``RESOLVED`` carries a value."""

    state: ContextResolutionState
    path: str
    value: Any = None
    reason: str = ""

    @property
    def resolved(self) -> bool:
        return self.state is ContextResolutionState.RESOLVED

    def require_value(self) -> Any:
        if self.resolved:
            return self.value
        raise ContextResolutionError(
            self.reason,
            state=self.state,
            path=self.path,
            conflict_status=(
                "conflict"
                if self.state is ContextResolutionState.REPRESENTATION_CONFLICT
                else "invalid"
            ),
        )


@dataclass(frozen=True)
class PreparedContext:
    """Frozen-by-copy context snapshot plus proof-binding metadata."""

    canonical: dict[str, Any]
    original_context_hash: str
    canonical_context_hash: str
    context_representation_id: str = CONTEXT_REPRESENTATION_ID
    normalization_algorithm_id: str = NORMALIZATION_ALGORITHM_ID
    normalization_version: str = NORMALIZATION_VERSION
    context_conflict_status: str = "none"

    def binding_dict(self) -> dict[str, str]:
        return {
            "original_context_hash": self.original_context_hash,
            "canonical_context_hash": self.canonical_context_hash,
            "context_representation_id": self.context_representation_id,
            "normalization_algorithm_id": self.normalization_algorithm_id,
            "normalization_version": self.normalization_version,
            "context_conflict_status": self.context_conflict_status,
        }


def canonical_context_bytes(context: Any) -> bytes:
    """Deterministic byte encoding shared by runtime, proof, and verifier."""
    return json.dumps(
        context,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def hash_context(context: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_context_bytes(context)).hexdigest()


def _rejected_value(value: Any, active: set[int]) -> Any:
    """Type-tag invalid Python values for a non-authoritative DENY hash."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return {"$invalid_float": repr(value)}

    identity = id(value)
    if identity in active:
        return {"$cycle": f"{type(value).__module__}.{type(value).__qualname__}"}
    active.add(identity)
    try:
        if isinstance(value, dict):
            entries = [
                [_rejected_value(key, active), _rejected_value(item, active)]
                for key, item in value.items()
            ]
            entries.sort(key=lambda entry: canonical_context_bytes(entry[0]))
            return {"$invalid_object_entries": entries}
        if isinstance(value, list):
            return {"$list": [_rejected_value(item, active) for item in value]}
        if isinstance(value, tuple):
            return {"$tuple": [_rejected_value(item, active) for item in value]}
        if isinstance(value, (set, frozenset)):
            items = [_rejected_value(item, active) for item in value]
            items.sort(key=canonical_context_bytes)
            return {
                "$frozenset" if isinstance(value, frozenset) else "$set": items
            }
        try:
            display = repr(value)
        except Exception:
            display = "<unrepresentable>"
        return {
            "$python_type": f"{type(value).__module__}.{type(value).__qualname__}",
            "$repr": display,
        }
    finally:
        active.remove(identity)


def hash_rejected_context(context: Any) -> str:
    diagnostic = _rejected_value(context, set())
    return "sha256:" + hashlib.sha256(
        canonical_context_bytes(diagnostic)
    ).hexdigest()


def hash_rejected_canonical_binding(
    original_context_hash: str, conflict_status: str
) -> str:
    """Hash the canonical rejection record used when no context was evaluated."""
    return hash_context(
        {
            "context_conflict_status": conflict_status,
            "normalization_algorithm_id": "rejected",
            "normalization_version": NORMALIZATION_VERSION,
            "original_context_hash": original_context_hash,
        }
    )


def load_context_json(raw: str) -> Any:
    """Decode JSON while rejecting duplicate object keys.

    Python's ordinary ``json.loads`` silently keeps the last duplicate key,
    which would let validation and authorization observe different values.
    """
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ContextRepresentationError(
                    f"context representation conflict: duplicate key '{key}'",
                    state=ContextResolutionState.REPRESENTATION_CONFLICT,
                    path=key,
                    conflict_status="conflict",
                )
            result[key] = value
        return result

    def reject_non_finite(value: str) -> None:
        raise ContextRepresentationError(
            f"context representation violation: non-finite number {value}",
            state=ContextResolutionState.TYPE_ERROR,
        )

    return json.loads(
        raw,
        object_pairs_hook=reject_duplicates,
        parse_constant=reject_non_finite,
    )


def _snapshot(value: Any) -> Any:
    try:
        return copy.deepcopy(value)
    except Exception as exc:
        raise ContextRepresentationError(
            f"context representation violation: context could not be snapshotted: {exc}",
            state=ContextResolutionState.TYPE_ERROR,
        ) from exc


def _strict_equal(left: Any, right: Any) -> bool:
    """Type-sensitive equality (unlike Python's ``True == 1``)."""
    if type(left) is not type(right):
        return False
    try:
        return canonical_context_bytes(left) == canonical_context_bytes(right)
    except (TypeError, ValueError):
        return False


def _raw_nested_resolution(
    mapping: dict[str, Any], parts: list[str]
) -> ContextResolution:
    path = ".".join(parts)
    current: Any = mapping
    traversed: list[str] = []
    for part in parts:
        if not isinstance(current, dict):
            at = ".".join(traversed) or "<root>"
            return ContextResolution(
                ContextResolutionState.TYPE_ERROR,
                path,
                reason=(
                    f"context path '{path}' cannot be resolved: '{at}' has type "
                    f"{type(current).__name__}, expected object"
                ),
            )
        traversed.append(part)
        if part not in current:
            return ContextResolution(
                ContextResolutionState.MISSING,
                path,
                reason=f"context path '{path}' is missing at '{'.'.join(traversed)}'",
            )
        current = current[part]
    return ContextResolution(ContextResolutionState.RESOLVED, path, value=current)


def resolve_context_path(
    context: dict[str, Any], path: str | Iterable[str]
) -> ContextResolution:
    """Resolve a dotted path without collapsing failure states into ``False``."""
    parts = path.split(".") if isinstance(path, str) else [str(p) for p in path]
    display = ".".join(parts)
    if not parts or any(not part for part in parts):
        return ContextResolution(
            ContextResolutionState.TYPE_ERROR,
            display,
            reason=f"context path '{display}' is invalid",
        )
    return _raw_nested_resolution(context, parts)


def _validate_mapping_shape(
    mapping: dict[Any, Any],
    *,
    prefix: tuple[str, ...] = (),
    allow_source_keys: bool = False,
    active: set[int] | None = None,
) -> None:
    if type(mapping) is not dict:
        raise ContextRepresentationError(
            "context representation violation: objects must use the built-in dict type",
            state=ContextResolutionState.TYPE_ERROR,
            path=".".join(prefix),
        )
    active = active if active is not None else set()
    identity = id(mapping)
    if identity in active:
        raise ContextRepresentationError(
            "context representation violation: circular object reference",
            state=ContextResolutionState.TYPE_ERROR,
        )
    active.add(identity)
    try:
        # Reject non-string keys before sorting. Calling ``str`` on an
        # attacker-controlled Python key can execute user code or raise
        # outside the typed fail-closed boundary.
        for key in mapping:
            if type(key) is not str:
                raise ContextRepresentationError(
                    "context representation violation: object keys must be strings",
                    state=ContextResolutionState.TYPE_ERROR,
                )
        for key in sorted(mapping):
            full_key = ".".join((*prefix, key))
            parts = key.split(".")
            if any(not part for part in parts):
                raise ContextRepresentationError(
                    f"context representation violation: dotted key '{full_key}' is invalid",
                    state=ContextResolutionState.REPRESENTATION_CONFLICT,
                    path=full_key,
                    conflict_status="invalid",
                )
            for index, part in enumerate(parts):
                component_path = ".".join((*prefix, *parts[: index + 1]))
                if part.startswith("__tarl_"):
                    raise ContextRepresentationError(
                        "context representation violation: reserved field "
                        f"'{component_path}'",
                        state=ContextResolutionState.REPRESENTATION_CONFLICT,
                        path=component_path,
                        conflict_status="invalid",
                    )
                if not prefix and index == 0:
                    if part in RESERVED_CONTEXT_IDENTIFIERS:
                        raise ContextRepresentationError(
                            "context representation violation: reserved identifier "
                            f"'{part}'",
                            state=ContextResolutionState.REPRESENTATION_CONFLICT,
                            path=part,
                            conflict_status="invalid",
                        )
                    if part.startswith("source:") and not allow_source_keys:
                        raise ContextRepresentationError(
                            "context representation violation: reserved source field "
                            f"'{part}'",
                            state=ContextResolutionState.REPRESENTATION_CONFLICT,
                            path=part,
                            conflict_status="invalid",
                        )

            _validate_context_value(
                mapping[key],
                path=full_key,
                allow_source_keys=allow_source_keys,
                active=active,
            )
    finally:
        active.remove(identity)


def _validate_context_value(
    value: Any,
    *,
    path: str,
    allow_source_keys: bool,
    active: set[int],
) -> None:
    if value is None or type(value) in {str, bool, int}:
        return
    if type(value) is float:
        if math.isfinite(value):
            return
        raise ContextRepresentationError(
            f"context representation violation: field '{path}' contains a non-finite number",
            state=ContextResolutionState.TYPE_ERROR,
            path=path,
        )
    if type(value) is dict:
        _validate_mapping_shape(
            value,
            prefix=tuple(path.split(".")),
            allow_source_keys=allow_source_keys,
            active=active,
        )
        return
    if type(value) is list:
        identity = id(value)
        if identity in active:
            raise ContextRepresentationError(
                f"context representation violation: circular list at '{path}'",
                state=ContextResolutionState.TYPE_ERROR,
                path=path,
            )
        active.add(identity)
        try:
            for index, item in enumerate(value):
                _validate_context_value(
                    item,
                    path=f"{path}[{index}]",
                    allow_source_keys=allow_source_keys,
                    active=active,
                )
        finally:
            active.remove(identity)
        return
    raise ContextRepresentationError(
        f"context representation violation: field '{path}' has unsupported "
        f"type {type(value).__name__}",
        state=ContextResolutionState.TYPE_ERROR,
        path=path,
    )


def _merge_canonical_objects(
    target: dict[str, Any],
    incoming: dict[str, Any],
    *,
    prefix: tuple[str, ...],
) -> None:
    """Merge two normalized object contributions, rejecting value conflicts."""
    for key in sorted(incoming):
        path = (*prefix, key)
        if key not in target:
            target[key] = incoming[key]
            continue
        existing = target[key]
        proposed = incoming[key]
        if type(existing) is dict and type(proposed) is dict:
            _merge_canonical_objects(existing, proposed, prefix=path)
            continue
        if _strict_equal(existing, proposed):
            continue
        display = ".".join(path)
        raise ContextRepresentationError(
            f"context representation conflict: {display} has contradictory "
            "flat and nested values",
            state=ContextResolutionState.REPRESENTATION_CONFLICT,
            path=display,
            conflict_status="conflict",
        )


def _insert_canonical_path(
    target: dict[str, Any],
    parts: list[str],
    value: Any,
    *,
    prefix: tuple[str, ...],
) -> None:
    current = target
    for index, part in enumerate(parts[:-1]):
        traversed = (*prefix, *parts[: index + 1])
        if part not in current:
            current[part] = {}
        elif type(current[part]) is not dict:
            display = ".".join((*prefix, *parts))
            intermediate = ".".join(traversed)
            raise ContextRepresentationError(
                f"context representation conflict: {display} collides with "
                f"non-object intermediate '{intermediate}'",
                state=ContextResolutionState.REPRESENTATION_CONFLICT,
                path=display,
                conflict_status="conflict",
            )
        current = current[part]

    leaf = parts[-1]
    leaf_path = (*prefix, *parts)
    if leaf not in current:
        current[leaf] = value
        return
    existing = current[leaf]
    if type(existing) is dict and type(value) is dict:
        _merge_canonical_objects(existing, value, prefix=leaf_path)
        return
    if _strict_equal(existing, value):
        return
    display = ".".join(leaf_path)
    raise ContextRepresentationError(
        f"context representation conflict: {display} has contradictory flat "
        "and nested values",
        state=ContextResolutionState.REPRESENTATION_CONFLICT,
        path=display,
        conflict_status="conflict",
    )


def _canonicalize_context_value(value: Any, *, path: str) -> Any:
    if type(value) is dict:
        return _canonicalize_mapping(
            value,
            prefix=tuple(path.split(".")) if path else (),
        )
    if type(value) is list:
        return [
            _canonicalize_context_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    return value


def _canonicalize_mapping(
    mapping: dict[str, Any], *, prefix: tuple[str, ...] = ()
) -> dict[str, Any]:
    """Expand dotted keys and merge equivalent contributions deterministically."""
    canonical: dict[str, Any] = {}
    for key in sorted(mapping):
        parts = key.split(".")
        display = ".".join((*prefix, *parts))
        value = _canonicalize_context_value(mapping[key], path=display)
        _insert_canonical_path(
            canonical,
            parts,
            value,
            prefix=prefix,
        )
    return canonical


def prepare_context(
    context: Any, *, allow_source_keys: bool = False
) -> PreparedContext:
    """Deep-snapshot and validate one authoritative nested context."""
    if type(context) is not dict:
        raise ContextRepresentationError(
            "context representation violation: context must be a JSON object",
            state=ContextResolutionState.TYPE_ERROR,
        )
    # Validate before copying so a hostile ``__deepcopy__`` implementation on
    # a Python-only object cannot silently normalize itself into JSON data.
    _validate_mapping_shape(context, allow_source_keys=allow_source_keys)
    snapshot = _snapshot(context)
    if type(snapshot) is not dict:
        raise ContextRepresentationError(
            "context representation violation: context must be a JSON object",
            state=ContextResolutionState.TYPE_ERROR,
        )
    _validate_mapping_shape(snapshot, allow_source_keys=allow_source_keys)
    original_hash = hash_context(snapshot)
    canonical = _canonicalize_mapping(snapshot)
    canonical_hash = hash_context(canonical)
    return PreparedContext(
        canonical=canonical,
        original_context_hash=original_hash,
        canonical_context_hash=canonical_hash,
    )


def rejected_context_binding(
    context: Any, *, conflict_status: str = "invalid"
) -> PreparedContext:
    """Bind an invalid input to a DENY proof without claiming it was evaluated."""
    original_hash = hash_rejected_context(context)
    canonical_hash = hash_rejected_canonical_binding(
        original_hash, conflict_status
    )
    return PreparedContext(
        canonical={},
        original_context_hash=original_hash,
        canonical_context_hash=canonical_hash,
        normalization_algorithm_id="rejected",
        context_conflict_status=conflict_status,
    )


def compose_context_layers(
    *layers: tuple[str, dict[str, Any]],
) -> dict[str, Any]:
    """Merge trusted context layers while rejecting every key collision."""
    result: dict[str, Any] = {}
    owners: dict[str, str] = {}
    for layer_name, layer in layers:
        if type(layer) is not dict:
            raise ContextRepresentationError(
                f"context layer '{layer_name}' must be an object",
                state=ContextResolutionState.TYPE_ERROR,
            )
        _validate_mapping_shape(layer, allow_source_keys=True)
        for key, value in layer.items():
            if key in result:
                raise ContextRepresentationError(
                    f"context layer conflict: field '{key}' is supplied by both "
                    f"{owners[key]} and {layer_name}",
                    state=ContextResolutionState.REPRESENTATION_CONFLICT,
                    path=key,
                    conflict_status="conflict",
                )
            result[key] = _snapshot(value)
            owners[key] = layer_name
    return result


__all__ = [
    "CONTEXT_REPRESENTATION_ID",
    "NORMALIZATION_ALGORITHM_ID",
    "NORMALIZATION_VERSION",
    "SOURCE_INJECTION_ALGORITHM_ID",
    "RESERVED_CONTEXT_IDENTIFIERS",
    "ContextRepresentationError",
    "ContextResolution",
    "ContextResolutionError",
    "ContextResolutionState",
    "PreparedContext",
    "canonical_context_bytes",
    "compose_context_layers",
    "hash_context",
    "hash_rejected_canonical_binding",
    "hash_rejected_context",
    "load_context_json",
    "prepare_context",
    "rejected_context_binding",
    "resolve_context_path",
]
