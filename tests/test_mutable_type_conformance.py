"""Writable container aliases are invariant; fresh values retain contextual typing."""

import pytest

from utf.thirsty_lang.checker import Checker
from utf.thirsty_lang.interpreter import Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser
from utf.thirsty_lang.typesys import (
    AnyType,
    ConstructorType,
    DictType,
    EnumType,
    FloatType,
    FunctionType,
    IntType,
    ReservoirType,
    StringType,
    StructType,
    is_assignable,
)


def parse(source):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors, lexer.errors
    assert not parser.errors, parser.errors
    return program


def check(source):
    return Checker().check_all(parse(source))


def run(source):
    program = parse(source)
    assert Checker().check_all(program) == []
    with Interpreter() as interpreter:
        return interpreter.interpret(program)


def assert_mismatch(source, code="E021"):
    errors = check(source)
    assert any(error.code == code for error in errors), errors
    assert all(error.code in {"E021", "E023"} for error in errors), errors


CONTAINERS = [
    pytest.param(lambda item: ReservoirType(item), id="reservoir"),
    pytest.param(lambda item: DictType(StringType(), item), id="dictionary-value"),
    pytest.param(lambda item: DictType(item, StringType()), id="dictionary-key"),
    pytest.param(
        lambda item: ReservoirType(ReservoirType(item)), id="nested-reservoir"
    ),
    pytest.param(
        lambda item: DictType(StringType(), ReservoirType(item)),
        id="dictionary-reservoir-value",
    ),
    pytest.param(
        lambda item: ReservoirType(DictType(StringType(), item)),
        id="reservoir-dictionary-value",
    ),
]


@pytest.mark.parametrize("container", CONTAINERS)
@pytest.mark.parametrize("reverse", [False, True])
def test_mutable_container_type_arguments_are_invariant(container, reverse):
    first, second = container(IntType()), container(FloatType())
    source, target = (second, first) if reverse else (first, second)
    assert not is_assignable(source, target)
    assert is_assignable(source, container(FloatType() if reverse else IntType()))


@pytest.mark.parametrize("container", CONTAINERS)
@pytest.mark.parametrize("position", ["parameter", "return"])
@pytest.mark.parametrize("reverse", [False, True])
def test_function_variance_does_not_widen_a_mutable_parameter_or_return(
    container, position, reverse
):
    first, second = container(IntType()), container(FloatType())
    if position == "parameter":
        first = FunctionType([first], IntType())
        second = FunctionType([second], IntType())
    else:
        first = FunctionType([], first)
        second = FunctionType([], second)
    source, target = (second, first) if reverse else (first, second)
    assert not is_assignable(source, target)


@pytest.mark.parametrize("container", CONTAINERS[:2])
@pytest.mark.parametrize("reverse", [False, True])
def test_writable_function_elements_cannot_use_scalar_callable_variance(
    container, reverse
):
    broad = FunctionType([FloatType()], IntType())
    narrow = FunctionType([IntType()], FloatType())
    assert is_assignable(broad, narrow)
    source, target = (narrow, broad) if reverse else (broad, narrow)
    assert not is_assignable(container(source), container(target))


@pytest.mark.parametrize("nominal", [EnumType, StructType])
@pytest.mark.parametrize("container", CONTAINERS[:2])
def test_nominal_container_arguments_preserve_declaration_identity(nominal, container):
    identity = object()
    first = nominal("Record", declaration_id=identity)
    same = nominal("Record", declaration_id=identity)
    other = nominal("Record", declaration_id=object())
    assert is_assignable(container(first), container(same))
    assert not is_assignable(container(first), container(other))
    assert not is_assignable(container(other), container(first))


def test_writable_constructor_elements_retain_nominal_constructor_identity():
    first = ConstructorType(StructType("Box", declaration_id=object()))
    other = ConstructorType(StructType("Box", declaration_id=object()))
    assert is_assignable(ReservoirType(first), ReservoirType(first))
    assert not is_assignable(ReservoirType(first), ReservoirType(other))
    assert not is_assignable(ReservoirType(first), ReservoirType(first.signature))


@pytest.mark.parametrize("container", CONTAINERS)
def test_any_container_compatibility_remains_an_explicit_gradual_boundary(container):
    assert is_assignable(container(AnyType()), container(IntType()))
    assert is_assignable(container(IntType()), container(AnyType()))


def test_scalar_int_to_float_and_scalar_function_variance_remain_valid():
    assert is_assignable(IntType(), FloatType())
    assert not is_assignable(FloatType(), IntType())
    assert is_assignable(
        FunctionType([FloatType()], IntType()),
        FunctionType([IntType()], FloatType()),
    )
    assert run("drink value: Float = 1\nvalue") == 1


