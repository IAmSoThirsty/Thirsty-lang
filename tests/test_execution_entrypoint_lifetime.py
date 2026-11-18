"""CLI and tier entry points release resources they create, including setup failures."""

import sys
from argparse import Namespace
from collections import Counter

import pytest

from utf.tarl import archive as archive_module
from utf.tarl import runtime as runtime_module
from utf.thirst_of_gods import core as gods_core
from utf.thirsty_lang import cli
from utf.thirsty_lang import interpreter as interpreter_module
from utf.thirsty_lang.execution import ExecutionLimits
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser


@pytest.fixture
def resources(monkeypatch):
    """Observe real acquisition and disposal without replacing resource behavior."""
    acquired = {"interpreter": [], "runtime": [], "archive": []}
    disposed = Counter()
    options = []
    resource_types = {}
    released = set()
    kinds = (
        ("interpreter", interpreter_module, "Interpreter", "close"),
        ("runtime", runtime_module, "TarlRuntime", "shutdown"),
        ("archive", archive_module, "TarlAuditArchive", "close"),
    )
    for kind, module, name, closer in kinds:
        resource_type = getattr(module, name)
        resource_types[kind] = resource_type
        original_close = getattr(resource_type, closer)

        def observed_close(self, *, _kind=kind, _close=original_close):
            disposed[_kind] += 1
            result = _close(self)
            released.add(id(self))
            return result

        monkeypatch.setattr(resource_type, closer, observed_close)

        def acquire(*args, _kind=kind, _type=resource_type, **kwargs):
            resource = _type(*args, **kwargs)
            acquired[_kind].append(resource)
            if _kind == "interpreter":
                options.append(kwargs)
            return resource

        monkeypatch.setattr(module, name, acquire)
    yield acquired, disposed, options, resource_types
    for kind, _module, _name, closer in reversed(kinds):
        for resource in acquired[kind]:
            if id(resource) not in released:
                getattr(resource, closer)()


@pytest.fixture
def run_args(tmp_path):
    source = tmp_path / "main.thirsty"
    source.write_text("40 + 2", encoding="utf-8")
    policy = tmp_path / "permit.tarl"
    policy.write_text("when true => ALLOW", encoding="utf-8")
    return Namespace(
        file=str(source),
        demo=False,
        opt=0,
        trace=False,
        release=False,
        thirst_level=None,
        policy=str(policy),
        audit_db=str(tmp_path / "audit.sqlite3"),
    )


def assert_all_released(resources, *, interpreter=1, runtime=1, archive=1):
    acquired, disposed, _, _ = resources
    expected = {"interpreter": interpreter, "runtime": runtime, "archive": archive}
    assert {kind: len(values) for kind, values in acquired.items()} == expected
    assert {kind: disposed[kind] for kind in expected} == expected


@pytest.mark.parametrize("source", ["40 + 2", 'print("allowed")'])
def test_run_releases_owned_resources_on_success(run_args, resources, source):
    with open(run_args.file, "w", encoding="utf-8") as stream:
        stream.write(source)
    cli.cmd_run(run_args)
    assert_all_released(resources)
    assert resources[2][0]["execution_limits"] == ExecutionLimits()


@pytest.mark.parametrize("source", ["1 / 0", 'throw "failure"'])
def test_run_releases_owned_resources_on_runtime_error(run_args, resources, source):
    with open(run_args.file, "w", encoding="utf-8") as stream:
        stream.write(source)
    with pytest.raises(SystemExit) as error:
        cli.cmd_run(run_args)
    assert error.value.code == 1
    assert_all_released(resources)


def test_run_releases_owned_resources_on_governance_denial(run_args, resources):
    with open(run_args.file, "w", encoding="utf-8") as stream:
        stream.write('print("denied")')
    with open(run_args.policy, "w", encoding="utf-8") as stream:
        stream.write("when true => DENY")
    with pytest.raises(SystemExit) as error:
        cli.cmd_run(run_args)
    assert error.value.code == 2
    assert_all_released(resources)


@pytest.mark.parametrize(
    ("changes", "runtime_count"),
    [
        ({"policy": "missing-policy.tarl"}, 0),
        ({"context_schema": "missing-schema.json"}, 1),
        ({"authority_token": "missing-token.json"}, 1),
        ({"sign_proofs_file": "missing-key.json"}, 1),
        ({"sign_proofs": "signer:invalid"}, 1),
        ({"require_audit": True, "audit_db": None}, 1),
        ({"policy": None, "context_schema": "schema.json"}, 0),
        ({"policy": None}, 0),
    ],
)
def test_run_setup_exit_releases_every_acquired_resource(
    run_args, resources, changes, runtime_count
):
    for name, value in changes.items():
        setattr(run_args, name, value)
    with pytest.raises(SystemExit) as error:
        cli.cmd_run(run_args)
    assert error.value.code == 1
    assert_all_released(resources, runtime=runtime_count, archive=0)


