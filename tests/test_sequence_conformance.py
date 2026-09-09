"""Source-level conformance for sequence reads, slices, and effect boundaries."""

import pytest

from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
from utf.thirsty_lang.checker import check_ast
from utf.thirsty_lang.formatter import format_program
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
    if interpreter is None:
        interpreter = (
            Interpreter()
            .attach_tarl(
                TarlRuntime(PolicyParser.parse('when action == "import" => ALLOW'))
            )
            .set_authority("sequence-test")
        )
    return interpreter.interpret(program)


@pytest.mark.parametrize(
    ("expression", "value"),
    [
        ("[0, 1, 2, 3, 4]", [0, 1, 2, 3, 4]),
        ('"abcde"', "abcde"),
        ("c.tuple([0, 1, 2, 3, 4])", (0, 1, 2, 3, 4)),
        ("c.bytes([0, 1, 2, 3, 4])", bytes(range(5))),
    ],
)
@pytest.mark.parametrize(
    ("bounds", "selection"),
    [
        (":", slice(None)),
        ("1:", slice(1, None)),
        (":3", slice(None, 3)),
        ("1:4", slice(1, 4)),
        ("::2", slice(None, None, 2)),
        ("::-1", slice(None, None, -1)),
        ("-1:0:-2", slice(-1, 0, -2)),
        ("4:1", slice(4, 1)),
        ("1:4:-1", slice(1, 4, -1)),
        ("-999:999", slice(-999, 999)),
        ("999:-999:-1", slice(999, -999, -1)),
        ("none:none:none", slice(None, None, None)),
        ("::-999999999999999999999999", slice(None, None, -(10**24 - 1))),
    ],
)
def test_slices_preserve_sequence_kind_and_python_bound_normalization(
    expression, value, bounds, selection
):
    result = run(
        f'import "thirst::collections" as c\n'
        f"drink values = {expression}\nvalues[{bounds}]"
    )
    expected = value[selection]
    assert type(result) is type(expected)
    assert result == expected


@pytest.mark.parametrize("expression", ["[]", '""', "c.tuple()", "c.bytes()"])
def test_empty_slices_remain_empty_but_indexing_fails(expression):
    source = f'import "thirst::collections" as c\ndrink values = {expression}\n'
    assert len(run(source + "values[::-1]")) == 0
    with pytest.raises(IndexError):
        run(source + "values[-1]")


def test_unicode_indices_and_slices_count_code_points_without_normalizing():
    # The astral character is one code point; e + combining acute remain two.
    text = "A\U0001f4a7e\u0301Z"
    assert run(f'drink text = "{text}"\nlength(text)') == 5
    assert run(f'drink text = "{text}"\ntext[1]') == "\U0001f4a7"
    assert run(f'drink text = "{text}"\ntext[-2]') == "\u0301"
    assert run(f'drink text = "{text}"\ntext[1:4]') == "\U0001f4a7e\u0301"
    assert run(f'drink text = "{text}"\ntext[::-1]') == "Z\u0301e\U0001f4a7A"


def test_list_slicing_copies_structure_and_preserves_nested_aliases():
    result = run(
        "drink original = [[1], [2], [3]]\n"
        "drink selected = original[0:2]\n"
        "selected[0][0] = 9\n"
        "selected[1] = [8];\n"
        "[original, selected]"
    )
    assert result == [[[9], [2], [3]], [[9], [8]]]
    assert result[0] is not result[1]
    assert result[0][0] is result[1][0]


def test_nested_container_slice_type_survives_subscript_chains():
    assert (
        run(
            "drink rows: Dict[String, Reservoir[Reservoir[Int]]] = "
            '{"values": [[1, 2], [3, 4]]}\n'
            'drink selected: Reservoir[Reservoir[Int]] = rows["values"][::-1]\n'
            "drink result: Int = selected[:1][0][1]\nresult"
        )
        == 4
    )