SHAPES = [
    pytest.param("Reservoir[Int]", "Reservoir[Float]", "[1]", "[]", id="reservoir"),
    pytest.param(
        "Dict[String, Int]",
        "Dict[String, Float]",
        '{"value": 1}',
        "{}",
        id="dictionary-value",
    ),
    pytest.param(
        "Dict[Int, String]",
        "Dict[Float, String]",
        '{1: "value"}',
        "{}",
        id="dictionary-key",
    ),
    pytest.param(
        "Reservoir[Reservoir[Int]]",
        "Reservoir[Reservoir[Float]]",
        "[[1]]",
        "[]",
        id="nested-reservoir",
    ),
    pytest.param(
        "Dict[String, Reservoir[Int]]",
        "Dict[String, Reservoir[Float]]",
        '{"value": [1]}',
        "{}",
        id="dictionary-reservoir",
    ),
]

ROUTES = [
    "declaration",
    "assignment",
    "subscript-assignment",
    "record-constructor",
    "constructor-alias",
    "return",
    "call",
    "pipe",
    "pipeline",
    "arrow-pipe",
    "cascade",
]


def receiving_source(route, annotation, expression, empty):
    if route == "declaration":
        return f"drink target: {annotation} = {expression}\ntarget"
    if route == "assignment":
        return (
            f"drink mut target: {annotation} = {empty}\ntarget = {expression}\ntarget"
        )
    if route == "subscript-assignment":
        return (
            f"drink values: Reservoir[{annotation}] = [{empty}]\n"
            f"values[0] = {expression}\nvalues[0]"
        )
    if route in {"record-constructor", "constructor-alias"}:
        definition = f"struct Box {{ value: {annotation} }}\n"
        if route == "constructor-alias":
            return (
                definition + f"drink constructor = Box\nconstructor({expression}).value"
            )
        return definition + f"new Box({expression}).value"
    if route == "return":
        return f"glass target() -> {annotation} {{ return {expression} }}\ntarget()"
    definition = (
        f"glass target(value: {annotation}) -> {annotation} {{ return value }}\n"
    )
    calls = {
        "call": f"target({expression})",
        "pipe": f"({expression}) | target",
        "pipeline": f"({expression}) |> target",
        "arrow-pipe": f"({expression}) -> target",
        "cascade": f"cascade target({expression})",
    }
    return definition + calls[route]


@pytest.mark.parametrize("narrow,broad,literal,empty", SHAPES)
@pytest.mark.parametrize("route", ROUTES)
def test_shared_mutable_alias_cannot_widen_at_any_typed_receiving_boundary(
    narrow, broad, literal, empty, route
):
    source = f"drink shared: {narrow} = {literal}\n" + receiving_source(
        route, broad, "shared", empty
    )
    assert_mismatch(source, "E023" if route == "return" else "E021")


@pytest.mark.parametrize("narrow,broad,literal,empty", SHAPES)
@pytest.mark.parametrize("route", ROUTES)
def test_fresh_contextual_literal_widening_remains_valid_at_receiving_boundaries(
    narrow, broad, literal, empty, route
):
    source = receiving_source(route, broad, literal, empty)
    expected = {
        "[1]": [1],
        '{"value": 1}': {"value": 1},
        '{1: "value"}': {1: "value"},
        "[[1]]": [[1]],
        '{"value": [1]}': {"value": [1]},
    }
    assert run(source) == expected[literal]


@pytest.mark.parametrize("narrow,broad,literal,empty", SHAPES)
def test_annotated_mutable_alias_cannot_narrow_even_if_current_members_are_integers(
    narrow, broad, literal, empty
):
    source = (
        f"drink shared: {broad} = {literal}\n"
        f"drink target: {narrow} = shared\ntarget"
    )
    assert_mismatch(source)


@pytest.mark.parametrize("narrow,broad,literal,empty", SHAPES)
@pytest.mark.parametrize(
    "route", ["declaration", "call", "return", "record-constructor"]
)
def test_empty_literals_accept_the_receiving_concrete_container_type(
    narrow, broad, literal, empty, route
):
    assert run(receiving_source(route, broad, empty, empty)) == (
        [] if empty == "[]" else {}
    )


@pytest.mark.parametrize(
    "annotation,expression",
    [
        ("Reservoir[Reservoir[Float]]", "[inner]"),
        ("Reservoir[Reservoir[Float]]", "[[2.0], inner]"),
        ("Dict[String, Reservoir[Float]]", '{"shared": inner}'),
        ("Dict[String, Reservoir[Float]]", '{"fresh": [2.0], "shared": inner}'),
        ("Reservoir[Dict[String, Reservoir[Float]]]", '[{"shared": inner}]'),
    ],
)
@pytest.mark.parametrize(
    "route", ["declaration", "call", "return", "record-constructor"]
)
def test_fresh_outer_literal_does_not_change_shared_nested_alias_type(
    annotation, expression, route
):
    empty = "{}" if annotation.startswith("Dict") else "[]"
    source = "drink inner: Reservoir[Int] = [1]\n" + receiving_source(
        route, annotation, expression, empty
    )
    assert_mismatch(source, "E023" if route == "return" else "E021")


