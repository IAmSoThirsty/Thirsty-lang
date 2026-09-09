"""Executable backend counterexamples, supported subsets, and artifact gates."""

from __future__ import annotations

import json
import math
import random
import shutil
import struct
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from utf.thirsty_lang import cli
from utf.thirsty_lang.interpreter import Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.package_manager import runtime_source_integrity
from utf.thirsty_lang.parser import Parser


def parse(source):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    ast = parser.parse()
    assert not lexer.errors and not parser.errors
    return ast


def packed(value):
    if type(value) is float:
        if math.isnan(value):
            return ["Float", "NaN"]
        return ["Float", struct.pack(">d", value).hex()]
    if type(value) is int:
        return ["Int", str(value)]
    if type(value) is list:
        return ["List", [packed(item) for item in value]]
    return [type(value).__name__, value]


_JS_PACK = """
function __pack(v) {
  if (typeof v === 'bigint') return ['Int', String(v)];
  if (typeof v === 'number') {
    if (Number.isNaN(v)) return ['Float', 'NaN'];
    const buffer = new ArrayBuffer(8); new DataView(buffer).setFloat64(0, v, false);
    return ['Float', Array.from(new Uint8Array(buffer), x => x.toString(16).padStart(2, '0')).join('')];
  }
  if (Array.isArray(v)) return ['List', v.map(__pack)];
  if (v === null) return ['NoneType', null];
  return [typeof v === 'boolean' ? 'bool' : 'str', v];
}
"""


def run_js(source):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for executable JS backend validation")
    program = cli._transpile_to_js(parse(source))
    program += (
        _JS_PACK + f"console.log(JSON.stringify(__pack({cli._js_name('main')})));"
    )
    result = subprocess.run(
        [node, "-e", program], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.splitlines()[-1])


@pytest.mark.parametrize(
    "expression",
    [
        "1 % -2",
        "-4 % 2",
        "-4 % 2.0",
        "1 % -2.0",
        "0 / -1",
        "[1, 2, [3]] + [4]",
        "[1, [2]] * 2",
        "3 * 'a'",
        "[] or [7]",
        "[] and (1 / 0)",
        "not []",
        "[1] == [1.0]",
        "[1, 3] > [1, 2]",
        "'𐀀' < '\ue000'",
        "9007199254740993 == 9007199254740992.0",
        "9007199254740993 + 0.0",
        "(1 < 2) and 2",
        "1 / 3",
        f"{1 << 2000} / {1 << 2000}",
        f"1 / {1 << 1075}",
        f"3 / {1 << 1075}",
    ],
)
def test_js_values_match_reference_interpreter(expression):
    source = "drink main = " + expression
    interpreter = Interpreter()
    interpreter.interpret(parse(source))
    assert run_js(source) == packed(interpreter.env.get("main"))


def test_js_integer_division_rounding_matches_python_across_bit_lengths():
    rng = random.Random(7619)
    for _ in range(25):
        numerator = rng.getrandbits(rng.randint(1, 1800))
        denominator = rng.getrandbits(rng.randint(1, 1800)) or 1
        try:
            expected = numerator / denominator
        except OverflowError:
            continue
        assert run_js(f"drink main = {numerator} / {denominator}") == packed(expected)


def test_js_bare_return_matches_none():
    assert run_js("glass f() { return } drink main = f()") == packed(None)


def test_js_local_functions_and_early_return_match_runtime():
    assert run_js(
        "glass f(x) { drink y = x + 1; return y; return 99 } drink main = f(2)"
    ) == packed(3)


def test_js_does_not_hoist_callable_availability():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required")
    source = "drink main = f(); glass f() { return 1 }"
    with pytest.raises(NameError):
        Interpreter().interpret(parse(source))
    result = subprocess.run(
        [node, "-e", cli._transpile_to_js(parse(source))],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0


@pytest.mark.parametrize(
    "source",
    [
        "drink x = 1; drink x = 2",
        "glass f(x, x) { return x }",
        "return 1",
        "drink main = __error__",
        "pour 1",
        "drink main = open('x')",
    ],
)
def test_js_rejects_unsupported_constructs_before_emission(source):
    with pytest.raises(ValueError, match="JS target"):
        cli._transpile_to_js(parse(source))


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("1 % -2", -1),
        ("-4 % 2", 0),
        ("2 and 3", 3),
        ("0 or 4", 4),
        ("-2147483648", -2147483648),
        ("2147483647", 2147483647),
        ("(3 >= 2) and 2", 2),
        ("0 and (1 % 0)", 0),
    ],
)
def test_llvm_closed_integer_semantics(expression, expected):
    ir = cli._transpile_to_llvm_ir(parse("drink main = " + expression))
    assert f"ret i32 {expected}" in ir


