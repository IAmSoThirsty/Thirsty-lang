"""Native callable bodies and contracts retain their defining lexical scope."""

import pytest

from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
from utf.tarl.spec import TarlVerdict
from utf.thirsty_lang.checker import Checker
from utf.thirsty_lang.interpreter import GovernanceViolation, Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser


def parse(source, *, check=True):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors, lexer.errors
    assert not parser.errors, parser.errors
    if check:
        assert Checker().check_all(program) == []
    return program


@pytest.fixture
def make_interpreter():
    interpreters = []
    runtimes = []

    def make(optimization=0):
        interpreter = Interpreter(opt_level=optimization)
        runtime = TarlRuntime(PolicyParser.parse("when true => ALLOW"))
        interpreter.attach_tarl(runtime).set_authority("lexical-scope-test")
        interpreters.append(interpreter)
        runtimes.append(runtime)
        return interpreter

    yield make
    for interpreter in interpreters:
        interpreter.executor.shutdown(wait=True)
    for runtime in runtimes:
        runtime.shutdown()


def declaration(kind, body="return captured"):
    if kind == "lambda":
        return f"drink target = glass() {{ {body} }}"
    if kind == "morph":
        return f"morph target() {{ {body} }}"
    contract = " requires true" if kind == "governed" else ""
    return f"glass target(){contract} {{ {body} }}"


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("kind", ["function", "lambda", "morph", "governed"])
@pytest.mark.parametrize("cascade", [False, True])
def test_caller_shadowing_cannot_replace_callable_free_variables(
    optimization, kind, cascade, make_interpreter
):
    call = "cascade target()" if cascade else "target()"
    program = parse(
        "drink captured = 7\n"
        + declaration(kind)
        + f"\nglass caller(captured) {{ return {call} }}\ncaller(99)"
    )
    interpreter = make_interpreter(optimization)
    original = interpreter.env
    assert interpreter.interpret(program) == 7
    assert interpreter.env is original
    assert interpreter.env.get("captured") == 7


@pytest.mark.parametrize("kind", ["function", "lambda", "morph", "governed"])
def test_escaped_factory_callables_keep_distinct_enclosing_scopes(
    kind, make_interpreter
):
    interpreter = make_interpreter()
    factory = interpreter.interpret(
        parse(
            "glass factory(captured) {\n"
            + declaration(kind)
            + "\nreturn target\n}\nfactory"
        )
    )
    first = factory(7)
    second = factory(9)
    original = interpreter.env
    assert [first(), second(), first()] == [7, 9, 7]
    assert interpreter.env is original
    assert not interpreter.env.has("captured")


@pytest.mark.parametrize("receiver", ["", "self"])
@pytest.mark.parametrize("governed", [False, True])
@pytest.mark.parametrize("cascade", [False, True])
def test_fountain_method_uses_class_scope_after_constructor_returns(
    receiver, governed, cascade, make_interpreter
):
    contract = " requires true" if governed else ""
    call = "cascade box.read()" if cascade else "box.read()"
    program = parse(
        "glass factory(captured) {\n"
        "fountain Box {\nvalue = captured\n"
        f"glass read({receiver}){contract} {{ return captured + this.value }}\n"
        "}\nreturn Box\n}\n"
        "drink Box = factory(7)\n"
        "glass construct(captured) { return new Box() }\n"
        "drink box = construct(100)\n"
        f"glass caller(captured) {{ return {call} }}\ncaller(99)"
    )
    interpreter = make_interpreter()
    assert interpreter.interpret(program) == 14
    assert interpreter.env.get("box").fields["value"] == 7
    assert not interpreter.env.has("captured")


