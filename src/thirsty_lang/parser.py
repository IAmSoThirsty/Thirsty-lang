from __future__ import annotations
from typing import Any, Dict, List
import yaml

from .errors import ParseError
from .grammar import Edge, FlowDocument, Policy, TaskNode


def parse_yaml(src: str) -> FlowDocument:
    """Parse a Thirsty-Lang YAML flow definition into a FlowDocument AST.

    Args:
        src: Raw YAML string.

    Returns:
        FlowDocument with un-validated task/edge data.

    Raises:
        ParseError: on YAML syntax errors or missing required fields.
    """
    try:
        raw = yaml.safe_load(src)
    except yaml.YAMLError as exc:
        raise ParseError(f"YAML parse error: {exc}") from exc

    if not isinstance(raw, dict):
        raise ParseError("top-level document must be a mapping")

    version = int(raw.get("version", 1))
    flow_id = str(raw.get("id", ""))
    tenant = str(raw.get("tenant", ""))

    raw_tasks = _require_list(raw, "tasks")
    tasks: List[TaskNode] = []
    for t in raw_tasks:
        if not isinstance(t, dict):
            raise ParseError("each task entry must be a mapping")
        tasks.append(
            TaskNode(
                name=str(t.get("name", "")),
                agent=str(t.get("agent", "")),
                input=dict(t.get("input", {}) or {}),
                resources=dict(t.get("resources", {}) or {}),
                labels=dict(t.get("labels", {}) or {}),
            )
        )

    raw_edges = raw.get("edges") or []
    if not isinstance(raw_edges, list):
        raise ParseError("edges must be a list")
    edges: List[Edge] = []
    for e in raw_edges:
        if not isinstance(e, dict):
            raise ParseError("each edge entry must be a mapping")
        edges.append(
            Edge(
                source=str(e.get("from", "")),
                target=str(e.get("to", "")),
                condition=e.get("condition"),
            )
        )

    raw_policy = raw.get("policy") or {}
    policy = Policy(
        risk_level=str(raw_policy.get("risk_level", "low")),
        requires_approval=bool(raw_policy.get("requires_approval", False)),
        retention=raw_policy.get("retention"),
        extra={
            k: v
            for k, v in raw_policy.items()
            if k not in {"risk_level", "requires_approval", "retention"}
        },
    )

    return FlowDocument(
        version=version,
        id=flow_id,
        tenant=tenant,
        tasks=tasks,
        edges=edges,
        policy=policy,
    )


def _require_list(raw: Dict[str, Any], key: str) -> list:
    value = raw.get(key)
    if value is None:
        raise ParseError(f"missing required field: {key!r}")
    if not isinstance(value, list):
        raise ParseError(f"{key!r} must be a list")
    return value
