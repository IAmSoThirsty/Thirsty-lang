from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TaskNode:
    """A single agent invocation within a flow."""

    name: str
    agent: str
    input: Dict[str, object]
    resources: Dict[str, object] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Edge:
    """A directed dependency between two TaskNodes."""

    source: str
    target: str
    condition: Optional[str] = None  # expression over upstream results/metadata


@dataclass
class Policy:
    """Governance policy attached to a FlowDocument."""

    risk_level: str = "low"          # low | medium | high | critical
    requires_approval: bool = False
    retention: Optional[str] = None  # e.g. "30d", "90d"
    extra: Dict[str, object] = field(default_factory=dict)


@dataclass
class FlowDocument:
    """Raw AST produced by the parser — not yet validated or normalized."""

    version: int
    id: str
    tenant: str
    tasks: List[TaskNode]
    edges: List[Edge]
    policy: Policy
