"""Scalar Bool boundaries across compiled and recorded analysis surfaces."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import replace

import pytest

from utf.shadow_thirst import convergence
from utf.shadow_thirst.admission import (
    ENGINE_VERSION,
    AdmissionEngine,
    ChangeAdmissionRecord,
    EvidenceStatus,
)
from utf.shadow_thirst.core import ShadowModule, parse_block
from utf.tarl.keystore import ROLE_PROOF_SIGNER, generate
from utf.thirsty_lang import cli
from utf.thirsty_lang.interpreter import Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser


def parse(source):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors and not parser.errors
    return program


def block(source):
    result = parse_block(source)
    assert result is not None
    return result


def node_run(source):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for executable Boolean backend validation")
    return subprocess.run(
        [node, "-e", source], capture_output=True, text=True, timeout=10
    )


def packed(value):
    if type(value) is list:
        return ["List", [packed(item) for item in value]]
    if type(value) is int:
        return ["Int", str(value)]
    return [type(value).__name__, value]


_JS_PACK = """
function pack(v) {
  if (Array.isArray(v)) return ['List', v.map(pack)];
  if (typeof v === 'bigint') return ['Int', String(v)];
  const names = {boolean: 'bool', number: 'float', string: 'str'};
  return [v === null ? 'NoneType' : names[typeof v], v];
}
"""


INVALID_EXPRESSIONS = [
    *[
        f"{left} {op} {right}"
        for op in ["+", "-", "*", "/", "%", "<", "<=", ">", ">="]
        for left, right in [
            ("true", "false"),
            ("false", "true"),
            ("true", "1"),
            ("1", "false"),
            ("false", "1.0"),
        ]
    ],
    *[
        f"{left} {op} {right}"
        for op in ["==", "!="]
        for left, right in [
            ("true", "1"),
            ("0", "false"),
            ("false", "0.0"),
            ("true", "'yes'"),
            ("none", "false"),
            ("true", "[]"),
        ]
    ],
    "-true",
    "-false",
    "true * [1]",
    "[1] * false",
    "true * 'x'",
    "'x' * false",
]


@pytest.mark.parametrize("expression", INVALID_EXPRESSIONS)
def test_scalar_bool_operations_reject_in_runtime_and_js(expression):
    program = parse("drink main = " + expression)
    with pytest.raises(TypeError, match="Bool"):
        Interpreter().interpret(program)
    result = node_run(cli._transpile_to_js(program))
    assert result.returncode != 0
    assert "TypeError" in result.stderr and "Bool" in result.stderr


@pytest.mark.parametrize("expression", INVALID_EXPRESSIONS)
def test_llvm_bool_operations_reject_before_emission(expression, tmp_path):
    with pytest.raises(ValueError, match="LLVM"):
        cli._build_llvm(
            parse("drink result = " + expression + "; drink main = 0"),
            str(tmp_path / "bool"),
            "llvm-ir",
        )
    assert not (tmp_path / "bool.ll").exists()


@pytest.mark.parametrize(
    "expression",
    [
        "true == true",
        "true == false",
        "false != true",
        "false != false",
        "[] or true",
        "false and (true + 1)",
        "true or (false + 1)",
        "true and 7",
        "false or 8",
        "0 or false",
        "0 and true",
        "not true",
        "not 0",
        "[true] == [1]",
        "[false] != [0]",
        "[[true], false] == [[1], 0]",
        "[false] < [true]",
        "[true] >= [1]",
        "[[false]] <= [[true]]",
        "[false] < [0, true]",
    ],
)
def test_boolean_logic_and_native_container_comparison_preserve_runtime_values(
    expression,
):
    program = parse("drink main = " + expression)
    interpreter = Interpreter()
    interpreter.interpret(program)
    script = cli._transpile_to_js(program) + _JS_PACK
    script += f"console.log(JSON.stringify(pack({cli._js_name('main')})));"
    result = node_run(script)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.splitlines()[-1]) == packed(
        interpreter.env.get("main")
    )


@pytest.mark.parametrize(
    "expression",
    ["true == true", "true != false", "false == false", "not 0", "true or (false + 1)"],
)
def test_llvm_keeps_valid_bool_values_for_truthiness(expression):
    source = f"drink condition = {expression}; drink main = condition and 7"
    assert "ret i32 7" in cli._transpile_to_llvm_ir(parse(source))


@pytest.mark.parametrize(
    "operator", ["+", "-", "*", "%", "==", "!=", "<", "<=", ">", ">="]
)
def test_llvm_evaluates_each_operand_once_before_bool_rejection(operator):
    expr = parse(f"true {operator} 1").stmts[0].expr
    visits = []

    class RecordedEvaluator(cli._LLVMExpr):
        def evaluate(self, node, env):
            if node is expr.left or node is expr.right:
                visits.append(node)
            return super().evaluate(node, env)

    with pytest.raises(ValueError, match="Bool"):
        RecordedEvaluator().evaluate(expr, {})
    assert visits == [expr.left, expr.right]


def test_js_evaluates_each_operand_once_before_bool_rejection():
    source = """drink mut trace = 0
