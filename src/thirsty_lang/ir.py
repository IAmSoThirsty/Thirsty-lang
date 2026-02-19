from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class IRTask:
    """Normalized task node after validation."""

    name: str
    agent: str
    input: Dict[str, object]
    priority: int
    timeout_ms: int
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class IREdge:
    """Normalized dependency edge."""

    source: str
    target: str
    condition: Optional[str] = None


@dataclass
class IRPolicy:
    """Validated governance policy."""

    risk_level: str          # low | medium | high | critical
    requires_approval: bool
    retention: Optional[str]


@dataclass
class IRFlow:
    """Fully normalized, validated flow ready for compilation."""

    id: str
    tenant: str
    tasks: Dict[str, IRTask]    # keyed by task name for O(1) lookup
    edges: List[IREdge]
    policy: IRPolicy
