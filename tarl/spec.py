"""TARL Specification - Decision types and verdicts"""
from dataclasses import dataclass
from enum import Enum
from typing import Any


class TarlVerdict(Enum):
    """Policy verdict types"""
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class TarlDecision:
    """Policy decision with verdict, reason, and metadata"""
    verdict: TarlVerdict
    reason: str
    metadata: dict[str, Any] | None = None

    def is_terminal(self) -> bool:
        """Check if decision terminates evaluation"""
        return self.verdict in (TarlVerdict.DENY, TarlVerdict.ESCALATE)
