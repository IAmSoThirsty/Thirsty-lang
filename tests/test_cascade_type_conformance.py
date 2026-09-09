"""Cascade exposes its awaited value while preserving call/effect boundaries."""

import pytest

from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
from utf.thirsty_lang.ast import CascadeCall
from utf.thirsty_lang.checker import Checker
from utf.thirsty_lang.interpreter import GovernanceViolation, Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser
from utf.thirsty_lang.typesys import (
    AnyType,
    FloatType,
    FunctionType,
    FunctionUnionType,
    IntType,
    unify,
)


def parsed(source):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors, lexer.errors
    assert not parser.errors, parser.errors
    return program


def inspect_source(source, bindings=None):
    checker = Checker()
    for name, descriptor in (bindings or {}).items():
        checker.scope.declare(
            name, {"type": descriptor, "is_mut": False, "kind": "function"}
        )
    program = parsed(source)
    return checker, program, checker.check_all(program)


@pytest.fixture
def make_interpreter():
    interpreters = []
    runtimes = []

    def make(*, policy=None, **options):
        interpreter = Interpreter(**options)
        interpreters.append(interpreter)
        if policy is not None:
            runtime = TarlRuntime(PolicyParser.parse(policy))
            runtimes.append(runtime)
            interpreter.attach_tarl(runtime).set_authority("cascade-test")
        return interpreter

    yield make
    for interpreter in interpreters:
        interpreter.executor.shutdown(wait=True)
    for runtime in runtimes:
        runtime.shutdown()


def run(source, interpreter):
    _, program, errors = inspect_source(source)
    assert errors == []
    return interpreter.interpret(program)


@pytest.mark.parametrize(
    "invocation", ["cascade value()", "cascade (cascade value())", "cascade 7"]
)
def test_cascade_infers_the_completed_value(invocation, make_interpreter):
    source = f"glass value() -> Int {{ return 7 }}\ndrink result = {invocation}\nresult"
    checker, program, errors = inspect_source(source)
    assert errors == []
    assert isinstance(checker.scope.lookup("result")["type"], IntType)
    assert make_interpreter().interpret(program) == 7


@pytest.mark.parametrize("site", ["declaration", "assignment", "return", "argument"])
@pytest.mark.parametrize("valid", [False, True])
def test_cascade_value_contract_flows_through_typed_sites(
    site, valid, make_interpreter
):
    annotation = "Int" if valid else "String"
    prefix = "glass value() -> Int { return 7 }\n"
    if site == "declaration":
        body = f"drink result: {annotation} = cascade value()\nresult"
    elif site == "assignment":
        initial = "0" if valid else '"initial"'
        body = (
            f"drink mut result: {annotation} = {initial}\n"
            "result = cascade value()\nresult"
        )
    elif site == "return":
        body = f"glass wrap() -> {annotation} {{ return cascade value() }}\nwrap()"
    else:
        body = (
            f"glass take(result: {annotation}) -> {annotation} {{ return result }}\n"
            "take(cascade value())"
        )
    _, program, errors = inspect_source(prefix + body)
    if valid:
        assert errors == []
        assert make_interpreter().interpret(program) == 7
    else:
        assert any(
            error.code == ("E023" if site == "return" else "E021") for error in errors
        )


@pytest.mark.parametrize("site", ["variable", "return"])
def test_cascade_result_is_not_a_task_value(site):
    prefix = "glass value() -> Int { return 7 }\n"
    source = (
        "drink result: Task[Int] = cascade value()"
        if site == "variable"
        else "glass wrap() -> Task[Int] { return cascade value() }"
    )
    _, _, errors = inspect_source(prefix + source)
    assert [error.code for error in errors] == [
        "E021" if site == "variable" else "E023"
    ]


def test_cascade_collections_preserve_nested_nominal_values(make_interpreter):
    source = (
        "struct Row { count: Int }\n"
        "glass load() -> Dict[String, Reservoir[Row]] {\n"
        'return {"rows": [new Row(2), new Row(3)]}\n}\n'
        "drink groups = cascade load()\ndrink mut total = 0\n"
        'refill (row in groups["rows"]) { total = total + row.count }\ntotal'
    )
    assert run(source, make_interpreter()) == 5
    _, _, errors = inspect_source(source.replace("total + row.count", "total + row"))
    assert any(error.code == "E022" for error in errors)


@pytest.mark.parametrize("operator", ["|", "->"])
@pytest.mark.parametrize("alias", [False, True])
@pytest.mark.parametrize("valid", [False, True])
def test_awaited_callback_preserves_pipe_parameter_and_result_contract(
    operator, alias, valid, make_interpreter
):
    source = "glass add(value: Int) -> Float { return value + 0.5 }\n"
    if alias:
        source += "drink callback = cascade add\n"
        callback = "callback"
    else:
        callback = "(cascade add)"
    argument = "4" if valid else "4.5"
    source += f"drink result: Float = {argument} {operator} {callback}\nresult"
    checker, program, errors = inspect_source(source)
    if alias:
        assert isinstance(checker.scope.lookup("callback")["type"], FunctionType)
    if valid:
        assert errors == []
        assert make_interpreter().interpret(program) == 4.5
    else:
        assert any(error.code == "E021" for error in errors)


def test_collection_of_awaited_callbacks_retains_all_signatures(make_interpreter):
    source = (
        "glass add(value: Int) -> Int { return value + 1 }\n"
        "glass half(value: Float) -> Float { return value / 2 }\n"
        "drink callbacks = [cascade add, cascade half]\n"
        "drink mut result: Float = 0.0\n"
        "refill (callback in callbacks) { result = result + callback(4) }\nresult"
    )
    assert run(source, make_interpreter()) == 7.0
    _, _, errors = inspect_source(source.replace("callback(4)", "callback(4.5)"))
    assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("argument,valid", [("1", True), ("1.5", False)])
