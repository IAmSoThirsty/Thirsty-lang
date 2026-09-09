"""Runtime callable arity is exact even when the checker sees dynamic values."""

from unittest.mock import Mock

import pytest

from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
from utf.tarl.spec import TarlVerdict
from utf.thirsty_lang.interpreter import GovernanceViolation, Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser


def parse(source):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors, lexer.errors
    assert not parser.errors, parser.errors
    return program


@pytest.fixture
def make_interpreter():
    interpreters = []
    runtimes = []

    def make(*, optimization=0, policy="when true => ALLOW", allow_ungoverned=False):
        interpreter = Interpreter(
            opt_level=optimization, allow_ungoverned=allow_ungoverned
        )
        interpreters.append(interpreter)
        if policy is not None:
            runtime = TarlRuntime(PolicyParser.parse(policy))
            runtimes.append(runtime)
            interpreter.attach_tarl(runtime).set_authority("arity-test")
        return interpreter

    yield make
    for interpreter in interpreters:
        interpreter.executor.shutdown(wait=True)
    for runtime in runtimes:
        runtime.shutdown()


def declaration(kind, params="value", body="hit(value)\nreturn value"):
    if kind == "lambda":
        return f"drink target = glass({params}) {{ {body} }}"
    if kind == "morph":
        return f"morph target({params}) {{ {body} }}"
    contract = " requires contract()" if kind == "governed" else ""
    return f"glass target({params}){contract} {{ {body} }}"


KINDS = ["function", "lambda", "morph", "governed"]


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("count", [0, 2])
@pytest.mark.parametrize(
    "route", ["direct", "any-alias", "list", "dict", "cascade", "host"]
)
def test_wrong_arity_precedes_body_contract_and_policy_and_restores_scope(
    optimization, kind, count, route, make_interpreter, monkeypatch
):
    interpreter = make_interpreter(optimization=optimization)
    hit = Mock()
    contract = Mock(return_value=True)
    interpreter.env.define("hit", hit)
    interpreter.env.define("contract", contract)
    interpreter.interpret(parse(declaration(kind)))
    original = interpreter.env
    policy = Mock(wraps=interpreter.tarl_runtime.evaluate_with_proof)
    monkeypatch.setattr(interpreter.tarl_runtime, "evaluate_with_proof", policy)
    arguments = ", ".join(str(index) for index in range(count))
    sources = {
        "direct": f"target({arguments})",
        "any-alias": f"drink alias: Any = target\nalias({arguments})",
        "list": f"drink callbacks = [target]\ncallbacks[0]({arguments})",
        "dict": f'drink callbacks = {{"fn": target}}\ncallbacks["fn"]({arguments})',
        "cascade": f"cascade target({arguments})",
    }
    with pytest.raises(TypeError, match=f"expects 1 arguments, got {count}"):
        if route == "host":
            interpreter.env.get("target")(*range(count))
        else:
            interpreter.interpret(parse(sources[route]))
    assert interpreter.env is original
    hit.assert_not_called()
    contract.assert_not_called()
    policy.assert_not_called()
    assert interpreter._last_proof is None
    assert interpreter.interpret(parse("target(7)")) == 7
    hit.assert_called_once_with(7)


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("route", ["direct", "cascade"])
def test_argument_and_callee_expressions_run_once_in_source_order_before_error(
    kind, route, make_interpreter
):
    interpreter = make_interpreter()
    events = []
    interpreter.env.define("hit", lambda value: events.append("body"))
    interpreter.env.define("contract", lambda: events.append("contract") or True)
    interpreter.interpret(parse(declaration(kind)))
    target = interpreter.env.get("target")
    interpreter.env.define("lookup", lambda: events.append("callee") or target)
    interpreter.env.define("first", lambda: events.append("first") or 1)
    interpreter.env.define("second", lambda: events.append("second") or 2)
    expression = "lookup()(first(), second())"
    if route == "cascade":
        expression = "cascade " + expression
    with pytest.raises(TypeError, match="expects 1 arguments, got 2"):
        interpreter.interpret(parse(expression))
    assert events == ["callee", "first", "second"]


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("operator", ["|", "|>", "->"])
@pytest.mark.parametrize("params", ["", "first, second"])
def test_pipes_require_exact_one_argument_without_running_target(
    optimization, kind, operator, params, make_interpreter
):
    interpreter = make_interpreter(optimization=optimization)
    events = []
    interpreter.env.define("hit", lambda: events.append("body"))
    interpreter.env.define("contract", lambda: events.append("contract") or True)
    interpreter.interpret(parse(declaration(kind, params, "hit()")))
    target = interpreter.env.get("target")
    interpreter.env.define("argument", lambda: events.append("argument") or 7)
    interpreter.env.define("lookup", lambda: events.append("callee") or target)
    expected = 0 if not params else 2
    with pytest.raises(TypeError, match=f"expects {expected} arguments, got 1"):
        interpreter.interpret(parse(f"argument() {operator} lookup()"))
    assert events == ["argument", "callee"]


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("count", [0, 2])
def test_escaped_closure_returned_to_host_keeps_arity(kind, count, make_interpreter):
    interpreter = make_interpreter()
    hit = Mock()
    interpreter.env.define("hit", hit)
    interpreter.env.define("contract", lambda: True)
    source = "glass factory() {\n" + declaration(kind) + "\nreturn target\n}\nfactory()"
    target = interpreter.interpret(parse(source))
    with pytest.raises(TypeError, match=f"expects 1 arguments, got {count}"):
        target(*range(count))
    hit.assert_not_called()
    assert target(7) == 7
    hit.assert_called_once_with(7)


