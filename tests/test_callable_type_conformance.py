"""Callable substitution and selection preserve safe input and output contracts."""

import pytest

from utf.thirsty_lang.checker import Checker
from utf.thirsty_lang.interpreter import Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser
from utf.thirsty_lang.typesys import (
    AnyType,
    DictType,
    EnumType,
    FloatType,
    FunctionType,
    FunctionUnionType,
    IntType,
    ReservoirType,
    StringType,
    StructType,
    is_assignable,
    type_to_string,
    unify,
)


def parse(source):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors and not parser.errors
    return program


def inspect_source(source):
    checker = Checker()
    errors = checker.check_all(parse(source))
    return checker, errors


def run(source):
    interpreter = Interpreter()
    try:
        return interpreter.interpret(parse(source))
    finally:
        interpreter.executor.shutdown(wait=True)


@pytest.mark.parametrize(
    "source_input,target_input,source_output,target_output,expected",
    [
        (FloatType, IntType, IntType, IntType, True),
        (IntType, FloatType, IntType, IntType, False),
        (IntType, IntType, IntType, FloatType, True),
        (IntType, IntType, FloatType, IntType, False),
        (FloatType, IntType, IntType, FloatType, True),
        (IntType, FloatType, FloatType, IntType, False),
        (FloatType, FloatType, FloatType, FloatType, True),
        (IntType, IntType, IntType, IntType, True),
    ],
)
def test_callable_substitution_checks_contravariant_input_and_covariant_output(
    source_input, target_input, source_output, target_output, expected
):
    source = FunctionType([source_input()], source_output())
    target = FunctionType([target_input()], target_output())
    assert is_assignable(source, target) is expected


@pytest.mark.parametrize("position", [0, 1, 2])
def test_every_parameter_must_accept_the_target_call_domain(position):
    target = FunctionType([FloatType(), FloatType(), FloatType()], IntType())
    source_parameters = [FloatType(), FloatType(), FloatType()]
    source_parameters[position] = IntType()
    assert not is_assignable(FunctionType(source_parameters, IntType()), target)
    assert is_assignable(target, FunctionType(source_parameters, FloatType()))


@pytest.mark.parametrize("reverse", [False, True])
def test_callable_join_preserves_alternatives_and_safe_common_contract(reverse):
    narrow = FunctionType([IntType()], IntType())
    broad = FunctionType([FloatType()], FloatType())
    joined = unify(*(reversed((narrow, broad)) if reverse else (narrow, broad)))
    assert isinstance(joined, FunctionUnionType)
    assert len(joined.alternatives) == 2
    assert is_assignable(narrow, joined)
    assert is_assignable(broad, joined)
    assert is_assignable(joined, FunctionType([IntType()], FloatType()))
    assert not is_assignable(joined, FunctionType([FloatType()], FloatType()))
    assert not is_assignable(joined, FunctionType([IntType()], IntType()))


@pytest.mark.parametrize("reverse", [False, True])
def test_callable_join_intersects_each_parameter_independently(reverse):
    first = FunctionType([FloatType(), IntType()], IntType())
    second = FunctionType([IntType(), FloatType()], FloatType())
    joined = unify(*(reversed((first, second)) if reverse else (first, second)))
    assert isinstance(joined, FunctionUnionType)
    assert len(joined.alternatives) == 2
    assert is_assignable(first, joined) and is_assignable(second, joined)
    assert is_assignable(joined, FunctionType([IntType(), IntType()], FloatType()))
    assert not is_assignable(joined, first)
    assert not is_assignable(joined, second)


def test_higher_order_parameter_variance_reverses_at_each_boundary():
    broad_callback = FunctionType([FloatType()], IntType())
    narrow_callback = FunctionType([IntType()], IntType())
    accepts_narrow_callback = FunctionType([narrow_callback], IntType())
    requires_broad_callback = FunctionType([broad_callback], IntType())
    assert is_assignable(broad_callback, narrow_callback)
    assert is_assignable(accepts_narrow_callback, requires_broad_callback)
    assert not is_assignable(requires_broad_callback, accepts_narrow_callback)


def test_callable_returning_callable_keeps_covariant_result_contract():
    broader = FunctionType([], FunctionType([FloatType()], IntType()))
    narrower = FunctionType([], FunctionType([IntType()], FloatType()))
    assert is_assignable(broader, narrower)
    assert not is_assignable(narrower, broader)


