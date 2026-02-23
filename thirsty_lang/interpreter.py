#!/usr/bin/env python3
"""
Thirsty-lang Python Interpreter
================================
Canonical pip-installable module for the Thirsty language family.

Supports all four tiers:
  - Thirsty-Lang (.thirsty)  — variables, output, comments
  - Thirst of Gods (.tog)    — control flow, arithmetic, comparisons
  - T.A.R.L. (.tarl)         — loops, functions, arrays, security
  - Thirsty's Shadow (.shadow) — classes, OOP (planned)
"""

from __future__ import annotations

import re
import sys
from typing import Any, Dict, List, Optional, Tuple


class ThirstyInterpreter:
    """Main interpreter class for the Thirsty language family."""

    VALID_EXTENSIONS = (".thirsty", ".tog", ".tarl", ".shadow")

    def __init__(self) -> None:
        self.variables: Dict[str, Any] = {}
        self.functions: Dict[str, Tuple[List[str], List[str]]] = {}
        self.output: List[str] = []

    # ── Public API ────────────────────────────────────────────────────────

    def interpret(self, code: str) -> List[str]:
        """Interpret Thirsty-lang code and return output lines."""
        self.output = []
        lines = code.strip().split("\n")
        self._execute_block(lines)
        return self.output

    def execute_line(self, line: str) -> None:
        """Execute a single line of Thirsty-lang code (public interface)."""
        self._execute_single(line.strip())

    def get_variables(self) -> Dict[str, Any]:
        """Return a copy of the current variable state."""
        return self.variables.copy()

    # ── Block execution (handles control flow) ────────────────────────────

    def _execute_block(self, lines: List[str], start: int = 0) -> int:
        """Execute a block of lines, returning the index after the last processed line."""
        i = start
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines and comments
            if not line or line.startswith("//") or line.startswith("#"):
                i += 1
                continue

            # ── Function definition: glass name(params) { ──
            glass_match = re.match(
                r"glass\s+(\w+)\s*\(([^)]*)\)\s*\{?", line
            )
            if glass_match:
                func_name = glass_match.group(1)
                params = [
                    p.strip()
                    for p in glass_match.group(2).split(",")
                    if p.strip()
                ]
                body_lines: List[str] = []
                i += 1
                brace_depth = 1
                while i < len(lines) and brace_depth > 0:
                    bl = lines[i].strip()
                    if bl == "}":
                        brace_depth -= 1
                        if brace_depth == 0:
                            break
                    else:
                        if bl.endswith("{"):
                            brace_depth += 1
                        body_lines.append(lines[i])
                    i += 1
                self.functions[func_name] = (params, body_lines)
                i += 1
                continue

            # ── Conditional: thirsty condition { ──
            thirsty_match = re.match(r"thirsty\s+(.+?)\s*\{?\s*$", line)
            if thirsty_match:
                condition = thirsty_match.group(1)
                cond_result = self._evaluate_condition(condition)

                # Collect if-body
                if_body: List[str] = []
                i += 1
                brace_depth = 1
                while i < len(lines):
                    bl = lines[i].strip()
                    if bl == "}":
                        brace_depth -= 1
                        if brace_depth == 0:
                            i += 1
                            break
                    elif bl.startswith("hydrated"):
                        break
                    else:
                        if bl.endswith("{"):
                            brace_depth += 1
                        if_body.append(lines[i])
                    i += 1

                # Collect else-body if present
                else_body: List[str] = []
                if i < len(lines) and lines[i].strip().startswith("hydrated"):
                    i += 1
                    brace_depth = 1
                    while i < len(lines):
                        bl = lines[i].strip()
                        if bl == "}":
                            brace_depth -= 1
                            if brace_depth == 0:
                                i += 1
                                break
                        else:
                            if bl.endswith("{"):
                                brace_depth += 1
                            else_body.append(lines[i])
                        i += 1

                if cond_result:
                    self._execute_block(if_body)
                else:
                    self._execute_block(else_body)
                continue

            # ── Loop: refill condition { ──
            refill_match = re.match(r"refill\s+(.+?)\s*\{?\s*$", line)
            if refill_match:
                condition = refill_match.group(1)
                loop_body: List[str] = []
                i += 1
                brace_depth = 1
                while i < len(lines):
                    bl = lines[i].strip()
                    if bl == "}":
                        brace_depth -= 1
                        if brace_depth == 0:
                            i += 1
                            break
                    else:
                        if bl.endswith("{"):
                            brace_depth += 1
                        loop_body.append(lines[i])
                    i += 1

                safety = 0
                while self._evaluate_condition(condition) and safety < 10000:
                    self._execute_block(loop_body)
                    safety += 1
                continue

            # ── Single-line statements ──
            try:
                result = self._execute_single(line)
                if result == "__RETURN__":
                    return i
            except Exception as e:
                error_msg = f"Error on line {i + 1}: {e!s}"
                print(error_msg, file=sys.stderr)
                self.output.append(f"ERROR: {error_msg}")

            i += 1

        return i

    # ── Single-line execution ─────────────────────────────────────────────

    def _execute_single(self, line: str) -> Optional[str]:
        """Execute a single statement. Returns '__RETURN__' for return statements."""
        # Variable declaration: drink varname = value
        drink_match = re.match(r"drink\s+([\w.]+)\s*=\s*(.+)", line)
        if drink_match:
            var_name = drink_match.group(1)
            value_expr = drink_match.group(2).strip()
            self.variables[var_name] = self._evaluate_expression(value_expr)
            return None

        # Output statement: pour expression
        pour_match = re.match(r"pour\s+(.+)", line)
        if pour_match:
            expr = pour_match.group(1).strip()
            value = self._evaluate_expression(expr)
            output_str = str(value)
            print(output_str)
            self.output.append(output_str)
            return None

        # Input statement: sip varname
        sip_match = re.match(r"sip\s+(\w+)", line)
        if sip_match:
            var_name = sip_match.group(1)
            user_input = input(f"Enter value for {var_name}: ")
            self.variables[var_name] = user_input
            return None

        # Return statement
        return_match = re.match(r"return\s+(.+)", line)
        if return_match:
            expr = return_match.group(1).strip()
            self.variables["__return__"] = self._evaluate_expression(expr)
            return "__RETURN__"

        if line == "return":
            self.variables["__return__"] = None
            return "__RETURN__"

        # Array declaration: reservoir name = [...]
        reservoir_match = re.match(r"reservoir\s+(\w+)\s*=\s*\[([^\]]*)\]", line)
        if reservoir_match:
            var_name = reservoir_match.group(1)
            elements_str = reservoir_match.group(2).strip()
            if elements_str:
                elements = [
                    self._evaluate_expression(e.strip())
                    for e in elements_str.split(",")
                ]
            else:
                elements = []
            self.variables[var_name] = elements
            return None

        # Security keywords (no-op stubs for now)
        for kw in ("shield", "sanitize", "armor", "detect", "defend"):
            if line.startswith(kw):
                return None

        # Function call: name(args)
        call_match = re.match(r"(\w+)\s*\(([^)]*)\)", line)
        if call_match:
            func_name = call_match.group(1)
            if func_name in self.functions:
                self._call_function(func_name, call_match.group(2))
                return None

        # Method call on variable: obj.method(args)
        method_match = re.match(r"(\w+)\.(\w+)\s*\(([^)]*)\)", line)
        if method_match:
            obj_name = method_match.group(1)
            method = method_match.group(2)
            args = method_match.group(3)
            self._call_method(obj_name, method, args)
            return None

        # Closing brace (no-op)
        if line == "}":
            return None

        raise SyntaxError(f"Unknown statement: {line}")

    # ── Expression evaluation ─────────────────────────────────────────────

    def _evaluate_expression(self, expr: str) -> Any:
        """Evaluate an expression and return its value."""
        expr = expr.strip()

        # String literal
        if (expr.startswith('"') and expr.endswith('"')) or (
            expr.startswith("'") and expr.endswith("'")
        ):
            return expr[1:-1]

        # Boolean literals (Thirsty keywords)
        if expr == "parched":
            return True
        if expr == "quenched":
            return False
        if expr.lower() == "true":
            return True
        if expr.lower() == "false":
            return False

        # Number literal
        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass

        # String concatenation with +
        if "+" in expr and '"' in expr:
            return self._evaluate_string_concat(expr)

        # Arithmetic expression
        if any(op in expr for op in ("+", "-", "*", "/")):
            try:
                return self._evaluate_arithmetic(expr)
            except Exception:
                pass

        # Array access: name[index]
        array_match = re.match(r"(\w+)\[(.+)\]", expr)
        if array_match:
            arr_name = array_match.group(1)
            index_expr = array_match.group(2)
            arr = self.variables.get(arr_name)
            if isinstance(arr, list):
                idx = int(self._evaluate_expression(index_expr))
                return arr[idx]

        # Property access: name.prop
        prop_match = re.match(r"(\w+)\.(\w+)", expr)
        if prop_match:
            obj_name = prop_match.group(1)
            prop = prop_match.group(2)
            obj = self.variables.get(obj_name)

            # Array length
            if isinstance(obj, list) and prop == "length":
                return len(obj)

            # Math constants
            if obj_name == "Math":
                import math

                if prop == "PI":
                    return math.pi
                if prop == "E":
                    return math.e

            # String methods
            if isinstance(obj, str):
                if prop == "length":
                    return len(obj)
                if prop == "upper":
                    return obj.upper()
                if prop == "lower":
                    return obj.lower()

            # Variable with dot notation
            full_name = f"{obj_name}.{prop}"
            if full_name in self.variables:
                return self.variables[full_name]

        # Math function call: Math.pow(x, y), Math.sqrt(x), etc.
        math_call = re.match(r"Math\.(\w+)\((.+)\)", expr)
        if math_call:
            import math

            func_name = math_call.group(1)
            args_str = math_call.group(2)
            args = [
                self._evaluate_expression(a.strip()) for a in args_str.split(",")
            ]
            math_funcs = {
                "pow": math.pow,
                "sqrt": math.sqrt,
                "abs": abs,
                "floor": math.floor,
                "ceil": math.ceil,
                "round": round,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "log": math.log,
                "max": max,
                "min": min,
            }
            if func_name in math_funcs:
                return math_funcs[func_name](*args)

        # String function call: String.repeat(str, n), etc.
        string_call = re.match(r"String\.(\w+)\((.+)\)", expr)
        if string_call:
            func_name = string_call.group(1)
            args_str = string_call.group(2)
            args = [
                self._evaluate_expression(a.strip()) for a in args_str.split(",")
            ]
            if func_name == "repeat":
                return str(args[0]) * int(args[1])
            if func_name == "length":
                return len(str(args[0]))
            if func_name == "upper":
                return str(args[0]).upper()
            if func_name == "lower":
                return str(args[0]).lower()

        # Function call as expression: name(args)
        call_match = re.match(r"(\w+)\s*\(([^)]*)\)", expr)
        if call_match:
            func_name = call_match.group(1)
            if func_name in self.functions:
                return self._call_function(func_name, call_match.group(2))

        # Variable reference
        if expr in self.variables:
            return self.variables[expr]

        # Fallback — return as string
        return expr

    def _evaluate_string_concat(self, expr: str) -> str:
        """Evaluate string concatenation expressions."""
        parts: List[str] = []
        current = ""
        in_string = False
        quote_char = ""

        for ch in expr:
            if not in_string and ch in ('"', "'"):
                in_string = True
                quote_char = ch
                current += ch
            elif in_string and ch == quote_char:
                in_string = False
                current += ch
            elif not in_string and ch == "+":
                parts.append(current.strip())
                current = ""
            else:
                current += ch

        if current.strip():
            parts.append(current.strip())

        return "".join(str(self._evaluate_expression(p)) for p in parts)

    def _evaluate_arithmetic(self, expr: str) -> Any:
        """Evaluate a simple arithmetic expression."""
        # Tokenize respecting order of operations
        expr = expr.strip()

        # Handle subtraction and addition
        for op in ("+", "-"):
            depth = 0
            i = len(expr) - 1
            while i >= 0:
                if expr[i] == ")":
                    depth += 1
                elif expr[i] == "(":
                    depth -= 1
                elif depth == 0 and expr[i] == op and i > 0:
                    left = self._evaluate_expression(expr[:i])
                    right = self._evaluate_expression(expr[i + 1 :])
                    if op == "+":
                        return float(left) + float(right)
                    return float(left) - float(right)
                i -= 1

        # Handle multiplication and division
        for op in ("*", "/"):
            depth = 0
            i = len(expr) - 1
            while i >= 0:
                if expr[i] == ")":
                    depth += 1
                elif expr[i] == "(":
                    depth -= 1
                elif depth == 0 and expr[i] == op:
                    left = self._evaluate_expression(expr[:i])
                    right = self._evaluate_expression(expr[i + 1 :])
                    if op == "*":
                        return float(left) * float(right)
                    if float(right) == 0:
                        raise ZeroDivisionError("Division by zero")
                    return float(left) / float(right)
                i -= 1

        raise ValueError(f"Cannot evaluate arithmetic: {expr}")

    # ── Condition evaluation ──────────────────────────────────────────────

    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a boolean condition."""
        condition = condition.strip()

        for op, symbol in [(">=", ">="), ("<=", "<="), (">", ">"), ("<", "<"), ("==", "=="), ("!=", "!=")]:
            if symbol in condition:
                parts = condition.split(symbol, 1)
                left = self._evaluate_expression(parts[0].strip())
                right = self._evaluate_expression(parts[1].strip())
                if op == ">=":
                    return float(left) >= float(right)
                if op == "<=":
                    return float(left) <= float(right)
                if op == ">":
                    return float(left) > float(right)
                if op == "<":
                    return float(left) < float(right)
                if op == "==":
                    return left == right
                if op == "!=":
                    return left != right

        # Single value truthy check
        val = self._evaluate_expression(condition)
        return bool(val)

    # ── Function calls ────────────────────────────────────────────────────

    def _call_function(self, name: str, args_str: str) -> Any:
        """Call a Thirsty-lang function."""
        params, body = self.functions[name]
        args = [
            self._evaluate_expression(a.strip())
            for a in args_str.split(",")
            if a.strip()
        ]

        # Save state
        saved_vars = self.variables.copy()

        # Bind parameters
        for param, arg in zip(params, args):
            self.variables[param] = arg

        # Execute body
        self._execute_block(body)

        # Get return value
        return_val = self.variables.get("__return__")

        # Restore state (keep output)
        self.variables = saved_vars
        if return_val is not None:
            self.variables["__return__"] = return_val

        return return_val

    def _call_method(self, obj_name: str, method: str, args_str: str) -> Any:
        """Call a method on an object."""
        obj = self.variables.get(obj_name)
        args = [
            self._evaluate_expression(a.strip())
            for a in args_str.split(",")
            if a.strip()
        ]

        if isinstance(obj, list):
            if method == "push":
                obj.append(args[0] if args else None)
            elif method == "pop":
                return obj.pop() if obj else None
            elif method == "length":
                return len(obj)

        return None


# ── Module-level API ──────────────────────────────────────────────────────


def run_file(filename: str) -> None:
    """Run a Thirsty-lang file."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            code = f.read()

        interpreter = ThirstyInterpreter()
        interpreter.interpret(code)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e!s}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point for the Python interpreter CLI."""
    if len(sys.argv) < 2:
        print("Usage: thirsty <file.thirsty>")
        print("       python -m thirsty_lang <file.thirsty>")
        sys.exit(1)

    filename = sys.argv[1]
    run_file(filename)


if __name__ == "__main__":
    main()
