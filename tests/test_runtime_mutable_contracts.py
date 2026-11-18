"""Exercise native mutable contracts through the guest interpreter."""

import pytest

from utf.thirsty_lang.checker import Checker
from utf.thirsty_lang.execution import ExecutionLimits
from utf.thirsty_lang.interpreter import Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser


def program(source):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    tree = parser.parse()
    assert not lexer.errors and not parser.errors, (lexer.errors, parser.errors)
    return tree


@pytest.fixture
def machine():
    # These assertions exercise type semantics, including cold governance imports.
    with Interpreter(
        allow_ungoverned=True, execution_limits=ExecutionLimits(timeout_seconds=180)
    ) as interpreter:
        yield interpreter


def run(machine, source):
    return machine.interpret(program(source), mode="core")


@pytest.mark.parametrize(
    "statement",
    [
        'shared[0] = "bad"',
        'push(shared, "bad")',
        'res.push(shared, "bad")',
        'res.flood(shared, "bad")',
    ],
)
def test_every_list_write_checks_an_existing_alias(machine, statement):
    setup = 'import "thirst::reservoir" as res\ndrink shared: Any = [1]\ndrink typed: Reservoir[Int] = shared'
    run(machine, setup)
    with pytest.raises(TypeError, match="requires Int"):
        run(machine, statement)
    values = machine.env.get("shared")
    assert values is machine.env.get("typed") and values == [1]
    assert run(machine, "res.push(shared, 2)\ntyped") is values
    assert values == [1, 2]


@pytest.mark.parametrize(
    "statement",
    [
        'shared["entry"] = false',
        "shared.entry = false",
        'json.set(shared, "entry", false)',
        "json.set(shared, false, 1)",
        "shared[1] = 3",
    ],
)
def test_dictionary_writes_check_keys_and_values_before_change(machine, statement):
    run(
        machine,
        'import "thirst::json" as json\ndrink shared: Any = {"entry": 1}\ndrink typed: Dict[String, Int] = shared',
    )
    with pytest.raises(TypeError, match="requires"):
        run(machine, statement)
    assert machine.env.get("typed") == {"entry": 1}
    assert run(machine, 'json.set(shared, "entry", 2)') is machine.env.get("typed")


@pytest.mark.parametrize(
    "boundary",
    [
        "glass accept(x: Reservoir[Int]) { return x }\naccept(shared)",
        "glass produce() -> Reservoir[Int] { return shared }\nproduce()",
        "drink accept = glass(x: Reservoir[Int]) { return x }\naccept(shared)",
        "drink produce = glass() -> Reservoir[Int] { return shared }\nproduce()",
        "morph accept(x: Reservoir[Int]) { return x }\naccept(shared)",
        "fountain Box { glass accept(x: Reservoir[Int]) { return x } }\nnew Box().accept(shared)",
        "fountain Box { glass produce() -> Reservoir[Int] { return shared } }\nnew Box().produce()",
        "struct Box { items: Reservoir[Int] }\nnew Box(shared)",
        "struct Box { items: Reservoir[Int] }\ndrink box = new Box([])\nbox.items = shared",
        "fountain Box { items: Reservoir[Int] = shared }\nnew Box()",
        "fountain Box { items: Reservoir[Int] }\ndrink box = new Box()\nbox.items = shared",
        "drink mut typed: Reservoir[Int] = []\ntyped = shared",
    ],
)
def test_call_and_field_boundaries_retain_identity_and_contract(machine, boundary):
    run(machine, "drink shared: Any = [1]\n" + boundary)
    with pytest.raises(TypeError, match="requires Int"):
        run(machine, "shared[0] = true")
    assert machine.env.get("shared") == [1]


