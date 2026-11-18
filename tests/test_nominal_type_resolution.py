"""Recursive named annotations, generic coherence, and declaration identity."""

import pytest

from utf.thirsty_lang.typesys import (
    AnyType,
    BoolType,
    DictType,
    EnumType,
    ErrorType,
    FloatType,
    GenericType,
    GovernedType,
    InterfaceType,
    IntType,
    QuenchedType,
    ReservoirType,
    ResultType,
    StringType,
    StructType,
    TaskType,
    ValueChoiceType,
    is_assignable,
    type_from_name,
    type_to_string,
    unify,
)


def test_nested_resolution_retains_exact_declared_objects_and_live_fields():
    status = EnumType("Status", ["Ready", "Done"], declaration_id=object())
    record = StructType("Record", {"status": status}, declaration_id=object())
    protocol = InterfaceType("Reportable", declaration_id=object())
    symbols = {"Status": status, "Record": record, "Reportable": protocol}
    actual = type_from_name(
        "Dict[Status, Reservoir[Result[Record, Governed[Reportable]]]]",
        symbols.get,
    )
    assert isinstance(actual, DictType)
    assert actual.key_type is status
    result = actual.value_type.inner_type
    assert isinstance(result, ResultType)
    assert result.ok_type is record
    assert result.err_type.type_args[0] is protocol
    record.field_types["next"] = ReservoirType(record)
    assert result.ok_type.field_types["next"].inner_type is record
    assert type_to_string(actual) == (
        "Dict[Status, Reservoir[Result[Record, Governed[Reportable]]]]"
    )


def test_resolver_receives_leaf_names_in_order_and_can_supply_nested_aliases():
    visits = []
    status = EnumType("Status", ["Ready"])
    aliases = {"int": IntType(), "string": StringType(), "bool": BoolType()}

    def resolve(name):
        visits.append(name)
        return status if name == "Status" else aliases.get(name)

    actual = type_from_name(
        " Dict [ string, Reservoir [ Result [ Status, Dict [ int, bool ] ] ] ] ",
        resolver=resolve,
    )
    assert visits == ["string", "Status", "int", "bool"]
    assert actual.key_type is aliases["string"]
    result = actual.value_type.inner_type
    assert result.ok_type is status
    assert result.err_type.key_type is aliases["int"]
    assert result.err_type.value_type is aliases["bool"]


def test_resolver_shadowing_is_lexical_and_no_global_resolution_cache_exists():
    first = EnumType("Status", ["Ready"], declaration_id=object())
    second = EnumType("Status", ["Ready"], declaration_id=object())
    left = type_from_name("Reservoir[Status]", {"Status": first}.get)
    right = type_from_name("Reservoir[Status]", {"Status": second}.get)
    assert left.inner_type is first and right.inner_type is second
    assert not is_assignable(left, right)
    # Resolver precedence preserves a caller's declared shadowing policy.
    named_int = EnumType("Int", ["Named"])
    assert type_from_name("Int", {"Int": named_int}.get) is named_int
    assert isinstance(type_from_name("Int"), IntType)
    assert isinstance(type_from_name("int"), AnyType)


def test_unknown_names_and_custom_generic_constructors_keep_existing_fallbacks():
    assert isinstance(type_from_name("Missing"), AnyType)
    assert isinstance(type_from_name("Missing", {}.get), AnyType)
    actual = type_from_name("Box[Missing, Int]")
    assert type(actual) is GenericType
    assert actual.base_type == "Box"
    assert isinstance(actual.type_args[0], AnyType)
    assert isinstance(actual.type_args[1], IntType)


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        ("Quenched[]", "Quenched[Any]"),
        ("Reservoir[]", "Reservoir[Any]"),
        ("Task[]", "Task[Any]"),
        ("Governed[]", "Governed[Any]"),
        ("Dict[]", "Dict[Any, Any]"),
        ("Dict[Int]", "Dict[Int, Any]"),
        ("Result[]", "Result[Any, Any]"),
        ("Result[Int]", "Result[Int, Any]"),
        ("Box[]", "Box[]"),
        ("rEsErVoIr[task[Int]]", "Reservoir[Task[Int]]"),
    ],
)
def test_omitted_arguments_and_known_wrapper_case_remain_compatible(
    annotation, expected
):
    assert type_to_string(type_from_name(annotation)) == expected


@pytest.mark.parametrize(
    "annotation",
    [
        "Reservoir[Int",
        "Reservoir[Int]]",
        "Reservoir[Int] suffix",
        "Reservoir[Int][String]",
        "Reservoir[,Int]",
        "Reservoir[Int,]",
        "Dict[String,,Int]",
        "Dict[ , Int]",
        "Dict[String, Reservoir[Int,]]",
        "Dict[String, Reservoir[Int]",
        "Dict[String, Reservoir]Int]",
        "[Int]",
        "[]",
        "Int]",
        "Int, String",
        "Bad,Name[Int]",
        "Box[[]]",
    ],
)
def test_malformed_generic_syntax_fails_instead_of_reinterpreting(annotation):
    with pytest.raises(ValueError):
        type_from_name(annotation)


@pytest.mark.parametrize(
    "annotation",
    [
        "Quenched[Int, String]",
        "Reservoir[Int, String]",
        "Task[Int, String]",
        "Governed[Int, String]",
        "Dict[Int, String, Bool]",
        "Result[Int, String, Bool]",
        "Reservoir[Result[Int, Error, Bool]]",
    ],
)
def test_excess_known_wrapper_arguments_are_never_discarded(annotation):
    with pytest.raises(ValueError, match="type argument"):
        type_from_name(annotation)