def test_run_archive_constructor_failure_releases_prior_resources(
    run_args, resources, monkeypatch
):
    def unavailable(*args, **kwargs):
        raise OSError("archive unavailable")

    monkeypatch.setattr(archive_module, "TarlAuditArchive", unavailable)
    with pytest.raises(SystemExit) as error:
        cli.cmd_run(run_args)
    assert error.value.code == 1
    assert_all_released(resources, archive=0)


def test_run_failure_after_archive_creation_releases_archive(
    run_args, resources, monkeypatch
):
    # Patch the real class behind the observed factory.
    def reject_archive(self, archive):
        raise RuntimeError("archive binding failed")

    monkeypatch.setattr(resources[3]["runtime"], "set_archive", reject_archive)
    with pytest.raises(RuntimeError, match="archive binding failed"):
        cli.cmd_run(run_args)
    assert_all_released(resources)


def test_run_releases_resources_on_keyboard_interrupt(run_args, resources, monkeypatch):
    def interrupted(self, ast, **options):
        raise KeyboardInterrupt

    monkeypatch.setattr(resources[3]["interpreter"], "interpret", interrupted)
    with pytest.raises(KeyboardInterrupt):
        cli.cmd_run(run_args)
    assert_all_released(resources)


def test_repl_releases_interpreter_after_error_and_exit(resources, monkeypatch):
    lines = iter(["1 / 0", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(lines))
    cli.cmd_repl(Namespace(trace=False, opt=0, thirst_level=None))
    assert_all_released(resources, runtime=0, archive=0)


@pytest.mark.parametrize("exception", [EOFError, KeyboardInterrupt])
def test_repl_releases_interpreter_on_input_interrupt(
    resources, monkeypatch, exception
):
    def interrupted(prompt):
        raise exception

    monkeypatch.setattr("builtins.input", interrupted)
    cli.cmd_repl(Namespace(trace=False, opt=0, thirst_level=None))
    assert_all_released(resources, runtime=0, archive=0)


@pytest.mark.parametrize("command", ["run", "repl"])
def test_cli_passes_explicit_limits(command, run_args, resources, monkeypatch):
    arguments = ["thirsty", command]
    if command == "run":
        arguments.append(run_args.file)
    else:
        monkeypatch.setattr("builtins.input", lambda prompt: "exit")
    arguments.extend(
        ["--max-steps", "1000", "--timeout-seconds", "4.5", "--max-call-depth", "12"]
    )
    monkeypatch.setattr(sys, "argv", arguments)
    cli.main()
    assert resources[2][0]["execution_limits"] == ExecutionLimits(
        max_steps=1000, timeout_seconds=4.5, max_call_depth=12
    )
    assert_all_released(resources, runtime=0, archive=0)


@pytest.mark.parametrize("command", ["run", "repl"])
@pytest.mark.parametrize(
    ("option", "value"),
    [
        ("--max-steps", "0"),
        ("--max-steps", "-1"),
        ("--timeout-seconds", "0"),
        ("--timeout-seconds", "nan"),
        ("--timeout-seconds", "inf"),
        ("--max-call-depth", "0"),
    ],
)
def test_invalid_cli_limit_rejected_before_resource_acquisition(
    command, option, value, resources, monkeypatch, capsys
):
    monkeypatch.setattr(sys, "argv", ["thirsty", command, option, value])
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 1
    assert "invalid execution limits" in capsys.readouterr().err
    assert_all_released(resources, interpreter=0, runtime=0, archive=0)


@pytest.mark.parametrize(
    ("option", "value"),
    [("--max-steps", "100"), ("--timeout-seconds", "3"), ("--max-call-depth", "8")],
)
def test_gods_cli_does_not_silently_discard_explicit_limit(
    option, value, resources, monkeypatch, capsys
):
    monkeypatch.setattr(
        sys, "argv", ["thirsty", "run", "test.thirstofgods", option, value]
    )
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 1
    assert "restricted runs" in capsys.readouterr().err
    assert_all_released(resources, interpreter=0, runtime=0, archive=0)


@pytest.mark.parametrize("source", ["40 + 2", "1 / 0"])
def test_gods_interpreter_lifetime_after_validated_contract(
    source, resources, monkeypatch
):
    monkeypatch.setattr(gods_core, "to_gods", lambda ast: gods_core.DeityContract())
    ast = Parser(Lexer(source).lex()).parse()
    if source == "1 / 0":
        with pytest.raises(ZeroDivisionError):
            gods_core.interpret_gods(ast)
    else:
        assert gods_core.interpret_gods(ast) == 42
    assert_all_released(resources, runtime=0, archive=0)


def run_repl_lines(monkeypatch, lines, **options):
    input_lines = iter([*lines, "exit"])
    prompts = []

    def read(prompt):
        prompts.append(prompt)
        return next(input_lines)

    monkeypatch.setattr("builtins.input", read)
    cli.cmd_repl(Namespace(trace=False, opt=0, thirst_level=None, **options))
    return prompts


def test_repl_each_submission_emits_its_effect_once(monkeypatch, capsys, resources):
    run_repl_lines(
        monkeypatch,
        ['pour "first effect"', 'pour "second effect"'],
        unsafe_core=True,
    )
    counts = Counter(capsys.readouterr().out.splitlines())
    assert counts["first effect"] == 1
    assert counts["second effect"] == 1
    assert_all_released(resources, runtime=0, archive=0)


def test_repl_retains_variables_functions_and_nominal_types(
    monkeypatch, capsys, resources
):
    run_repl_lines(
        monkeypatch,
        [
            "drink base: Int = 40",
            "struct Row { value: Int }",
            "glass build(value: Int) -> Row { return new Row(base + value) }",
            "drink row: Row = build(2)",
            "row.value",
        ],
    )
    output = capsys.readouterr().out
    assert "Error" not in output
    assert "E011" not in output
    assert output.splitlines().count("42") == 1
    assert resources[0]["interpreter"][0].env.get("row").fields["value"] == 42


def test_repl_empty_lines_and_multiline_pending_input_do_not_repeat_effects(
    monkeypatch, capsys, resources
):
    prompts = run_repl_lines(
        monkeypatch,
        [
            "",
            'pour "single effect"',
            "",
            "glass add(value: Int) -> Int {",
            "",
            "return value + 2",
            "}",
            "add(40)",
            "",
        ],
        unsafe_core=True,
    )
    output = capsys.readouterr().out.splitlines()
    assert output.count("single effect") == 1
    assert output.count("42") == 1
    assert prompts == [">>> "] * 4 + ["... "] * 3 + [">>> "] * 3
    assert_all_released(resources, runtime=0, archive=0)


def test_repl_failed_execution_requires_clear_without_replaying_effects(
    monkeypatch, capsys, resources
):
    run_repl_lines(
        monkeypatch,
        [
            'pour "before failure"',
            'pour "partial effect"; drink missing = 1 / 0',
            'pour "blocked effect"',
            ".clear",
            'pour "after reset"',
        ],
        unsafe_core=True,
    )
    output = capsys.readouterr().out
    counts = Counter(output.splitlines())
    assert counts["before failure"] == 1
    assert counts["partial effect"] == 1
    assert counts["blocked effect"] == 0
    assert counts["after reset"] == 1
    assert "partial effects or state may remain" in output
    assert not resources[0]["interpreter"][0].env.has("missing")


def test_repl_static_error_preserves_successful_context_without_reexecution(
    monkeypatch, capsys, resources
):
    run_repl_lines(
        monkeypatch,
        [
            'pour "once"; drink value: Int = 42',
            "unknown_value",
            "value",
        ],
        unsafe_core=True,
    )
    output = capsys.readouterr().out.splitlines()
    assert output.count("once") == 1
    assert output.count("42") == 1
    assert any("E011" in line for line in output)


def test_repl_module_mode_remains_active_across_submissions(
    monkeypatch, capsys, resources
):
    run_repl_lines(
        monkeypatch,
        ["module test: pure", 'pour "forbidden"'],
        unsafe_core=True,
    )
    output = capsys.readouterr().out
    assert "pure" in output
    assert "forbidden" not in output.splitlines()
    assert "Execution failed" in output


def test_repl_module_header_requires_clear_before_replacement(
    monkeypatch, capsys, resources
):
    run_repl_lines(
        monkeypatch,
        [
            "module test: pure",
            "module other: core",
            ".clear",
            "module other: core",
            'pour "new session"',
        ],
        unsafe_core=True,
    )
    output = capsys.readouterr().out
    assert output.count("A module header is already active") == 1
    assert output.splitlines().count("new session") == 1


def test_cli_resource_stop_closes_owned_resources(run_args, resources, capsys):
    with open(run_args.file, "w", encoding="utf-8") as stream:
        stream.write("refill (true) {}")
    run_args.max_steps = 12
    with pytest.raises(SystemExit) as error:
        cli.cmd_run(run_args)
    assert error.value.code == 1
    assert "step limit exceeded" in capsys.readouterr().err
    assert_all_released(resources)