@pytest.mark.parametrize("route", ["direct", "cascade", "any-alias", "host"])
@pytest.mark.parametrize("count", [0, 2])
def test_imported_file_callable_keeps_arity(route, count, make_interpreter, tmp_path):
    path = tmp_path / "callback.thirsty"
    path.write_text("glass target(value) { return value }", encoding="utf-8")
    interpreter = make_interpreter(policy='when action == "import" => ALLOW')
    interpreter.source_directory = tmp_path
    interpreter.interpret(parse('import "callback.thirsty" as callbacks'))
    arguments = ", ".join(str(index) for index in range(count))
    source = f"callbacks.target({arguments})"
    if route == "cascade":
        source = "cascade " + source
    elif route == "any-alias":
        source = f"drink callback: Any = callbacks.target\ncallback({arguments})"
    with pytest.raises(TypeError, match=f"expects 1 arguments, got {count}"):
        if route == "host":
            interpreter.env.get("callbacks")["target"](*range(count))
        else:
            interpreter.interpret(parse(source))
    assert interpreter.interpret(parse("callbacks.target(7)")) == 7


def fountain_program(receiver, *, contract=False, initializer=True):
    prefix = "" if receiver == "implicit" else "self, "
    condition = " requires contract()" if contract else ""
    init = (
        f"glass init({prefix}value){condition} {{ this.value = value\ninit_hit() }}"
        if initializer
        else ""
    )
    program = parse(
        "fountain Box {\nvalue = default_value()\n"
        + init
        + f"\nglass take({prefix}amount){condition} {{ method_hit()\nreturn this.value + amount }}\n}}"
    )
    if receiver == "this-ast":
        # Source uses implicit `this` or leading `self`; host ASTs also support
        # an explicit leading `this` parameter in the existing runtime API.
        for method in program.stmts[0].methods:
            method.params[0] = ("this", method.params[0][1])
    return program


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("receiver", ["implicit", "self", "this-ast"])
@pytest.mark.parametrize("contract", [False, True])
@pytest.mark.parametrize("count", [0, 2])
def test_fountain_constructor_rejects_before_field_defaults_and_init(
    optimization, receiver, contract, count, make_interpreter
):
    # Explicit host compatibility exercises local contracts without an
    # attached access policy; all arity and native context checks still run.
    interpreter = make_interpreter(
        optimization=optimization, policy=None, allow_ungoverned=True
    )
    defaults = Mock(return_value=1)
    initialize = Mock(return_value=None)
    predicate = Mock(return_value=True)
    interpreter.env.define("default_value", defaults)
    interpreter.env.define("init_hit", initialize)
    interpreter.env.define("method_hit", Mock())
    interpreter.env.define("contract", predicate)
    interpreter.interpret(fountain_program(receiver, contract=contract))
    original = interpreter.env
    arguments = ", ".join(str(index) for index in range(count))
    with pytest.raises(TypeError, match=f"'Box' expects 1 arguments, got {count}"):
        interpreter.interpret(parse(f"new Box({arguments})"))
    defaults.assert_not_called()
    initialize.assert_not_called()
    predicate.assert_not_called()
    assert interpreter.env is original
    instance = interpreter.interpret(parse("new Box(7)"))
    assert instance.fields["value"] == 7
    defaults.assert_called_once_with()
    initialize.assert_called_once_with()