def test_resolver_errors_are_not_replaced_with_any():
    def failed(_name):
        raise LookupError("scope failed")

    with pytest.raises(LookupError, match="scope failed"):
        type_from_name("Reservoir[Status]", failed)
    with pytest.raises(TypeError, match="Type or None"):
        type_from_name("Reservoir[Status]", lambda _name: "Status")


def wrappers():
    return [
        QuenchedType,
        ReservoirType,
        TaskType,
        GovernedType,
        lambda inner: ResultType(inner, ErrorType()),
        lambda inner: ResultType(IntType(), inner),
        lambda inner: DictType(StringType(), inner),
        lambda inner: DictType(inner, StringType()),
        lambda inner: GenericType("Box", [inner]),
    ]


def assert_both_choices(joined, first, second):
    assert isinstance(joined, ValueChoiceType)
    assert len(joined.alternatives) == 2
    assert joined.alternatives[0] is first
    assert joined.alternatives[1] is second


@pytest.mark.parametrize("wrapper", wrappers())
def test_every_generic_argument_checks_assignability_and_unifies(wrapper):
    integer = wrapper(IntType())
    floating = wrapper(FloatType())
    string = wrapper(StringType())
    writable = isinstance(integer, (ReservoirType, DictType, QuenchedType))
    assert is_assignable(integer, floating) is (not writable)
    assert not is_assignable(floating, integer)
    assert not is_assignable(integer, string)
    assert not is_assignable(string, integer)
    if writable:
        for left, right in [
            (integer, floating),
            (floating, integer),
            (integer, string),
            (string, integer),
        ]:
            assert_both_choices(unify(left, right), left, right)
    else:
        assert unify(integer, floating) == floating
        assert unify(floating, integer) == floating
        joined = wrapper(ValueChoiceType((IntType(), StringType())))
        assert unify(integer, string) == joined
        assert unify(string, integer) == joined


@pytest.mark.parametrize("wrapper", wrappers())
def test_nominal_identity_stays_visible_inside_every_generic_argument(wrapper):
    left = StructType("Record", {"count": IntType()}, declaration_id=object())
    right = StructType("Record", {"count": IntType()}, declaration_id=object())
    assert is_assignable(wrapper(left), wrapper(left))
    assert not is_assignable(wrapper(left), wrapper(right))
    first, second = wrapper(left), wrapper(right)
    if isinstance(first, (ReservoirType, DictType, QuenchedType)):
        assert_both_choices(unify(first, second), first, second)
    else:
        assert unify(first, second) == wrapper(ValueChoiceType((left, right)))


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (GenericType("Left", [IntType()]), GenericType("Right", [IntType()])),
        (GenericType("Box", [IntType()]), GenericType("Box", [IntType(), IntType()])),
        (GenericType("Box", []), GenericType("Box", [IntType()])),
        (GenericType("Task", [IntType()]), TaskType(IntType())),
        (TaskType(IntType()), GovernedType(IntType())),
    ],
)
def test_generic_base_constructor_and_arity_must_agree(left, right):
    assert not is_assignable(left, right)
    assert not is_assignable(right, left)
    assert_both_choices(unify(left, right), left, right)
    assert_both_choices(unify(right, left), right, left)


@pytest.mark.parametrize("nominal", [EnumType, StructType, InterfaceType])
def test_same_name_different_declarations_do_not_match(nominal):
    identity = object()
    first = nominal("Repeated", declaration_id=identity)
    same = nominal("Repeated", declaration_id=identity)
    other = nominal("Repeated", declaration_id=object())
    unidentified = nominal("Repeated")
    assert first == other  # Structural descriptor equality stays compatible.
    assert is_assignable(first, same)
    assert unify(first, same) is first
    for value in (other, unidentified):
        assert not is_assignable(first, value)
        assert not is_assignable(value, first)
        assert_both_choices(unify(first, value), first, value)
        assert_both_choices(unify(value, first), value, first)
    assert is_assignable(unidentified, nominal("Repeated"))
    assert unify(unidentified, nominal("Repeated")) is unidentified
    assert not is_assignable(unidentified, nominal("Different"))


def test_recursive_struct_arguments_compare_identity_without_recursing_fields():
    identity = object()
    left = StructType("Node", declaration_id=identity)
    same = StructType("Node", declaration_id=identity)
    other = StructType("Node", declaration_id=object())
    for node in (left, same, other):
        node.field_types["children"] = ReservoirType(node)
        node.field_types["lookup"] = DictType(StringType(), node)
    assert is_assignable(left, same)
    assert is_assignable(ReservoirType(left), ReservoirType(same))
    assert unify(left, same) is left
    assert unify(ReservoirType(left), ReservoirType(same)).inner_type is left
    assert not is_assignable(left, other)
    assert not is_assignable(ReservoirType(left), ReservoirType(other))
    assert_both_choices(unify(left, other), left, other)
    first, second = ReservoirType(left), ReservoirType(other)
    assert_both_choices(unify(first, second), first, second)


def test_declaration_identity_comparison_does_not_invoke_host_equality():
    class Identity:
        def __eq__(self, other):
            pytest.fail("declaration identity uses object identity, not equality")

    identity = Identity()
    left = StructType("S", declaration_id=identity)
    same = StructType("S", declaration_id=identity)
    other = StructType("S", declaration_id=Identity())
    assert is_assignable(left, same)
    assert not is_assignable(left, other)
    assert unify(left, same) is left
    assert_both_choices(unify(left, other), left, other)
