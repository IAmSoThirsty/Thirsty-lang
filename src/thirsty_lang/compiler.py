from __future__ import annotations
from typing import Any, Dict, List

from .ir import IRFlow


def ir_to_monolith_tasks(flow: IRFlow) -> List[Dict[str, Any]]:
    """Compile an IRFlow to Monolith task payloads.

    Each task in the flow becomes one payload dict suitable for
    ``Supervisor.submit_task()``. Tasks are emitted in topological order
    (sources before targets) when possible; otherwise in declaration order.

    Args:
        flow: Validated, normalized IRFlow.

    Returns:
        List of payload dicts:
          {
            "meta": {
              "owner": str,          # flow tenant
              "priority": int,
              "labels": {...},
              "resource_hints": {"timeout_ms": int}
            },
            "agent": str,
            "input": {...},
            "flow_id": str,
          }
    """
    order = _topological_order(flow)
    tasks: List[Dict[str, Any]] = []
    for name in order:
        t = flow.tasks[name]
        tasks.append({
            "meta": {
                "owner": flow.tenant,
                "priority": t.priority,
                "labels": {
                    "flow_id": flow.id,
                    "task_name": t.name,
                    "agent": t.agent,
                    **t.labels,
                },
                "resource_hints": {
                    "timeout_ms": t.timeout_ms,
                },
            },
            "agent": t.agent,
            "input": t.input,
            "flow_id": flow.id,
        })
    return tasks


def ir_to_waterfall_spec(flow: IRFlow) -> Dict[str, Any]:
    """Compile an IRFlow to a Thirstys-Waterfall DAG spec.

    Args:
        flow: Validated, normalized IRFlow.

    Returns:
        Dict conforming to the Waterfall workflow definition schema:
          {
            "id": str,
            "tenant": str,
            "policy": {...},
            "tasks": [...],
            "edges": [...]
          }
    """
    order = _topological_order(flow)
    return {
        "id": flow.id,
        "tenant": flow.tenant,
        "policy": {
            "risk_level": flow.policy.risk_level,
            "requires_approval": flow.policy.requires_approval,
            "retention": flow.policy.retention,
        },
        "tasks": [
            {
                "name": t.name,
                "agent": t.agent,
                "priority": t.priority,
                "timeout_ms": t.timeout_ms,
                "labels": t.labels,
            }
            for name in order
            for t in [flow.tasks[name]]
        ],
        "edges": [
            {
                "from": e.source,
                "to": e.target,
                "condition": e.condition,
            }
            for e in flow.edges
        ],
    }


def _topological_order(flow: IRFlow) -> List[str]:
    """Kahn's algorithm — returns task names in topological order (sources first).

    Assumes the graph is a DAG (enforced by the validator).
    """
    from collections import defaultdict, deque

    in_degree: Dict[str, int] = {name: 0 for name in flow.tasks}
    adj: Dict[str, List[str]] = defaultdict(list)
    for e in flow.edges:
        adj[e.source].append(e.target)
        in_degree[e.target] += 1

    queue: deque[str] = deque(
        name for name, deg in sorted(in_degree.items()) if deg == 0
    )
    order: List[str] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for nxt in sorted(adj[node]):
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)

    return order
