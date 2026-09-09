"""Foreach type, scope, iterator protocol, and execution-boundary conformance."""

import pytest

from utf.thirsty_lang.checker import check_ast
from utf.thirsty_lang.interpreter import GovernanceViolation, Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser


def parsed(source):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors, lexer.errors
    assert not parser.errors, parser.errors
    return program


@pytest.fixture
def make_interpreter():
    interpreters = []

    def make(**options):
        interpreter = Interpreter(**options)
        interpreters.append(interpreter)
        return interpreter

    yield make
    for interpreter in interpreters:
        interpreter.executor.shutdown(wait=True)


def run(source, interpreter):
    program = parsed(source)
    assert check_ast(program) == []
    return interpreter.interpret(program)


@pytest.mark.parametrize(
    ("iterable", "element_type", "wrong_type"),
    [
        ("[1, 2]", "Int", "String"),
        ("[1, 2.5]", "Float", "Int"),
        ("[true, false]", "Bool", "Int"),
        ('["one", "two"]', "String", "Int"),
        ('{"one": 1, "two": 2}', "String", "Int"),
        ('{1: "one", 2: "two"}', "Int", "String"),
        ('"water"', "String", "Int"),
        ('""', "String", "Int"),
        ("[[1], [2]]", "Reservoir[Int]", "Reservoir[String]"),
    ],
)
def test_loop_element_types_follow_the_iterable(iterable, element_type, wrong_type):
    source = f"refill (item in {iterable}) {{ drink value: {element_type} = item }}"
    assert check_ast(parsed(source)) == []
    errors = check_ast(parsed(source.replace(f": {element_type}", f": {wrong_type}")))
    assert [error.code for error in errors] == ["E021"]


@pytest.mark.parametrize("iterable", ["[]", "{}", '[1, "two"]'])
def test_unknown_element_types_remain_dynamic(iterable):
    assert (
        check_ast(parsed(f"refill (item in {iterable}) {{ drink value: Int = item }}"))
        == []
    )


@pytest.mark.parametrize(
    ("declarations", "iterable"),
    [
        ("enum Item { Ready }", "[Item.Ready]"),
        ("enum Item { Ready }", "{Item.Ready: 1}"),
        ("struct Item { value: Int }", "[new Item(1)]"),
    ],
)
def test_loop_element_nominal_identity_survives_shadowing(declarations, iterable):
    source = (
        f"{declarations}\ndrink items = {iterable}\n"
        "refill (item in items) { drink same: Item = item }"
    )
    assert check_ast(parsed(source)) == []
    source = source.replace(
        "{ drink same: Item", f"{{ {declarations}\ndrink same: Item"
    )
    errors = check_ast(parsed(source))
    assert [error.code for error in errors] == ["E021"]


def test_nested_typed_loops_keep_record_fields(make_interpreter):
    source = (
        "struct Row { count: Int }\n"
        "glass total(groups: Dict[String, Reservoir[Row]]) -> Int {\n"
        "drink mut amount = 0\n"
        "refill (key in groups) { refill (row in groups[key]) {\n"
        "amount = amount + row.count\n} }\nreturn amount\n}\n"
        'total({"first": [new Row(2), new Row(3)], "second": [new Row(5)]})'
    )
    assert run(source, make_interpreter()) == 10
    errors = check_ast(parsed(source.replace("amount + row.count", "amount + row")))
    assert any(error.code == "E022" for error in errors)


def test_iterable_is_resolved_before_the_loop_binding(make_interpreter):
    errors = check_ast(parsed("refill (missing in missing) {}"))
    assert [error.code for error in errors] == ["E011"]
    source = (
        "drink items = [2, 3]\ndrink mut total = 0\n"
        "refill (items in items) { drink item: Int = items\ntotal = total + item }\n"
        "total + items[0]"
    )
    assert run(source, make_interpreter()) == 7


def test_invalid_iterable_does_not_hide_independent_body_errors():
    errors = check_ast(parsed("refill (item in 1) { missing }"))
    assert [error.code for error in errors] == ["E025", "E011"]