@pytest.mark.parametrize("nominal_kind", [EnumType, StructType])
@pytest.mark.parametrize("reverse", [False, True])
def test_join_keeps_nested_nominal_declaration_identity(nominal_kind, reverse):
    nominal = nominal_kind("Record", declaration_id=object())
    domain = DictType(StringType(), ReservoirType(nominal))
    first = FunctionType([domain], IntType())
    second = FunctionType([domain], FloatType())
    joined = unify(*(reversed((first, second)) if reverse else (first, second)))
    assert isinstance(joined, FunctionUnionType)
    assert len(joined.alternatives) == 2
    for alternative in joined.alternatives:
        assert alternative.param_types[0].value_type.inner_type is nominal
    assert is_assignable(joined, FunctionType([domain], FloatType()))


@pytest.mark.parametrize("nominal_kind", [EnumType, StructType])
def test_same_named_distinct_nominal_callable_parameters_are_not_substitutable(
    nominal_kind,
):
    first = nominal_kind("Record", declaration_id=object())
    second = nominal_kind("Record", declaration_id=object())
    first_fn = FunctionType([ReservoirType(first)], IntType())
    second_fn = FunctionType([ReservoirType(second)], IntType())
    assert not is_assignable(first_fn, second_fn)
    assert not is_assignable(second_fn, first_fn)


@pytest.mark.parametrize(
    "initial,replacement,expected_errors",
    [
        ("takes_float", "takes_int", True),
        ("takes_int", "takes_float", False),
    ],
)
def test_inferred_callback_assignment_respects_input_contract(
    initial, replacement, expected_errors
):
    source = (
        "glass takes_int(value: Int) -> Int { return 1 }\n"
        "glass takes_float(value: Float) -> Int { return 2 }\n"
        f"drink mut callback = {initial}\ncallback = {replacement}\ncallback(3)"
    )
    _, errors = inspect_source(source)
    assert bool(errors) is expected_errors
    if expected_errors:
        assert any(error.code == "E021" for error in errors)
    else:
        assert run(source) == 2


@pytest.mark.parametrize(
    "initial,replacement,expected_errors",
    [
        ("returns_float", "returns_int", False),
        ("returns_int", "returns_float", True),
    ],
)
def test_inferred_callback_assignment_respects_return_contract(
    initial, replacement, expected_errors
):
    source = (
        "glass returns_int(value: Int) -> Int { return 1 }\n"
        "glass returns_float(value: Int) -> Float { return 2.5 }\n"
        f"drink mut callback = {initial}\ncallback = {replacement}\ncallback(3)"
    )
    _, errors = inspect_source(source)
    assert bool(errors) is expected_errors
    if expected_errors:
        assert any(error.code == "E021" for error in errors)
    else:
        assert run(source) == 1


SELECTIONS = [
    pytest.param("[{first}, {second}][0]", id="array"),
    pytest.param('{{"first": {first}, "second": {second}}}["first"]', id="dictionary"),
    pytest.param("{first} or {second}", id="or"),
    pytest.param("{first} and {second}", id="and"),
]
DEFINITIONS = (
    "glass takes_int(value: Int) -> Int { return 1 }\n"
    "glass takes_float(value: Float) -> Float { return 2.5 }\n"
)


@pytest.mark.parametrize("selection", SELECTIONS)
@pytest.mark.parametrize("reverse", [False, True])
def test_source_callable_selection_never_widens_accepted_argument(selection, reverse):
    names = ("takes_float", "takes_int") if reverse else ("takes_int", "takes_float")
    expression = selection.format(first=names[0], second=names[1])
    source = DEFINITIONS + f"drink selected = {expression}\nselected(1.5)"
    checker, errors = inspect_source(source)
    assert any(error.code == "E021" for error in errors)
    selected_type = checker.scope.lookup("selected")["type"]
    assert isinstance(selected_type, FunctionUnionType)
    assert len(selected_type.alternatives) == 2
    assert is_assignable(selected_type, FunctionType([IntType()], FloatType()))
    assert not is_assignable(selected_type, FunctionType([FloatType()], FloatType()))


