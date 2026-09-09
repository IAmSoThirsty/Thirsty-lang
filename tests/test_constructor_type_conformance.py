"""Constructor values retain callability without becoming nominal instances."""

import pytest

from utf.thirsty_lang.checker import Checker, check_ast
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
    FunctionUnionType,
    IntType,
    ReservoirType,
    StringType,
    StructType,
    is_assignable,
    unify,
)


def parse(source):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors, lexer.errors
    assert not parser.errors, parser.errors
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


NOMINALS = [
    pytest.param("struct Row { value: Int }", "Row", "new Row(7)", id="struct"),
    pytest.param("enum State { Ready }", "State", "State.Ready", id="enum"),
]
SELECTIONS = [
    pytest.param("[{first}, {second}][0]", id="array"),
    pytest.param('{{"a": {first}, "b": {second}}}["a"]', id="dictionary"),
    pytest.param("{first} or {second}", id="or"),
    pytest.param("{first} and {second}", id="and"),
]


@pytest.mark.parametrize("declaration,name,instance", NOMINALS)
def test_declaration_expression_and_instance_annotation_have_distinct_types(
    declaration, name, instance
):
    checker, errors = inspect_source(
        f"{declaration}\ndrink build = {name}\ndrink value: {name} = {instance}"
    )
    assert errors == []
    constructor = checker.scope.lookup("build")["type"]
    value_type = checker.scope.lookup("value")["type"]
    assert isinstance(constructor, ConstructorType)
    assert constructor.instance_type is value_type
    assert not is_assignable(constructor, value_type)
    assert not is_assignable(value_type, constructor)


@pytest.mark.parametrize("declaration,name,instance", NOMINALS)
@pytest.mark.parametrize(
    "site",
    ["declaration", "assignment", "argument", "return", "array", "dictionary", "field"],
)
def test_constructor_cannot_satisfy_an_instance_annotation(
    declaration, name, instance, site
):
    source = {
        "declaration": f"drink value: {name} = {name}",
        "assignment": f"drink mut value: {name} = {instance}\nvalue = {name}",
        "argument": f"glass take(value: {name}) {{ return 1 }}\ntake({name})",
        "return": f"glass make() -> {name} {{ return {name} }}",
        "array": f"drink values: Reservoir[{name}] = [{name}]",
        "dictionary": f'drink values: Dict[String, {name}] = {{"value": {name}}}',
        "field": f"struct Holder {{ value: {name} }}\nnew Holder({name})",
    }[site]
    errors = check_ast(parse(declaration + "\n" + source))
    assert any(
        error.code == ("E023" if site == "return" else "E021") for error in errors
    )


@pytest.mark.parametrize("declaration,name,instance", NOMINALS)
@pytest.mark.parametrize("route", ["call", "new"])
def test_known_nominal_instances_are_not_callable(declaration, name, instance, route):
    expression = "value()" if route == "call" else "new value()"
    source = f"{declaration}\ndrink value = {instance}\n{expression}"
    errors = check_ast(parse(source))
    assert any(error.code == "E031" for error in errors)
    with pytest.raises(TypeError, match="non-callable"):
        run(source)


@pytest.mark.parametrize("declaration,name,instance", NOMINALS)
def test_instance_cannot_replace_an_inferred_constructor_binding(
    declaration, name, instance
):
    errors = check_ast(
        parse(f"{declaration}\ndrink mut build = {name}\nbuild = {instance}")
    )
    assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize("declaration,name,instance", NOMINALS)
@pytest.mark.parametrize("generic", [False, True])
def test_instance_value_name_cannot_define_a_nominal_annotation(
    declaration, name, instance, generic
):
    annotation = "Reservoir[value]" if generic else "value"
    initializer = f"[{instance}]" if generic else instance
    source = f"{declaration}\ndrink value = {instance}\ndrink other: {annotation} = {initializer}"
    assert check_ast(parse(source))


@pytest.mark.parametrize("declaration,name,instance", NOMINALS)
@pytest.mark.parametrize("selection", SELECTIONS)
def test_collection_selection_does_not_turn_nominal_instances_into_constructors(
    declaration, name, instance, selection
):
    expression = selection.format(first="value", second="alias")
    source = f"{declaration}\ndrink value = {instance}\ndrink alias = value\ndrink selected = {expression}\nselected()"
    errors = check_ast(parse(source))
    assert any(error.code == "E031" for error in errors)
    with pytest.raises(TypeError, match="non-callable"):
        run(source)