@pytest.mark.parametrize(
    ("declaration", "iterable"),
    [
        ("", "1"),
        ("", "1.5"),
        ("", "true"),
        ("", "none"),
        ("", "quenched(1)"),
        ("enum State { Ready }\n", "State.Ready"),
        ("struct Row { count: Int }\n", "new Row(1)"),
        ("glass value() { return 1 }\n", "value"),
    ],
)
def test_known_noniterables_are_rejected_at_the_iterable_span(declaration, iterable):
    program = parsed(f"{declaration}refill (item in {iterable}) {{}}")
    errors = check_ast(program)
    assert len(errors) == 1
    assert errors[0].code == "E025"
    assert "iteration requires an iterable" in errors[0].message
    assert errors[0].span == program.stmts[-1].iterable.span


def test_loop_binding_is_immutable_and_loop_locals_do_not_escape():
    errors = check_ast(
        parsed("refill (item in [1]) { item = 2\ndrink local = item }\nitem\nlocal")
    )
    assert [error.code for error in errors] == ["E020", "E011", "E011"]


@pytest.mark.parametrize(
    ("items", "expected"),
    [
        ([3, 1, 2], [3, 1, 2]),
        ({"second": 2, "first": 1}, ["second", "first"]),
        ("a\U0001f30a", ["a", "\U0001f30a"]),
        ((3, 1, 2), [3, 1, 2]),
        (bytes([3, 1, 2]), [3, 1, 2]),
        ([], []),
    ],
)
def test_dynamic_iterables_preserve_native_order(items, expected, make_interpreter):
    interpreter = make_interpreter()
    walk = run(
        "glass walk(items, visit) { refill (item in items) { visit(item) } }\nwalk",
        interpreter,
    )
    visited = []
    walk(items, visited.append)
    assert visited == expected
    assert not interpreter.env.has("item")


@pytest.mark.parametrize("items", [None, False, 0, 2.5, object()])
@pytest.mark.parametrize("optimization", [0, 3])
def test_dynamic_noniterable_raises_and_restores_scope(
    items, optimization, make_interpreter
):
    interpreter = make_interpreter(opt_level=optimization)
    walk = run(
        "glass walk(items, visit) { refill (item in items) { visit(item) } }\nwalk",
        interpreter,
    )
    environment = interpreter.env
    visited = []
    with pytest.raises(TypeError, match="not iterable"):
        walk(items, visited.append)
    assert visited == []
    assert interpreter.env is environment
    assert not interpreter.env.has("item")


def test_source_evaluates_once_and_iterator_is_acquired_once_lazily(make_interpreter):
    events = []

    class Items:
        def __init__(self):
            self.next_value = 1

        def __iter__(self):
            events.append("iter")
            return self

        def __next__(self):
            events.append(f"next:{self.next_value}")
            if self.next_value > 2:
                raise StopIteration
            value = self.next_value
            self.next_value += 1
            return value

    def source():
        events.append("source")
        return Items()

    walk = run(
        "glass walk(source, visit) { refill (item in source()) { visit(item) } }\nwalk",
        make_interpreter(),
    )
    walk(source, lambda item: events.append(f"body:{item}"))
    assert events == [
        "source",
        "iter",
        "next:1",
        "body:1",
        "next:2",
        "body:2",
        "next:3",
    ]


def test_host_sequence_protocol_is_iterated(make_interpreter):
    class Items:
        def __getitem__(self, index):
            if index == 2:
                raise IndexError
            return index + 1

    walk = run(
        "glass walk(items, visit) { refill (item in items) { visit(item) } }\nwalk",
        make_interpreter(),
    )
    visited = []
    walk(Items(), visited.append)
    assert visited == [1, 2]


@pytest.mark.parametrize("failure_site", ["source", "iter", "next", "body"])
@pytest.mark.parametrize("exception_type", [TypeError, RuntimeError])
def test_original_iteration_errors_propagate_and_restore_scope(
    failure_site, exception_type, make_interpreter
):
    failure = exception_type("original failure")
    events = []

    def event(site):
        events.append(site)
        if site == failure_site:
            raise failure

    class Items:
        def __iter__(self):
            event("iter")
            return self

        def __next__(self):
            event("next")
            return 1

    def source():
        event("source")
        return Items()

    interpreter = make_interpreter()
    walk = run(
        "glass walk(source, visit) { refill (item in source()) { visit(item) } }\nwalk",
        interpreter,
    )
    environment = interpreter.env
    with pytest.raises(exception_type) as error:
        walk(source, lambda item: event("body"))
    assert error.value is failure
    order = ["source", "iter", "next", "body"]
    assert events == order[: order.index(failure_site) + 1]
    assert interpreter.env is environment
    assert not interpreter.env.has("item")


