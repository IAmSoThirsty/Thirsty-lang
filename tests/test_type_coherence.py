"""Source conformance for nominal generics, key types, and scalar Bool rules."""

import subprocess
import sys
from pathlib import Path

import pytest

from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
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


def run(source, interpreter=None):
    program = parsed(source)
    assert check_ast(program) == []
    return (interpreter or Interpreter()).interpret(program)


@pytest.mark.parametrize(
    "nominal", ["enum Item { Ready }", "struct Item { value: Int }"]
)
@pytest.mark.parametrize(
    "callable_decl", ["glass Item() { return 1 }", "fountain Item { }"]
)
@pytest.mark.parametrize("reverse", [False, True])
def test_nominal_preparation_does_not_hide_duplicate_callable_names(
    nominal, callable_decl, reverse
):
    declarations = [nominal, callable_decl]
    if reverse:
        declarations.reverse()
    errors = check_ast(parsed("\n".join(declarations)))
    assert any(error.code == "E010" for error in errors)


@pytest.mark.parametrize(
    ("declarations", "name", "correct", "wrong"),
    [
        (
            "enum State { Ready }\nenum Other { Ready }\n",
            "State",
            "State.Ready",
            "Other.Ready",
        ),
        (
            "struct Row { value: Int }\nstruct Other { value: Int }\n",
            "Row",
            "new Row(1)",
            "new Other(1)",
        ),
    ],
)
@pytest.mark.parametrize("site", ["declaration", "argument", "return", "struct_field"])
def test_nested_nominal_generic_annotations_reject_distinct_declared_types(
    declarations, name, correct, wrong, site
):
    annotation = f"Dict[String, Reservoir[{name}]]"

    def source(value):
        literal = '{"rows": [' + value + "]}"
        if site == "declaration":
            body = f"drink values: {annotation} = {literal}\nvalues"
        elif site == "argument":
            body = (
                f"glass take(values: {annotation}) {{ return values }}\ntake({literal})"
            )
        elif site == "return":
            body = f"glass make() -> {annotation} {{ return {literal} }}\nmake()"
        else:
            body = (
                f"struct Container {{ values: {annotation} }}\n"
                f"drink container = new Container({literal})\ncontainer.values"
            )
        return declarations + body

    assert check_ast(parsed(source(correct))) == []
    errors = check_ast(parsed(source(wrong)))
    assert any(item.code in {"E021", "E023"} for item in errors)
    # Runtime variable/parameter annotations remain gradual. Existing struct
    # field enforcement is a separate runtime boundary and must stay active.
    if site == "struct_field":
        with pytest.raises(TypeError, match="requires"):
            Interpreter().interpret(parsed(source(wrong)))


@pytest.mark.parametrize("value", ["1", '"Ready"', "true"])
def test_nested_nominal_annotations_do_not_decay_to_any_for_primitive_values(value):
    source = (
        "enum State { Ready }\n"
        f'drink values: Dict[String, Reservoir[State]] = {{"rows": [{value}]}}'
    )
    assert check_ast(parsed(source))


@pytest.mark.parametrize(
    ("declarations", "annotation", "correct", "wrong"),
    [
        ("enum State { Ready }\n", "Reservoir[State]", "[State.Ready]", "[1]"),
        (
            "struct Row { value: Int }\n",
            "Dict[String, Reservoir[Row]]",
            '{"rows": [new Row(1)]}',
            '{"rows": [1]}',
        ),
    ],
)
def test_forward_calls_retain_nominal_types_in_later_function_signatures(
    declarations, annotation, correct, wrong
):
    def source(value):
        return (
            declarations
            + f"glass first() {{ return later({value}) }}\n"
            + f"glass later(values: {annotation}) -> Int {{ return 7 }}\nfirst()"
        )

    assert run(source(correct)) == 7
    assert check_ast(parsed(source(wrong)))


@pytest.mark.parametrize(
    ("declaration", "name", "value"),
    [
        ("enum State { Ready }", "State", "State.Ready"),
        ("struct Row { value: Int }", "Row", "new Row(1)"),
    ],
)
def test_same_name_nominals_in_different_scopes_are_not_the_same_type(
    declaration, name, value
):
    source = (
        f"{declaration}\n"
        f"glass take(values: Reservoir[{name}]) {{ return 0 }}\n"
        f"glass caller() {{ {declaration}\nreturn take([{value}]) }}\ncaller()"
    )
    assert check_ast(parsed(source))


def test_nested_record_field_rejects_same_named_enum_from_another_scope():
    source = (
        "enum State { Ready }\nstruct Container { values: Reservoir[State] }\n"
        "glass make() { enum State { Ready }\n"
        "return new Container([State.Ready]) }\nmake()"
    )
    program = parsed(source)
    assert check_ast(program)
    with pytest.raises(TypeError, match="requires"):
        Interpreter().interpret(program)