@pytest.mark.parametrize("route", ["call", "new"])
def test_struct_alias_is_callable_and_valid_as_a_nominal_annotation(route):
    invocation = "build(7)" if route == "call" else "new build(7)"
    source = (
        "struct Row { value: Int }\ndrink build = Row\n"
        f"drink row: build = {invocation}\ndrink answer: Int = row.value\nanswer"
    )
    assert check_ast(parse(source)) == []
    assert run(source) == 7


@pytest.mark.parametrize("route", ["member", "string_call", "instance_call", "new"])
def test_enum_alias_preserves_variants_constructor_and_instance_identity(route):
    expression = {
        "member": "build.Ready",
        "string_call": 'build("Ready")',
        "instance_call": "build(State.Ready)",
        "new": 'new build("Ready")',
    }[route]
    source = (
        "enum State { Ready }\ndrink build = State\n"
        f"drink result: build = {expression}\nresult == State.Ready"
    )
    assert check_ast(parse(source)) == []
    assert run(source) is True


@pytest.mark.parametrize("expression", ["Row.value", "State.Ready.Ready"])
def test_members_distinguish_struct_constructor_and_enum_instance(expression):
    source = "struct Row { value: Int }\nenum State { Ready }\n" + expression
    errors = check_ast(parse(source))
    assert errors
    with pytest.raises(TypeError, match="Cannot access member"):
        run(source)


@pytest.mark.parametrize("operator", ["|", "|>", "->"])
@pytest.mark.parametrize("declaration,name,instance", NOMINALS)
def test_noncallable_nominal_pipe_fallback_preserves_actual_result(
    operator, declaration, name, instance
):
    annotation = name if operator == "->" else "Int"
    final = "result == value" if operator == "->" else "result"
    expected = True if operator == "->" else 3
    source = (
        f"{declaration}\ndrink value = {instance}\n"
        f"drink result: {annotation} = 3 {operator} value\n{final}"
    )
    assert check_ast(parse(source)) == []
    assert run(source) == expected
    wrong = "Int" if operator == "->" else name
    errors = check_ast(
        parse(source.replace(f"result: {annotation}", f"result: {wrong}"))
    )
    assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize("operator", ["|", "|>", "->"])
@pytest.mark.parametrize("alias", [False, True])
def test_struct_constructor_pipes_preserve_result_and_field_argument_types(
    operator, alias
):
    target = "build" if alias else "Row"
    source = (
        "struct Row { value: Int }\ndrink build = Row\n"
        f"drink row: Row = 7 {operator} {target}\nrow.value"
    )
    assert check_ast(parse(source)) == []
    assert run(source) == 7
    errors = check_ast(parse(source.replace("= 7 " + operator, '= "bad" ' + operator)))
    assert any(error.code == "E021" for error in errors)
    errors = check_ast(parse(source.replace("row: Row", "row: Int")))
    assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize("operator", ["|", "|>", "->"])
def test_enum_constructor_alias_pipe_preserves_instance_result(operator):
    source = (
        "enum State { Ready }\ndrink build = State\n"
        f'drink value: State = "Ready" {operator} build\nvalue == State.Ready'
    )
    assert check_ast(parse(source)) == []
    assert run(source) is True
    errors = check_ast(parse(source.replace("value: State", "value: String")))
    assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize("route", ["direct", "alias", "new", "pipe", "pipeline"])
@pytest.mark.parametrize("field_count", [0, 2])
def test_constructor_arity_is_checked_for_every_call_route(route, field_count):
    fields = "" if field_count == 0 else "first: Int\nsecond: Int"
    expression = {
        "direct": "Row(7)",
        "alias": "build(7)",
        "new": "new build(7)",
        "pipe": "7 | build",
        "pipeline": "7 -> build",
    }[route]
    source = f"struct Row {{ {fields} }}\ndrink build = Row\n{expression}"
    errors = check_ast(parse(source))
    assert any(error.code == "E030" for error in errors)
    with pytest.raises(TypeError, match=f"expects {field_count} fields, got 1"):
        run(source)


@pytest.mark.parametrize(
    "expression", ["State()", 'State("Ready", "Ready")', "new State()"]
)
def test_enum_constructor_arity_is_known_even_when_value_domain_is_gradual(expression):
    errors = check_ast(parse("enum State { Ready }\n" + expression))
    assert any(error.code == "E030" for error in errors)