def test_governed_arg_and_return(machine):
    from utf.tarl.core import PolicyParser
    from utf.tarl.runtime import TarlRuntime

    machine.attach_tarl(
        TarlRuntime(PolicyParser.parse('when action == "take" => ALLOW'))
    ).set_authority("type-test")
    for signature in ("x: Reservoir[Int]", "x: Any"):
        tree = program(
            f"glass take({signature}) -> Reservoir[Int] requires true {{ return x }}"
        )
        machine.interpret(tree, mode="governed")
        payload = [1]
        assert machine.env.get("take")(payload) is payload
        machine.env.define("shared", payload)
        with pytest.raises(TypeError, match="requires Int"):
            run(machine, "push(shared, false)")


def test_shallow_copy_and_nested_write_keep_only_shared_constraints(machine):
    run(
        machine,
        'drink inner: Any = [1]\ndrink mapping: Dict[String, Reservoir[Int]] = {"row": inner}\ndrink copy = inner[:]\ncopy[0] = "fresh"',
    )
    assert machine.env.get("copy") == ["fresh"]
    with pytest.raises(TypeError, match="requires Int"):
        run(machine, 'mapping["row"][0] = "bad"')
    assert machine.env.get("inner") == [1]
    run(machine, 'drink other: Any = [3]\nmapping["row"] = other')
    with pytest.raises(TypeError, match="requires Int"):
        run(machine, 'other[0] = "bad"')


def test_failed_batch_or_write_leaves_no_partial_constraints(machine):
    run(
        machine,
        "drink raw: Any = [1]\nglass take(x: Reservoir[Int], y: Reservoir[Int]) { return 0 }",
    )
    with pytest.raises(TypeError, match="requires Int"):
        run(machine, 'take(raw, ["bad"])')
    run(machine, 'raw[0] = "still free"')
    run(
        machine,
        "drink typed: Reservoir[Reservoir[Int]] = [[]]\ndrink new_row: Any = [7]",
    )
    with pytest.raises(IndexError):
        run(machine, "typed[8] = new_row")
    run(machine, 'new_row[0] = "still free"')


def test_invariant_contracts_refine_any_and_preserve_numeric_widening(machine):
    run(
        machine,
        "drink shared: Any = [1]\ndrink broad: Reservoir[Any] = shared\ndrink narrow: Reservoir[Float] = shared",
    )
    assert run(machine, "push(shared, 2.5)\nnarrow") == [1, 2.5]
    with pytest.raises(TypeError, match="incompatible writable contracts"):
        run(machine, "drink integers: Reservoir[Int] = shared")
    with pytest.raises(TypeError, match="requires Float"):
        run(machine, "push(broad, true)")


def test_dynamic_failure_is_consistent_with_checker_boundary(machine):
    source = 'glass take(x: Reservoir[Int]) { return x }\ndrink dynamic: Any = ["bad"]\ntake(dynamic)'
    assert Checker().check_all(program(source)) == []
    with pytest.raises(TypeError, match="requires Int"):
        run(machine, source)


def test_nominal_elements_use_declaration_identity(machine):
    run(
        machine,
        "struct Row { n: Int }\nenum Status { Good }\ndrink rows: Reservoir[Row] = [new Row(1)]\ndrink states: Reservoir[Status] = [Status.Good]",
    )
    with pytest.raises(TypeError, match="requires Row"):
        run(machine, "push(rows, Status.Good)")
    with pytest.raises(TypeError, match="requires Status"):
        run(machine, "push(states, new Row(1))")


def test_bounded_graph_validation_and_cycles_are_transactional(machine, monkeypatch):
    from utf.thirsty_lang import mutable_contracts

    cycle = []
    cycle.append(cycle)
    machine.env.define("shared", cycle)
    assert run(machine, "drink typed: Reservoir[Any] = shared\ntyped") is cycle
    with pytest.raises(TypeError):
        run(machine, "drink mismatch: Reservoir[Reservoir[Int]] = shared")
    monkeypatch.setattr(mutable_contracts, "_MAX_VISITS", 4)
    with pytest.raises(TypeError, match="validation limit"):
        run(machine, "drink too_long: Reservoir[Int] = [1, 2, 3, 4]")
    monkeypatch.setattr(mutable_contracts, "_MAX_RETAINED", 1)
    with pytest.raises(TypeError, match="identity limit"):
        run(machine, "drink extra: Reservoir[Int] = []")


