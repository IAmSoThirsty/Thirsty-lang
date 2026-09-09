"""Native governed values project to bounded, owned JSON without host hooks."""

import json
from enum import Enum

import pytest

from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
from utf.thirsty_lang.governed_values import (
    MAX_DEPTH,
    MAX_INTEGER_BITS,
    MAX_NODES,
    MAX_UTF8_BYTES,
    GovernedValueError,
    project_governed_context,
)
from utf.thirsty_lang.interpreter import (
    Environment,
    FountainInstance,
    Interpreter,
    StructInstance,
)
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser

MARKER = "__thirsty_native__"
PROFILE = "thirsty.native-value.v1"


def parse(source):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors, lexer.errors
    assert not parser.errors, parser.errors
    return program


@pytest.fixture
def execute():
    interpreters = []

    def evaluate(source):
        interpreter = Interpreter()
        interpreters.append(interpreter)
        return interpreter.interpret(parse(source))

    yield evaluate
    for interpreter in interpreters:
        interpreter.executor.shutdown(wait=True)


def metadata(value, kind, name):
    result = value[MARKER]
    assert type(result) is dict
    assert set(result) == {"profile", "scope_id", "declaration_id", "kind", "name"}
    assert result["profile"] == PROFILE
    assert result["kind"] == kind and result["name"] == name
    assert type(result["scope_id"]) is str and result["scope_id"]
    assert type(result["declaration_id"]) is str and result["declaration_id"]
    return result


def nest(value, levels):
    for _ in range(levels):
        value = [value]
    return value


def json_stats(value, depth=0):
    """Measure the public output format, counting every key as a string node."""
    nodes, size, deepest = 1, 0, depth
    if type(value) is str:
        size = len(value.encode("utf-8"))
    elif type(value) is dict:
        for key, item in value.items():
            nodes += 1
            size += len(key.encode("utf-8"))
            child_nodes, child_size, child_depth = json_stats(item, depth + 1)
            nodes += child_nodes
            size += child_size
            deepest = max(deepest, child_depth)
    elif type(value) is list:
        for item in value:
            child_nodes, child_size, child_depth = json_stats(item, depth + 1)
            nodes += child_nodes
            size += child_size
            deepest = max(deepest, child_depth)
    else:
        assert value is None or type(value) in (bool, int, float)
    return nodes, size, deepest


def test_profile_resource_limits_are_explicit():
    assert MAX_DEPTH == 32
    assert MAX_NODES == 10_000
    assert MAX_UTF8_BYTES == 1_048_576
    assert MAX_INTEGER_BITS == 4096


def test_plain_json_preserves_paths_values_and_owned_containers():
    shared = {"items": [None, True, False, 0, -7, 1.25, "water 💧"]}
    source = {
        "request.id": "one",
        "request": {"kind": "read"},
        "left": shared,
        "right": shared,
    }
    projected = project_governed_context(source)
    assert projected == source
    assert projected is not source
    assert projected["left"] is not shared
    assert projected["left"] is not projected["right"]
    assert projected["left"]["items"] is not projected["right"]["items"]
    shared["items"].append("source-only")
    projected["left"]["items"].append("output-only")
    assert "source-only" not in projected["right"]["items"]
    assert "output-only" not in shared["items"]
    assert "output-only" not in projected["right"]["items"]
    assert json.loads(json.dumps(projected, allow_nan=False)) == projected


def test_real_nested_fountain_struct_and_enum_have_native_envelopes(execute):
    value = execute(
        "enum State { Ready }\n"
        "struct Reading { state: State\nvalues: Reservoir[Int] }\n"
        "fountain Sensor { reading = new Reading(State.Ready, [1, 2]) }\n"
        "new Sensor()"
    )
    projected = project_governed_context({"sensor": value})
    sensor = projected["sensor"]
    sensor_metadata = metadata(sensor, "fountain", "Sensor")
    assert set(sensor) == {MARKER, "fields"}
    reading = sensor["fields"]["reading"]
    reading_metadata = metadata(reading, "struct", "Reading")
    state = reading["fields"]["state"]
    state_metadata = metadata(state, "enum", "State")
    assert set(state) == {MARKER, "variant"}
    assert state["variant"] == "Ready"
    assert reading["fields"]["values"] == [1, 2]
    assert (
        len(
            {
                item["scope_id"]
                for item in (sensor_metadata, reading_metadata, state_metadata)
            }
        )
        == 1
    )
    assert (
        len(
            {
                item["declaration_id"]
                for item in (sensor_metadata, reading_metadata, state_metadata)
            }
        )
        == 3
    )
    assert json.loads(json.dumps(projected, allow_nan=False)) == projected


