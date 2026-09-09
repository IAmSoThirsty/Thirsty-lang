"""
Lock test: every shipped example parses, type-checks, and (where runnable)
executes with zero diagnostics. This keeps the language's own examples from
drifting away from the implemented grammar.
"""

import glob
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
from utf.thirsty_lang.checker import check_ast
from utf.thirsty_lang.interpreter import Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "src", "utf", "examples")

THIRSTY_EXAMPLES = sorted(
    glob.glob(os.path.join(EXAMPLES_DIR, "**", "*.thirsty"), recursive=True)
    + glob.glob(os.path.join(EXAMPLES_DIR, "**", "*.thirstofgods"), recursive=True)
)
TARL_EXAMPLES = sorted(
    glob.glob(os.path.join(EXAMPLES_DIR, "**", "*.tarl"), recursive=True)
)


def _rel(path):
    return os.path.relpath(path, EXAMPLES_DIR)


@pytest.mark.parametrize("path", THIRSTY_EXAMPLES, ids=_rel)
def test_thirsty_example_parses_checks_runs(path, monkeypatch, capsys):
    with open(path, encoding="utf-8") as f:
        source = f.read()

    lexer = Lexer(source)
    tokens = lexer.lex()
    assert not lexer.errors, f"lex errors in {_rel(path)}: {lexer.errors}"

    parser = Parser(tokens)
    ast = parser.parse()
    assert not parser.errors, (
        f"parse errors in {_rel(path)}: " f"{[e.message for e in parser.errors]}"
    )

    diags = check_ast(ast)
    assert not diags, (
        f"checker diagnostics in {_rel(path)}: " f"{[d.message for d in diags]}"
    )

    # Example policies describe that example's effects. An unrelated sibling
    # policy.tarl is a policy-language sample, not ambient execution authority.
    relative = Path(path).resolve().relative_to(Path(EXAMPLES_DIR).resolve()).as_posix()
    policy_source = None
    if relative == "governed_agent_runner/main.thirsty":
        policy_source = Path(path).with_name("policy.tarl").read_text(encoding="utf-8")
    elif relative in {"hello.thirsty", "gods.thirstofgods"}:
        policy_source = (
            'when action == "write" and target == "stdout" => ALLOW\nwhen true => DENY'
        )
    elif relative == "data_report/main.thirsty":
        input_path = Path(path).resolve().with_name("orders.json").as_posix()
        monkeypatch.setenv("THIRSTY_REPORT_INPUT", input_path)
        grants = [
            ("import", f"thirst::{namespace}")
            for namespace in ("collections", "json", "fs", "env")
        ] + [
            ("read", "thirst::env.get:THIRSTY_REPORT_INPUT"),
            ("read", f"thirst::fs.read_file:{input_path}"),
            ("write", "stdout"),
        ]
        policy_source = (
            "\n".join(
                f"when action == {json.dumps(action)} and target == {json.dumps(target)} => ALLOW"
                for action, target in grants
            )
            + "\nwhen true => DENY"
        )
    interp = Interpreter()
    interp.source_directory = Path(path).resolve().parent
    runtime = None
    if policy_source is not None:
        runtime = TarlRuntime(PolicyParser.parse(policy_source))
        interp.attach_tarl(runtime).set_authority("example")
    try:
        interp.interpret(ast)
        output = capsys.readouterr().out
        if relative == "compiler_scalar.thirsty":
            assert interp.env.get("main") == 11
            assert output == ""
        elif relative == "data_report/main.thirsty":
            report = json.loads(output)
            assert report["orders"] == 4
            assert report["revenue_cents"] == 8900
        else:
            expected = {
                "hello.thirsty": "hello, thirsty world!\n",
                "gods.thirstofgods": "ok: test\n",
                "governed_agent_runner/main.thirsty": "processed: sample data\n",
            }
            if relative in expected:
                assert output == expected[relative]
    finally:
        interp.executor.shutdown(wait=True)
        if runtime is not None:
            runtime.shutdown()


@pytest.mark.parametrize("path", TARL_EXAMPLES, ids=_rel)
def test_tarl_example_parses(path):
    from utf.tarl.core import PolicyParser

    with open(path, encoding="utf-8") as f:
        source = f.read()
    policy = PolicyParser.parse(source)
    assert policy is not None


def test_examples_discovered():
    # Guard against the globs silently matching nothing.
    assert THIRSTY_EXAMPLES, "no .thirsty/.thirstofgods examples found"
    assert TARL_EXAMPLES, "no .tarl examples found"