@pytest.mark.parametrize("receiver", ["[1, 2]", "shared"])
@pytest.mark.parametrize(
    "route", ["declaration", "call", "return", "record-constructor"]
)
def test_fresh_outer_slice_can_widen_scalar_elements_without_aliasing_its_receiver(
    receiver, route
):
    source = "drink shared: Reservoir[Int] = [1, 2]\n" + receiving_source(
        route, "Reservoir[Float]", f"{receiver}[: ]", "[]"
    )
    assert run(source) == [1, 2]


@pytest.mark.parametrize("receiver", ["[inner]", "nested"])
@pytest.mark.parametrize(
    "route", ["declaration", "call", "return", "record-constructor"]
)
def test_slice_does_not_widen_shared_nested_containers(receiver, route):
    source = (
        "drink inner: Reservoir[Int] = [1]\n"
        "drink nested: Reservoir[Reservoir[Int]] = [inner]\n"
    ) + receiving_source(route, "Reservoir[Reservoir[Float]]", f"{receiver}[: ]", "[]")
    assert_mismatch(source, "E023" if route == "return" else "E021")


@pytest.mark.parametrize("bounds", [":", "0:1", "0:0", "::-1"])
def test_fresh_nested_literal_slice_keeps_contextual_typing(bounds):
    source = f"drink target: Reservoir[Reservoir[Float]] = [[1], [2]][{bounds}]"
    assert check(source) == []


@pytest.mark.parametrize("bounds", [":", "0:1", "0:0", "::-1"])
def test_literal_slice_cannot_hide_invalid_elements_behind_its_bounds(bounds):
    source = f'drink target: Reservoir[Float] = [1, "wrong"][{bounds}]'
    assert_mismatch(source)


def test_scalar_slice_widening_does_not_allow_mutating_the_original_integer_list():
    source = (
        "drink integers: Reservoir[Int] = [1, 2]\n"
        "drink floats: Reservoir[Float] = integers[:]\n"
        "floats[0] = 1.5\n"
        "integers[0]"
    )
    assert run(source) == 1


@pytest.mark.parametrize("container", ["list", "dict"])
def test_nominal_aliases_with_the_same_declaration_remain_compatible(container):
    annotation = "Reservoir[Row]" if container == "list" else "Dict[String, Row]"
    value = "[new Row(7)]" if container == "list" else '{"row": new Row(7)}'
    source = (
        "struct Row { value: Int }\n"
        f"drink first: {annotation} = {value}\n"
        f"drink second: {annotation} = first"
    )
    assert check(source) == []


@pytest.mark.parametrize("position", ["parameter", "return"])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    "narrow,broad,integer_value,float_value",
    [
        ("Reservoir[Int]", "Reservoir[Float]", "[1]", "[1.5]"),
        (
            "Dict[String, Int]",
            "Dict[String, Float]",
            '{"value": 1}',
            '{"value": 1.5}',
        ),
    ],
)
def test_inferred_callable_bindings_preserve_mutable_signature_types(
    position, reverse, narrow, broad, integer_value, float_value
):
    if position == "parameter":
        declarations = (
            f"glass integers(value: {narrow}) {{ return 0 }}\n"
            f"glass floats(value: {broad}) {{ return 0 }}\n"
        )
    else:
        declarations = (
            f"glass integers() -> {narrow} {{ return {integer_value} }}\n"
            f"glass floats() -> {broad} {{ return {float_value} }}\n"
        )
    first, second = ("floats", "integers") if reverse else ("integers", "floats")
    assert_mismatch(declarations + f"drink mut target = {first}\ntarget = {second}")


@pytest.mark.parametrize("reverse", [False, True])
def test_shared_function_container_cannot_change_its_element_callable_contract(reverse):
    first, second = ("narrow", "broad") if reverse else ("broad", "narrow")
    source = (
        "glass broad(value: Float) -> Int { return 1 }\n"
        "glass narrow(value: Int) -> Float { return 1.5 }\n"
        f"drink shared = [{first}]\n"
        f"drink mut target = [{second}]\ntarget = shared"
    )
    assert_mismatch(source)


def test_fresh_function_container_retains_scalar_callable_substitution():
    source = (
        "glass broad(value: Float) -> Int { return 1 }\n"
        "glass narrow(value: Int) -> Float { return 1.5 }\n"
        "drink mut callbacks = [narrow]\ncallbacks = [broad]\ncallbacks[0](1)"
    )
    assert run(source) == 1


@pytest.mark.parametrize(
    "annotation,literal,index",
    [
        ("Reservoir[Int]", "[1]", "0"),
        ("Dict[String, Int]", '{"value": 1}', '"value"'),
    ],
)
def test_same_type_aliases_keep_shared_writable_container_behavior(
    annotation, literal, index
):
    source = (
        f"drink original: {annotation} = {literal}\n"
        f"drink alias: {annotation} = original\n"
        f"alias[{index}] = 7\noriginal[{index}]"
    )
    assert run(source) == 7