@pytest.mark.parametrize(
    "source",
    [
        "drink selected: String = [1, 2][:]",
        "drink selected: Reservoir[String] = [1, 2][:]",
        'drink selected: Int = "water"[:]',
        'drink selected: Int = "water"[:][0]',
        "drink selected: String = [[1, 2]][:][0][1]",
    ],
)
def test_known_slice_and_index_results_cannot_hide_type_mismatches(source):
    assert any(item.code == "E021" for item in check_ast(parsed(source)))


@pytest.mark.parametrize(
    "source",
    [
        'drink values: Reservoir[Int] = [1, "wrong"][:]',
        'drink values: Reservoir[Int] = [1, "wrong"][:][:]',
        'drink values: Reservoir[Reservoir[Int]] = [[1], ["wrong"]][:]',
        'glass values() -> Reservoir[Int] { return [1, "wrong"][:] }',
        'glass take(values: Reservoir[Int]) { return 0 }\ntake([1, "wrong"][:])',
        # Checking validates the source literal; it does not execute bounds to
        # prove that a particular heterogeneous element was excluded.
        'drink values: Reservoir[Int] = [1, "wrong"][:1]',
    ],
)
def test_slicing_cannot_hide_known_heterogeneous_literals_behind_any(source):
    assert any(item.code == "E021" for item in check_ast(parsed(source)))


@pytest.mark.parametrize("bound", ["true", "false", "1.5", '"1"', "[1]"])
@pytest.mark.parametrize("position", [0, 1, 2])
def test_known_invalid_bounds_are_checked_and_runtime_rejects_them(bound, position):
    bounds = ["none", "none", "none"]
    bounds[position] = bound
    program = parsed(f"[0, 1, 2][{':'.join(bounds)}]")
    assert check_ast(program)
    with pytest.raises(TypeError):
        Interpreter().interpret(program)


@pytest.mark.parametrize("bound", ["true", "1.5", '"1"', "none"])
@pytest.mark.parametrize("assignment", [False, True])
def test_index_type_contract_matches_for_reads_and_writes(bound, assignment):
    source = f"drink values: Reservoir[Int] = [1, 2]\nvalues[{bound}]"
    if assignment:
        source += " = 9"
    program = parsed(source)
    assert check_ast(program)
    with pytest.raises(TypeError):
        Interpreter().interpret(program)


def test_slice_checker_visits_every_invalid_subexpression():
    errors = check_ast(parsed("[0, 1][missing_start:missing_stop:missing_step]"))
    missing = [item for item in errors if item.code == "E011"]
    assert len(missing) == 3
    for name in ("missing_start", "missing_stop", "missing_step"):
        assert any(name in item.message for item in missing)


@pytest.mark.parametrize("step", ["0", "1 - 1"])
def test_zero_step_fails_explicitly(step):
    with pytest.raises(ValueError, match="zero"):
        Interpreter().interpret(parsed(f"[0, 1, 2][::{step}]"))


@pytest.mark.parametrize("expression", ['{"a": 1}', "42", "true", "none"])
def test_non_sequence_slicing_is_rejected_statically_and_at_runtime(expression):
    program = parsed(f"({expression})[:]")
    assert check_ast(program)
    with pytest.raises(TypeError):
        Interpreter().interpret(program)


def test_slice_operands_evaluate_once_in_source_order():
    assert run(
        "drink trace = []\n"
        'glass object() { push(trace, "object")\nreturn [0, 1, 2, 3] }\n'
        'glass start() -> Int { push(trace, "start")\nreturn 1 }\n'
        'glass stop() -> Int { push(trace, "stop")\nreturn 4 }\n'
        'glass step() -> Int { push(trace, "step")\nreturn 2 }\n'
        "drink selected = object()[start():stop():step()];\n"
        "[selected, trace]"
    ) == [[1, 3], ["object", "start", "stop", "step"]]