def test_deep_annotation_is_bounded(machine):
    annotation = "Reservoir[" * 65 + "Any" + "]" * 65
    with pytest.raises(TypeError, match="annotation limit"):
        run(machine, f"drink deep: {annotation} = []")


def test_imported_module_retains_contract_after_call_returns(machine, tmp_path):
    (tmp_path / "typed.thirsty").write_text(
        "glass take(rows: Dict[String, Reservoir[Int]]) { return rows }",
        encoding="utf-8",
    )
    machine.source_directory = tmp_path
    run(
        machine,
        'import "typed.thirsty" as typed_module\ndrink row: Any = [1]\ndrink mapping: Any = {"row": row}\ntyped_module.take(mapping)',
    )
    with pytest.raises(TypeError, match="requires Int"):
        run(machine, 'row[0] = "bad"')
    assert run(machine, 'row[0] = 3\nmapping["row"]') is machine.env.get("row")


def test_rejected_struct_constructor_leaves_other_field_unconstrained(machine):
    run(
        machine,
        "struct Pair { left: Reservoir[Int]; right: Dict[String, Int] }\ndrink shared: Any = [1]",
    )
    with pytest.raises(TypeError, match="field 'right' requires Dict"):
        run(machine, 'new Pair(shared, {"k": "bad"})')
    run(machine, 'shared[0] = "still free"')


def test_nested_shallow_slice_protects_shared_children(machine):
    run(
        machine,
        "drink items: Reservoir[Reservoir[Int]] = [[1]]\ndrink copied = items[:]\ndrink alias: Any = copied[0]",
    )
    with pytest.raises(TypeError, match="requires Int"):
        run(machine, "push(alias, false)")
    assert run(machine, "push(alias, 2)\nitems[0]") == [1, 2]


def test_existing_nested_contracts_cannot_exhaust_the_python_stack(
    machine, monkeypatch
):
    from utf.thirsty_lang import mutable_contracts

    monkeypatch.setattr(mutable_contracts, "_MAX_DEPTH", 2)
    run(machine, "drink inner: Reservoir[Reservoir[Int]] = [[1]]")
    with pytest.raises(TypeError, match="nesting limit"):
        run(machine, "drink nested: Reservoir[Reservoir[Any]] = [inner]")
    assert run(machine, "inner[0][0]") == 1


@pytest.mark.parametrize(
    "declaration",
    [
        "drink target: Reservoir[Quenched[Int]] = [quenched(1)]",
        'drink target: Dict[String, Quenched[Int]] = {"key": quenched(1)}',
    ],
)
def test_native_quenched_literal_works_in_typed_containers(machine, declaration):
    assert Checker().check_all(program(declaration)) == []
    run(machine, declaration)
    target = machine.env.get("target")
    assert (target[0] if type(target) is list else target["key"]) == {
        "type": "Any",
        "value": 1,
    }


def test_quenched_payload_alias_and_replacement_preserve_the_inner_contract(machine):
    run(
        machine,
        "drink inner: Any = [1]\ndrink wrapped: Any = quenched(inner)\ndrink rows: Reservoir[Quenched[Reservoir[Int]]] = [wrapped]",
    )
    with pytest.raises(TypeError, match="requires Int"):
        run(machine, "push(inner, false)")
    with pytest.raises(TypeError, match="requires Reservoir"):
        run(machine, 'wrapped.value = "bad"')
    with pytest.raises(TypeError, match="requires String"):
        run(machine, 'wrapped["type"] = false')
    with pytest.raises(TypeError, match="exactly type and value"):
        run(machine, 'wrapped["another"] = 1')
    with pytest.raises(TypeError, match="required Quenched fields"):
        run(machine, "evaporate wrapped")
    with pytest.raises(TypeError, match="required Quenched fields"):
        machine.env.get("evaporate")(machine.env.get("wrapped"))
    assert run(machine, "condense wrapped") is machine.env.get("inner")
    run(machine, "drink replacement: Any = [3]\nwrapped.value = replacement")
    with pytest.raises(TypeError, match="requires Int"):
        run(machine, "replacement[0] = false")
    assert run(machine, "replacement[0] = 4\ncondense wrapped") == [4]


