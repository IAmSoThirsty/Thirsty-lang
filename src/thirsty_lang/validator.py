from __future__ import annotations
from typing import Dict, List, Set

from .errors import ValidationError
from .grammar import FlowDocument
from .ir import IREdge, IRFlow, IRPolicy, IRTask

DEFAULT_PRIORITY = 0
DEFAULT_TIMEOUT_MS = 10_000
VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}


def validate_and_normalize(doc: FlowDocument) -> IRFlow:
    """Validate a FlowDocument and produce a normalized IRFlow.

    Validation rules:
      - flow id and tenant are required and non-empty
      - at least one task is required
      - task names are unique and non-empty
      - agent names are non-empty
      - edge source and target must refer to known task names
      - the task dependency graph must be acyclic (DAG)
      - risk_level must be one of low | medium | high | critical

    Args:
        doc: Raw FlowDocument from the parser.

    Returns:
        Validated, normalized IRFlow.

    Raises:
        ValidationError: on any constraint violation.
    """
    if not doc.id.strip():
        raise ValidationError("flow id is required and must be non-empty")
    if not doc.tenant.strip():
        raise ValidationError("tenant is required and must be non-empty")
    if not doc.tasks:
        raise ValidationError("at least one task is required")

    seen_names: Set[str] = set()
    ir_tasks: Dict[str, IRTask] = {}

    for t in doc.tasks:
        if not t.name.strip():
            raise ValidationError("task name is required and must be non-empty")
        if t.name in seen_names:
            raise ValidationError(f"duplicate task name: {t.name!r}")
        if not t.agent.strip():
            raise ValidationError(f"task {t.name!r}: agent is required")
        seen_names.add(t.name)

        priority = _int_field(t.resources, "priority", DEFAULT_PRIORITY, t.name)
        timeout_ms = _int_field(t.resources, "timeout_ms", DEFAULT_TIMEOUT_MS, t.name)
        if timeout_ms <= 0:
            raise ValidationError(f"task {t.name!r}: timeout_ms must be > 0")

        ir_tasks[t.name] = IRTask(
            name=t.name,
            agent=t.agent,
            input=t.input,
            priority=priority,
            timeout_ms=timeout_ms,
            labels=t.labels,
        )

    ir_edges: List[IREdge] = []
    for e in doc.edges:
        if e.source not in ir_tasks:
            raise ValidationError(
                f"edge source {e.source!r} does not match any task name"
            )
        if e.target not in ir_tasks:
            raise ValidationError(
                f"edge target {e.target!r} does not match any task name"
            )
        ir_edges.append(IREdge(source=e.source, target=e.target, condition=e.condition))

    if doc.policy.risk_level not in VALID_RISK_LEVELS:
        raise ValidationError(
            f"invalid risk_level {doc.policy.risk_level!r}; "
            f"must be one of {sorted(VALID_RISK_LEVELS)}"
        )

    _assert_dag(ir_tasks, ir_edges)

    ir_policy = IRPolicy(
        risk_level=doc.policy.risk_level,
        requires_approval=doc.policy.requires_approval,
        retention=doc.policy.retention,
    )

    return IRFlow(
        id=doc.id,
        tenant=doc.tenant,
        tasks=ir_tasks,
        edges=ir_edges,
        policy=ir_policy,
    )


def _int_field(
    resources: dict, key: str, default: int, task_name: str
) -> int:
    val = resources.get(key, default)
    try:
        return int(val)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"task {task_name!r}: {key} must be an integer, got {val!r}"
        ) from exc


def _assert_dag(tasks: Dict[str, IRTask], edges: List[IREdge]) -> None:
    """DFS cycle detection. Raises ValidationError if a cycle is found."""
    graph: Dict[str, Set[str]] = {name: set() for name in tasks}
    for e in edges:
        graph[e.source].add(e.target)

    visiting: Set[str] = set()
    visited: Set[str] = set()

    def dfs(node: str) -> None:
        if node in visiting:
            raise ValidationError(
                f"cycle detected in task dependency graph at {node!r}"
            )
        if node in visited:
            return
        visiting.add(node)
        for nxt in graph[node]:
            dfs(nxt)
        visiting.discard(node)
        visited.add(node)

    for name in tasks:
        dfs(name)