@pytest.mark.parametrize("name", ["Int", "String", "Bool"])
def test_declared_nominal_names_take_precedence_over_primitive_field_aliases(name):
    declarations = f"enum {name} {{ Ready }}\nstruct Container {{ value: {name} }}\n"
    assert (
        run(
            declarations
            + f"drink container = new Container({name}.Ready)\ncontainer.value == {name}.Ready"
        )
        is True
    )
    invalid = parsed(declarations + "new Container(1)")
    assert check_ast(invalid)
    with pytest.raises(TypeError, match="requires"):
        Interpreter().interpret(invalid)


@pytest.mark.parametrize(
    "source",
    [
        'drink mut value: Int;\nvalue = "wrong"',
        "enum State { Ready }\ndrink mut values: Reservoir[State];\nvalues = [1]",
        'drink mut data: Dict[String, Int];\ndata = {1: "wrong"}',
    ],
)
def test_uninitialized_bindings_retain_annotations_for_later_assignment(source):
    assert check_ast(parsed(source))


def test_valid_later_assignment_preserves_existing_core_none_initialization():
    assert run("drink value: Int\nvalue") is None
    assert (
        run(
            "enum State { Ready }\ndrink mut values: Reservoir[State];\n"
            "values = [State.Ready]\nvalues[0] == State.Ready"
        )
        is True
    )


@pytest.mark.parametrize(
    "declaration", ["struct Row { status: String, cents: Int }", "interface Bad { * }"]
)
def test_malformed_declarations_fail_without_hanging_or_running_prior_code(
    declaration, tmp_path
):
    source = tmp_path / "malformed.thirsty"
    source.write_text('print("forbidden")\n' + declaration, encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "-m", "utf.thirsty_lang.cli", "run", str(source)],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "E901" in completed.stderr


def test_parameter_names_cannot_shadow_nominals_in_the_same_function_signature():
    assert (
        run(
            "enum State { Ready }\n"
            "glass preserve(State: Int, rows: Reservoir[State]) -> Reservoir[State] {\n"
            "return rows\n}\n"
            "drink result = preserve(1, [State.Ready])\nresult[0] == State.Ready"
        )
        is True
    )


@pytest.mark.parametrize("bad_return", [False, True])
def test_parameter_name_shadowing_does_not_weaken_later_parameter_or_return_types(
    bad_return,
):
    source = (
        "enum State { Ready }\n"
        "glass preserve(State: Int, rows: Reservoir[State]) -> Reservoir[State] {\n"
        + ("return [1]" if bad_return else "return rows")
        + "\n}\n"
        + ("preserve(1, [State.Ready])" if bad_return else "preserve(1, [1])")
    )
    errors = check_ast(parsed(source))
    assert any(item.code in {"E021", "E023"} for item in errors)


@pytest.mark.parametrize(
    "declaration",
    [
        "drink values: Reservoir[Int, String] = [1]",
        "glass wrong(value: Reservoir[Int, String]) { return value }",
        'glass wrong() -> Dict[String, Int, Bool] { return {"one": 1} }',
        "struct Wrong { values: Dict[String, Reservoir[Int, Bool]] }",
    ],
)
def test_excess_generic_arguments_report_the_owning_declaration_source_span(
    declaration,
):
    program = parsed("drink prior = 1\n\n" + declaration)
    errors = [item for item in check_ast(program) if item.code == "E901"]
    assert errors
    assert all("type argument" in item.message for item in errors)
    assert all(item.span[0] == 3 and item.span[1] > 0 for item in errors)


def test_nested_record_fields_remain_typed_through_calls_and_returns():
    source = (
        "enum Status { Ready }\nstruct Row { status: Status\ncents: Int }\n"
        "glass preserve(values: Dict[String, Reservoir[Row]]) -> Dict[String, Reservoir[Row]] {\n"
        "return values\n}\n"
        'drink records = preserve({"orders": [new Row(Status.Ready, 125)]})\n'
        'drink cents: Int = records["orders"][0].cents\ncents'
    )
    assert run(source) == 125
    assert check_ast(parsed(source.replace("drink cents: Int", "drink cents: String")))


def test_recursive_struct_children_preserve_their_declared_node_type():
    assert (
        run(
            "struct Node { value: Int\nchildren: Reservoir[Node] }\n"
            "drink tree = new Node(1, [new Node(2, [])])\n"
            "drink child: Node = tree.children[0]\nchild.value"
        )
        == 2
    )


def test_recursive_struct_children_reject_another_nominal_declaration():
    program = parsed(
        "struct Node { value: Int\nchildren: Reservoir[Node] }\n"
        "struct Other { value: Int\nchildren: Reservoir[Other] }\n"
        "new Node(1, [new Other(2, [])])"
    )
    assert check_ast(program)
    with pytest.raises(TypeError, match="requires Reservoir"):
        Interpreter().interpret(program)