@pytest.mark.parametrize(
    "value",
    ['quenched("invalid")', '{"value": 1}', '{"type": true, "value": 1}', "[1]"],
)
def test_quenched_write_rejects_invalid_native_payload_or_shape(machine, value):
    run(machine, "drink target: Reservoir[Quenched[Int]] = [quenched(1)]")
    with pytest.raises(TypeError):
        run(machine, f"push(target, {value})")
    assert machine.env.get("target") == [{"type": "Any", "value": 1}]


@pytest.mark.parametrize(
    "annotation", ["Task[Int]", "Result[Int, Error]", "Governed[Int]"]
)
def test_descriptors_without_native_guest_values_reject_real_elements(
    machine, annotation
):
    run(machine, f"drink target: Reservoir[{annotation}] = []")
    with pytest.raises(TypeError, match="no guest runtime representation"):
        run(machine, "push(target, 1)")
    assert machine.env.get("target") == []


def test_cross_interpreter_callable_composes_caller_and_definer_contracts(machine):
    with Interpreter(allow_ungoverned=True) as other:
        run(
            other,
            "drink theirs: Reservoir[Int] = [2]\nglass append(x: Any, value: Any) { return push(x, value) }\nglass give() { return theirs }",
        )
        machine.env.define("append", other.env.get("append"))
        machine.env.define("give", other.env.get("give"))
        run(machine, "drink ours: Reservoir[Int] = [1]")
        with pytest.raises(TypeError, match="requires Int"):
            run(machine, "append(ours, false)")
        assert run(machine, "append(ours, 3)\nours") == [1, 3]
        run(machine, "drink received: Any = give()")
        assert machine.env.get("received") is other.env.get("theirs")
    with pytest.raises(TypeError, match="requires Int"):
        run(machine, "received[0] = false")
    assert run(machine, "received[0] = 5\nreceived") == [5]


def test_cross_interpreter_conflict_preserves_each_existing_contract(machine):
    native = []
    with Interpreter(allow_ungoverned=True) as other:
        for owner, element in ((machine, "Int"), (other, "String")):
            owner.env.define("raw", native)
            run(owner, f"drink typed: Reservoir[{element}] = raw")
        run(other, "glass call_me() { return 1 }")
        machine.env.define("foreign", other.env.get("call_me"))
        with pytest.raises(TypeError, match="incompatible writable contracts"):
            run(machine, "foreign()")
        for owner, invalid in ((machine, '"bad"'), (other, "2")):
            with pytest.raises(TypeError, match="typed value requires"):
                run(owner, f"push(typed, {invalid})")
        assert native == []


@pytest.mark.parametrize("empty", ["quenched()", "quenched(none)"])
def test_optional_quenched_payload_can_be_filled_and_cleared(machine, empty):
    run(
        machine,
        f"drink items: Reservoir[Quenched[Int]] = [{empty}]\ndrink alias: Any = items[0]",
    )
    wrapped = machine.env.get("alias")
    assert wrapped == {"type": "Any", "value": None}
    run(machine, "alias.value = 3\nalias.value = none")
    assert machine.env.get("items")[0] is wrapped and wrapped["value"] is None
    with pytest.raises(TypeError, match="requires Int"):
        run(machine, 'alias["value"] = "invalid"')
    assert wrapped == {"type": "Any", "value": None}