def test_bound_exception_aborts_later_bounds():
    assert run(
        "drink trace = []\n"
        'glass start() { push(trace, "start")\nthrow "stop now" }\n'
        'glass stop() { push(trace, "stop")\nreturn 3 }\n'
        'glass step() { push(trace, "step")\nreturn 1 }\n'
        "spillage { [0, 1, 2][start():stop():step()] } error (failure) {\n"
        "push(trace, failure)\n}\ntrace"
    ) == ["start", "stop now"]


def test_invalid_bound_value_is_validated_after_all_bounds_are_evaluated():
    program = parsed(
        "drink trace = []\n"
        'glass start() -> Bool { push(trace, "start")\nreturn true }\n'
        'glass stop() -> Int { push(trace, "stop")\nreturn 3 }\n'
        'glass step() -> Int { push(trace, "step")\nreturn 1 }\n'
        "[0, 1, 2][start():stop():step()]"
    )
    assert check_ast(program)
    interpreter = Interpreter()
    with pytest.raises(TypeError):
        interpreter.interpret(program)
    assert interpreter.env.get("trace") == ["start", "stop", "step"]


def test_operand_returning_logical_operators_are_valid_integer_bounds():
    assert run("[0, 1, 2, 3][(0 or 1):(1 and 3)]") == [1, 2]


@pytest.mark.parametrize("expression", ["[0, 1][1 / 1]", "[0, 1][:1 / 1]"])
def test_division_results_are_floating_point_bounds_even_for_whole_values(expression):
    program = parsed(expression)
    assert check_ast(program)
    with pytest.raises(TypeError):
        Interpreter().interpret(program)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("1 + 2.0", 3.0),
        ("2.0 + 1", 3.0),
        ("1 - 2.0", -1.0),
        ("2.0 - 1", 1.0),
        ("2 * 3.0", 6.0),
        ("3.0 * 2", 6.0),
        ("5 / 2.0", 2.5),
        ("5.0 / 2", 2.5),
        ("5 % 2.0", 1.0),
        ("5.0 % 2", 1.0),
        ("24 / (6 / 2)", 8.0),
    ],
)
def test_mixed_numeric_orders_match_annotated_float_results(expression, expected):
    result = run(f"drink result: Float = {expression}\nresult")
    assert type(result) is float
    assert result == expected


@pytest.mark.parametrize(
    ("operator", "expected"),
    [
        ("<", True),
        ("<=", True),
        (">", False),
        (">=", False),
        ("==", False),
        ("!=", True),
    ],
)
@pytest.mark.parametrize(("left", "right"), [("1", "2.0"), ("1.0", "2")])
def test_mixed_numeric_comparisons_are_symmetric_in_operand_types(
    left, operator, right, expected
):
    result = run(f"drink result: Bool = {left} {operator} {right}\nresult")
    assert result is expected


@pytest.mark.parametrize("bounds", ["bound():", ":bound()", "::bound()"])
def test_annotated_division_function_cannot_supply_a_float_slice_bound(bounds):
    program = parsed(
        "glass bound() -> Float { return 24 / (6 / 2) }\n" f"[0, 1, 2][{bounds}]"
    )
    errors = check_ast(program)
    assert errors and all(item.code != "E022" for item in errors)
    with pytest.raises(TypeError):
        Interpreter().interpret(program)


def test_negative_index_assignment_preserves_rhs_object_index_order():
    assert run(
        "drink values = [1, 2]\ndrink trace = []\n"
        'glass value() { push(trace, "value")\nreturn 9 }\n'
        'glass object() { push(trace, "object")\nreturn values }\n'
        'glass index() { push(trace, "index")\nreturn -2 }\n'
        "object()[index()] = value();\n[values, trace]"
    ) == [[9, 2], ["value", "object", "index"]]


@pytest.mark.parametrize("index", [-4, 3])
@pytest.mark.parametrize("assignment", [False, True])
def test_scalar_indices_do_not_clip_like_slices(index, assignment):
    source = f"drink values = [1, 2, 3]\nvalues[{index}]"
    if assignment:
        source += " = 9"
    with pytest.raises(IndexError):
        run(source)


