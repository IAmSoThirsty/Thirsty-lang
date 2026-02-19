from __future__ import annotations


class ThirstyLangError(Exception):
    """Base class for all Thirsty-Lang errors."""


class ParseError(ThirstyLangError):
    """Raised when the YAML/JSON source cannot be parsed into a FlowDocument."""


class ValidationError(ThirstyLangError):
    """Raised when a FlowDocument fails static validation rules."""


class CompileError(ThirstyLangError):
    """Raised when a validated IRFlow cannot be compiled to a target format."""
