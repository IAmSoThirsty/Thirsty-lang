"""Every shipped stdlib callable has a reviewed ambient-effect classification."""

from unittest.mock import Mock

import pytest

from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
from utf.tarl.spec import TarlVerdict
from utf.thirsty_lang.interpreter import GovernanceViolation, Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.module_system import (
    NO_AMBIENT_STDLIB_EXPORTS,
    SENSITIVE_STDLIB_CAPABILITIES,
    STDLIB_MODULES,
    ModuleCache,
    validate_stdlib_exports,
)
from utf.thirsty_lang.parser import Parser

IMPORT_ONLY = 'when action == "import" => ALLOW\nwhen true => DENY'


def parse(source):
    parser = Parser(Lexer(source).lex())
    program = parser.parse()
    assert not parser.errors
    return program


@pytest.fixture
def runner():
    runtime = TarlRuntime(PolicyParser.parse(IMPORT_ONLY))
    interpreter = Interpreter().attach_tarl(runtime).set_authority("operator")
    yield interpreter
    interpreter.executor.shutdown(wait=True)
    runtime.shutdown()


def test_reviewed_inventory_covers_the_shipped_registry():
    assert set(NO_AMBIENT_STDLIB_EXPORTS) == set(STDLIB_MODULES)
    assert set(SENSITIVE_STDLIB_CAPABILITIES) <= set(STDLIB_MODULES)
    assert sum(map(len, NO_AMBIENT_STDLIB_EXPORTS.values())) == 56
    assert sum(map(len, SENSITIVE_STDLIB_CAPABILITIES.values())) == 43
    assert all(
        isinstance(names, frozenset) for names in NO_AMBIENT_STDLIB_EXPORTS.values()
    )


@pytest.mark.parametrize("namespace", sorted(STDLIB_MODULES))
def test_each_shipped_namespace_has_exact_callable_classifications(namespace):
    module = STDLIB_MODULES[namespace]()
    validate_stdlib_exports(namespace, module)
    effects = SENSITIVE_STDLIB_CAPABILITIES.get(namespace, {})
    no_ambient = NO_AMBIENT_STDLIB_EXPORTS[namespace]
    assert not set(effects).intersection(no_ambient)
    assert set(module) == set(effects).union(no_ambient)
    assert all(callable(value) for value in module.values())


@pytest.mark.parametrize("namespace", sorted(STDLIB_MODULES))
@pytest.mark.parametrize("change", ["unknown", "missing", "noncallable"])
def test_export_changes_require_review_before_exposure(namespace, change):
    module = STDLIB_MODULES[namespace]()
    name = sorted(module)[0]
    if change == "unknown":
        module["unreviewed"] = lambda: None
    elif change == "missing":
        module.pop(name)
    else:
        module[name] = 42
    with pytest.raises(ImportError, match="exports"):
        validate_stdlib_exports(namespace, module)


@pytest.mark.parametrize("namespace", ["thirst::unknown", "library.thirsty"])
def test_unreviewed_namespace_has_no_implicit_classification(namespace):
    with pytest.raises(ImportError, match="namespace"):
        validate_stdlib_exports(namespace, {"value": lambda: 42})


def test_new_factory_is_not_implicitly_reviewed(monkeypatch):
    monkeypatch.setitem(STDLIB_MODULES, "thirst::new", lambda: {"value": lambda: 42})
    with pytest.raises(ImportError, match="namespace"):
        validate_stdlib_exports("thirst::new", {"value": lambda: 42})


@pytest.mark.parametrize("module", [None, [], {1: lambda: None}])
def test_invalid_export_dictionary_is_rejected(module):
    with pytest.raises(ImportError, match="dictionary"):
        validate_stdlib_exports("thirst::json", module)


@pytest.mark.parametrize("change", ["overlap", "unknown-action", "non-string-action"])
def test_ambiguous_effect_classification_is_rejected(monkeypatch, change):
    effects = {"parse": "read"}
    if change == "unknown-action":
        effects = {"parse": "ambient"}
    elif change == "non-string-action":
        effects = {"parse": []}
    monkeypatch.setitem(SENSITIVE_STDLIB_CAPABILITIES, "thirst::json", effects)
    with pytest.raises(ImportError, match="classification"):
        validate_stdlib_exports("thirst::json", STDLIB_MODULES["thirst::json"]())


def test_unreviewed_cached_callable_cannot_be_imported(monkeypatch, runner):
    module = STDLIB_MODULES["thirst::json"]()
    unexpected = Mock()
    module["unreviewed"] = unexpected
    monkeypatch.setitem(ModuleCache, "thirst::json", module)
    with pytest.raises(ImportError, match="Unreviewed"):
        runner.interpret(parse('import "thirst::json" as api'))
    unexpected.assert_not_called()
    assert not runner.env.has("api")


@pytest.mark.parametrize("name", ["absolute", "relative"])
@pytest.mark.parametrize("mode", ["", "pure"])
def test_ambient_path_helpers_are_denied_before_host_call(
    name, mode, monkeypatch, runner
):
    module = STDLIB_MODULES["thirst::path"]()
    ambient = Mock(side_effect=AssertionError("ambient path operation reached"))
    module[name] = ambient
    monkeypatch.setitem(ModuleCache, "thirst::path", module)
    header = "module test: pure\n" if mode else ""
    expected_error = RuntimeError if mode else GovernanceViolation
    with pytest.raises(expected_error) as error:
        runner.interpret(
            parse(header + f'import "thirst::path" as path\npath.{name}(".")')
        )
    if not mode:
        assert error.value.proof.verdict is TarlVerdict.DENY
        assert error.value.proof.context_hash
    else:
        assert "pure" in str(error.value)
    ambient.assert_not_called()


def test_assert_raises_cannot_swallow_a_governance_denial():
    helper = STDLIB_MODULES["thirst::test"]()["assert_raises"]
    denial = GovernanceViolation("write", "denied by policy")

    def denied():
        raise denial

    with pytest.raises(GovernanceViolation) as error:
        helper(denied)
    assert error.value is denial


def test_assert_raises_preserves_ordinary_exception_behavior():
    helper = STDLIB_MODULES["thirst::test"]()["assert_raises"]

    def invalid():
        raise ValueError("expected")

    assert helper(invalid) is None
    with pytest.raises(AssertionError, match="Expected exception"):
        helper(lambda: None)


def test_guest_assert_raises_does_not_resume_after_denial(runner, capsys):
    source = (
        'import "thirst::test" as test\n'
        'test.assert_raises(print, "forbidden")\n'
        "drink continued = true"
    )
    with pytest.raises(GovernanceViolation):
        runner.interpret(parse(source))
    assert not runner.env.has("continued")
    assert capsys.readouterr().out == ""


def test_exported_collection_callback_keeps_defining_restrictions(runner, capsys):
    runner.interpret(parse('import "thirst::collections" as collections'))
    callback_helper = runner.env.get("collections")["map"]
    foreign = Interpreter(allow_ungoverned=True)
    try:
        with pytest.raises(GovernanceViolation):
            callback_helper(foreign.env.get("print"), ["forbidden"])
    finally:
        foreign.executor.shutdown(wait=True)
    assert capsys.readouterr().out == ""