@pytest.mark.parametrize("route", ["new", "alias", "host", "cascade"])
def test_fountain_without_init_has_zero_constructor_arguments(route, make_interpreter):
    interpreter = make_interpreter()
    defaults = Mock(return_value=7)
    interpreter.env.define("default_value", defaults)
    interpreter.interpret(fountain_program("implicit", initializer=False))
    sources = {
        "new": "new Box(1)",
        "alias": "drink build: Any = Box\nbuild(1)",
        "cascade": "cascade Box(1)",
    }
    with pytest.raises(TypeError, match="'Box' expects 0 arguments, got 1"):
        if route == "host":
            interpreter.env.get("Box")(1)
        else:
            interpreter.interpret(parse(sources[route]))
    defaults.assert_not_called()
    assert interpreter.interpret(parse("new Box()")).fields["value"] == 7
    defaults.assert_called_once_with()


@pytest.mark.parametrize("receiver", ["implicit", "self", "this-ast"])
@pytest.mark.parametrize("contract", [False, True])
@pytest.mark.parametrize("route", ["direct", "alias", "host", "cascade"])
@pytest.mark.parametrize("count", [0, 2])
def test_bound_method_arity_excludes_only_implicit_receiver(
    receiver, contract, route, count, make_interpreter
):
    interpreter = make_interpreter(policy=None, allow_ungoverned=True)
    hit = Mock()
    predicate = Mock(return_value=True)
    interpreter.env.define("default_value", lambda: 1)
    interpreter.env.define("init_hit", Mock(return_value=None))
    interpreter.env.define("method_hit", hit)
    interpreter.env.define("contract", predicate)
    interpreter.interpret(fountain_program(receiver, contract=contract))
    interpreter.interpret(parse("drink box = new Box(7)\ndrink callback = box.take"))
    predicate.reset_mock()
    original = interpreter.env
    arguments = ", ".join(str(index) for index in range(count))
    source = f"box.take({arguments})"
    if route == "alias":
        source = f"callback({arguments})"
    elif route == "cascade":
        source = "cascade " + source
    with pytest.raises(TypeError, match=f"'take' expects 1 arguments, got {count}"):
        if route == "host":
            interpreter.env.get("callback")(*range(count))
        else:
            interpreter.interpret(parse(source))
    hit.assert_not_called()
    predicate.assert_not_called()
    assert interpreter.env is original
    assert interpreter.interpret(parse("callback(2)")) == 9
    hit.assert_called_once_with()


@pytest.mark.parametrize("route", ["new", "alias", "cascade", "host"])
@pytest.mark.parametrize("count", [0, 2])
def test_struct_constructor_retains_exact_field_count(route, count, make_interpreter):
    interpreter = make_interpreter()
    interpreter.interpret(parse("struct Row { value: Int }\ndrink build: Any = Row"))
    arguments = ", ".join(str(index) for index in range(count))
    sources = {
        "new": f"new Row({arguments})",
        "alias": f"build({arguments})",
        "cascade": f"cascade build({arguments})",
    }
    with pytest.raises(TypeError, match=f"'Row' expects 1 fields, got {count}"):
        if route == "host":
            interpreter.env.get("build")(*range(count))
        else:
            interpreter.interpret(parse(sources[route]))
    assert interpreter.interpret(parse("build(7)")).fields == {"value": 7}


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("cascade", [False, True])
def test_valid_arity_does_not_swallow_or_bypass_governance_denials(
    kind, cascade, make_interpreter, capsys
):
    interpreter = make_interpreter(policy=None)
    interpreter.env.define("contract", lambda: True)
    interpreter.interpret(parse(declaration(kind, body="print(value)")))
    invocation = "cascade target(7)" if cascade else "target(7)"
    with pytest.raises(GovernanceViolation) as error:
        interpreter.interpret(
            parse(f"spillage {{ {invocation} }} error(e) {{ return 99 }}")
        )
    assert error.value.proof is not None
    assert error.value.proof.verdict is TarlVerdict.DENY
    assert capsys.readouterr().out == ""


def test_wrong_arity_is_catchable_without_entering_callee(make_interpreter):
    interpreter = make_interpreter()
    hit = Mock()
    interpreter.env.define("hit", hit)
    interpreter.interpret(parse(declaration("function")))
    assert (
        interpreter.interpret(parse("spillage { target() } error(e) { return 99 }"))
        == 99
    )
    hit.assert_not_called()
    assert interpreter.interpret(parse("target(7)")) == 7