@pytest.mark.parametrize("selection", SELECTIONS)
@pytest.mark.parametrize("reverse", [False, True])
def test_constructor_function_choice_keeps_argument_and_result_contracts(
    selection, reverse
):
    names = ("make", "Row") if reverse else ("Row", "make")
    selected = selection.format(first=names[0], second=names[1])
    source = (
        "struct Row { value: Int }\n"
        "glass make(value: Float) -> Row { return new Row(8) }\n"
        f"drink selected = {selected}\ndrink row: Row = selected(7)\nrow.value"
    )
    checker, errors = inspect_source(source)
    assert errors == []
    choice = checker.scope.lookup("selected")["type"]
    assert isinstance(choice, FunctionUnionType)
    assert any(isinstance(item, ConstructorType) for item in choice.alternatives)
    assert any(isinstance(item, FunctionType) for item in choice.alternatives)
    assert run(source) in (7, 8)
    errors = check_ast(parse(source.replace("selected(7)", "selected(7.5)")))
    assert any(error.code == "E021" for error in errors)
    errors = check_ast(parse(source.replace("row: Row", "row: String")))
    assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize("selection", SELECTIONS)
def test_repeated_constructor_choice_preserves_enum_member_access(selection):
    selected = selection.format(first="State", second="alias")
    source = (
        "enum State { Ready }\ndrink alias = State\n"
        f"drink selected = {selected}\ndrink value: State = selected.Ready\n"
        'selected("Ready") == value'
    )
    checker, errors = inspect_source(source)
    assert errors == []
    assert isinstance(checker.scope.lookup("selected")["type"], ConstructorType)
    assert run(source) is True


@pytest.mark.parametrize("reverse", [False, True])
def test_enum_constructor_function_choice_does_not_guarantee_enum_members(reverse):
    names = ("make", "State") if reverse else ("State", "make")
    source = (
        "enum State { Ready }\n"
        "glass make(value: String) -> State { return State.Ready }\n"
        f"drink selected = [{names[0]}, {names[1]}][0]\nselected.Ready"
    )
    assert check_ast(parse(source))


@pytest.mark.parametrize("reverse", [False, True])
def test_constructor_choice_arity_does_not_decay_to_any(reverse):
    names = ("Pair", "Single") if reverse else ("Single", "Pair")
    source = (
        "struct Single { value: Int }\nstruct Pair { left: Int\nright: Int }\n"
        f"drink selected = [{names[0]}, {names[1]}][0]\nselected(1)"
    )
    checker, errors = inspect_source(source)
    assert isinstance(checker.scope.lookup("selected")["type"], FunctionUnionType)
    assert any(error.code == "E030" for error in errors)


@pytest.mark.parametrize(
    "initial,replacement,accepted", [("Row", "make", False), ("make", "Row", True)]
)
def test_constructor_identity_and_ordinary_function_substitution_are_directional(
    initial, replacement, accepted
):
    source = (
        "struct Row { value: Int }\n"
        "glass make(value: Int) -> Row { return new Row(value) }\n"
        f"drink mut build = {initial}\nbuild = {replacement}\nbuild(7).value"
    )
    errors = check_ast(parse(source))
    assert bool(errors) is not accepted
    if accepted:
        assert run(source) == 7
    else:
        assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize("declaration,name,instance", NOMINALS)
def test_constructor_alias_annotation_retains_original_nominal_across_shadowing(
    declaration, name, instance
):
    source = (
        f"{declaration}\ndrink Original = {name}\n"
        f"glass take(values: Reservoir[Original]) {{ return 1 }}\n"
        f"glass caller() {{ {declaration}\nreturn take([{instance}]) }}"
    )
    errors = check_ast(parse(source))
    assert any(error.code == "E021" for error in errors)


def test_constructor_alias_keeps_nested_record_field_types():
    source = (
        "enum State { Ready }\ndrink Status = State\n"
        "struct Row { state: Status\nvalues: Reservoir[Int] }\ndrink Record = Row\n"
        "struct Holder { rows: Dict[String, Reservoir[Record]] }\n"
        'drink holder = new Holder({"rows": [new Record(Status.Ready, [7])]})\n'
        'drink result: Int = holder.rows["rows"][0].values[0]\nresult'
    )
    assert check_ast(parse(source)) == []
    assert run(source) == 7
    errors = check_ast(parse(source.replace("[7]", '["wrong"]')))
    assert any(error.code == "E021" for error in errors)


@pytest.mark.parametrize("route", ["ordinary_call", "new"])
def test_new_preserves_existing_runtime_support_for_ordinary_function_aliases(route):
    invocation = "alias(7)" if route == "ordinary_call" else "new alias(7)"
    source = f"glass increment(value: Int) -> Int {{ return value + 1 }}\ndrink alias = increment\ndrink result: Int = {invocation}\nresult"
    assert check_ast(parse(source)) == []
    assert run(source) == 8
    errors = check_ast(parse(source.replace("alias(7)", 'alias("wrong")')))
    assert any(error.code == "E021" for error in errors)