def test_awaited_factory_preserves_nested_callback_alternatives(
    nested, argument, valid, make_interpreter
):
    signature = unify(
        FunctionType([], FunctionType([IntType()], IntType())),
        FunctionType([], FunctionType([FloatType()], FloatType())),
    )
    invocation = "cascade (cascade factory())" if nested else "cascade factory()"
    source = (
        f"drink callback = {invocation}\n"
        f"drink result: Float = callback({argument})\nresult"
    )
    checker, program, errors = inspect_source(source, {"factory": signature})
    assert isinstance(checker.scope.lookup("callback")["type"], FunctionUnionType)
    if valid:
        assert errors == []
        interpreter = make_interpreter()
        interpreter.env.define("factory", lambda: lambda value: value + 1)
        assert interpreter.interpret(program) == 2
    else:
        assert any(error.code == "E021" for error in errors)


def test_unknown_cascade_results_remain_dynamic():
    checker, _, errors = inspect_source(
        "drink result = cascade foreign()", {"foreign": AnyType()}
    )
    assert errors == []
    assert isinstance(checker.scope.lookup("result")["type"], AnyType)


@pytest.mark.parametrize("statement", [False, True])
def test_cascade_keeps_argument_diagnostics_and_span(statement):
    prefix = "glass value(input: Int) -> Int { return input }\n"
    invocation = 'cascade value("wrong")'
    source = prefix + (invocation if statement else "drink result = " + invocation)
    _, program, errors = inspect_source(source)
    assert [error.code for error in errors] == ["E021"]
    cascade = program.stmts[-1] if statement else program.stmts[-1].init_expr
    assert isinstance(cascade, CascadeCall)
    assert errors[0].span == cascade.expr.args[0].span


@pytest.mark.parametrize("statement", [False, True])
def test_cascade_checks_unknown_callee_and_argument_once(statement):
    invocation = "cascade missing(unknown)"
    source = invocation if statement else "drink result = " + invocation
    _, _, errors = inspect_source(source)
    names = [error.message for error in errors if error.code == "E011"]
    assert len(names) == 2
    assert sum("'missing'" in message for message in names) == 1
    assert sum("'unknown'" in message for message in names) == 1


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("callable_result", [False, True])
def test_cascade_evaluates_callee_and_arguments_once_before_invocation(
    optimization, callable_result, make_interpreter
):
    interpreter = make_interpreter(opt_level=optimization)
    invoke = run(
        "glass invoke(make, argument) { return cascade make()(argument()) }\ninvoke",
        interpreter,
    )
    environment = interpreter.env
    events = []

    def body(value):
        events.append("body")
        return value + 1

    def make():
        events.append("callee")
        return body if callable_result else 1

    def argument():
        events.append("argument")
        return 4

    if callable_result:
        assert invoke(make, argument) == 5
        assert events == ["callee", "argument", "body"]
    else:
        with pytest.raises(TypeError, match="non-callable"):
            invoke(make, argument)
        assert events == ["callee", "argument"]
    assert interpreter.env is environment


@pytest.mark.parametrize("mode", ["governed", "pure"])
def test_cascade_denial_prevents_output_and_preserves_scope(
    mode, make_interpreter, capsys
):
    interpreter = make_interpreter()
    source = (
        f"module example: {mode}\n"
        "glass emit(value: Int) -> Int { print(value)\nreturn value }\n"
        "drink result: Int = cascade emit(7)\nresult"
    )
    environment = interpreter.env
    exception = GovernanceViolation if mode == "governed" else RuntimeError
    with pytest.raises(exception):
        run(source, interpreter)
    assert capsys.readouterr().out == ""
    assert interpreter.env is environment


def test_cascade_allowed_output_returns_its_typed_value(make_interpreter, capsys):
    interpreter = make_interpreter(
        policy='when action == "write" and target == "stdout" => ALLOW\nwhen true => DENY'
    )
    result = run(
        "glass emit(value: Int) -> Int { print(value)\nreturn value }\n"
        "drink result: Int = cascade emit(7)\nresult",
        interpreter,
    )
    assert result == 7
    assert capsys.readouterr().out == "7\n"


def test_cascade_callee_denial_precedes_argument_effects(make_interpreter, capsys):
    interpreter = make_interpreter()
    invoke = run(
        'glass make() { print("forbidden")\nreturn 1 }\n'
        "glass invoke(argument) { return cascade make()(argument()) }\ninvoke",
        interpreter,
    )
    events = []
    with pytest.raises(GovernanceViolation):
        invoke(lambda: events.append("argument"))
    assert events == []
    assert capsys.readouterr().out == ""


def test_cascade_propagates_worker_exception_identity(make_interpreter):
    interpreter = make_interpreter()
    invoke = run(
        "glass invoke(callback) { return cascade callback() }\ninvoke", interpreter
    )
    failure = ValueError("worker failure")

    def callback():
        raise failure

    environment = interpreter.env
    with pytest.raises(ValueError) as error:
        invoke(callback)
    assert error.value is failure
    assert interpreter.env is environment


def test_cascade_governance_denial_cannot_be_caught_by_spillage(
    make_interpreter, capsys
):
    interpreter = make_interpreter()
    source = (
        "drink mut handled = false\n"
        'spillage { cascade print("forbidden") } error { handled = true }'
    )
    with pytest.raises(GovernanceViolation):
        run(source, interpreter)
    assert interpreter.env.get("handled") is False
    assert capsys.readouterr().out == ""
