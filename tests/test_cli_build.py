"""Tests for `thirsty build` targets: JS, LLVM-IR, the LLVM toolchain dispatch,
and the wasm/Pyodide bundle. These cover the previously-stubbed backends."""

import json
import os

import pytest

from utf.thirsty_lang import cli
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser

SOURCE = """module demo: core

glass add(a, b) {
    return a + b
}

glass neg(x) {
    return -x
}

glass cmp(a, b) {
    return a < b
}

drink main = add(2, 3) * 4 - 1
"""


def _parse(source=SOURCE):
    return Parser(Lexer(source).lex()).parse()


def _write(tmp_path, source=SOURCE):
    p = tmp_path / "prog.thirsty"
    p.write_text(source)
    return str(p)


def _build(tmp_path, target, source=SOURCE, monkeypatch=None):
    import sys

    f = _write(tmp_path, source)
    if monkeypatch is not None:
        monkeypatch.setattr(sys, "argv", ["thirsty", "build", "--target", target, f])
    else:
        sys.argv = ["thirsty", "build", "--target", target, f]
    cli.main()
    return os.path.splitext(f)[0]


# --- LLVM IR emitter -------------------------------------------------------


def test_llvm_ir_emits_verified_closed_computation():
    ir = cli._transpile_to_llvm_ir(_parse())
    assert "define i32 @main()" in ir
    assert "closed-scalar-i32/v1" in ir
    assert "ret i32 19" in ir
    assert "define i32 @add" not in ir  # No unverified callable export ABI.


def test_llvm_ir_unary_and_compare():
    ir = cli._transpile_to_llvm_ir(_parse("drink main = -2 + (1 < 2)"))
    assert "ret i32 -1" in ir


def test_llvm_ir_rejects_division_in_unused_functions():
    src = """module m: core
glass f(a, b) { return a + b - a * b }
glass g(a, b) { return a / b }
glass h(a, b) { return a % b }
glass eq(a, b) { return a == b }
glass ne(a, b) { return a != b }
glass band(a, b) { return a and b }
glass bor(a, b) { return a or b }
glass lnot(a) { return not a }
glass ge(a, b) { return a >= b }
drink main = f(1, 2)
"""
    with pytest.raises(ValueError, match="does not support division"):
        cli._transpile_to_llvm_ir(_parse(src))


def test_llvm_ir_no_main_defaults_zero():
    src = "module m: core\nglass f(a) { return a }\n"
    ir = cli._transpile_to_llvm_ir(_parse(src))
    assert "define i32 @main()" in ir
    assert "ret i32 0" in ir


def test_llvm_expr_fallbacks():
    # Bool literal, identifier, and an unknown-call callee exercise edge branches.
    em = cli._LLVMExpr()
    from utf.thirsty_lang.ast import BoolLiteral, Identifier

    assert em.emit(BoolLiteral(span=None, value=True), {}) == "1"
    assert em.emit(BoolLiteral(span=None, value=False), {}) == "0"
    with pytest.raises(ValueError, match="unresolved identifier"):
        em.emit(Identifier(span=None, name="missing"), {})


def test_build_llvm_ir_writes_file(tmp_path, monkeypatch, capsys):
    base = _build(tmp_path, "llvm-ir", monkeypatch=monkeypatch)
    assert os.path.exists(base + ".ll")
    assert "Built:" in capsys.readouterr().out


# --- LLVM toolchain dispatch ----------------------------------------------


@pytest.mark.parametrize("target", ["llvm-asm", "llvm-obj", "llvm-exe", "llvm-jit"])
def test_build_llvm_missing_toolchain_errors(tmp_path, monkeypatch, target):
    import shutil

    monkeypatch.setattr(shutil, "which", lambda _tool: None)
    with pytest.raises(RuntimeError, match="not found on PATH"):
        cli._build_llvm(_parse(), str(tmp_path / "p"), target)
    # IR is still written as a side effect.
    assert os.path.exists(str(tmp_path / "p.ll"))


@pytest.mark.parametrize(
    "target,expected_tool,out_ext",
    [
        ("llvm-asm", "llc", ".s"),
        ("llvm-obj", "llc", ".o"),
        ("llvm-exe", "clang", None),
        ("llvm-jit", "lli", ".ll"),
    ],
)
def test_build_llvm_with_toolchain(
    tmp_path, monkeypatch, target, expected_tool, out_ext
):
    import shutil
    import subprocess

    calls = {}
    monkeypatch.setattr(shutil, "which", lambda tool: f"/usr/bin/{tool}")

    def fake_run(cmd, check):
        calls["cmd"] = cmd
        calls["check"] = check

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = cli._build_llvm(_parse(), str(tmp_path / "p"), target)
    assert calls["check"] is True
    assert calls["cmd"][0] == f"/usr/bin/{expected_tool}"
    if out_ext is not None:
        assert out.endswith(out_ext)


# --- JS + Pyodide ----------------------------------------------------------


def test_build_js(tmp_path, monkeypatch, capsys):
    base = _build(tmp_path, "js", monkeypatch=monkeypatch)
    js = open(base + ".js").read()
    assert f"const {cli._js_name('add')} = function" in js
    assert "console.log" in js
    assert "Built:" in capsys.readouterr().out


def test_build_pyodide_bundle(tmp_path, monkeypatch, capsys):
    base = _build(tmp_path, "wasm-pyodide", monkeypatch=monkeypatch)
    html = open(base + ".pyodide.html").read()
    assert "loadPyodide" in html
    assert 'micropip.install("thirsty-lang==" + EXPECTED_VERSION)' in html
    assert "EXPECTED_SOURCE_INTEGRITY" in html
    assert "Interpreter().interpret(ast)" in html
    # Source is embedded as valid JSON.
    embedded = html.split("const SOURCE = ", 1)[1].split(";\n", 1)[0]
    assert json.loads(embedded).startswith("module demo")
    assert "Built:" in capsys.readouterr().out


def test_build_emit_manifest(tmp_path, monkeypatch, capsys):
    import sys

    f = _write(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["thirsty", "build", "--target", "js", "--emit-manifest", f],
    )
    cli.main()
    manifest_path = os.path.splitext(f)[0] + ".manifest.json"
    assert os.path.exists(manifest_path)
    manifest = json.loads(open(manifest_path).read())
    assert manifest["mode"] == "core"
    assert any(fn["name"] == "add" for fn in manifest["functions"])


def test_build_file_not_found(monkeypatch):
    import sys

    monkeypatch.setattr(sys, "argv", ["thirsty", "build", "nonexistent.thirsty"])
    with pytest.raises(SystemExit):
        cli.main()


def test_build_no_file_no_main(tmp_path, monkeypatch):
    import sys

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["thirsty", "build"])
    with pytest.raises(SystemExit):
        cli.main()