def test_slice_assignment_source_is_rejected_before_execution(capsys):
    lexer = Lexer('print("forbidden")\ndrink values = [0, 1, 2]\nvalues[1:2] = [9]')
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors
    assert parser.errors and program.parse_failed
    assert any("slice" in item.message.lower() for item in parser.errors)
    with pytest.raises(GovernanceViolation, match="parse"):
        Interpreter().interpret(program)
    assert capsys.readouterr().out == ""


def test_direct_slice_assignment_ast_rejects_before_any_operand_effect(capsys):
    from utf.thirsty_lang.ast import AssignStmt

    program = parsed(
        'glass receiver() { print("receiver")\nreturn [0, 1, 2] }\n'
        'glass bound() { print("bound")\nreturn 1 }\n'
        'glass replacement() { print("replacement")\nreturn [9] }\n'
        "receiver()[bound():]"
    )
    target = program.stmts[-1].expr
    program.stmts[-1] = AssignStmt(
        target=target,
        value=parsed("replacement()").stmts[0].expr,
        span=target.span,
    )
    assert check_ast(program)
    with pytest.raises(NotImplementedError, match="slice"):
        Interpreter().interpret(program)
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("mode", ["core", "governed"])
@pytest.mark.parametrize("tail", ["[1:2:3:4]", "[1:2", "[]", "[:,]", "[1:2,3]"])
def test_malformed_slice_diagnostics_prevent_recovered_execution(mode, tail, capsys):
    source = f'module broken: {mode}\nprint("forbidden")\n[0, 1, 2]{tail}'
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert lexer.errors == []
    assert parser.errors
    assert program.parse_failed
    assert all(item.span[0] >= 3 and item.span[1] > 0 for item in parser.errors)
    with pytest.raises((RuntimeError, GovernanceViolation), match="parse"):
        Interpreter().interpret(program)
    assert capsys.readouterr().out == ""


def test_slice_and_chained_subscript_spans_include_their_closing_brackets():
    from utf.thirsty_lang.ast import SliceExpr, Subscript

    prefix = "values[1:2:1]"
    expression = prefix + "[0]"
    program = parsed("drink values = [0, 1, 2]\n" + expression)
    outer = program.stmts[-1].expr
    assert isinstance(outer, Subscript)
    assert isinstance(outer.obj, SliceExpr)
    assert outer.span == (2, 1, 2, len(expression) + 1)
    assert outer.obj.span == (2, 1, 2, len(prefix) + 1)
    assert outer.obj.start.span == (2, 8, 2, 9)
    assert outer.obj.stop.span == (2, 10, 2, 11)
    assert outer.obj.step.span == (2, 12, 2, 13)


def test_multiline_negative_index_span_starts_at_the_minus_operator():
    from utf.thirsty_lang.ast import UnaryOp

    source = "drink values = [0, 1, 2]\n\nvalues[\n    -2\n]"
    program = parsed(source)
    index = program.stmts[-1].expr.index
    assert isinstance(index, UnaryOp)
    assert index.span == (4, 5, 4, 7)
    assert index.operand.span == (4, 6, 4, 7)
    assert run(source) == 1


def test_multiline_negative_slice_bounds_keep_their_individual_source_spans():
    from utf.thirsty_lang.ast import UnaryOp

    source = "drink values = [0, 1, 2]\n\nvalues[\n    -1:\n    -4:\n    -1\n]"
    program = parsed(source)
    expression = program.stmts[-1].expr
    assert expression.span == (3, 1, 7, 2)
    for line, bound in zip(
        (4, 5, 6), (expression.start, expression.stop, expression.step), strict=True
    ):
        assert isinstance(bound, UnaryOp)
        assert bound.span == (line, 5, line, 7)
        assert bound.operand.span == (line, 6, line, 7)
    assert run(source) == [2, 1, 0]