@pytest.mark.parametrize(
    "source,kind,name",
    [
        (
            "struct Row { value: Int }\ndrink first = new Row(1);\n[first, first, new Row(2)]",
            "struct",
            "Row",
        ),
        (
            "enum State { Ready, Busy }\n[State.Ready, State.Ready, State.Busy]",
            "enum",
            "State",
        ),
        (
            "fountain Box { value = 1 }\ndrink first = new Box();\n[first, first, new Box()]",
            "fountain",
            "Box",
        ),
    ],
)
def test_aliases_and_same_declaration_instances_keep_identity(
    source, kind, name, execute
):
    values = execute(source)
    first = project_governed_context({"values": values})
    second = project_governed_context({"values": values})
    entries = first["values"]
    identities = [metadata(item, kind, name) for item in entries]
    assert identities[0] == identities[1] == identities[2]
    assert first == second
    assert entries[0] is not entries[1]
    assert entries[0][MARKER] is not entries[1][MARKER]
    entries[0][MARKER]["name"] = "output-only"
    assert second["values"][0][MARKER]["name"] == name
    assert (
        project_governed_context({"value": values[0]})["value"][MARKER]["name"] == name
    )


@pytest.mark.parametrize(
    "declaration,instance,kind,name",
    [
        ("struct Item { value: Int }", "new Item(1)", "struct", "Item"),
        ("enum Item { Ready }", "Item.Ready", "enum", "Item"),
        ("fountain Item { value = 1 }", "new Item()", "fountain", "Item"),
    ],
)
def test_same_named_declarations_have_distinct_identity(
    declaration, instance, kind, name, execute
):
    values = execute(
        f"{declaration}\ndrink outer = {instance}\n"
        f"glass make() {{ {declaration}\nreturn {instance} }}\n[outer, make()]"
    )
    outer, inner = project_governed_context({"values": values})["values"]
    first, second = metadata(outer, kind, name), metadata(inner, kind, name)
    assert first["scope_id"] == second["scope_id"]
    assert first["declaration_id"] != second["declaration_id"]


def test_separate_interpreters_do_not_share_native_scope_identity(execute):
    source = "struct Row { value: Int }\nnew Row(1)"
    first = project_governed_context({"row": execute(source)})["row"][MARKER]
    second = project_governed_context({"row": execute(source)})["row"][MARKER]
    assert first["scope_id"] != second["scope_id"]


def test_imported_aliases_share_caller_scope_and_keep_the_imported_declaration(
    tmp_path,
):
    module = tmp_path / "records.thirsty"
    module.write_text(
        "struct Row { value: Int }\ndrink sample = new Row(1)", encoding="utf-8"
    )
    targets = (module.name, str(module.resolve()))
    policy = (
        "\n".join(
            f'when action == "import" and target == {json.dumps(target)} => ALLOW'
            for target in targets
        )
        + "\nwhen true => DENY"
    )
    runtime = TarlRuntime(PolicyParser.parse(policy))
    interpreter = (
        Interpreter().attach_tarl(runtime).set_authority("projection-import-test")
    )
    interpreter.source_directory = tmp_path
    try:
        values = interpreter.interpret(
            parse(
                'import "records.thirsty" as records\nstruct Row { value: Int }\ndrink Alias = records.Row;\n[records.sample, Alias(2), new Row(3)]'
            )
        )
        imported, alias, local = project_governed_context({"values": values})["values"]
        assert imported[MARKER] == alias[MARKER]
        assert imported[MARKER]["scope_id"] == local[MARKER]["scope_id"]
        assert imported[MARKER]["declaration_id"] != local[MARKER]["declaration_id"]
    finally:
        interpreter.executor.shutdown(wait=True)
        runtime.shutdown()