def test_small_nested_record_report_uses_declared_nominal_collections():
    assert run(
        "enum Status { Ready, Skipped }\n"
        "struct Row { status: Status\ncents: Int }\n"
        "glass total(groups: Dict[String, Reservoir[Row]]) -> Int {\n"
        "drink mut amount = 0\n"
        'refill (row in groups["orders"]) {\n'
        "thirsty (row.status == Status.Ready) { amount = amount + row.cents }\n"
        "}\nreturn amount\n}\n"
        "drink groups: Dict[String, Reservoir[Row]] = {\n"
        '"orders": [new Row(Status.Ready, 125), new Row(Status.Skipped, 500), new Row(Status.Ready, 75)]\n'
        "}\n"
        'drink report = {"cents": total(groups), "rows": length(groups["orders"])}\nreport'
    ) == {"cents": 200, "rows": 3}


@pytest.mark.parametrize(
    ("annotation", "literal", "wrong_key"),
    [
        ("Dict[String, Int]", '{"one": 1}', "1"),
        ("Dict[Int, String]", '{1: "one"}', '"1"'),
        ("Dict[Int, String]", '{1: "one"}', "true"),
        ("Dict[Bool, String]", '{true: "one"}', "1"),
        ("Dict[Int, String]", '{1: "one"}', "1.0"),
    ],
)
@pytest.mark.parametrize("assignment", [False, True])
def test_known_wrong_dictionary_keys_are_rejected_for_reads_and_writes(
    annotation, literal, wrong_key, assignment
):
    source = f"drink data: {annotation} = {literal}\ndata[{wrong_key}]"
    if assignment:
        source += " = " + ("2" if annotation.endswith(", Int]") else '"two"')
    assert check_ast(parsed(source))


def test_dictionary_key_checking_still_visits_key_expressions():
    errors = check_ast(
        parsed('drink data: Dict[String, Int] = {"one": 1}\ndata[missing]')
    )
    assert any(item.code == "E011" and "missing" in item.message for item in errors)


def test_any_keys_preserve_native_dictionary_equality_and_replacement():
    assert run(
        'drink data: Dict[Any, String] = {true: "boolean"}\n'
        'data[1] = "integer"\n'
        'drink result = {"size": length(data), "value": data[true]}\nresult'
    ) == {"size": 1, "value": "integer"}


def test_any_key_expression_preserves_the_gradual_dictionary_boundary():
    assert (
        run(
            'drink data: Dict[String, Int] = {"one": 1}\n'
            "drink key: Any = 2\ndata[key] = 3\ndata[key]"
        )
        == 3
    )


def test_unchecked_dictionary_access_retains_native_bool_integer_key_semantics():
    program = parsed('drink data: Dict[Int, String] = {1: "one"}\ndata[true]')
    assert check_ast(program)
    assert Interpreter().interpret(program) == "one"


@pytest.mark.parametrize("operator", ["+", "-", "*", "/", "%"])
@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("true", "false"),
        ("true", "2"),
        ("2", "false"),
        ("true", "2.0"),
        ("2.0", "false"),
    ],
)
def test_scalar_boolean_arithmetic_fails_in_checker_and_runtime(left, operator, right):
    program = parsed(f"{left} {operator} {right}")
    assert check_ast(program)
    with pytest.raises(TypeError, match="Bool"):
        Interpreter().interpret(program)


@pytest.mark.parametrize("value", ["true", "false"])
def test_scalar_boolean_unary_negation_fails_in_checker_and_runtime(value):
    program = parsed(f"-{value}")
    assert check_ast(program)
    with pytest.raises(TypeError, match="Bool"):
        Interpreter().interpret(program)


@pytest.mark.parametrize("operator", ["<", "<=", ">", ">="])
@pytest.mark.parametrize(
    ("left", "right"), [("true", "false"), ("true", "1"), ("1", "false")]
)
def test_scalar_boolean_ordering_fails_in_checker_and_runtime(left, operator, right):
    program = parsed(f"{left} {operator} {right}")
    assert check_ast(program)
    with pytest.raises(TypeError, match="Bool"):
        Interpreter().interpret(program)


@pytest.mark.parametrize("operator", ["==", "!="])
@pytest.mark.parametrize(
    "other", ["1", "1.0", '"true"', "none", "[true]", '{"value": true}']
)
@pytest.mark.parametrize("reverse", [False, True])
def test_scalar_bool_equality_rejects_non_bool_operands(operator, other, reverse):
    left, right = (other, "true") if reverse else ("true", other)
    program = parsed(f"({left}) {operator} ({right})")
    assert check_ast(program)
    with pytest.raises(TypeError, match="Bool"):
        Interpreter().interpret(program)