@pytest.mark.parametrize("suffix", ["]", ":]"])
def test_multiline_not_bound_diagnostic_covers_operator_and_operand(suffix):
    source = "drink values = [0, 1, 2]\n\nvalues[\n    not\n        true\n" + suffix
    program = parsed(source)
    expression = program.stmts[-1].expr
    bound = expression.index if suffix == "]" else expression.start
    assert bound.span == (4, 5, 5, 13)
    assert bound.operand.span == (5, 9, 5, 13)
    errors = check_ast(program)
    assert len(errors) == 1
    assert errors[0].code == "E901"
    assert errors[0].span == bound.span


def test_each_invalid_not_slice_bound_diagnostic_points_to_its_own_line():
    program = parsed(
        "drink values = [0, 1, 2]\n\n"
        "values[\n    not true:\n    not false:\n    not true\n]"
    )
    expected = [(4, 5, 4, 13), (5, 5, 5, 14), (6, 5, 6, 13)]
    expression = program.stmts[-1].expr
    assert [
        bound.span for bound in (expression.start, expression.stop, expression.step)
    ] == expected
    errors = check_ast(program)
    assert len(errors) == 3
    assert all(item.code == "E901" for item in errors)
    assert [item.span for item in errors] == expected


@pytest.mark.parametrize("suffix", ["]", ":]"])
def test_negative_float_bound_diagnostic_includes_minus_operator(suffix):
    program = parsed("drink values = [0, 1, 2]\n\nvalues[\n    -1.5\n" + suffix)
    errors = check_ast(program)
    assert len(errors) == 1
    assert errors[0].code == "E901"
    assert errors[0].span == (4, 5, 4, 9)


@pytest.mark.parametrize(
    "source",
    [
        "([1, 2, 3] + [4, 5])[::-1][1:4]",
        "[0, 1, 2, 3, 4][1 + 1:5 - 1:2 - 1]",
        "[0, 1, 2][none:none:none]",
        '"A\U0001f4a7e\u0301Z"[1:4][::-1]',
        'drink rows = {"items": [[1, 2], [3, 4]]}\nrows["items"][::-1][0][:1]',
        "glass choose() { return [0, 1, 2, 3] }\nchoose()[1:][::2]",
    ],
)
def test_formatter_round_trip_preserves_slice_grouping_and_execution(source):
    formatted = format_program(parsed(source))
    assert run(formatted) == run(source)
    assert format_program(parsed(formatted)) == formatted


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("drink previous = [1, 2, 3];\n[9, 8][:1][0]", 9),
        ("drink previous = 2;\nprevious;\n[9, 8][1:][0]", 8),
        ("drink previous = 1;\n(2 + 3) * 4", 20),
        ("drink previous = 2;\n-1", -1),
        (
            "glass select() -> Int {\n"
            "drink previous = [1, 2, 3];\n[9, 8][:1][0];\n"
            "return previous[0]\n}\nselect()",
            1,
        ),
        (
            "glass select() -> Int {\n"
            "drink previous = 1;\n(2 + 3) * 4;\n"
            "return previous\n}\nselect()",
            1,
        ),
        (
            "glass select() -> Int {\n"
            "drink previous = 2;\n-1;\n"
            "return previous\n}\nselect()",
            2,
        ),
    ],
)
def test_formatter_keeps_statement_boundary_before_array_or_parenthesized_expression(
    source, expected
):
    assert run(source) == expected
    formatted = format_program(parsed(source))
    assert run(formatted) == expected
    assert format_program(parsed(formatted)) == formatted


