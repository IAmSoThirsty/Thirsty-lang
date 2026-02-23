"""
Thirsty-lang — The Hydration Language Family
=============================================

A fun, water-themed programming language with defensive security features.

Tiers:
    - Thirsty-Lang  (.thirsty) — variables, output, comments
    - Thirst of Gods (.tog)    — control flow, arithmetic, comparisons
    - T.A.R.L.      (.tarl)   — loops, functions, arrays, security
    - Thirsty's Shadow (.shadow) — classes, OOP

Usage::

    from thirsty_lang import ThirstyInterpreter

    interp = ThirstyInterpreter()
    output = interp.interpret('drink msg = "Hello"\\npour msg')
    print(output)  # ['Hello']
"""

from __future__ import annotations

__version__ = "2.0.0"
__author__ = "Jeremy Karrick"

from thirsty_lang.interpreter import ThirstyInterpreter, main, run_file

__all__ = [
    "ThirstyInterpreter",
    "main",
    "run_file",
    "__version__",
]
