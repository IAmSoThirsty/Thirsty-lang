"""TARL Policy - Policy evaluation framework"""
from collections.abc import Callable
from typing import Any

from .spec import TarlDecision


class TarlPolicy:
    """Policy with name and evaluation rule"""
    def __init__(self, name: str, rule: Callable[[dict[str, Any]], TarlDecision]):
        self.name = name
        self.rule = rule

    def evaluate(self, context: dict[str, Any]) -> TarlDecision:
        """Evaluate policy against context"""
        return self.rule(context)