@pytest.mark.parametrize("left", [False, True])
@pytest.mark.parametrize("right", [False, True])
@pytest.mark.parametrize("operator", ["==", "!="])
def test_bool_equality_remains_supported(left, right, operator):
    expected = left == right if operator == "==" else left != right
    assert run(f"{str(left).lower()} {operator} {str(right).lower()}") is expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("true and false", False),
        ("false or true", True),
        ("not true", False),
        ("not 0", True),
        ('"" or "fallback"', "fallback"),
        ("1 and 2", 2),
        ("false and (true + 1)", False),
        ("true or (false / 0)", True),
    ],
)
def test_logical_operators_keep_truthiness_and_short_circuit_execution(
    source, expected
):
    # Checking still visits unreachable expressions; runtime short-circuit
    # behavior is independent of whether those expressions type-check.
    assert Interpreter().interpret(parsed(source)) == expected


@pytest.mark.parametrize("optimization", [0, 1, 2, 3])
@pytest.mark.parametrize("route", ["direct", "return", "callback", "cascade", "import"])
def test_dynamic_boolean_arithmetic_cannot_bypass_through_execution_routes(
    optimization, route, tmp_path
):
    declaration = "glass add(left, right) { return left + right }\n"
    body = {
        "direct": "add(true, 1)",
        "return": "glass wrapper() { return add(true, 1) }\nwrapper()",
        "callback": "glass apply(callback, left, right) { return callback(left, right) }\napply(add, true, 1)",
        "cascade": "cascade add(true, 1)",
        "import": 'import "arithmetic.thirsty" as arithmetic\narithmetic.add(true, 1)',
    }[route]
    if route == "import":
        (tmp_path / "arithmetic.thirsty").write_text(declaration, encoding="utf-8")
        declaration = ""
    interpreter = (
        Interpreter(opt_level=optimization)
        .attach_tarl(
            TarlRuntime(PolicyParser.parse('when action == "import" => ALLOW'))
        )
        .set_authority("type-test")
    )
    interpreter.source_directory = tmp_path
    with pytest.raises(TypeError, match="Bool"):
        run(declaration + body, interpreter)


@pytest.mark.parametrize("operator", ["+", "<", "=="])
@pytest.mark.parametrize("optimization", [0, 1, 2, 3])
def test_dynamic_operands_evaluate_once_left_to_right_before_type_validation(
    operator, optimization
):
    source = (
        "drink trace = []\n"
        'glass left() { push(trace, "left")\nreturn true }\n'
        'glass right() { push(trace, "right")\nreturn 0 }\n'
        f"left() {operator} right()"
    )
    interpreter = Interpreter(opt_level=optimization)
    with pytest.raises(TypeError, match="Bool"):
        run(source, interpreter)
    assert interpreter.env.get("trace") == ["left", "right"]


def test_dynamic_unary_operand_is_evaluated_exactly_once_before_validation():
    source = (
        "drink trace = []\n"
        'glass operand() { push(trace, "operand")\nreturn true }\n-operand()'
    )
    interpreter = Interpreter()
    with pytest.raises(TypeError, match="Bool"):
        run(source, interpreter)
    assert interpreter.env.get("trace") == ["operand"]


def test_right_operand_exception_precedes_scalar_type_validation():
    assert run(
        "drink trace = []\n"
        'glass left() { push(trace, "left")\nreturn true }\n'
        'glass right() { push(trace, "right")\nthrow "operand failed" }\n'
        "spillage { left() + right() } error (failure) { push(trace, failure) }\ntrace"
    ) == ["left", "right", "operand failed"]


def test_governance_denial_in_right_operand_is_not_replaced_or_swallowed(capsys):
    runtime = TarlRuntime(PolicyParser.parse("policy deny\nwhen true => DENY"))
    interpreter = Interpreter().attach_tarl(runtime).set_authority("tester")
    source = (
        "module test: governed\ndrink trace = []\n"
        'glass left() { push(trace, "left")\nreturn true }\n'
        'glass right() { push(trace, "right")\nprint("forbidden")\nreturn 0 }\n'
        'spillage { left() + right() } error (failure) { push(trace, "swallowed") }'
    )
    with pytest.raises(GovernanceViolation):
        run(source, interpreter)
    assert interpreter.env.get("trace") == ["left", "right"]
    assert capsys.readouterr().out == ""


def test_pure_denial_in_right_operand_precedes_scalar_type_validation(capsys):
    source = (
        "module test: pure\n"
        "glass left() { return true }\n"
        'glass right() { print("forbidden")\nreturn 0 }\nleft() + right()'
    )
    with pytest.raises(RuntimeError, match="pure"):
        run(source)
    assert capsys.readouterr().out == ""
