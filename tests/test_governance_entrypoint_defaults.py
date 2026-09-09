"""Execution defaults cannot lose governance at a public CLI boundary."""

import builtins
import importlib.metadata
import json
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

import utf
from utf.thirst_of_gods import cli as gods_cli
from utf.thirsty_lang import cli
from utf.thirsty_lang.interpreter import GovernanceViolation
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.package_manager import (
    create_thirsty_toml,
    runtime_source_integrity,
)
from utf.thirsty_lang.parser import Parser
from utf.thirsty_lang.proof_obligations import (
    denial_explanation,
    extract_proof_obligations,
)


def invoke(monkeypatch, *arguments):
    monkeypatch.setattr(sys, "argv", ["thirsty", *map(str, arguments)])
    cli.main()


def write_program(tmp_path, header="", body='pour "guest-effect"\n'):
    path = tmp_path / "main.thirsty"
    path.write_text(header + body, encoding="utf-8")
    return path


@pytest.mark.parametrize("mode", [None, "core", "governed", "strict", "pure"])
@pytest.mark.parametrize("requested", [[], ["--thirst-level", "core"]])
def test_cli_governance_default_survives_source_headers(
    monkeypatch, tmp_path, capsys, mode, requested
):
    path = write_program(tmp_path, f"module main: {mode}\n" if mode else "")
    with pytest.raises(SystemExit) as error:
        invoke(monkeypatch, "run", path, *requested)
    assert error.value.code == (1 if mode == "pure" else 2)
    captured = capsys.readouterr()
    assert "guest-effect" not in captured.out
    assert ("not allowed" if mode == "pure" else "denied") in captured.err


@pytest.mark.parametrize("header", ["", "module main: core\n"])
def test_explicit_unsafe_core_is_disclosed(monkeypatch, tmp_path, capsys, header):
    path = write_program(tmp_path, header)
    invoke(monkeypatch, "run", path, "--unsafe-core")
    captured = capsys.readouterr()
    assert "guest-effect" in captured.out
    assert "ungoverned compatibility" in captured.err


def test_explicit_governed_declaration_keeps_floor_with_unsafe_opt_out(
    monkeypatch, tmp_path, capsys
):
    path = write_program(tmp_path, "module main: governed\n")
    with pytest.raises(SystemExit) as error:
        invoke(monkeypatch, "run", path, "--unsafe-core")
    assert error.value.code == 2
    assert "guest-effect" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "controls",
    [
        ["--locked"],
        ["--hardened"],
        ["--require-audit"],
        ["--policy", "missing.tarl"],
        ["--policy", ""],
        ["--context-schema", "missing.json"],
        ["--authority", "admin"],
        ["--authority", ""],
        ["--authority-token", "missing.json"],
        ["--authority-key", "key:00"],
        ["--authority-key-file", "missing.json"],
        ["--sign-proofs", "key:00"],
        ["--sign-proofs-file", "missing.json"],
        ["--audit-db", "must-not-create.db"],
        ["--thirst-level", "governed"],
    ],
)
def test_unsafe_opt_out_rejects_security_controls_before_source_access(
    monkeypatch, tmp_path, capsys, controls
):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as error:
        invoke(monkeypatch, "run", "missing.thirsty", "--unsafe-core", *controls)
    assert error.value.code == 1
    assert "cannot be combined" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_repl_source_header_cannot_downgrade_default(monkeypatch, capsys):
    entries = iter(
        [
            'module demo: core\npour "guest-effect"',
            ".clear",
            'pour "second-effect"',
            "exit",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(entries))
    invoke(monkeypatch, "repl")
    output = capsys.readouterr().out
    assert "guest-effect" not in output
    assert "second-effect" not in output
    assert "governance: required" in output


def test_scaffold_is_governed_and_runs_pure_calculation(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    invoke(monkeypatch, "new", "example")
    project = tmp_path / "example"
    source = project / "src" / "main.thirsty"
    assert source.read_text().startswith("module example: governed")
    manifest = tomllib.loads((project / "thirsty.toml").read_text())
    assert manifest["package"]["mode"] == "governed"
    invoke(monkeypatch, "run", source)
    assert "hello, thirsty world!" in capsys.readouterr().out


@pytest.mark.parametrize("mode", ["core", "governed", "strict", "pure"])
def test_manifest_creation_preserves_explicit_semantics(tmp_path, mode):
    path = create_thirsty_toml(str(tmp_path), "example", "0.2.0", mode=mode)
    manifest = tomllib.loads(Path(path).read_text())
    assert manifest["package"]["mode"] == mode
    assert manifest["package"]["version"] == "0.2.0"


@pytest.mark.parametrize(
    "header", ["", "module main: core\n", "module main: governed\n"]
)
@pytest.mark.parametrize("target", ["js", "llvm-ir", "wasm-pyodide"])
def test_all_public_builds_require_explicit_loss_acknowledgement(
    monkeypatch, tmp_path, capsys, header, target
):
    path = write_program(tmp_path, header, "drink main = 5\n")
    with pytest.raises(SystemExit) as error:
        invoke(monkeypatch, "build", path, "--target", target)
    assert error.value.code == 1
    assert list(tmp_path.iterdir()) == [path]
    assert "governance is required by default" in capsys.readouterr().err


@pytest.mark.parametrize("target", ["js", "llvm-ir", "wasm-pyodide"])
def test_loss_acknowledgement_always_emits_disclosure(monkeypatch, tmp_path, target):
    path = write_program(tmp_path, body="drink main = 5\n")
    invoke(monkeypatch, "build", path, "--target", target, "--allow-governance-loss")
    manifest = json.loads(path.with_suffix(".manifest.json").read_text())
    assert manifest["mode"] == "governed"
    assert manifest["declared_mode"] is None
    assert manifest["execution"]["governance_required"] is True
    assert manifest["build"]["unsafe_opt_out_requested"] is True
    assert manifest["build"]["artifact_governance_required"] is False


def test_pyodide_disclosure_preserves_declared_governance_floor(monkeypatch, tmp_path):
    path = write_program(tmp_path, "module main: governed\n", "drink main = 5\n")
    invoke(
        monkeypatch,
        "build",
        path,
        "--target",
        "wasm-pyodide",
        "--allow-governance-loss",
    )
    manifest = json.loads(path.with_suffix(".manifest.json").read_text())
    assert manifest["build"]["unsafe_opt_out_requested"] is True
    assert manifest["build"]["artifact_governance_required"] is True
    assert manifest["build"]["host_policy_configuration_preserved"] is False


def test_gods_js_public_route_cannot_bypass_build_guard(monkeypatch, tmp_path):
    path = write_program(tmp_path, body="drink main = 5\n")
    monkeypatch.setattr(
        sys, "argv", ["thirst-of-gods", "transpile", str(path), "--target", "js"]
    )
    with pytest.raises(SystemExit):
        gods_cli.main()
    assert not path.with_suffix(".js").exists()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "thirst-of-gods",
            "transpile",
            str(path),
            "--target",
            "js",
            "--allow-governance-loss",
        ],
    )
    gods_cli.main()
    assert path.with_suffix(".js").exists()
    manifest = json.loads(path.with_suffix(".manifest.json").read_text())
    assert manifest["build"]["governance_loss"] is True