@pytest.mark.parametrize("selection", SELECTIONS)
@pytest.mark.parametrize("reverse", [False, True])
def test_source_callable_selection_accepts_common_domain_with_covariant_result(
    selection, reverse
):
    names = ("takes_float", "takes_int") if reverse else ("takes_int", "takes_float")
    expression = selection.format(first=names[0], second=names[1])
    source = (
        DEFINITIONS
        + f"drink selected = {expression}\ndrink result: Float = selected(1)\nresult"
    )
    _, errors = inspect_source(source)
    assert errors == []
    assert run(source) in (1, 2.5)


@pytest.mark.parametrize("selection", SELECTIONS)
def test_return_statement_uses_common_callable_result_type(selection):
    expression = selection.format(first="takes_int", second="takes_float")
    source = DEFINITIONS + (
        "glass report() -> Int {\n"
        f"drink selected = {expression}\nreturn selected(1)\n}}"
    )
    _, errors = inspect_source(source)
    assert any(error.code == "E023" for error in errors)


@pytest.mark.parametrize(
    "source_name,accepted", [("takes_float", True), ("takes_int", False)]
)
def test_higher_order_source_call_uses_explicit_host_signature(source_name, accepted):
    # Callable annotation syntax is not yet a source-language feature. A host
    # supplied static signature still must enforce the same substitution rules.
    checker = Checker()
    checker.scope.declare(
        "consume",
        {
            "type": FunctionType([FunctionType([FloatType()], IntType())], IntType()),
            "is_mut": False,
            "kind": "function",
        },
    )
    source = (
        "glass takes_int(value: Int) -> Int { return 1 }\n"
        "glass takes_float(value: Float) -> Int { return 2 }\n"
        f"consume({source_name})"
    )
    errors = checker.check_all(parse(source))
    assert bool(errors) is not accepted
    if not accepted:
        assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize("reverse", [False, True])
def test_callable_join_flattens_and_deduplicates_exact_signatures(reverse):
    first = FunctionType([IntType()], IntType())
    second = FunctionType([FloatType()], FloatType())
    third = FunctionType([], StringType())
    left = unify(first, second)
    right = unify(second, third)
    combined = unify(*(reversed((left, right)) if reverse else (left, right)))
    assert isinstance(combined, FunctionUnionType)
    assert len(combined.alternatives) == 3
    assert combined == unify(first, unify(second, third))
    assert type_to_string(combined) == type_to_string(unify(right, left))
    assert all(is_assignable(item, combined) for item in (first, second, third))
    assert not is_assignable(combined, first)
    assert not is_assignable(combined, second)
    assert not is_assignable(combined, third)


def test_identical_callable_join_preserves_single_signature():
    first = FunctionType([ReservoirType(IntType())], FloatType())
    same = FunctionType([ReservoirType(IntType())], FloatType())
    joined = unify(first, same)
    assert isinstance(joined, FunctionType)
    assert type_to_string(joined) == "(Reservoir[Int]) -> Float"


@pytest.mark.parametrize("location", ["parameter", "return"])
def test_gradual_any_inside_signature_does_not_erase_known_alternative(location):
    if location == "parameter":
        known = FunctionType([IntType()], IntType())
        gradual = FunctionType([AnyType()], IntType())
    else:
        known = FunctionType([IntType()], IntType())
        gradual = FunctionType([IntType()], AnyType())
    joined = unify(known, gradual)
    assert isinstance(joined, FunctionUnionType)
    assert len(joined.alternatives) == 2
    assert is_assignable(known, gradual) and is_assignable(gradual, known)
    assert isinstance(unify(joined, AnyType()), AnyType)
    assert isinstance(unify(AnyType(), joined), AnyType)


@pytest.mark.parametrize("nominal_kind", [EnumType, StructType])
@pytest.mark.parametrize("location", ["parameter", "return", "nested_callback"])
def test_callable_join_never_deduplicates_distinct_nominal_declarations(
    nominal_kind, location
):
    first_nominal = nominal_kind("Record", declaration_id=object())
    second_nominal = nominal_kind("Record", declaration_id=object())

    def signature(nominal):
        domain = DictType(StringType(), ReservoirType(nominal))
        if location == "parameter":
            return FunctionType([domain], IntType())
        if location == "return":
            return FunctionType([], domain)
        return FunctionType([FunctionType([domain], IntType())], IntType())

    first, second = signature(first_nominal), signature(second_nominal)
    # Descriptor dataclass equality is deliberately insufficient for identity.
    assert first == second
    joined = unify(first, second)
    assert isinstance(joined, FunctionUnionType)
    assert len(joined.alternatives) == 2
    assert not is_assignable(joined, first)
    assert not is_assignable(joined, second)
    assert unify(joined, first) == joined