glass left() { trace = trace * 10 + 1; return true }
glass right() { trace = trace * 10 + 2; return 1 }
glass compute() { return left() + right() }
"""
    program = parse(source)
    script = cli._transpile_to_js(program)
    script += f"""
try {{ {cli._js_name('compute')}(); }} catch (error) {{
  console.log(JSON.stringify({{error: error.name, trace: String({cli._js_name('trace')})}}));
}}
"""
    result = node_run(script)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"error": "TypeError", "trace": "12"}


@pytest.mark.parametrize(
    "expression", ["true + 1", "-false", "false < true", "true == 1", "false != 0"]
)
def test_shadow_never_samples_invalid_bool_operations_as_success(expression):
    assert convergence._run_block_guarded(block("return " + expression), {}) == (
        False,
        None,
    )
    result = convergence.execute_and_compare(
        block("return " + expression), block("return 1")
    )
    assert result.status == "unsupported"


@pytest.mark.parametrize(
    ("left", "right"),
    [("true", "1"), ("false", "0"), ("1 < 2", "1"), ("true == false", "0")],
)
def test_z3_return_types_never_coerce_bool_to_int(left, right):
    pytest.importorskip("z3")
    candidate, canonical = "return " + left, "return " + right
    result = convergence.z3_equivalence(block(candidate), block(canonical))
    assert result.status == "diverge"
    assert "types differ" in result.detail
    record = AdmissionEngine().evaluate(
        ShadowModule("types", shadow_code=candidate, canonical_code=canonical)
    )
    proof = next(
        item for item in record.evidence if item.analyzer == "CanonicalConvergence"
    )
    assert proof.status == EvidenceStatus.VIOLATED
    assert record.admission_decision == "REJECTED"


@pytest.mark.parametrize("operator", ["==", "!="])
@pytest.mark.parametrize("left", [False, True])
@pytest.mark.parametrize("right", [False, True])
def test_z3_models_bool_equality_without_arithmetic_coercion(operator, left, right):
    pytest.importorskip("z3")
    expected = left == right if operator == "==" else left != right
    candidate = block(f"return {str(left).lower()} {operator} {str(right).lower()}")
    canonical = block("return " + str(expected).lower())
    result = convergence.z3_equivalence(candidate, canonical)
    assert result.status == "equivalent"
    assert result.assumptions == {}


@pytest.mark.parametrize(
    "expression", ["true + false", "-true", "true < false", "true == 1", "false != 0"]
)
def test_z3_abstains_from_invalid_bool_operations(expression):
    pytest.importorskip("z3")
    assert (
        convergence.z3_equivalence(
            block("return " + expression), block("return 0")
        ).status
        == "unsupported"
    )


@pytest.mark.parametrize("signed", [False, True])
@pytest.mark.parametrize(
    "old_method", ["alpha-renamed-ast-equivalence/v3", "z3-symbolic-equivalence/v3"]
)
def test_stored_pre_bool_records_require_reanalysis_but_retain_integrity(
    signed, old_method
):
    record = AdmissionEngine().evaluate(
        ShadowModule("historical", shadow_code="return 1", canonical_code="return 1")
    )
    record.engine_version = "0.3.0"
    record.evidence = [
        (
            replace(item, method=old_method)
            if item.status == EvidenceStatus.PROVEN
            else item
        )
        for item in record.evidence
    ]
    signer = generate("old-bool-method", ROLE_PROOF_SIGNER) if signed else None
    record.sign(signer) if signer else record.seal_unsigned()
    stored = ChangeAdmissionRecord.from_dict(json.loads(record.to_json()))
    key = signer.public_only() if signer else None
    assert stored.verify(key)[0] is False
    valid, reason = stored.verify(key, historical=True)
    assert valid and "semantic assurance was not verified" in reason
    stored.mutation_name = "tampered"
    assert stored.verify(key, historical=True)[0] is False


@pytest.mark.parametrize(
    "method", ["alpha-renamed-ast-equivalence/v3", "z3-symbolic-equivalence/v3"]
)
def test_current_engine_rejects_relabelled_pre_bool_methods(method):
    record = AdmissionEngine().evaluate(
        ShadowModule("current", shadow_code="return 1", canonical_code="return 1")
    )
    assert record.engine_version == ENGINE_VERSION == "0.4.0"
    record.evidence = [
        replace(item, method=method) if item.status == EvidenceStatus.PROVEN else item
        for item in record.evidence
    ]
    record.seal_unsigned()
    assert record.verify()[0] is False