@pytest.mark.parametrize("kind", ["struct", "fountain", "enum"])
def test_raw_host_native_objects_are_not_runtime_registered(kind):
    if kind == "struct":
        declaration = parse("struct Row { value: Int }").stmts[0]
        value = StructInstance(declaration, {"value": 1}, Environment())
    elif kind == "fountain":
        declaration = parse("fountain Box { value = 1 }").stmts[0]
        value = FountainInstance(declaration, Environment())
    else:
        value = Enum("State", {"Ready": "Ready"}).Ready
    with pytest.raises(GovernedValueError):
        project_governed_context({"value": value})


@pytest.mark.parametrize("kind", ["struct", "fountain"])
def test_identity_from_another_declaration_cannot_authorize_a_native_value(
    kind, execute
):
    source = (
        "struct First { value: Int }\nstruct Second { value: Int }\n[new First(1), new Second(2)]"
        if kind == "struct"
        else "fountain First { value = 1 }\nfountain Second { value = 2 }\n[new First(), new Second()]"
    )
    first, second = execute(source)
    second.native_identity = first.native_identity
    with pytest.raises(GovernedValueError):
        project_governed_context({"value": second})


def test_enum_identity_cannot_be_borrowed_from_another_runtime_enum(
    execute, monkeypatch
):
    first, second = execute(
        "enum First { Ready }\nenum Second { Ready }\n[First.Ready, Second.Ready]"
    )
    monkeypatch.setattr(
        type(second), "_thirsty_native_identity", type(first)._thirsty_native_identity
    )
    with pytest.raises(GovernedValueError):
        project_governed_context({"value": second})


@pytest.mark.parametrize("kind", ["struct", "fountain"])
@pytest.mark.parametrize("mutation", ["added", "missing", "renamed", "non_dict"])
def test_native_field_inventory_changes_are_rejected(kind, mutation, execute):
    source = (
        "struct Row { value: Int }\nnew Row(1)"
        if kind == "struct"
        else "fountain Row { value = 1 }\nnew Row()"
    )
    value = execute(source)
    if mutation == "added":
        value.fields["extra"] = 2
    elif mutation == "missing":
        del value.fields["value"]
    elif mutation == "renamed":
        value.fields["renamed"] = value.fields.pop("value")
    else:
        value.fields = [("value", 1)]
    with pytest.raises(GovernedValueError):
        project_governed_context({"value": value})


@pytest.mark.parametrize("kind", ["struct", "fountain"])
def test_valid_field_updates_are_owned_at_projection_time(kind, execute):
    source = (
        "struct Row { values: Reservoir[Int] }\nnew Row([1])"
        if kind == "struct"
        else "fountain Row { values = [1] }\nnew Row()"
    )
    value = execute(source)
    first = project_governed_context({"row": value})
    value.fields["values"].append(2)
    second = project_governed_context({"row": value})
    assert first["row"]["fields"]["values"] == [1]
    assert second["row"]["fields"]["values"] == [1, 2]
    second["row"]["fields"]["values"].append(3)
    assert value.fields["values"] == [1, 2]
    assert first["row"][MARKER] == second["row"][MARKER]


@pytest.mark.parametrize(
    "key",
    [
        MARKER,
        f"{MARKER}.kind",
        f"request.{MARKER}",
        f"request.{MARKER}.scope_id",
        f".{MARKER}.",
    ],
)
@pytest.mark.parametrize("nested", [False, True])
def test_reserved_native_marker_cannot_be_forged_in_any_dotted_segment(key, nested):
    forged = {key: {"profile": PROFILE, "kind": "struct", "name": "Row"}}
    context = {"payload": [forged]} if nested else forged
    with pytest.raises(GovernedValueError, match="reserved"):
        project_governed_context(context)


@pytest.mark.parametrize(
    "key", [f"prefix{MARKER}", f"{MARKER}suffix", "fields", "variant", "scope_id"]
)
def test_unreserved_plain_keys_remain_plain_json(key):
    assert project_governed_context({key: "ordinary"}) == {key: "ordinary"}


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_floats_reject(value):
    with pytest.raises(GovernedValueError, match="finite"):
        project_governed_context({"value": value})