def test_callable_union_assignment_checks_every_source_alternative():
    number = FunctionType([IntType()], IntType())
    text = FunctionType([StringType()], StringType())
    empty = FunctionType([], IntType())
    source = unify(number, text)
    containing = unify(source, empty)
    partial = unify(number, empty)
    assert is_assignable(source, containing)
    assert not is_assignable(containing, source)
    assert not is_assignable(source, partial)
    assert is_assignable(number, source)
    assert not is_assignable(empty, source)


@pytest.mark.parametrize("selection", SELECTIONS)
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("arguments", ["", "1", "1, 2"])
def test_source_mixed_arity_choice_requires_every_possible_arity(
    selection, reverse, arguments
):
    names = ("one", "zero") if reverse else ("zero", "one")
    expression = selection.format(first=names[0], second=names[1])
    source = (
        "glass zero() -> Int { return 0 }\n"
        "glass one(value: Int) -> Int { return value }\n"
        f"drink selected = {expression}\nselected({arguments})"
    )
    checker, errors = inspect_source(source)
    selected_type = checker.scope.lookup("selected")["type"]
    assert isinstance(selected_type, FunctionUnionType)
    assert {len(item.param_types) for item in selected_type.alternatives} == {0, 1}
    assert any(error.code == "E030" for error in errors)


@pytest.mark.parametrize("selection", SELECTIONS)
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("argument", ["1", '"text"'])
def test_source_disjoint_callable_choice_is_not_overload_dispatch(
    selection, reverse, argument
):
    names = ("text", "number") if reverse else ("number", "text")
    expression = selection.format(first=names[0], second=names[1])
    source = (
        "glass number(value: Int) -> Int { return 1 }\n"
        "glass text(value: String) -> Int { return 2 }\n"
        f"drink selected = {expression}\nselected({argument})"
    )
    checker, errors = inspect_source(source)
    assert isinstance(checker.scope.lookup("selected")["type"], FunctionUnionType)
    assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize(
    "container,index",
    [("[{initial}]", "0"), ('{{"callback": {initial}}}', '"callback"')],
)
@pytest.mark.parametrize(
    "initial,replacement,accepted",
    [("takes_float", "takes_int", False), ("takes_int", "takes_float", True)],
)
def test_source_collection_callback_assignment_preserves_input_contract(
    container, index, initial, replacement, accepted
):
    source = (
        "glass takes_int(value: Int) -> Int { return 1 }\n"
        "glass takes_float(value: Float) -> Int { return 2 }\n"
        f"drink callbacks = {container.format(initial=initial)}\n"
        f"callbacks[{index}] = {replacement}\ncallbacks[{index}](1)"
    )
    _, errors = inspect_source(source)
    assert bool(errors) is not accepted
    if accepted:
        assert run(source) == 2
    else:
        assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize(
    "declaration,nominal,value",
    [
        ("enum State { Ready }", "State", "State.Ready"),
        ("struct Row { value: Int }", "Row", "new Row(1)"),
    ],
)
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("valid", [False, True])
def test_source_callable_choice_preserves_nested_nominal_input(
    declaration, nominal, value, reverse, valid
):
    annotation = f"Dict[String, Reservoir[{nominal}]]"
    names = ("second", "first") if reverse else ("first", "second")
    argument = '{"rows": [' + (value if valid else "1") + "]}"
    source = (
        f"{declaration}\n"
        f"glass first(value: {annotation}) -> Int {{ return 1 }}\n"
        f"glass second(value: {annotation}) -> Float {{ return 2.5 }}\n"
        f"drink selected = [{names[0]}, {names[1]}][0]\n"
        f"drink result: Float = selected({argument})\nresult"
    )
    _, errors = inspect_source(source)
    assert bool(errors) is not valid
    if valid:
        assert run(source) == (2.5 if reverse else 1)
    else:
        assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize(
    "declaration,nominal,value",
    [
        ("enum State { Ready }", "State", "State.Ready"),
        ("struct Row { value: Int }", "Row", "new Row(1)"),
    ],
)
@pytest.mark.parametrize("reverse", [False, True])
def test_source_callable_choice_keeps_same_named_nominals_from_distinct_scopes(
    declaration, nominal, value, reverse
):
    names = ("inner", "outer") if reverse else ("outer", "inner")
    source = (
        f"{declaration}\n"
        f"glass outer(value: Reservoir[{nominal}]) -> Int {{ return 1 }}\n"
        "glass caller() -> Int {\n"
        f"{declaration}\n"
        f"glass inner(value: Reservoir[{nominal}]) -> Int {{ return 2 }}\n"
        f"drink selected = [{names[0]}, {names[1]}][0]\n"
        f"return selected([{value}])\n}}"
    )
    _, errors = inspect_source(source)
    assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize(
    "callback_input,accepted", [(FloatType, True), (IntType, False)]
)
@pytest.mark.parametrize("reverse", [False, True])
def test_higher_order_choice_checks_callback_against_every_alternative(
    callback_input, accepted, reverse
):
    signatures = (
        FunctionType([FunctionType([IntType()], IntType())], IntType()),
        FunctionType([FunctionType([FloatType()], IntType())], FloatType()),
    )
    selected_type = unify(*(reversed(signatures) if reverse else signatures))
    checker = Checker()
    for name, signature in (
        ("selected", selected_type),
        ("argument", FunctionType([callback_input()], IntType())),
    ):
        checker.scope.declare(
            name, {"type": signature, "is_mut": False, "kind": "function"}
        )
    errors = checker.check_all(parse("drink result: Float = selected(argument)"))
    assert bool(errors) is not accepted
    assert isinstance(checker.scope.lookup("result")["type"], FloatType)
    if not accepted:
        assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize("argument,accepted", [("1", True), ("1.5", False)])
