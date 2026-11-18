"""Known value joins retain mutable aliases and every possible operation contract."""

import pytest

from utf.thirsty_lang import typesys
from utf.thirsty_lang.checker import Checker
from utf.thirsty_lang.interpreter import Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser
from utf.thirsty_lang.typesys import (
    AnyType,
    DictType,
    FloatType,
    FunctionType,
    FunctionUnionType,
    IntType,
    ReservoirType,
    StringType,
    StructType,
    VoidType,
    is_assignable,
    unify,
)


def inspect_source(source):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors and not parser.errors, (lexer.errors, parser.errors)
    checker = Checker()
    return checker, program, checker.check_all(program)


def run_checked(source):
    _, program, errors = inspect_source(source)
    assert errors == []
    with Interpreter() as interpreter:
        return interpreter.interpret(program)


def assert_rejected(source, *, codes=("E021", "E023", "E901")):
    _, _, errors = inspect_source(source)
    assert errors, "known incompatible alternative was erased"
    assert any(error.code in codes for error in errors), errors
    assert all(error.code != "E011" for error in errors), errors


_NUMERIC_LISTS = (
    "drink ints: Reservoir[Int] = [1]\n" "drink floats: Reservoir[Float] = [1.5]\n"
)


@pytest.mark.parametrize(
    "selection",
    [
        "ints or floats",
        "floats and ints",
        "[ints, floats][0]",
        '{"first": ints, "second": floats}["first"]',
        "[ints, floats][:][0]",
        "(ints or floats)[:]",
    ],
)
def test_numeric_selected_alias_cannot_widen_an_existing_integer_slot(selection):
    assert_rejected(
        _NUMERIC_LISTS + f"drink alias = {selection}\nalias[0] = 2.5\nints[0]"
    )


@pytest.mark.parametrize("selection", ["ints or floats", "floats and ints"])
def test_selected_numeric_alias_accepts_values_valid_for_every_container(selection):
    assert (
        run_checked(
            _NUMERIC_LISTS + f"drink alias = {selection}\nalias[0] = 2\nints[0]"
        )
        == 2
    )


@pytest.mark.parametrize("route", ["list", "dictionary", "foreach"])
def test_fresh_outer_collection_does_not_copy_or_widen_shared_inner_rows(route):
    if route == "list":
        body = "drink rows = [ints, floats]\nrows[0][0] = 2.5"
    elif route == "dictionary":
        body = 'drink rows = {"ints": ints, "floats": floats}\nrows["ints"][0] = 2.5'
    else:
        body = "refill (row in [ints, floats]) { row[0] = 2.5 }"
    assert_rejected(_NUMERIC_LISTS + body)


@pytest.mark.parametrize("container", ["list", "dictionary"])
def test_fresh_outer_collection_can_replace_its_own_slot_with_an_alternative(container):
    body = (
        "drink rows = [ints, floats]\nrows[0] = floats\nints[0]"
        if container == "list"
        else 'drink rows = {"ints": ints, "floats": floats}\nrows["ints"] = floats\nints[0]'
    )
    assert run_checked(_NUMERIC_LISTS + body) == 1


@pytest.mark.parametrize(
    "selection", ["ints or 0", "[ints, 0][0]", '{"list": ints, "number": 0}["list"]']
)
def test_mixed_mutable_and_scalar_choices_do_not_become_gradual_any(selection):
    assert_rejected(_NUMERIC_LISTS + f"drink alias = {selection}\nalias[0] = 2.5")


def test_unannotated_heterogeneous_scalar_collection_preserves_known_alternatives():
    checker, _, errors = inspect_source(
        'drink mixed = [1, "two"]\ndrink value = mixed[0]'
    )
    assert errors == []
    value_type = checker.scope.lookup("value")["type"]
    assert isinstance(value_type, typesys.ValueChoiceType)
    assert {type(item) for item in value_type.alternatives} == {IntType, StringType}
    assert not is_assignable(value_type, IntType())
    assert run_checked('drink mixed = [1, "two"]\nmixed[0]') == 1


def test_known_heterogeneous_scalar_choice_cannot_claim_a_single_alternative():
    assert_rejected('drink mixed = [1, "two"]\ndrink value: Int = mixed[0]')


def test_shallow_slice_may_widen_copied_scalar_slots():
    assert (
        run_checked(
            "drink ints: Reservoir[Int] = [1]\n"
            "drink copy: Reservoir[Float] = ints[:]\ncopy[0] = 2.5\nints[0]"
        )
        == 1
    )