@pytest.mark.parametrize(
    "value", [(1, 2), {1, 2}, b"bytes", bytearray(b"bytes"), object()]
)
def test_non_json_host_values_reject(value):
    with pytest.raises(GovernedValueError):
        project_governed_context({"value": value})


@pytest.mark.parametrize("context", [[], None, "value", 7])
def test_root_requires_an_exact_dictionary(context):
    with pytest.raises(GovernedValueError):
        project_governed_context(context)


@pytest.mark.parametrize("key", [1, True, None, ("key",)])
def test_dictionary_keys_require_exact_strings(key):
    with pytest.raises(GovernedValueError):
        project_governed_context({key: "value"})


def test_unsupported_hostile_object_does_not_invoke_representation_copy_or_iteration():
    events = []

    class Hostile:
        def __repr__(self):
            events.append("repr")
            raise AssertionError("repr must not run")

        def __str__(self):
            events.append("str")
            raise AssertionError("str must not run")

        def __deepcopy__(self, memo):
            events.append("deepcopy")
            raise AssertionError("deepcopy must not run")

        def __iter__(self):
            events.append("iter")
            raise AssertionError("iter must not run")

        def __getattr__(self, name):
            events.append("getattr")
            raise AssertionError("getattr must not run")

    with pytest.raises(GovernedValueError):
        project_governed_context({"value": Hostile()})
    assert events == []


@pytest.mark.parametrize("base", [dict, list, str, int, float])
def test_builtin_subclasses_are_rejected_without_calling_hooks(base):
    events = []

    class Hostile(base):
        def __iter__(self):
            events.append("iter")
            raise AssertionError("iter must not run")

        def items(self):
            events.append("items")
            raise AssertionError("items must not run")

        def __len__(self):
            events.append("len")
            raise AssertionError("len must not run")

        def __repr__(self):
            events.append("repr")
            raise AssertionError("repr must not run")

        def __deepcopy__(self, memo):
            events.append("deepcopy")
            raise AssertionError("deepcopy must not run")

        def encode(self, *args, **kwargs):
            events.append("encode")
            raise AssertionError("encode must not run")

    value = Hostile()
    with pytest.raises(GovernedValueError):
        project_governed_context({"value": value})
    if base is dict:
        with pytest.raises(GovernedValueError):
            project_governed_context(value)
    if base is str:
        with pytest.raises(GovernedValueError):
            project_governed_context({value: "ordinary"})
    assert events == []


@pytest.mark.parametrize("native_type", [StructInstance, FountainInstance])
def test_native_subclasses_are_rejected_without_attribute_hooks(native_type):
    events = []

    class Hostile(native_type):
        def __getattribute__(self, name):
            events.append(name)
            raise AssertionError("native subclass attributes must not be read")

    value = object.__new__(Hostile)
    with pytest.raises(GovernedValueError):
        project_governed_context({"value": value})
    assert events == []


def test_native_field_dictionary_subclass_does_not_run_hooks(execute):
    events = []

    class HostileFields(dict):
        def __iter__(self):
            events.append("iter")
            raise AssertionError("field iteration must not run")

        def __len__(self):
            events.append("len")
            raise AssertionError("field length hook must not run")

        def items(self):
            events.append("items")
            raise AssertionError("field items hook must not run")

    value = execute("struct Row { value: Int }\nnew Row(1)")
    value.fields = HostileFields({"value": 1})
    with pytest.raises(GovernedValueError):
        project_governed_context({"value": value})
    assert events == []


@pytest.mark.parametrize("kind", ["list", "dict", "native"])
def test_cycles_are_rejected(kind, execute):
    if kind == "list":
        value = []
        value.append(value)
    elif kind == "dict":
        value = {}
        value["self"] = value
    else:
        value = execute("struct Node { child: Any }\nnew Node(none)")
        value.fields["child"] = value
    with pytest.raises(GovernedValueError, match="cyclic"):
        project_governed_context({"value": value})


