"""
Context schema validation for T.A.R.L. evaluation.

Policies decide over a context dict, but an attacker controls that dict's shape
(threat-model A8, context poisoner). Two failure modes matter:

  * **Missing required field (C045)** — a policy that gates on ``amount`` sees no
    ``amount`` at all; a naive ``when amount > 100`` silently fails to match and
    the context slips to a more permissive later rule or to DEFAULT-DENY for the
    wrong reason.
  * **Type confusion (C046)** — ``amount`` arrives as a non-numeric string or a
    dict, so the policy cannot prove the comparison is well-typed.

A :class:`ContextSchema` declares the fields a policy requires and their accepted
types. The runtime validates the context **before** any rule is evaluated; a
violation short-circuits to a fail-closed verdict (DENY by default, or ESCALATE)
with a proof recording exactly which fields were missing or mistyped — never a
silent permissive default.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from utf.tarl.context import (
    CONTEXT_REPRESENTATION_ID,
    RESERVED_CONTEXT_IDENTIFIERS,
    ContextResolutionError,
    ContextResolutionState,
    PreparedContext,
    prepare_context,
    resolve_context_path,
)
from utf.tarl.spec import TarlVerdict

# Friendly names for the accepted "kinds" a field may declare.
_KIND_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "int": (int,),
    "float": (float,),
    "number": (int, float),
    "bool": (bool,),
    "list": (list,),
    "dict": (dict,),
}


@dataclass
class FieldSpec:
    """One required/optional context field and its accepted kind(s)."""

    name: str
    kinds: tuple[str, ...] = ("string",)
    required: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name or any(
            not part for part in self.name.split(".")
        ):
            raise ValueError("context schema field name must be a valid path")
        if self.name.split(".", 1)[0] in RESERVED_CONTEXT_IDENTIFIERS:
            raise ValueError(
                f"context schema field '{self.name}' uses a reserved identifier"
            )
        if not isinstance(self.kinds, tuple) or not self.kinds:
            raise ValueError("context schema field kinds must be a non-empty tuple")
        unknown = set(self.kinds) - set(_KIND_TYPES)
        if unknown:
            raise ValueError(
                "unknown context schema field kinds: "
                + ", ".join(sorted(unknown))
            )
        if type(self.required) is not bool:
            raise ValueError("context schema field required must be a boolean")

    def accepts(self, value: object) -> bool:
        for kind in self.kinds:
            types = _KIND_TYPES.get(kind, ())
            # bool is a subclass of int; only accept it when explicitly allowed,
            # so a `bool` slipped into an `int`/`number` field is type confusion.
            if isinstance(value, bool):
                if kind == "bool":
                    return True
                continue
            if isinstance(value, types):
                return True
        return False


@dataclass
class ContextSchema:
    """A set of field specs plus the verdict to return on any violation."""

    fields: list[FieldSpec] = field(default_factory=list)
    on_violation: TarlVerdict = TarlVerdict.DENY
    representation_id: str = CONTEXT_REPRESENTATION_ID

    def __post_init__(self) -> None:
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        if self.on_violation is TarlVerdict.ALLOW:
            raise ValueError("context schema on_violation cannot be ALLOW")
        if not isinstance(self.on_violation, TarlVerdict):
            raise ValueError("context schema on_violation must be a TARL verdict")
        if self.representation_id != CONTEXT_REPRESENTATION_ID:
            raise ValueError(
                "unsupported context representation: "
                f"{self.representation_id!r}; expected "
                f"{CONTEXT_REPRESENTATION_ID!r}"
            )
        if not isinstance(self.fields, list):
            raise ValueError("context schema fields must be a list")
        names: set[str] = set()
        for spec in self.fields:
            if type(spec) is not FieldSpec:
                raise ValueError("context schema fields must be FieldSpec values")
            spec.__post_init__()
            if spec.name in names:
                raise ValueError(
                    f"duplicate context schema field '{spec.name}'"
                )
            names.add(spec.name)

    def to_dict(self) -> dict:
        """Return the canonical, JSON-friendly schema representation."""
        self._validate_configuration()
        fields = sorted(
            (
                {
                    "name": spec.name,
                    "kinds": sorted(set(spec.kinds)),
                    "required": spec.required,
                }
                for spec in self.fields
            ),
            key=lambda item: (
                item["name"],
                item["kinds"],
                item["required"],
            ),
        )
        return {
            "representation": {
                "id": self.representation_id,
                "path_model": "nested-objects",
                "normalization": "none",
            },
            "on_violation": self.on_violation.value,
            "fields": fields,
        }

    def fingerprint(self) -> str:
        """Return the deterministic SHA-256 identity bound into proofs."""
        encoded = json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(encoded).hexdigest()

    def validate(self, context: dict | PreparedContext) -> list[str]:
        """Return a list of human-readable violations ([] when the context is ok)."""
        self._validate_configuration()
        try:
            prepared = (
                context
                if isinstance(context, PreparedContext)
                else prepare_context(context)
            )
        except ContextResolutionError as exc:
            return [str(exc)]

        violations: list[str] = []
        for spec in self.fields:
            resolution = resolve_context_path(prepared.canonical, spec.name)
            if resolution.state is ContextResolutionState.MISSING:
                if spec.required:
                    violations.append(f"missing required field '{spec.name}'")
                continue
            if resolution.state is not ContextResolutionState.RESOLVED:
                violations.append(resolution.reason)
                continue
            value = resolution.value
            if not spec.accepts(value):
                violations.append(
                    f"field '{spec.name}' has type {type(value).__name__}, "
                    f"expected one of {', '.join(spec.kinds)}"
                )
        return violations

    @classmethod
    def from_dict(cls, data: dict) -> ContextSchema:
        """Build a schema from a JSON-friendly dict.

        ``{"on_violation": "DENY", "fields": [
              {"name": "amount", "kinds": ["number"], "required": true}, ...]}``
        """
        if type(data) is not dict:
            raise ValueError("context schema must be an object")
        unknown_top_level = set(data) - {
            "fields",
            "gaps",
            "on_violation",
            "representation",
            "representation_id",
            "source",
            "status",
        }
        if unknown_top_level:
            raise ValueError(
                "unknown context schema fields: "
                + ", ".join(sorted(unknown_top_level))
            )
        status = data.get("status")
        if status is not None:
            if status not in {"complete", "explicit"}:
                raise ValueError(
                    "only complete or explicit context schemas may be loaded"
                )
        representation = data.get("representation", {})
        if representation is None:
            representation = {}
        if not isinstance(representation, dict):
            raise ValueError("context schema representation must be an object")
        unknown_representation_keys = set(representation) - {
            "id",
            "path_model",
            "normalization",
        }
        if unknown_representation_keys:
            raise ValueError(
                "unknown context schema representation fields: "
                + ", ".join(sorted(unknown_representation_keys))
            )
        top_level_representation_id = data.get("representation_id")
        nested_representation_id = representation.get("id")
        if (
            top_level_representation_id is not None
            and nested_representation_id is not None
            and top_level_representation_id != nested_representation_id
        ):
            raise ValueError(
                "conflicting context schema representation identifiers"
            )
        representation_id = (
            nested_representation_id
            or top_level_representation_id
            or CONTEXT_REPRESENTATION_ID
        )
        if representation_id != CONTEXT_REPRESENTATION_ID:
            raise ValueError(
                "unsupported context representation: "
                f"{representation_id!r}; expected {CONTEXT_REPRESENTATION_ID!r}"
            )
        normalization = representation.get("normalization", "none")
        if normalization != "none":
            raise ValueError(
                "context schema normalization must be 'none'; silent "
                "conversion is not permitted"
            )
        path_model = representation.get("path_model", "nested-objects")
        if path_model != "nested-objects":
            raise ValueError(
                "context schema path_model must be 'nested-objects'"
            )

        on_violation = TarlVerdict(data.get("on_violation", "DENY"))
        if on_violation is TarlVerdict.ALLOW:
            raise ValueError("context schema on_violation cannot be ALLOW")
        raw_fields = data.get("fields", [])
        if not isinstance(raw_fields, list):
            raise ValueError("context schema fields must be a list")
        fields = []
        for raw_field in raw_fields:
            if type(raw_field) is not dict:
                raise ValueError("context schema field entries must be objects")
            unknown_field_keys = set(raw_field) - {
                "name",
                "kinds",
                "required",
            }
            if unknown_field_keys:
                raise ValueError(
                    "unknown context schema field attributes: "
                    + ", ".join(sorted(unknown_field_keys))
                )
            raw_kinds = raw_field.get("kinds", ["string"])
            if not isinstance(raw_kinds, list) or not all(
                type(kind) is str for kind in raw_kinds
            ):
                raise ValueError(
                    "context schema field kinds must be a list of strings"
                )
            fields.append(
                FieldSpec(
                    name=raw_field["name"],
                    kinds=tuple(raw_kinds),
                    required=raw_field.get("required", True),
                )
            )
        return cls(
            fields=fields,
            on_violation=on_violation,
            representation_id=representation_id,
        )


__all__ = ["FieldSpec", "ContextSchema"]