@pytest.mark.parametrize("position", [0, 1, 2])
def test_pure_slice_bound_cannot_hide_an_imported_effect(position, tmp_path, capsys):
    (tmp_path / "bounds.thirsty").write_text(
        'glass value() -> Int { print("forbidden")\nreturn 1 }', encoding="utf-8"
    )
    bounds = ["none", "none", "none"]
    bounds[position] = "bounds.value()"
    interpreter = (
        Interpreter()
        .attach_tarl(
            TarlRuntime(PolicyParser.parse('when action == "import" => ALLOW'))
        )
        .set_authority("sequence-test")
    )
    interpreter.source_directory = tmp_path
    source = (
        'module test: pure\nimport "bounds.thirsty" as bounds\n'
        f"[0, 1, 2][{':'.join(bounds)}]"
    )
    with pytest.raises(RuntimeError, match="pure"):
        run(source, interpreter)
    assert capsys.readouterr().out == ""


def test_exported_pure_slicing_function_retains_callback_restrictions(capsys):
    pure = Interpreter()
    run(
        "module library: pure\n"
        "glass select(callback) { return [0, 1, 2][callback():] }",
        pure,
    )
    core = Interpreter()
    run('glass start() { print("forbidden")\nreturn 1 }', core)
    with pytest.raises(RuntimeError, match="pure"):
        pure.env.get("select")(core.env.get("start"))
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("position", [0, 1, 2])
def test_governed_slice_bound_denial_aborts_before_later_effects(
    position, tmp_path, capsys
):
    (tmp_path / "bounds.thirsty").write_text(
        'glass value() { print("forbidden")\nreturn 1 }', encoding="utf-8"
    )
    runtime = TarlRuntime(
        PolicyParser.parse(
            'policy bounds\nwhen action == "import" => ALLOW\nwhen true => DENY'
        )
    )
    interpreter = Interpreter().attach_tarl(runtime).set_authority("tester")
    interpreter.source_directory = tmp_path
    bounds = ["none", "none", "none"]
    bounds[position] = "bounds.value()"
    for later in range(position + 1, len(bounds)):
        bounds[later] = "later()"
    source = (
        'module test: governed\nimport "bounds.thirsty" as bounds\n'
        'drink trace = []\nglass later() { push(trace, "later")\nreturn 1 }\n'
        f"[0, 1, 2][{':'.join(bounds)}]"
    )
    with pytest.raises(GovernanceViolation):
        run(source, interpreter)
    assert capsys.readouterr().out == ""
    assert interpreter.env.get("trace") == []


def test_governed_function_contract_still_gates_imported_slice_bounds(tmp_path):
    (tmp_path / "bounds.thirsty").write_text(
        "drink trace = [0]\n" "glass value() requires true { trace[0] = 1\nreturn 1 }",
        encoding="utf-8",
    )
    runtime = TarlRuntime(
        PolicyParser.parse(
            'policy bounds\nwhen action == "import" => ALLOW\nwhen true => DENY'
        )
    )
    interpreter = Interpreter().attach_tarl(runtime).set_authority("tester")
    interpreter.source_directory = tmp_path
    with pytest.raises(GovernanceViolation):
        run(
            'module test: governed\nimport "bounds.thirsty" as bounds\n'
            "[0, 1, 2][bounds.value():]",
            interpreter,
        )
    assert interpreter.env.get("bounds")["trace"] == [0]


def test_imported_slice_function_observes_live_authority_revocation(tmp_path, capsys):
    (tmp_path / "bounds.thirsty").write_text(
        'glass bound() { print("authorized")\nreturn 1 }\n'
        "glass select() { return [0, 1, 2][bound():] }",
        encoding="utf-8",
    )
    runtime = TarlRuntime(
        PolicyParser.parse(
            'policy bounds\nwhen action == "import" => ALLOW\n'
            'when action == "write" => ALLOW\nwhen true => DENY'
        )
    )
    interpreter = Interpreter().attach_tarl(runtime).set_authority("tester")
    interpreter.source_directory = tmp_path
    run('module test: governed\nimport "bounds.thirsty" as bounds', interpreter)
    select = interpreter.env.get("bounds")["select"]
    assert select() == [1, 2]
    assert capsys.readouterr().out == "authorized\n"
    interpreter.set_authority(None)
    with pytest.raises(GovernanceViolation):
        select()
    assert capsys.readouterr().out == ""