def test_explicit_any_binding_remains_gradual_but_runtime_callability_is_checked():
    source = "struct Row { value: Int }\ndrink dynamic: Any = new Row(1)\ndynamic()"
    assert check_ast(parse(source)) == []
    with pytest.raises(TypeError, match="non-callable"):
        run(source)
    source = 'enum State { Ready }\ndrink dynamic: Any = State\ndynamic("Ready") == State.Ready'
    assert check_ast(parse(source)) == []
    assert run(source) is True


def test_enum_constructor_value_domain_remains_gradual_and_runtime_validated():
    source = 'enum State { Ready }\nState("Missing")'
    assert check_ast(parse(source)) == []
    with pytest.raises(ValueError, match="not a valid State"):
        run(source)


def test_constructor_signature_tracks_completed_recursive_nominal_descriptor():
    nominal = StructType("Node", declaration_id=object())
    constructor = ConstructorType(nominal)
    nominal.field_types.update({"value": IntType(), "children": ReservoirType(nominal)})
    assert constructor.instance_type is nominal
    signature = constructor.signature
    assert isinstance(signature, FunctionType)
    assert signature.return_type is nominal
    assert signature.param_types[1].inner_type is nominal
    assert not is_assignable(constructor, nominal)
    assert not is_assignable(nominal, constructor)
    assert is_assignable(constructor, signature)
    assert not is_assignable(signature, constructor)


def test_constructor_join_does_not_erase_identity_into_equivalent_function():
    nominal = StructType("Row", {"value": IntType()}, declaration_id=object())
    constructor = ConstructorType(nominal)
    ordinary = FunctionType([IntType()], nominal)
    joined = unify(constructor, ordinary)
    assert isinstance(joined, FunctionUnionType)
    assert len(joined.alternatives) == 2
    assert is_assignable(joined, ordinary)
    assert not is_assignable(joined, constructor)
    assert isinstance(unify(constructor, ConstructorType(nominal)), ConstructorType)
    assert isinstance(unify(constructor, AnyType()), AnyType)


@pytest.mark.parametrize("nominal_kind", [EnumType, StructType])
def test_same_named_constructor_choices_retain_declaration_identity(nominal_kind):
    first = ConstructorType(nominal_kind("Item", declaration_id=object()))
    second = ConstructorType(nominal_kind("Item", declaration_id=object()))
    joined = unify(first, second)
    assert isinstance(joined, FunctionUnionType)
    assert len(joined.alternatives) == 2
    assert not is_assignable(first, second)
    assert not is_assignable(second, first)
    assert not is_assignable(joined, first)


@pytest.mark.parametrize("accepts_float", [False, True])
def test_higher_order_source_call_respects_constructor_signature(accepts_float):
    program = parse("struct Row { value: Int }\nconsume(Row)")
    # Callable annotation syntax is not a language feature. Supply the host
    # signature while keeping the constructor argument and call source-level.
    checker = Checker()
    nominal = StructType("Result", declaration_id=object())
    checker.scope.declare(
        "consume",
        {
            "type": FunctionType(
                [
                    FunctionType(
                        [FloatType() if accepts_float else IntType()], AnyType()
                    )
                ],
                nominal,
            ),
            "is_mut": False,
            "kind": "function",
        },
    )
    errors = checker.check_all(program)
    assert bool(errors) is accepts_float
    if accepts_float:
        assert any(error.code == "E021" for error in errors)


def test_joined_factories_returning_constructors_preserve_nested_call_contract():
    row = StructType("Row", {"value": IntType()}, declaration_id=object())
    constructor = ConstructorType(row)
    ordinary = FunctionType([FloatType()], row)
    factory = unify(FunctionType([], constructor), FunctionType([], ordinary))
    checker = Checker()
    checker.scope.declare(
        "factory", {"type": factory, "is_mut": False, "kind": "function"}
    )
    errors = checker.check_all(parse("drink selected = factory()\nselected(1.5)"))
    choice = checker.scope.lookup("selected")["type"]
    assert isinstance(choice, FunctionUnionType)
    assert any(isinstance(item, ConstructorType) for item in choice.alternatives)
    assert any(error.code == "E021" for error in errors)


def test_nested_collection_constructor_type_is_not_an_instance_container():
    row = StructType("Row", {"value": IntType()}, declaration_id=object())
    constructors = DictType(StringType(), ReservoirType(ConstructorType(row)))
    instances = DictType(StringType(), ReservoirType(row))
    assert not is_assignable(constructors, instances)
    assert not is_assignable(instances, constructors)
