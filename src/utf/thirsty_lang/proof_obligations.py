"""Static proof-obligation extraction for Thirsty-Lang programs.

The extractor is intentionally read-only: it walks the parsed AST and TARL
policy text, but it never creates an Interpreter and never evaluates program
expressions. It is used by `thirsty prove`, denial explanations, checker effect
warnings, and build manifests.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any

from utf.tarl.context import (
    CONTEXT_REPRESENTATION_ID,
    NORMALIZATION_ALGORITHM_ID,
    RESERVED_CONTEXT_IDENTIFIERS,
    load_context_json,
)
from utf.tarl.core import PolicyParser, SafeExpr
from utf.tarl.schema import ContextSchema
from utf.thirsty_lang.ast import (
    CallExpr,
    ClassDecl,
    FunctionDecl,
    GovernedFunctionDecl,
    Identifier,
    ImportStmt,
    MemberAccess,
    PourStmt,
    Program,
    SipStmt,
)
from utf.thirsty_lang.diagnostics import Diagnostic
from utf.thirsty_lang.module_system import SENSITIVE_STDLIB_CAPABILITIES

RESERVED_CONTEXT_FIELDS = RESERVED_CONTEXT_IDENTIFIERS

AUTHORITY_FIELDS = {
    "authority": ("string",),
    "authority_subject": ("string",),
    "authority_authenticated": ("bool",),
    "authority_grants": ("list",),
}


@dataclass(frozen=True)
class CapabilityObligation:
    action: str
    target: str
    source: str
    function: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "action": self.action,
            "target": self.target,
            "source": self.source,
        }
        if self.function:
            data["function"] = self.function
        return data


@dataclass(frozen=True)
class ContractObligation:
    function: str
    phase: str
    annotation: str

    def to_dict(self) -> dict[str, str]:
        return {
            "function": self.function,
            "phase": self.phase,
            "annotation": self.annotation,
        }


@dataclass
class DerivedContextSchema:
    status: str
    fields: list[dict[str, Any]] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    source: str = "derived"
    on_violation: str = "DENY"

    @property
    def complete(self) -> bool:
        return self.status in {"complete", "explicit"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "on_violation": self.on_violation,
            "representation": {
                "id": CONTEXT_REPRESENTATION_ID,
                "path_model": "nested-objects",
                "normalization": NORMALIZATION_ALGORITHM_ID,
            },
            "fields": self.fields,
            "gaps": self.gaps,
        }


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_explicit_context_schema(path: str) -> DerivedContextSchema:
    with open(path, encoding="utf-8") as f:
        data = load_context_json(f.read())
    if not isinstance(data, dict):
        raise ValueError("context schema must be a JSON object")
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
    if status is not None and status not in {"complete", "explicit"}:
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
        raise ValueError("conflicting context schema representation identifiers")
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
    normalization = representation.get(
        "normalization", NORMALIZATION_ALGORITHM_ID
    )
    if normalization != NORMALIZATION_ALGORITHM_ID:
        raise ValueError(
            "unsupported context schema normalization: "
            f"{normalization!r}; expected {NORMALIZATION_ALGORITHM_ID!r}"
        )
    if representation.get("path_model", "nested-objects") != "nested-objects":
        raise ValueError("context schema path_model must be 'nested-objects'")
    on_violation = data.get("on_violation", "DENY")
    raw_fields = data.get("fields", [])
    fields_out = _normalize_explicit_schema_fields(raw_fields)
    validated = ContextSchema.from_dict(
        {
            "representation": {
                "id": representation_id,
                "path_model": "nested-objects",
                "normalization": NORMALIZATION_ALGORITHM_ID,
            },
            "on_violation": on_violation,
            "fields": fields_out,
        }
    )
    return DerivedContextSchema(
        status="explicit",
        source=path,
        on_violation=validated.on_violation.value,
        fields=validated.to_dict()["fields"],
        gaps=[],
    )


def _normalize_explicit_schema_fields(raw_fields: Any) -> list[dict[str, Any]]:
    fields_out: list[dict[str, Any]] = []
    if isinstance(raw_fields, dict):
        iterable = [
            _field_item_from_mapping(name, spec)
            for name, spec in raw_fields.items()
        ]
    elif isinstance(raw_fields, list):
        iterable = raw_fields
    else:
        raise ValueError("context schema 'fields' must be an object or list")

    for item in iterable:
        if not isinstance(item, dict):
            raise ValueError("context schema field entries must be objects")
        unknown_field_keys = set(item) - {
            "kind",
            "kinds",
            "name",
            "required",
        }
        if unknown_field_keys:
            raise ValueError(
                "unknown context schema field attributes: "
                + ", ".join(sorted(unknown_field_keys))
            )
        if "kind" in item and "kinds" in item:
            raise ValueError(
                "context schema field cannot declare both kind and kinds"
            )
        name = item.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("context schema field entries require a string name")
        kinds = item.get("kinds", [item.get("kind", "string")])
        if isinstance(kinds, str):
            kinds = [kinds]
        if not isinstance(kinds, list) or not all(isinstance(k, str) for k in kinds):
            raise ValueError(
                f"context schema field '{name}' must declare string kind values"
            )
        required = item.get("required", True)
        if type(required) is not bool:
            raise ValueError(
                f"context schema field '{name}' required must be a boolean"
            )
        fields_out.append({
            "name": name,
            "kinds": sorted(set(kinds)),
            "required": required,
        })
    return fields_out


def _field_item_from_mapping(name: str, spec: Any) -> dict[str, Any]:
    if isinstance(spec, str):
        return {"name": name, "kinds": [spec], "required": True}
    if isinstance(spec, list):
        return {"name": name, "kinds": spec, "required": True}
    if isinstance(spec, dict):
        unknown_field_keys = set(spec) - {"kind", "kinds", "required"}
        if unknown_field_keys:
            raise ValueError(
                f"unknown attributes for context schema field '{name}': "
                + ", ".join(sorted(unknown_field_keys))
            )
        if "kind" in spec and "kinds" in spec:
            raise ValueError(
                f"context schema field '{name}' cannot declare both kind and kinds"
            )
        return {
            "name": name,
            "kinds": spec.get("kinds", [spec.get("kind", "string")]),
            "required": spec.get("required", True),
        }
    raise ValueError(
        f"context schema field '{name}' must be a string, list, or object"
    )


def derive_context_schema(policy_text: str) -> DerivedContextSchema:
    """Infer a fail-closed ContextSchema shape from TARL policy references.

    Inference is conservative. If a referenced field has no clear kind, or if a
    field is used with incompatible kinds, the schema is marked incomplete and
    callers can fail closed before claiming proof readiness.
    """
    policy = PolicyParser.parse(policy_text)
    refs: dict[str, set[str]] = {}
    gaps: list[str] = []

    def add_ref(name: str, kind: str, reason: str = "") -> None:
        if not name or name in RESERVED_CONTEXT_FIELDS:
            return
        refs.setdefault(name, set()).add(kind)
        if reason:
            gaps.append(reason)

    for rule in policy.rules:
        try:
            tokens = PolicyParser._tokenize(rule.condition)
            parser = SafeExpr(tokens)
            node = parser.parse_expr()
            _infer_node(node, refs, gaps, expected="bool")
        except Exception as exc:
            gaps.append(
                f"rule {rule.source_line or '?'} could not be analyzed: {exc}"
            )

    fields_out: list[dict[str, Any]] = []
    for name, kinds in sorted(refs.items()):
        norm = _normalize_kinds(kinds)
        if norm is None:
            gaps.append(
                f"field '{name}' has ambiguous inferred kinds: "
                f"{', '.join(sorted(kinds))}"
            )
            continue
        fields_out.append({
            "name": name,
            "kinds": list(norm),
            "required": True,
        })

    status = "complete" if not gaps else "incomplete"
    return DerivedContextSchema(status=status, fields=fields_out, gaps=gaps)


def _normalize_kinds(kinds: set[str]) -> tuple[str, ...] | None:
    if not kinds:
        return None
    if kinds <= {"int", "float", "number"}:
        return ("number",)
    if len(kinds) == 1:
        return (next(iter(kinds)),)
    return None


def _field_name(node: Any) -> str | None:
    if not isinstance(node, tuple):
        return None
    tag = node[0]
    if tag == "ident":
        return str(node[1])
    if tag == "attr":
        return ".".join(str(p) for p in node[1])
    if tag == "source":
        return f"source:{node[1]}"
    return None


def _is_bound_field(name: str | None, bound: frozenset[str]) -> bool:
    """Return True when a reference belongs to a quantifier-local binder."""
    if not name:
        return False
    return any(name == item or name.startswith(f"{item}.") for item in bound)


def _literal_kind(node: Any) -> str | None:
    if not isinstance(node, tuple):
        return None
    tag = node[0]
    if tag in {"int", "float"}:
        return "number"
    if tag == "string":
        return "string"
    if tag == "bool":
        return "bool"
    if tag == "set":
        return "list"
    return None


def _infer_node(
    node: Any,
    refs: dict[str, set[str]],
    gaps: list[str],
    expected: str | None,
    bound: frozenset[str] = frozenset(),
) -> None:
    if not isinstance(node, tuple):
        return
    tag = node[0]

    name = _field_name(node)
    if name:
        if _is_bound_field(name, bound):
            return
        if expected is None:
            refs.setdefault(name, set())
            gaps.append(f"field '{name}' is referenced without an inferable kind")
        else:
            refs.setdefault(name, set()).add(expected)
        return

    if tag in {"and", "or"}:
        _infer_node(node[1], refs, gaps, expected="bool", bound=bound)
        _infer_node(node[2], refs, gaps, expected="bool", bound=bound)
        return
    if tag == "not":
        _infer_node(node[1], refs, gaps, expected="bool", bound=bound)
        return
    if tag == "compare":
        _infer_comparison(node[2], node[3], refs, gaps, bound=bound)
        return
    if tag in {"add", "sub", "mul", "div", "mod", "neg"}:
        for child in node[1:]:
            _infer_node(child, refs, gaps, expected="number", bound=bound)
        return
    if tag in {"in", "not_in"}:
        left, right = node[1], node[2]
        right_name = _field_name(right)
        left_name = _field_name(left)
        left_kind = _literal_kind(left)
        if right_name and not _is_bound_field(right_name, bound):
            refs.setdefault(right_name, set()).add("list")
        if left_name and not _is_bound_field(left_name, bound):
            right_kind = _literal_set_member_kind(right)
            if right_kind:
                refs.setdefault(left_name, set()).add(right_kind)
            else:
                refs.setdefault(left_name, set())
                gaps.append(
                    f"field '{left_name}' membership kind is ambiguous"
                )
        elif left_kind is not None:
            _infer_node(right, refs, gaps, expected="list", bound=bound)
        return
    if tag == "call":
        _infer_call(node, refs, gaps, bound=bound)
        return
    if tag in {"all", "any"}:
        _infer_node(node[1], refs, gaps, expected="list", bound=bound)
        binder = str(node[2])
        _infer_node(
            node[3],
            refs,
            gaps,
            expected="bool",
            bound=bound | {binder},
        )
        return
    if tag == "set":
        for child in node[1]:
            _infer_node(child, refs, gaps, expected=None, bound=bound)


def _literal_set_member_kind(node: Any) -> str | None:
    if not (isinstance(node, tuple) and node[0] == "set"):
        return None
    kinds = {kind for item in node[1] if (kind := _literal_kind(item)) is not None}
    if not kinds:
        return None
    norm = _normalize_kinds(kinds)
    return norm[0] if norm and len(norm) == 1 else None


def _infer_comparison(
    left: Any,
    right: Any,
    refs: dict[str, set[str]],
    gaps: list[str],
    bound: frozenset[str] = frozenset(),
) -> None:
    left_name = _field_name(left)
    right_name = _field_name(right)
    left_lit = _literal_kind(left)
    right_lit = _literal_kind(right)
    if left_name and right_lit and not _is_bound_field(left_name, bound):
        refs.setdefault(left_name, set()).add(right_lit)
    elif right_name and left_lit and not _is_bound_field(right_name, bound):
        refs.setdefault(right_name, set()).add(left_lit)
    else:
        _infer_node(left, refs, gaps, expected=None, bound=bound)
        _infer_node(right, refs, gaps, expected=None, bound=bound)


def _infer_call(
    node: tuple,
    refs: dict[str, set[str]],
    gaps: list[str],
    bound: frozenset[str] = frozenset(),
) -> None:
    name = str(node[1]).upper()
    args = list(node[2])
    if name in {
        "LOWER",
        "UPPER",
        "STARTS_WITH",
        "ENDS_WITH",
        "CONTAINS",
        "MATCHES",
        "ELAPSED_SINCE",
    }:
        for arg in args:
            _infer_node(arg, refs, gaps, expected="string", bound=bound)
    elif name == "LEN":
        for arg in args:
            fname = _field_name(arg)
            if fname and not _is_bound_field(fname, bound):
                refs.setdefault(fname, set())
                gaps.append(
                    f"field '{fname}' is used with LEN; list/string kind is ambiguous"
                )
            else:
                _infer_node(arg, refs, gaps, expected=None, bound=bound)
    else:
        for arg in args:
            _infer_node(arg, refs, gaps, expected=None, bound=bound)


def extract_proof_obligations(
    ast: Program,
    source: str,
    file_path: str,
    policy_text: str | None = None,
    policy_path: str | None = None,
    explicit_schema_path: str | None = None,
    diagnostics: list[Diagnostic] | None = None,
    target: str | None = None,
    governance_loss: bool = False,
) -> dict[str, Any]:
    mode = ast.header.mode if ast.header else "core"
    governed_module = mode == "governed"
    functions = _functions(ast)
    imports = _imports(ast)
    governed_names = {
        f["name"] for f in functions if f.get("governed") is True
    }
    alias_to_module = {
        item["alias"] or item["module_path"]: item["module_path"]
        for item in imports
    }

    capabilities: list[CapabilityObligation] = []
    sensitive_calls: list[dict[str, Any]] = []
    governed_calls: list[dict[str, Any]] = []
    _collect_effects(
        ast,
        alias_to_module,
        governed_names,
        capabilities,
        sensitive_calls,
        governed_calls,
        current_function=None,
        governed_module=governed_module,
    )

    contract_obligations = _contract_obligations(ast)
    required_actions = sorted(
        {c.action for c in capabilities}
        | {call["name"] for call in governed_calls}
    )
    unresolved_gaps: list[dict[str, str]] = []
    schema = None
    policy_hash = None
    policy_deps: dict[str, Any] = {
        "path": policy_path,
        "hash": None,
        "required_tarl_actions": required_actions,
        "rules": [],
        "includes": [],
    }
    if policy_text is not None:
        policy_hash = sha256_text(policy_text)
        policy = PolicyParser.parse(policy_text)
        policy_deps["hash"] = policy_hash
        policy_deps["rules"] = [
            {
                "index": i,
                "condition": rule.condition,
                "verdict": rule.verdict.value,
                "source_line": rule.source_line,
            }
            for i, rule in enumerate(policy.rules)
        ]
        policy_deps["includes"] = [
            {
                "name": ref.name,
                "alias": ref.alias,
                "is_file": ref.is_file,
            }
            for ref in policy.includes
        ]
        if explicit_schema_path:
            schema = load_explicit_context_schema(explicit_schema_path)
        else:
            schema = derive_context_schema(policy_text)
        if not schema.complete:
            unresolved_gaps.append({
                "category": "context_schema",
                "detail": "derived context schema is incomplete or ambiguous",
            })
    elif capabilities or governed_calls or governed_module:
        unresolved_gaps.append({
            "category": "policy",
            "detail": "policy source is required before proof can be verified",
        })
        schema = DerivedContextSchema(
            status="missing",
            source="none",
            fields=[],
            gaps=["no policy source was provided"],
        )

    if capabilities or governed_calls or governed_module:
        unresolved_gaps.append({
            "category": "authority",
            "detail": "runtime execution requires authority context",
        })

    if contract_obligations:
        unresolved_gaps.append({
            "category": "contracts",
            "detail": "contract predicates require runtime argument/result values",
        })

    diag_out = []
    for diag in diagnostics or []:
        diag_out.append({
            "code": diag.code,
            "severity": diag.severity,
            "message": diag.message,
            "span": list(diag.span),
        })

    return {
        "format": "thirsty.proof_obligations.v1",
        "file": file_path,
        "source_hash": sha256_text(source),
        "mode": mode,
        "functions": functions,
        "imports": imports,
        "stdlib_sensitive_calls": sensitive_calls,
        "governed_calls": governed_calls,
        "required_capabilities": [
            c.to_dict() for c in sorted(
                set(capabilities),
                key=lambda c: (c.action, c.target, c.source, c.function or ""),
            )
        ],
        "required_tarl_actions": required_actions,
        "authority_requirements": {
            "authority_required": bool(capabilities or governed_calls or governed_module),
            "authenticated_authority_required": "hardened-runtime-only",
            "fields": [
                {"name": name, "kinds": list(kinds), "required": True}
                for name, kinds in sorted(AUTHORITY_FIELDS.items())
            ],
        },
        "context_schema": schema.to_dict() if schema else None,
        "policy_dependencies": policy_deps,
        "contract_obligations": [c.to_dict() for c in contract_obligations],
        "proof_mode": {
            "verification": "required-for-governed-effects",
            "signature": "unsigned-unless-hardened",
            "policy_hash": policy_hash,
        },
        "audit_requirement": {
            "required": bool(capabilities or governed_calls or governed_module),
            "mode": "proof-record-required; durable archive required only when runtime demands audit",
        },
        "build": {
            "target": target,
            "governance_loss": governance_loss,
            "governance_loss_status": (
                "explicitly_allowed" if governance_loss else "not_detected"
            ),
        },
        "shadow_convergence_result": _shadow_status(ast),
        "governance_loss_status": (
            "explicitly_allowed" if governance_loss else "not_detected"
        ),
        "diagnostics": diag_out,
        "unresolved_proof_gaps": unresolved_gaps,
        "side_effects_executed": False,
    }


def denial_explanation(report: dict[str, Any]) -> dict[str, Any]:
    missing = []
    emitted_categories: set[str] = set()
    if report["policy_dependencies"]["hash"] is None:
        missing.append({
            "category": "policy",
            "detail": "attach a TARL policy with --policy",
        })
        emitted_categories.add("policy")
    schema = report.get("context_schema") or {}
    if schema.get("status") not in {"complete", "explicit"}:
        missing.append({
            "category": "context",
            "detail": "provide an explicit schema or make policy references derivable",
        })
        emitted_categories.add("context")
    if report["authority_requirements"]["authority_required"]:
        missing.append({
            "category": "authority",
            "detail": "runtime execution must provide authority context",
        })
    for gap in report.get("unresolved_proof_gaps", []):
        if gap.get("category") in emitted_categories:
            continue
        if gap not in missing:
            missing.append(gap)
    return {
        "format": "thirsty.denial_explanation.v1",
        "file": report["file"],
        "missing": missing,
        "required_capabilities": report["required_capabilities"],
        "required_tarl_actions": report["required_tarl_actions"],
        "context_schema": report.get("context_schema"),
        "side_effects_executed": False,
    }


def effect_warning_diagnostics(ast: Program) -> list[Diagnostic]:
    source = ""
    report = extract_proof_obligations(ast, source, "<checker>")
    diagnostics: list[Diagnostic] = []
    for cap in report["required_capabilities"]:
        diagnostics.append(Diagnostic(
            "W050",
            (
                f"effect requires proof obligation: action={cap['action']} "
                f"target={cap['target']}"
            ),
            (0, 0, 0, 0),
            "warning",
        ))
    for call in report["governed_calls"]:
        diagnostics.append(Diagnostic(
            "W051",
            f"governed call requires proof obligation: {call['name']}",
            (0, 0, 0, 0),
            "warning",
        ))
    return diagnostics


def _functions(ast: Program) -> list[dict[str, Any]]:
    result = []
    for stmt in ast.stmts:
        if isinstance(stmt, (FunctionDecl, GovernedFunctionDecl)):
            result.append(_function_info(stmt))
        elif isinstance(stmt, ClassDecl):
            for method in stmt.methods:
                info = _function_info(method)
                info["class"] = stmt.name
                result.append(info)
    return result


def _function_info(stmt: FunctionDecl | GovernedFunctionDecl) -> dict[str, Any]:
    info: dict[str, Any] = {
        "name": stmt.name,
        "params": [
            {"name": name, "type": ptype}
            for name, ptype in getattr(stmt, "params", [])
        ],
        "return_type": stmt.return_type,
        "governed": isinstance(stmt, GovernedFunctionDecl),
    }
    if isinstance(stmt, GovernedFunctionDecl):
        info["contracts"] = {
            "requires": stmt.requires_annotation,
            "ensures": stmt.ensures_annotation,
            "invariant": stmt.invariant_annotation,
        }
    return info


def _imports(ast: Program) -> list[dict[str, Any]]:
    result = []
    for stmt in ast.stmts:
        if isinstance(stmt, ImportStmt):
            result.append({
                "module_path": stmt.module_path,
                "alias": stmt.alias,
                "sensitive": stmt.module_path in SENSITIVE_STDLIB_CAPABILITIES,
            })
    return result


def _collect_effects(
    node: Any,
    alias_to_module: dict[str, str],
    governed_names: set[str],
    capabilities: list[CapabilityObligation],
    sensitive_calls: list[dict[str, Any]],
    governed_calls: list[dict[str, Any]],
    current_function: str | None,
    governed_module: bool,
) -> None:
    if isinstance(node, (FunctionDecl, GovernedFunctionDecl)):
        current_function = node.name
    if isinstance(node, ImportStmt) and governed_module:
        capabilities.append(CapabilityObligation(
            action="import",
            target=node.module_path,
            source="import",
            function=current_function,
        ))
    elif isinstance(node, PourStmt) and governed_module:
        capabilities.append(CapabilityObligation(
            action="write",
            target="stdout",
            source="pour",
            function=current_function,
        ))
    elif isinstance(node, SipStmt) and governed_module:
        capabilities.append(CapabilityObligation(
            action="read",
            target="stdin",
            source="sip",
            function=current_function,
        ))
    elif isinstance(node, CallExpr):
        _collect_call_effects(
            node,
            alias_to_module,
            governed_names,
            capabilities,
            sensitive_calls,
            governed_calls,
            current_function,
            governed_module,
        )

    for child in _children(node):
        _collect_effects(
            child,
            alias_to_module,
            governed_names,
            capabilities,
            sensitive_calls,
            governed_calls,
            current_function,
            governed_module,
        )


def _collect_call_effects(
    expr: CallExpr,
    alias_to_module: dict[str, str],
    governed_names: set[str],
    capabilities: list[CapabilityObligation],
    sensitive_calls: list[dict[str, Any]],
    governed_calls: list[dict[str, Any]],
    current_function: str | None,
    governed_module: bool,
) -> None:
    if isinstance(expr.callee, Identifier) and expr.callee.name in governed_names:
        governed_calls.append({
            "name": expr.callee.name,
            "function": current_function,
            "span": list(expr.span),
        })
    if not isinstance(expr.callee, MemberAccess):
        return
    receiver = expr.callee.obj
    if not isinstance(receiver, Identifier):
        return
    module_path = alias_to_module.get(receiver.name)
    if module_path is None:
        return
    action = SENSITIVE_STDLIB_CAPABILITIES.get(module_path, {}).get(
        expr.callee.member
    )
    if action is None:
        return
    target = f"{module_path}.{expr.callee.member}"
    sensitive_calls.append({
        "module": module_path,
        "function": expr.callee.member,
        "action": action,
        "called_from": current_function,
        "span": list(expr.span),
    })
    if governed_module:
        capabilities.append(CapabilityObligation(
            action=action,
            target=target,
            source="sensitive-stdlib-call",
            function=current_function,
        ))


def _contract_obligations(ast: Program) -> list[ContractObligation]:
    obligations: list[ContractObligation] = []
    for stmt in ast.stmts:
        candidates: list[Any] = []
        if isinstance(stmt, GovernedFunctionDecl):
            candidates.append(stmt)
        elif isinstance(stmt, ClassDecl):
            candidates.extend(
                m for m in stmt.methods if isinstance(m, GovernedFunctionDecl)
            )
        for decl in candidates:
            if decl.requires_annotation:
                obligations.append(ContractObligation(
                    decl.name, "entry", decl.requires_annotation))
            if decl.ensures_annotation:
                obligations.append(ContractObligation(
                    decl.name, "exit", decl.ensures_annotation))
            if decl.invariant_annotation:
                obligations.append(ContractObligation(
                    decl.name, "entry_exit", decl.invariant_annotation))
    return obligations


def _children(node: Any) -> list[Any]:
    if node is None or isinstance(node, (str, bytes, int, float, bool)):
        return []
    if isinstance(node, (list, tuple)):
        return list(node)
    if not is_dataclass(node):
        return []
    out = []
    for f in fields(node):
        if f.name == "span":
            continue
        out.append(getattr(node, f.name))
    return out


def _shadow_status(ast: Program) -> dict[str, Any]:
    mutations = [
        getattr(stmt, "name", "<unknown>")
        for stmt in ast.stmts
        if stmt.__class__.__name__ == "ShadowThirstMutation"
    ]
    if mutations:
        return {
            "available": False,
            "mutations": mutations,
            "reason": "static proof-obligation extraction does not run Shadow Thirst convergence",
        }
    return {
        "available": False,
        "mutations": [],
        "reason": "no Shadow Thirst mutation block found",
    }