@pytest.mark.parametrize("target", ["js", "llvm-ir", "wasm-pyodide", "gods-js"])
def test_disclosure_failure_prevents_artifact_write(monkeypatch, tmp_path, target):
    path = write_program(tmp_path, body="drink main = 5\n")

    def unavailable(*_args, **_kwargs):
        raise OSError("disclosure storage unavailable")

    monkeypatch.setattr(cli, "_emit_manifest", unavailable)
    with pytest.raises((SystemExit, OSError)):
        if target == "gods-js":
            gods_cli.transpile_file(str(path), target="js", allow_governance_loss=True)
        else:
            invoke(
                monkeypatch,
                "build",
                path,
                "--target",
                target,
                "--allow-governance-loss",
            )
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize(
    "header", ["", "module main: core\n", "module main: governed\n"]
)
@pytest.mark.parametrize("unsafe", [False, True])
def test_pyodide_launcher_preserves_effective_governance(
    monkeypatch, capsys, header, unsafe
):
    root = Path(utf.__file__).parent
    distribution = SimpleNamespace(
        version=cli.__version__, locate_file=lambda _name: root
    )
    monkeypatch.setattr(importlib.metadata, "distribution", lambda _name: distribution)
    values = {
        "SRC": header + 'pour "guest-effect"',
        "EXPECTED_VERSION": cli.__version__,
        "EXPECTED_SOURCE_INTEGRITY": runtime_source_integrity(),
        "ALLOW_UNGOVERNED": unsafe,
    }
    if not unsafe or "governed" in header:
        with pytest.raises(GovernanceViolation):
            exec(cli._PYODIDE_BOOTSTRAP, values)
        assert "guest-effect" not in capsys.readouterr().out
    else:
        exec(cli._PYODIDE_BOOTSTRAP, values)
        assert "guest-effect" in capsys.readouterr().out


def test_proof_report_separates_semantics_and_governance_without_invented_obligations():
    source = "module main: core\ndrink main = 5\n"
    ast = Parser(Lexer(source).lex()).parse()
    report = extract_proof_obligations(ast, source, "<test>")
    assert report["mode"] == report["declared_mode"] == "core"
    assert report["execution"]["governance_required"] is True
    assert report["required_tarl_actions"] == []
    assert not any(
        item["category"] == "policy" for item in report["unresolved_proof_gaps"]
    )
    assert report["audit_requirement"]["required"] is False
    assert denial_explanation(report)["missing"] == []
    assert report["analysis_scope"]["complete_effect_inventory"] is False


@pytest.mark.parametrize("operation", ["fmt", "govern", "gods-convert"])
def test_source_tools_use_utf8_independent_of_host_default(
    monkeypatch, tmp_path, operation
):
    path = write_program(tmp_path, body='drink label = "café"\n')
    original_open = builtins.open

    def legacy_default(file, mode="r", *args, **kwargs):
        if "b" not in mode and not args and "encoding" not in kwargs:
            kwargs["encoding"] = "cp1252"
        return original_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", legacy_default)
    if operation == "fmt":
        invoke(monkeypatch, "fmt", path)
    elif operation == "govern":
        _, errors, source = cli._lex_parse_check(str(path))
        assert errors == []
        assert '"café"' in source
    else:
        gods_cli.transpile_file(str(path), target="thirsty")
    assert '"café"' in path.read_text(encoding="utf-8")