@pytest.mark.parametrize("reverse", [False, True])
def test_choice_returning_callable_retains_known_inner_input_contract(
    argument, accepted, reverse
):
    signatures = (
        FunctionType([], FunctionType([IntType()], IntType())),
        FunctionType([], FunctionType([FloatType()], FloatType())),
    )
    checker = Checker()
    checker.scope.declare(
        "factory",
        {
            "type": unify(*(reversed(signatures) if reverse else signatures)),
            "is_mut": False,
            "kind": "function",
        },
    )
    errors = checker.check_all(
        parse(f"drink selected = factory()\ndrink result: Float = selected({argument})")
    )
    assert isinstance(checker.scope.lookup("selected")["type"], FunctionUnionType)
    assert bool(errors) is not accepted
    if not accepted:
        assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize("operator", ["|", "->"])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("argument,accepted", [("1", True), ("1.5", False)])
def test_source_pipeline_callable_choice_requires_every_input_contract(
    operator, reverse, argument, accepted
):
    names = ("takes_float", "takes_int") if reverse else ("takes_int", "takes_float")
    source = (
        DEFINITIONS + f"drink selected = [{names[0]}, {names[1]}][0]\n"
        f"drink result: Float = {argument} {operator} selected\nresult"
    )
    _, errors = inspect_source(source)
    assert bool(errors) is not accepted
    if accepted:
        assert run(source) == (2.5 if reverse else 1)
    else:
        assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize("operator", ["|", "->"])
@pytest.mark.parametrize("reverse", [False, True])
def test_source_pipeline_callable_choice_joins_every_return_contract(operator, reverse):
    names = ("takes_float", "takes_int") if reverse else ("takes_int", "takes_float")
    source = (
        DEFINITIONS + f"drink selected = [{names[0]}, {names[1]}][0]\n"
        f"drink result: Int = 1 {operator} selected"
    )
    _, errors = inspect_source(source)
    assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize("operator", ["|", "->"])
@pytest.mark.parametrize("reverse", [False, True])
def test_source_pipeline_callable_choice_checks_every_arity(operator, reverse):
    names = ("one", "zero") if reverse else ("zero", "one")
    source = (
        "glass zero() -> Int { return 0 }\n"
        "glass one(value: Int) -> Int { return value }\n"
        f"drink selected = [{names[0]}, {names[1]}][0]\n"
        f"1 {operator} selected"
    )
    _, errors = inspect_source(source)
    assert any(error.code == "E030" for error in errors)


@pytest.mark.parametrize("operator", ["|", "->"])
@pytest.mark.parametrize("argument,accepted", [("1", True), ("1.5", False)])
def test_source_pipeline_known_single_callable_checks_input(
    operator, argument, accepted
):
    source = (
        "glass take(value: Int) -> Int { return 7 }\n"
        f"drink result: Int = {argument} {operator} take\nresult"
    )
    _, errors = inspect_source(source)
    assert bool(errors) is not accepted
    if accepted:
        assert run(source) == 7
    else:
        assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize("operator", ["|", "->"])
