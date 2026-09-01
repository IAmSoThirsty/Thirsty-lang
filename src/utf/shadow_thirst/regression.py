"""Regression analyzers for governed Shadow Thirst change admission.

These analyzers compare the candidate (``shadow``) block with the validated
``canonical`` block.  They deliberately report typed evidence instead of a
confidence score: a syntactic observation is not presented as a semantic
proof, and an unavailable AST becomes ``UNKNOWN`` rather than a pass.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any

from utf.shadow_thirst.core import ShadowModule, astwalk
from utf.thirsty_lang.ast import (
    ArrayLiteral,
    CallExpr,
    ForStmt,
    GovernedFunctionDecl,
    GuardExpr,
    Identifier,
    IfStmt,
    ImportStmt,
    MemberAccess,
    NewExpr,
    PourStmt,
    SecurityBlock,
    SipStmt,
    SpillageStmt,
    ThrowStmt,
    TimesStmt,
    WhileStmt,
)
from utf.thirsty_lang.module_system import SENSITIVE_STDLIB_CAPABILITIES


@dataclass(frozen=True)
class RegressionFinding:
    """One machine-readable regression finding."""

    code: str
    analyzer: str
    status: str
    severity: str
    method: str
    summary: str
    details: dict[str, Any]
    required_for_eligibility: bool = False


_DIRECT_EFFECTS = {
    "open": "file",
    "read": "read",
    "read_file": "read",
    "write": "write",
    "write_file": "write",
    "print": "write",
    "exec": "execute",
    "eval": "execute",
    "system": "execute",
    "spawn": "execute",
    "http_get": "network",
    "http_post": "network",
    "tcp_connect": "network",
    "tcp_listen": "network",
    "udp_send": "network",
}

_GOVERNANCE_CALLS = {
    "authorize",
    "check_policy",
    "evaluate_policy",
    "require_authority",
    "require_capability",
    "verify_proof",
    "verify_signature",
    "append_audit",
    "audit",
}


def _callee_name(expr: Any) -> str | None:
    if isinstance(expr, Identifier):
        return expr.name
    if isinstance(expr, MemberAccess):
        if isinstance(expr.obj, Identifier):
            return f"{expr.obj.name}.{expr.member}"
        return expr.member
    return None


def _effect_surface(block: Any) -> set[str]:
    """Collect capability-bearing effects visible in a parsed block."""
    aliases: dict[str, str] = {}
    surface: set[str] = set()
    for node in astwalk(block):
        if isinstance(node, ImportStmt):
            alias = node.alias or node.module_path.rsplit("::", 1)[-1]
            aliases[alias] = node.module_path
            surface.add(f"import:{node.module_path}")
        elif isinstance(node, PourStmt):
            surface.add("write:stdout")
        elif isinstance(node, SipStmt):
            surface.add("read:stdin")
        elif isinstance(node, ThrowStmt):
            surface.add("control:throw")

    for node in astwalk(block):
        if not isinstance(node, CallExpr):
            continue
        name = _callee_name(node.callee)
        if not name:
            continue
        leaf = name.rsplit(".", 1)[-1].lower()
        if leaf in _DIRECT_EFFECTS:
            surface.add(f"{_DIRECT_EFFECTS[leaf]}:{name}")
        if isinstance(node.callee, MemberAccess) and isinstance(
            node.callee.obj, Identifier
        ):
            module_path = aliases.get(node.callee.obj.name)
            capability_map = SENSITIVE_STDLIB_CAPABILITIES.get(module_path or "", {})
            action = capability_map.get(node.callee.member)
            if action:
                surface.add(f"{action}:{module_path}.{node.callee.member}")
    return surface


def analyze_security_regression(module: ShadowModule) -> RegressionFinding:
    if module.shadow_ast is None or module.canonical_ast is None:
        return RegressionFinding(
            code="ST-S001",
            analyzer="SecurityRegression",
            status="UNKNOWN",
            severity="CRITICAL",
            method="ast-effect-delta/v1",
            summary="Security regression could not be evaluated without both ASTs",
            details={},
            required_for_eligibility=True,
        )
    candidate = _effect_surface(module.shadow_ast)
    canonical = _effect_surface(module.canonical_ast)
    added = sorted(candidate - canonical)
    removed = sorted(canonical - candidate)
    if added:
        return RegressionFinding(
            code="ST-S002",
            analyzer="SecurityRegression",
            status="VIOLATED",
            severity="CRITICAL",
            method="ast-effect-delta/v1",
            summary="Candidate introduces capability-bearing effects",
            details={"added_effects": added, "removed_effects": removed},
            required_for_eligibility=True,
        )
    return RegressionFinding(
        code="ST-S003",
        analyzer="SecurityRegression",
        status="OBSERVED",
        severity="INFO",
        method="ast-effect-delta/v1",
        summary="No additional capability-bearing effect was observed",
        details={
            "candidate_effects": sorted(candidate),
            "canonical_effects": sorted(canonical),
            "removed_effects": removed,
        },
        required_for_eligibility=True,
    )


def _governance_surface(block: Any) -> dict[str, int]:
    surface: dict[str, int] = {}

    def add(name: str) -> None:
        surface[name] = surface.get(name, 0) + 1

    for node in astwalk(block):
        if isinstance(node, GovernedFunctionDecl):
            add("governed-function")
            if node.requires_expr is not None:
                add("requires")
            if node.ensures_expr is not None:
                add("ensures")
            if node.invariant_expr is not None:
                add("invariant")
        elif isinstance(node, GuardExpr):
            add("guard-expression")
        elif isinstance(node, SecurityBlock):
            add(f"security-block:{node.block_type}")
        elif isinstance(node, CallExpr):
            name = _callee_name(node.callee)
            if name and name.rsplit(".", 1)[-1].lower() in _GOVERNANCE_CALLS:
                add(f"governance-call:{name.rsplit('.', 1)[-1].lower()}")
    return surface


def analyze_governance_regression(module: ShadowModule) -> RegressionFinding:
    if module.shadow_ast is None or module.canonical_ast is None:
        return RegressionFinding(
            code="ST-G001",
            analyzer="GovernanceRegression",
            status="UNKNOWN",
            severity="CRITICAL",
            method="ast-governance-surface-delta/v1",
            summary="Governance regression could not be evaluated without both ASTs",
            details={},
            required_for_eligibility=True,
        )
    candidate = _governance_surface(module.shadow_ast)
    canonical = _governance_surface(module.canonical_ast)
    if not canonical:
        return RegressionFinding(
            code="ST-G002",
            analyzer="GovernanceRegression",
            status="INAPPLICABLE",
            severity="INFO",
            method="ast-governance-surface-delta/v1",
            summary="Canonical block exposes no in-block governance surface to compare",
            details={"candidate_surface": candidate},
            required_for_eligibility=False,
        )
    removed = {
        name: count - candidate.get(name, 0)
        for name, count in canonical.items()
        if candidate.get(name, 0) < count
    }
    if removed:
        return RegressionFinding(
            code="ST-G003",
            analyzer="GovernanceRegression",
            status="VIOLATED",
            severity="CRITICAL",
            method="ast-governance-surface-delta/v1",
            summary="Candidate removes governance-bearing structures",
            details={
                "removed": removed,
                "candidate_surface": candidate,
                "canonical_surface": canonical,
            },
            required_for_eligibility=True,
        )
    return RegressionFinding(
        code="ST-G004",
        analyzer="GovernanceRegression",
        status="OBSERVED",
        severity="INFO",
        method="ast-governance-surface-delta/v1",
        summary="Candidate preserves the canonical in-block governance surface",
        details={
            "candidate_surface": candidate,
            "canonical_surface": canonical,
        },
        required_for_eligibility=True,
    )


_BRANCH_TYPES = (IfStmt, WhileStmt, ForStmt, TimesStmt, SpillageStmt)
_ALLOCATION_TYPES = (NewExpr, ArrayLiteral)


def _max_ast_depth(node: Any, depth: int = 0) -> int:
    if node is None or not dataclasses.is_dataclass(node):
        return depth
    maximum = depth
    for field in dataclasses.fields(node):
        if field.name == "span":
            continue
        value = getattr(node, field.name)
        if dataclasses.is_dataclass(value):
            maximum = max(maximum, _max_ast_depth(value, depth + 1))
        elif isinstance(value, (list, tuple)):
            for item in value:
                if dataclasses.is_dataclass(item):
                    maximum = max(maximum, _max_ast_depth(item, depth + 1))
    return maximum


def _complexity(block: Any) -> dict[str, int]:
    nodes = list(astwalk(block))
    branches = sum(isinstance(node, _BRANCH_TYPES) for node in nodes)
    calls = sum(isinstance(node, CallExpr) for node in nodes)
    allocations = sum(isinstance(node, _ALLOCATION_TYPES) for node in nodes)
    depth = _max_ast_depth(block)
    score = len(nodes) + branches * 4 + calls * 2 + allocations * 3 + depth
    return {
        "score": score,
        "nodes": len(nodes),
        "branches": branches,
        "calls": calls,
        "allocations": allocations,
        "depth": depth,
    }


def analyze_complexity_regression(
    module: ShadowModule,
    *,
    max_ratio: float,
    max_delta: int,
) -> RegressionFinding:
    if module.shadow_ast is None or module.canonical_ast is None:
        return RegressionFinding(
            code="ST-C001",
            analyzer="ComplexityRegression",
            status="UNKNOWN",
            severity="WARNING",
            method="weighted-ast-metrics/v1",
            summary="Complexity regression could not be evaluated without both ASTs",
            details={},
        )
    candidate = _complexity(module.shadow_ast)
    canonical = _complexity(module.canonical_ast)
    baseline = max(1, canonical["score"])
    ratio = candidate["score"] / baseline
    delta = candidate["score"] - canonical["score"]
    details: dict[str, Any] = {
        "candidate": candidate,
        "canonical": canonical,
        "score_ratio": round(ratio, 6),
        "score_delta": delta,
        "limits": {"max_ratio": max_ratio, "max_delta": max_delta},
    }
    if ratio > max_ratio and delta > max_delta:
        return RegressionFinding(
            code="ST-C002",
            analyzer="ComplexityRegression",
            status="VIOLATED",
            severity="WARNING",
            method="weighted-ast-metrics/v1",
            summary="Candidate complexity exceeds configured regression limits",
            details=details,
        )
    return RegressionFinding(
        code="ST-C003",
        analyzer="ComplexityRegression",
        status="OBSERVED",
        severity="INFO",
        method="weighted-ast-metrics/v1",
        summary="Candidate complexity is within configured regression limits",
        details=details,
    )


def analyze_explainability_regression(
    module: ShadowModule,
    *,
    max_depth_delta: int,
) -> RegressionFinding:
    """Compare a declared explainability proxy without claiming comprehension.

    AST nesting depth is deterministic and reviewable, but it is only a proxy
    for explainability.  The evidence therefore remains ``OBSERVED`` even on a
    pass and the method name explicitly records the proxy.
    """
    if module.shadow_ast is None or module.canonical_ast is None:
        return RegressionFinding(
            code="ST-X001",
            analyzer="ExplainabilityRegression",
            status="UNKNOWN",
            severity="WARNING",
            method="ast-depth-proxy/v1",
            summary="Explainability proxy could not be evaluated without both ASTs",
            details={},
        )
    candidate_depth = _max_ast_depth(module.shadow_ast)
    canonical_depth = _max_ast_depth(module.canonical_ast)
    delta = candidate_depth - canonical_depth
    details = {
        "metric": "AST nesting depth (proxy, not semantic explainability)",
        "candidate_depth": candidate_depth,
        "canonical_depth": canonical_depth,
        "depth_delta": delta,
        "max_depth_delta": max_depth_delta,
    }
    if delta > max_depth_delta:
        return RegressionFinding(
            code="ST-X002",
            analyzer="ExplainabilityRegression",
            status="VIOLATED",
            severity="WARNING",
            method="ast-depth-proxy/v1",
            summary="Candidate exceeds the configured explainability-proxy limit",
            details=details,
        )
    return RegressionFinding(
        code="ST-X003",
        analyzer="ExplainabilityRegression",
        status="OBSERVED",
        severity="INFO",
        method="ast-depth-proxy/v1",
        summary="Candidate is within the configured explainability-proxy limit",
        details=details,
    )


__all__ = [
    "RegressionFinding",
    "analyze_complexity_regression",
    "analyze_explainability_regression",
    "analyze_governance_regression",
    "analyze_security_regression",
]
