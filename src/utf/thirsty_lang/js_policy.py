"""Canonical stdout capability adapter for the governed JavaScript host.

The host sends one UTF-8 JSON request per process. A bind validates the policy
and asserted subject, check-write requests permission, and write requests it
again immediately before publishing UTF-8 bytes to stdout.
"""

from __future__ import annotations

import sys
from typing import BinaryIO, TextIO

from utf.tarl.broker import CapabilityBroker, CapabilityDenied
from utf.tarl.context import load_context_json
from utf.tarl.core import PolicyParser, SafeExpr, _strip_policy_comment
from utf.tarl.runtime import TarlRuntime
from utf.tarl.spec import TarlPolicy
from utf.thirsty_lang.proof_obligations import derive_context_schema

_FIELDS = {
    "action": "string",
    "target": "string",
    "authority": "string",
    "authority_subject": "string",
    "authority_authenticated": "bool",
    "authority_grants": "list",
}
_STATIC_FUNCTIONS = {
    "LOWER",
    "UPPER",
    "LEN",
    "CONTAINS",
    "STARTS_WITH",
    "ENDS_WITH",
    "MATCHES",
}


class _DelimitedExpression(SafeExpr):
    """Use TARL's expression grammar and require comma-separated arguments."""

    def _arguments(self, closing, parse_item):
        arguments = []
        if self.current().type != closing:
            arguments.append(parse_item())
            while self.current().type == "COMMA":
                self.advance()
                arguments.append(parse_item())
        self.expect(closing)
        return arguments

    def _parse_inline_set(self):
        self.expect("LBRACKET")
        return ("set", self._arguments("RBRACKET", self.parse_primary))

    def _parse_function_body(self, name):
        arguments = self._arguments("RPAREN", self.parse_expr)
        arity = 1 if name.upper() in {"LOWER", "UPPER", "LEN"} else 2
        if len(arguments) != arity:
            raise ValueError(f"{name} requires {arity} argument(s)")
        return ("call", name.upper(), arguments)


def _condition_key(condition: str) -> str:
    tokens = PolicyParser._tokenize(condition)
    for index, token in enumerate(tokens):
        if token.type == "STRING" and token.pos > len(condition):
            raise ValueError("unterminated policy string")
        if token.type in {"SOURCE", "DOT"}:
            raise ValueError("the stdout adapter has no external or nested context")
        if token.type == "IDENT":
            if tokens[index + 1].type == "LPAREN":
                if token.value.upper() not in _STATIC_FUNCTIONS:
                    raise ValueError(f"unsupported policy function {token.value}")
            elif token.value not in _FIELDS:
                raise ValueError(f"unknown stdout policy field {token.value}")
    parser = _DelimitedExpression(tokens)
    tree = parser.parse_expr()
    parser.expect("EOF")
    return repr(tree)


def _parse_policy(policy_text: str) -> TarlPolicy:
    if type(policy_text) is not str:
        raise ValueError("a TARL policy string is required")
    # Proofs bind the UTF-8 policy source. JSON can also encode lone surrogates.
    policy_text.encode("utf-8")
    conditions: set[str] = set()
    named = False
    for number, raw in enumerate(policy_text.split("\n"), 1):
        line = _strip_policy_comment(raw).strip()
        if not line:
            continue
        header = PolicyParser.POLICY_HEADER_RE.fullmatch(line)
        if header and not header.group(2) and not header.group(4):
            if named or conditions:
                raise ValueError(
                    f"line {number}: only one optional leading policy header is supported"
                )
            named = True
            continue
        rule = PolicyParser.RULE_RE.fullmatch(line)
        if rule is None or rule.group(3) is not None:
            raise ValueError(f"line {number}: expected a static TARL rule")
        try:
            key = _condition_key(rule.group(1).strip())
        except (SafeExpr.ParseError, ValueError, RecursionError) as error:
            raise ValueError(
                f"line {number}: invalid stdout policy condition: {error}"
            ) from error
        if key in conditions:
            raise ValueError(f"line {number}: duplicate policy condition")
        conditions.add(key)
    if not conditions:
        raise ValueError("at least one static TARL rule is required")

    policy = PolicyParser.parse(policy_text)
    schema = derive_context_schema(policy_text)
    if not schema.complete:
        raise ValueError(
            "the stdout policy requires a completely derived context schema"
        )
    for field in schema.fields:
        if _FIELDS.get(field["name"]) not in field["kinds"]:
            raise ValueError(f"unsupported stdout policy type for {field['name']}")
    return policy


def validate_js_policy(policy_text: str) -> None:
    """Validate the single-policy, fixed-context profile used by the Node host."""
    _parse_policy(policy_text)


def _serve(stdin: BinaryIO, stdout: BinaryIO, stderr: TextIO) -> int:
    try:
        request = load_context_json(stdin.read().decode("utf-8"))
        if type(request) is not dict:
            raise ValueError("expected an object")
        op = request.get("op")
        keys = {"op", "policy", "authority"}
        if op == "write":
            keys.add("text")
        if op not in ("bind", "check-write", "write") or set(request) != keys:
            raise ValueError("unexpected stdout broker request")
        authority = request["authority"]
        if type(authority) is not str or not authority.strip():
            raise ValueError("a nonblank host authority is required")
        authority.encode("utf-8")
        output = b""
        if op == "write":
            if type(request["text"]) is not str:
                raise ValueError("write requires text")
            output = request["text"].encode("utf-8") + b"\n"
        policy = _parse_policy(request["policy"])
    except (ValueError, RecursionError, SafeExpr.ParseError):
        print("Invalid governed stdout broker setup", file=stderr)
        return 1

    runtime = TarlRuntime(policy)
    try:
        if not runtime.ensure_context_schema():
            print("Invalid governed stdout broker schema", file=stderr)
            return 1
        broker = CapabilityBroker(runtime, authority=authority)
        if op == "bind":
            return 0
        try:
            broker.require("write", "stdout")
        except CapabilityDenied as denial:
            print(
                f"Governance denied: write stdout ({denial.decision.verdict.value})",
                file=stderr,
            )
            return 2
        except Exception:
            print("Governance denied: stdout policy evaluation failed", file=stderr)
            return 2
        if op == "write":
            stdout.write(output)
            stdout.flush()
        return 0
    finally:
        runtime.shutdown()


def main() -> int:
    try:
        return _serve(sys.stdin.buffer, sys.stdout.buffer, sys.stderr)
    except Exception:
        print("Governed stdout broker failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