@pytest.mark.parametrize("governed", [False, True])
def test_escaped_bound_method_keeps_receiver_and_declaration_scope(
    governed, make_interpreter
):
    contract = " requires true" if governed else ""
    interpreter = make_interpreter()
    factory = interpreter.interpret(
        parse(
            "glass factory(captured) {\n"
            "fountain Box {\nvalue = captured\n"
            f"glass read(self){contract} {{ return captured + self.value }}\n"
            "}\ndrink box = new Box()\nreturn box.read\n}\nfactory"
        )
    )
    first = factory(7)
    second = factory(9)
    original = interpreter.env
    assert [first(), second(), first()] == [14, 18, 14]
    assert interpreter.env is original
    assert not interpreter.env.has("this")
    assert not interpreter.env.has("self")


@pytest.mark.parametrize("method", [False, True])
@pytest.mark.parametrize("cascade", [False, True])
def test_caller_cannot_shadow_a_false_contract_free_variable_to_allow_execution(
    method, cascade, make_interpreter
):
    definition = "glass target() requires permitted { return 7 }"
    call = "target()"
    if method:
        definition = (
            "fountain Box {\n"
            "glass target() requires permitted { return 7 }\n"
            "}\ndrink box = new Box()"
        )
        call = "box.target()"
    if cascade:
        call = "cascade " + call
    program = parse(
        "drink permitted = false\n"
        + definition
        + f"\nglass caller(permitted) {{ return {call} }}\ncaller(true)"
    )
    interpreter = make_interpreter()
    original = interpreter.env
    with pytest.raises(GovernanceViolation, match="precondition failed") as error:
        interpreter.interpret(program)
    assert error.value.proof.verdict is TarlVerdict.DENY
    assert interpreter.env is original
    assert interpreter.env.get("permitted") is False


@pytest.mark.parametrize("method", [False, True])
def test_exit_contract_uses_definition_scope_even_when_caller_shadows_result_limit(
    method, make_interpreter
):
    definition = "glass target() ensures result <= limit { return 7 }"
    call = "target()"
    if method:
        definition = (
            "fountain Box {\n"
            "glass target() ensures result <= limit { return 7 }\n"
            "}\ndrink box = new Box()"
        )
        call = "box.target()"
    program = parse(
        "drink limit = 5\n"
        + definition
        + f"\nglass caller(limit) {{ return {call} }}\ncaller(99)"
    )
    interpreter = make_interpreter()
    original = interpreter.env
    with pytest.raises(GovernanceViolation, match="postcondition failed") as error:
        interpreter.interpret(program)
    assert error.value.proof.verdict is TarlVerdict.DENY
    assert interpreter.env is original
    assert interpreter.env.get("limit") == 5


@pytest.mark.parametrize("governed", [False, True])
def test_fountain_field_defaults_and_initializer_share_class_lexical_scope(
    governed, make_interpreter
):
    contract = " requires captured == 7" if governed else ""
    program = parse(
        "glass factory(captured) {\n"
        "fountain Box {\nvalue = captured\n"
        f"glass init(){contract} {{ this.value = this.value + captured }}\n"
        "}\nreturn Box\n}\n"
        "drink Box = factory(7)\n"
        "glass caller(captured) { return new Box() }\ncaller(99)"
    )
    interpreter = make_interpreter()
    original = interpreter.env
    instance = interpreter.interpret(program)
    assert instance.fields["value"] == 14
    assert interpreter.env is original
    assert not interpreter.env.has("this")


def test_failed_initializer_restores_caller_then_existing_lexical_closure(
    make_interpreter,
):
    program = parse(
        "drink captured = 7\n"
        "glass stable() { return captured }\n"
        "fountain Box {\nvalue = captured\n"
        "glass init() requires false { this.value = 99 }\n}\n"
        "glass caller(captured) { return new Box() }"
    )
    interpreter = make_interpreter()
    interpreter.interpret(program)
    original = interpreter.env
    with pytest.raises(GovernanceViolation):
        interpreter.env.get("caller")(99)
    assert interpreter.env is original
    assert interpreter.env.get("stable")() == 7
    assert not interpreter.env.has("this")