def test_pipeline_direct_struct_constructor_retains_result_type(operator):
    source = (
        "struct Box { value: Int }\n"
        f"drink result: Box = 1 {operator} Box\nresult.value"
    )
    _, errors = inspect_source(source)
    assert errors == []
    assert run(source) == 1
    _, errors = inspect_source(source.replace("result: Box", "result: Int"))
    assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize("operator", ["|", "->"])
@pytest.mark.parametrize("fields", ["", "first: Int\nsecond: Int"])
def test_pipeline_direct_struct_constructor_checks_arity(operator, fields):
    _, errors = inspect_source(f"struct Box {{ {fields} }}\n1 {operator} Box")
    assert any(error.code == "E030" for error in errors)


@pytest.mark.parametrize("operator", ["|", "->"])
@pytest.mark.parametrize("valid", [False, True])
def test_pipeline_direct_struct_constructor_keeps_nominal_field_contract(
    operator, valid
):
    argument = "State.Ready" if valid else "Other.Ready"
    source = (
        "enum State { Ready }\nenum Other { Ready }\n"
        "struct Box { state: State }\n"
        f"drink box = {argument} {operator} Box\nbox.state == State.Ready"
    )
    _, errors = inspect_source(source)
    assert bool(errors) is not valid
    if valid:
        assert run(source) is True
    else:
        assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize("operator", ["|", "->"])
@pytest.mark.parametrize("argument", ['"Ready"', "State.Ready"])
def test_pipeline_direct_enum_constructor_retains_result_type(operator, argument):
    source = (
        "enum State { Ready }\n"
        f"drink result: State = {argument} {operator} State\nresult == State.Ready"
    )
    _, errors = inspect_source(source)
    assert errors == []
    assert run(source) is True
    _, errors = inspect_source(source.replace("result: State", "result: Int"))
    assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize("operator", ["|", "->"])
@pytest.mark.parametrize("nominal", ["struct", "enum"])
def test_pipeline_nominal_instance_keeps_noncallable_fallback(operator, nominal):
    if nominal == "struct":
        declaration, instance, result_type, selection = (
            "struct Box { value: Int }",
            "new Box(2)",
            "Box",
            "result.value",
        )
    else:
        declaration, instance, result_type, selection = (
            "enum State { Ready }",
            "State.Ready",
            "State",
            "result == State.Ready",
        )
    if operator == "|":
        result_type, selection = "Int", "result"
    source = (
        f"{declaration}\n"
        f"drink result: {result_type} = 9 {operator} {instance}\n{selection}"
    )
    _, errors = inspect_source(source)
    assert errors == []
    expected = 9 if operator == "|" else 2 if nominal == "struct" else True
    assert run(source) == expected


@pytest.mark.parametrize("operator", ["|", "->"])
@pytest.mark.parametrize("operand", ["Box", "new Box(2)"])
def test_pipeline_nominal_alias_retains_value_identity(operator, operand):
    source = (
        "struct Box { value: Int }\n"
        f"drink operand = {operand}\ndrink result = 1 {operator} operand\nresult"
    )
    checker, errors = inspect_source(source)
    assert errors == []
    expected_type = IntType if operator == "|" and operand != "Box" else StructType
    assert isinstance(checker.scope.lookup("result")["type"], expected_type)
    result = run(source)
    if operator == "|" and operand != "Box":
        assert result == 1
    else:
        assert result.fields["value"] == (1 if operand == "Box" else 2)


@pytest.mark.parametrize("operator", ["|", "->"])
@pytest.mark.parametrize("alias", [False, True])
def test_pipeline_awaited_cascade_result_remains_dynamic(operator, alias):
    prefix = "glass factory() { return glass(value) { return value + 1 } }\n"
    if alias:
        prefix += "drink callback = cascade factory()\n"
        operand = "callback"
    else:
        operand = "(cascade factory())"
    source = prefix + f"drink result = 4 {operator} {operand}\nresult"
    checker, errors = inspect_source(source)
    assert errors == []
    assert isinstance(checker.scope.lookup("result")["type"], AnyType)
    assert run(source) == 5