def test_shallow_slice_must_preserve_shared_nested_slot_contract():
    assert_rejected(
        "drink ints: Reservoir[Int] = [1]\ndrink rows = [ints]\n"
        "drink copy: Reservoir[Reservoir[Float]] = rows[:]\ncopy[0][0] = 2.5"
    )


def test_fresh_nested_literals_can_be_constructed_under_wider_context():
    assert (
        run_checked(
            "drink rows: Reservoir[Reservoir[Float]] = [[1], [2.5]]\n"
            "rows[0][0] = 3.5\nrows[0][0]"
        )
        == 3.5
    )


@pytest.mark.parametrize(
    "invocation", ["(first or second)()", "cascade (first or second)()"]
)
def test_callable_choice_return_types_retain_collection_identity(invocation):
    prefix = (
        _NUMERIC_LISTS + "glass first() -> Reservoir[Int] { return ints }\n"
        "glass second() -> Reservoir[Float] { return floats }\n"
    )
    assert_rejected(prefix + f"drink alias = {invocation}\nalias[0] = 2.5")


@pytest.mark.parametrize("operator", ["|", "->"])
def test_pipe_callable_choice_return_types_retain_collection_identity(operator):
    prefix = (
        _NUMERIC_LISTS + "glass first(value: Int) -> Reservoir[Int] { return ints }\n"
        "glass second(value: Int) -> Reservoir[Float] { return floats }\n"
    )
    assert_rejected(
        prefix + f"drink alias = 1 {operator} (first or second)\nalias[0] = 2.5"
    )


def test_mutable_callable_slots_cannot_be_widened_to_a_callable_choice():
    assert_rejected(
        "glass onlyInt(value: Int) -> Int { return value }\n"
        'glass onlyString(value: String) -> String { return value + "!" }\n'
        "drink ints = [onlyInt]\ndrink strings = [onlyString]\n"
        "drink alias = ints or strings\nalias[0] = onlyString\nints[0](1)"
    )


def test_fresh_callable_collection_can_hold_and_replace_supported_alternatives():
    assert (
        run_checked(
            "glass integer(value: Int) -> Int { return value }\n"
            "glass floating(value: Float) -> Float { return value + 0.5 }\n"
            "drink functions = [integer, floating]\n"
            "functions[0] = floating\nfunctions[0](1)"
        )
        == 1.5
    )


def test_callable_mixed_with_noncallable_is_not_an_unconstrained_dynamic_call():
    assert_rejected(
        "glass identity(value: Int) -> Int { return value }\n"
        "drink values = [identity, 0]\nvalues[0](1)",
        codes=("E031", "E901"),
    )


@pytest.mark.parametrize("selection", ["aa or bb", "[aa, bb][0]"])
def test_different_nominal_list_alternatives_preserve_declaration_obligations(
    selection,
):
    assert_rejected(
        "struct A { value: Int }\nstruct B { value: String }\n"
        "drink aa: Reservoir[A] = [new A(1)]\n"
        'drink bb: Reservoir[B] = [new B("bad")]\n'
        f'drink alias = {selection}\nalias[0] = new B("changed")\naa[0].value'
    )


def test_different_nominal_owners_do_not_erase_shared_field_container_types():
    assert_rejected(
        "struct A { values: Reservoir[Int] }\n"
        "struct B { values: Reservoir[String] }\n"
        'drink aa = new A([1])\ndrink bb = new B(["bad"])\n'
        'drink alias = aa or bb\nalias.values[0] = "changed"\naa.values[0]'
    )


@pytest.mark.parametrize("assignment", [False, True])
def test_nominal_choice_requires_member_on_every_alternative(assignment):
    body = "alias.value = 2" if assignment else "alias.value"
    assert_rejected(
        "struct A { value: Int }\nstruct B { other: Int }\n"
        "drink alias = new A(1) or new B(2)\n" + body,
        codes=("E901",),
    )


def test_nominal_choice_field_assignment_must_satisfy_every_field_type():
    assert_rejected(
        "struct A { value: Int }\nstruct B { value: Float }\n"
        "drink aa = new A(1)\ndrink alias = aa or new B(1.5)\nalias.value = 2.5"
    )


@pytest.mark.parametrize("key", ["1.5", '"wrong"'])
def test_dictionary_choice_keys_are_checked_against_every_alternative(key):
    assert_rejected(
        "drink ints: Dict[Int, Int] = {1: 1}\n"
        "drink floats: Dict[Float, Int] = {1.5: 1}\n"
        f"drink alias = ints or floats\nalias[{key}] = 2"
    )


