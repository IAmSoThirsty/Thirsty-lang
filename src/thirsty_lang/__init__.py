"""
Thirsty-Lang — Sovereign Stack workflow definition language.

Pipeline:
  parse_yaml(src) → FlowDocument
  validate_and_normalize(doc) → IRFlow
  ir_to_monolith_tasks(flow) → List[dict]   # submit via Supervisor
  ir_to_waterfall_spec(flow) → dict          # send to Thirstys-Waterfall
"""

from .errors import ParseError, ThirstyLangError, ValidationError
from .compiler import ir_to_monolith_tasks, ir_to_waterfall_spec
from .parser import parse_yaml
from .validator import validate_and_normalize

__all__ = [
    "parse_yaml",
    "validate_and_normalize",
    "ir_to_monolith_tasks",
    "ir_to_waterfall_spec",
    "ThirstyLangError",
    "ParseError",
    "ValidationError",
]