def test_depth_limit_includes_root_zero_and_native_envelope(execute):
    context = {"value": nest(None, MAX_DEPTH - 1)}
    assert json_stats(project_governed_context(context))[2] == MAX_DEPTH
    with pytest.raises(GovernedValueError, match="depth"):
        project_governed_context({"value": nest(None, MAX_DEPTH)})
    native = execute("struct Row { value: Int }\nnew Row(1)")
    base_depth = json_stats(project_governed_context({"value": native}))[2]
    context = {"value": nest(native, MAX_DEPTH - base_depth)}
    assert json_stats(project_governed_context(context))[2] == MAX_DEPTH
    with pytest.raises(GovernedValueError, match="depth"):
        project_governed_context({"value": nest(native, MAX_DEPTH - base_depth + 1)})


def test_node_budget_counts_containers_values_and_dictionary_keys():
    context = {"items": [None] * (MAX_NODES - 3)}
    assert json_stats(project_governed_context(context))[0] == MAX_NODES
    context["items"].append(None)
    with pytest.raises(GovernedValueError, match="node"):
        project_governed_context(context)
    context = {str(index): None for index in range((MAX_NODES - 1) // 2)}
    assert json_stats(project_governed_context(context))[0] == MAX_NODES - 1
    context["over-budget"] = None
    with pytest.raises(GovernedValueError, match="node"):
        project_governed_context(context)


def test_node_budget_counts_native_envelopes_and_repeated_aliases(execute):
    native = execute("struct Row { value: Int }\nnew Row(1)")
    context = {"native": native, "padding": []}
    overhead = json_stats(project_governed_context(context))[0]
    context["padding"] = [None] * (MAX_NODES - overhead)
    assert json_stats(project_governed_context(context))[0] == MAX_NODES
    context["padding"].append(None)
    with pytest.raises(GovernedValueError, match="node"):
        project_governed_context(context)
    shared = [None] * (MAX_NODES // 2)
    with pytest.raises(GovernedValueError, match="node"):
        project_governed_context({"left": shared, "right": shared})


@pytest.mark.parametrize("unicode_payload", [False, True])
def test_utf8_budget_counts_strings_and_keys_not_code_points(unicode_payload):
    available = MAX_UTF8_BYTES - len("value")
    payload = (
        ("💧" * (available // 4) + "x" * (available % 4))
        if unicode_payload
        else "x" * available
    )
    context = {"value": payload}
    assert json_stats(project_governed_context(context))[1] == MAX_UTF8_BYTES
    with pytest.raises(GovernedValueError, match="UTF-8"):
        project_governed_context({"value": payload + "x"})


def test_utf8_budget_includes_native_metadata(execute):
    native = execute('struct Row { value: String }\nnew Row("")')
    overhead = json_stats(project_governed_context({"native": native}))[1]
    native.fields["value"] = "x" * (MAX_UTF8_BYTES - overhead)
    assert json_stats(project_governed_context({"native": native}))[1] == MAX_UTF8_BYTES
    native.fields["value"] += "x"
    with pytest.raises(GovernedValueError, match="UTF-8"):
        project_governed_context({"native": native})


def test_utf8_budget_counts_keys_and_repeated_aliases():
    key = "k" * MAX_UTF8_BYTES
    assert project_governed_context({key: None}) == {key: None}
    with pytest.raises(GovernedValueError, match="UTF-8"):
        project_governed_context({key + "k": None})
    shared = {"value": "x" * (MAX_UTF8_BYTES // 2)}
    with pytest.raises(GovernedValueError, match="UTF-8"):
        project_governed_context({"left": shared, "right": shared})


@pytest.mark.parametrize("sign", [1, -1])
def test_integer_bit_budget_preserves_exact_boundary(sign):
    accepted = sign * (1 << (MAX_INTEGER_BITS - 1))
    assert project_governed_context({"value": accepted})["value"] == accepted
    with pytest.raises(GovernedValueError, match="bit"):
        project_governed_context({"value": sign * (1 << MAX_INTEGER_BITS)})


@pytest.mark.parametrize("key", [False, True])
def test_invalid_unicode_rejects_in_keys_and_values(key):
    context = {"\ud800": "value"} if key else {"value": "\ud800"}
    with pytest.raises(GovernedValueError, match="Unicode"):
        project_governed_context(context)