@pytest.mark.parametrize(
    "source",
    [
        "drink main = 2147483647 + 1",
        "drink main = -2147483648 - 1",
        "drink main = 100000 * 100000",
        "drink main = 1 / 2",
        "drink main = 1 % 0",
        "drink main = missing",
        "drink main = [1]",
        "drink main = 'x'",
        "pour 1",
        "drink main = true",
        "drink main = 1; refill (true) {}",
        "glass loop() { return loop() } drink main = loop()",
        "glass f() { drink x = 1 } drink main = f()",
        "drink x = 1; x = 2; drink main = x",
    ],
)
def test_llvm_rejects_unknown_unsupported_or_unbounded_programs_before_writing(
    source, tmp_path
):
    with pytest.raises(ValueError, match="LLVM"):
        cli._build_llvm(parse(source), str(tmp_path / "unsupported"), "llvm-ir")
    assert not (tmp_path / "unsupported.ll").exists()


def test_llvm_function_return_stops_later_statements():
    ir = cli._transpile_to_llvm_ir(
        parse("glass f() { return 3; return 9 } drink main = f()")
    )
    assert "ret i32 3" in ir


def test_llvm_bounds_compile_time_work():
    evaluator = cli._LLVMExpr()
    evaluator.steps = 0
    with pytest.raises(ValueError, match="operation budget"):
        evaluator.emit(parse("return 1").stmts[0].value, {})


@pytest.mark.parametrize("target", ["js", "llvm-ir", "wasm-pyodide"])
@pytest.mark.parametrize(
    "body", ["drink main", "glass f() { drink x; return 1 } drink main = 1"]
)
def test_strict_mode_build_rejects_uninitialized_variables_before_artifact(
    target, body, tmp_path
):
    source = tmp_path / "strict.thirsty"
    source.write_text("module strict_demo: strict\n" + body, encoding="utf-8")
    args = SimpleNamespace(
        file=str(source),
        target=target,
        allow_governance_loss=False,
        emit_manifest=False,
    )
    with pytest.raises(ValueError, match="Strict build"):
        cli.cmd_build(args)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["strict.thirsty"]


def test_compose_compiler_example_builds_and_executes(tmp_path):
    root = Path(__file__).resolve().parents[1]
    source = root / "src/utf/examples/compiler_scalar.thirsty"
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    assert "/app/src/utf/examples/compiler_scalar.thirsty" in compose
    assert "--allow-governance-loss" in compose
    staged = tmp_path / source.name
    staged.write_bytes(source.read_bytes())
    cli.cmd_build(
        SimpleNamespace(
            file=str(staged),
            target="js",
            allow_governance_loss=True,
            emit_manifest=False,
        )
    )
    assert staged.with_suffix(".js").is_file()
    assert run_js(staged.read_text(encoding="utf-8")) == packed(11)


def test_pyodide_embedded_source_cannot_end_a_script_element(tmp_path):
    source = 'pour "</script><script>alert(1)</script>"'
    path = cli._build_pyodide(source, str(tmp_path / "web"))
    html = Path(path).read_text(encoding="utf-8")
    embedded = html.split("const SOURCE = ", 1)[1].split(";\n", 1)[0]
    assert "</script>" not in embedded.lower()
    assert json.loads(embedded) == source
    assert f'const EXPECTED_VERSION = "{cli.__version__}"' in html
    assert runtime_source_integrity() in html


def test_pyodide_launcher_javascript_is_syntactically_valid(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for generated JavaScript syntax validation")
    path = cli._build_pyodide('pour "</script>"', str(tmp_path / "syntax"))
    html = Path(path).read_text(encoding="utf-8")
    script = html.split('<script type="module">', 1)[1].split("</script>", 1)[0]
    result = subprocess.run(
        [node, "--input-type=module", "--check"],
        input=script,
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("fault", ["version", "source", None])
def test_pyodide_bootstrap_checks_identity_before_language_execution(
    monkeypatch, fault
):
    import importlib.metadata

    import utf

    root = Path(utf.__file__).parent
    distribution = SimpleNamespace(
        version="wrong" if fault == "version" else cli.__version__,
        locate_file=lambda _name: root,
    )
    monkeypatch.setattr(importlib.metadata, "distribution", lambda _name: distribution)
    executions = []
    monkeypatch.setattr(
        Interpreter, "interpret", lambda self, ast: executions.append(ast)
    )
    values = {
        "SRC": "pour 'would execute'",
        "ALLOW_UNGOVERNED": False,
        "EXPECTED_VERSION": cli.__version__,
        "EXPECTED_SOURCE_INTEGRITY": (
            "wrong" if fault == "source" else runtime_source_integrity()
        ),
    }
    if fault:
        with pytest.raises(RuntimeError, match="mismatch; execution refused"):
            exec(cli._PYODIDE_BOOTSTRAP, values)
        assert executions == []
    else:
        exec(cli._PYODIDE_BOOTSTRAP, values)
        assert len(executions) == 1