@pytest.mark.parametrize("optimization", range(4))
def test_each_iteration_has_its_own_closure_scope(optimization, make_interpreter):
    collect = run(
        "glass collect(save) { refill (item in [1, 2, 3]) {\n"
        "drink local = item * 10\nsave(glass() { return local })\n} }\ncollect",
        make_interpreter(opt_level=optimization),
    )
    callbacks = []
    collect(callbacks.append)
    assert [callback() for callback in callbacks] == [10, 20, 30]


@pytest.mark.parametrize("cascade", [False, True])
def test_return_stops_iteration_without_consuming_later_items(
    cascade, make_interpreter
):
    pulled = []

    def values():
        for value in [4, 5, 6]:
            pulled.append(value)
            yield value

    call = "cascade first(items)" if cascade else "first(items)"
    first = run(
        "glass first(items) { refill (item in items) { return item } }\n"
        f"glass launch(items) {{ return {call} }}\nlaunch",
        make_interpreter(),
    )
    assert first(values()) == 4
    assert pulled == [4]


def test_spillage_can_handle_dynamic_noniterable_error(make_interpreter):
    attempt = run(
        "glass attempt(items) {\n"
        "spillage { refill (item in items) {} } error (failure) { return failure }\n"
        "}\nattempt",
        make_interpreter(),
    )
    error = attempt(1)
    assert isinstance(error, TypeError)
    assert "not iterable" in str(error)


def test_cascade_propagates_dynamic_noniterable_error(make_interpreter):
    interpreter = make_interpreter()
    launch = run(
        "glass walk(items) { refill (item in items) {} }\n"
        "glass launch(items) { return cascade walk(items) }\nlaunch",
        interpreter,
    )
    environment = interpreter.env
    with pytest.raises(TypeError, match="not iterable"):
        launch(1)
    assert interpreter.env is environment


def test_throw_stops_iteration_and_retains_the_thrown_value(make_interpreter):
    interpreter = make_interpreter()
    source = (
        "drink mut visits = 0\ndrink mut caught = 0\n"
        "spillage { refill (item in [7, 8]) {\n"
        "visits = visits + 1\nthrow item\n} } error (failure) { caught = failure }\n"
        "[visits, caught]"
    )
    assert run(source, interpreter) == [1, 7]
    assert not interpreter.env.has("item")


def test_iterable_expression_governance_denial_precedes_loop_body(
    make_interpreter, capsys
):
    interpreter = make_interpreter()
    source = (
        "drink mut visited = false\n"
        'refill (item in print("source")) { visited = true }'
    )
    environment = interpreter.env
    with pytest.raises(GovernanceViolation):
        # print has an unknown static result; the source effect must still deny.
        run(source, interpreter)
    assert interpreter.env.get("visited") is False
    assert interpreter.env is environment
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("cascade", [False, True])
@pytest.mark.parametrize("mode", ["governed", "pure"])
def test_loop_effect_denial_stops_iteration_and_restores_scope(
    cascade, mode, make_interpreter, capsys
):
    interpreter = make_interpreter()
    call = "cascade walk(items)" if cascade else "walk(items)"
    walk = run(
        f"module example: {mode}\n"
        "glass walk(items) { refill (item in items) { print(item) } }\n"
        f"glass launch(items) {{ return {call} }}\nlaunch",
        interpreter,
    )
    environment = interpreter.env
    pulled = []

    def values():
        for value in [1, 2]:
            pulled.append(value)
            yield value

    exception_type = GovernanceViolation if mode == "governed" else RuntimeError
    with pytest.raises(exception_type):
        walk(values())
    assert pulled == [1]
    assert capsys.readouterr().out == ""
    assert interpreter.env is environment
    assert not interpreter.env.has("item")


def test_spillage_does_not_swallow_loop_governance_denial(make_interpreter, capsys):
    source = (
        "drink mut handled = false\n"
        "spillage { refill (item in [1, 2]) { print(item) } }\n"
        "error { handled = true }"
    )
    interpreter = make_interpreter()
    environment = interpreter.env
    with pytest.raises(GovernanceViolation):
        run(source, interpreter)
    assert interpreter.env.get("handled") is False
    assert interpreter.env is environment
    assert capsys.readouterr().out == ""