def test_dictionary_choice_accepts_a_key_valid_for_every_alternative():
    assert (
        run_checked(
            "drink ints: Dict[Int, Int] = {1: 1}\n"
            "drink floats: Dict[Float, Int] = {1.5: 1}\n"
            "drink alias = ints or floats\nalias[1] = 2\nints[1]"
        )
        == 2
    )


@pytest.mark.parametrize("slot", ['["value"]', ".value"])
def test_dictionary_choice_slot_write_must_satisfy_every_value_type(slot):
    assert_rejected(
        'drink ints: Dict[String, Int] = {"value": 1}\n'
        'drink floats: Dict[String, Float] = {"value": 1.5}\n'
        f"drink alias = ints or floats\nalias{slot} = 2.5"
    )


def test_dictionary_member_cannot_erase_nested_alias_obligations():
    assert_rejected(
        "drink ints: Reservoir[Int] = [1]\n"
        'drink rows = {"ints": ints}\nrows.ints[0] = 2.5'
    )


@pytest.mark.parametrize("assignment", [False, True])
def test_dictionary_member_syntax_requires_a_supported_string_key(assignment):
    body = "values.missing = 2" if assignment else "values.missing"
    assert_rejected("drink values: Dict[Int, Int] = {1: 1}\n" + body)


def test_dictionary_member_read_preserves_native_missing_value():
    checker, program, errors = inspect_source(
        'drink values: Dict[String, Int] = {"present": 1}\ndrink result = values.missing'
    )
    assert errors == []
    result_type = checker.scope.lookup("result")["type"]
    assert isinstance(result_type, typesys.ValueChoiceType)
    assert {type(item) for item in result_type.alternatives} == {IntType, VoidType}
    with Interpreter() as interpreter:
        assert interpreter.interpret(program) is None


def test_dictionary_member_write_uses_value_type_without_missing_read_alternative():
    assert (
        run_checked(
            'drink values: Dict[String, Int] = {}\nvalues.present = 2\nvalues["present"]'
        )
        == 2
    )
    assert_rejected("drink values: Dict[String, Int] = {}\nvalues.present = none")


def test_known_mutable_joins_preserve_whole_container_descriptors():
    integers = ReservoirType(IntType())
    floats = ReservoirType(FloatType())
    joined = unify(integers, floats)
    assert isinstance(joined, typesys.ValueChoiceType)
    assert joined.alternatives == (integers, floats)
    assert not is_assignable(joined, floats)
    assert is_assignable(integers, joined)
    assert is_assignable(floats, joined)
    assert not is_assignable(ReservoirType(StringType()), joined)


def test_known_dictionary_joins_preserve_key_and_value_pairing():
    first = DictType(StringType(), IntType())
    second = DictType(IntType(), StringType())
    joined = unify(first, second)
    assert isinstance(joined, typesys.ValueChoiceType)
    assert joined.alternatives == (first, second)
    assert not is_assignable(DictType(StringType(), StringType()), joined)


def test_value_choice_join_flattens_and_deduplicates_exact_alternatives():
    first = ReservoirType(IntType())
    second = ReservoirType(FloatType())
    joined = unify(unify(first, second), unify(second, first))
    assert isinstance(joined, typesys.ValueChoiceType)
    assert len(joined.alternatives) == 2
    assert is_assignable(first, joined)
    assert is_assignable(second, joined)


def test_equal_shaped_nominal_declarations_remain_distinct_choice_alternatives():
    first = StructType("Row", {"value": IntType()}, declaration_id=object())
    second = StructType("Row", {"value": IntType()}, declaration_id=object())
    joined = unify(first, second)
    assert isinstance(joined, typesys.ValueChoiceType)
    assert len(joined.alternatives) == 2
    assert not is_assignable(joined, first)
    assert not is_assignable(joined, second)


def test_existing_callable_choice_and_scalar_widening_contracts_remain():
    joined = unify(
        FunctionType([IntType()], IntType()), FunctionType([FloatType()], FloatType())
    )
    assert isinstance(joined, FunctionUnionType)
    assert isinstance(unify(IntType(), FloatType()), FloatType)
    assert isinstance(unify(StringType(), AnyType()), AnyType)
    assert isinstance(unify(AnyType(), ReservoirType(IntType())), AnyType)