def test_nested_optional_payloads_keep_their_individual_constraints(machine):
    run(
        machine,
        'drink vacant: Any = quenched()\ndrink row: Any = [1]\ndrink inner: Any = quenched(row)\ndrink wrappers: Dict[String, Quenched[Quenched[Reservoir[Int]]]] = {"vacant": vacant, "filled": quenched(inner)}',
    )
    run(machine, "vacant.value = inner\ninner.value = none\nvacant.value = none")
    assert (
        machine.env.get("vacant")
        == machine.env.get("inner")
        == {"type": "Any", "value": None}
    )
    with pytest.raises(TypeError, match="requires Int"):
        run(machine, "push(row, false)")
    with pytest.raises(TypeError, match="requires Reservoir"):
        run(machine, 'inner.value = "invalid"')
    with pytest.raises(TypeError, match="requires Quenched"):
        run(machine, 'vacant.value = "invalid"')


def prepare_shared_callback(caller, definer, native, strict, gradual):
    for machine, annotation in ((caller, strict), (definer, gradual)):
        machine.env.define("raw", native)
        run(machine, f"drink shared: {annotation} = raw")
    run(definer, "glass call_me() { return 1 }")
    caller.env.define("foreign", definer.env.get("call_me"))


def test_join_validates_shared_values_before_publishing_contracts(machine):
    native = [1]
    with Interpreter(allow_ungoverned=True) as other:
        prepare_shared_callback(
            machine, other, native, "Reservoir[Int]", "Reservoir[Any]"
        )
        run(other, 'shared[0] = "bad"')
        with pytest.raises(TypeError, match="requires Int"):
            run(machine, "foreign()")
        with pytest.raises(TypeError, match="requires Int"):
            run(machine, "shared[0] = false")
        assert native == ["bad"]
        # The rejected join left the definer's more gradual contract intact.
        run(other, "shared[0] = false\nshared[0] = 3")
        assert run(machine, "foreign()") == 1
        with pytest.raises(TypeError, match="requires Int"):
            run(other, "shared[0] = false")
        assert native == [3]


def test_join_checks_dictionary_keys_and_acquires_new_nested_aliases(machine):
    with Interpreter(allow_ungoverned=True) as other:
        prepare_shared_callback(
            machine, other, {}, "Dict[String, Reservoir[Int]]", "Dict[Any, Any]"
        )
        run(other, 'drink row: Any = [7]\nshared["row"] = row\nshared[false] = row')
        with pytest.raises(TypeError, match="requires String"):
            run(machine, "foreign()")
        # The row was visited before the bad key. Its proposed Int contract
        # must not be published until every shared entry has passed.
        run(other, 'row[0] = "loose"\nevaporate shared\nshared["row"] = row')
        with pytest.raises(TypeError, match="requires Int"):
            run(machine, "foreign()")
        run(other, "row[0] = 8")
        assert run(machine, "foreign()") == 1
        for source, required in (
            ("row[0] = false", "Int"),
            ("shared[9] = row", "String"),
        ):
            with pytest.raises(TypeError, match=f"requires {required}"):
                run(other, source)
        assert run(machine, 'shared["row"]') is other.env.get("row")


@pytest.mark.parametrize("overlapping", [False, True])
def test_join_traverses_only_shared_roots_with_one_validation_budget(
    machine, monkeypatch, overlapping
):
    from utf.thirsty_lang import mutable_contracts

    first = [1, 2, 3]
    with Interpreter(allow_ungoverned=True) as other:
        for owner, values in (
            (machine, first),
            (other, first if overlapping else [4, 5]),
        ):
            owner.env.define("raw", values)
            run(owner, "drink typed: Reservoir[Int] = raw")
        run(other, "glass call_me() { return 1 }")
        machine.env.define("foreign", other.env.get("call_me"))
        monkeypatch.setattr(mutable_contracts, "_MAX_VISITS", 1)
        if overlapping:
            with pytest.raises(TypeError, match="validation limit"):
                run(machine, "foreign()")
        else:
            assert run(machine, "foreign()") == 1
