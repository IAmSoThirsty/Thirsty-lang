"""Executable general-purpose data operations and formatting contracts."""

import pytest

from utf.thirsty_lang.checker import check_ast
from utf.thirsty_lang.formatter import format_program
from utf.thirsty_lang.interpreter import Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser
from utf.thirsty_lang.typesys import (
    DictType,
    IntType,
    StringType,
    is_assignable,
    type_from_name,
)


def parse(source):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    ast = parser.parse()
    assert not lexer.errors, lexer.errors
    assert not parser.errors, parser.errors
    return ast


def run(source):
    ast = parse(source)
    assert check_ast(ast) == []
    return Interpreter().interpret(ast)


def test_dictionary_literals_support_nested_values_and_assignment():
    assert (
        run(
            'drink data = {"answer": 42, "nested": {"values": [1, 2]},}\ndata["answer"] = 43\ndata["nested"]["values"][1] + data["answer"]'
        )
        == 45
    )


def test_dictionary_empty_and_iteration_order():
    assert run(
        'drink no_entries = {}\ndrink data = {"first": 1, "second": 2}\ndrink keys = []\nfor key in data { push(keys, key) }\nkeys'
    ) == ["first", "second"]


def test_dictionary_computed_keys_evaluate_in_order():
    assert (
        run(
            "drink mut n = 0\nglass next() { n = n + 1\nreturn n }\ndrink data = {next(): next(), next(): next()}\ndata[1] + data[3]"
        )
        == 6
    )


@pytest.mark.parametrize(
    "source",
    [
        'drink data = {"key": 1, "key": 2}',
        "drink data = {1: 1, true: 2}",
        "drink data = {none: 1, none: 2}",
    ],
)
def test_dictionary_literal_duplicate_keys_report_and_refuse(source):
    ast = parse(source)
    assert any("duplicate dictionary key" in item.message for item in check_ast(ast))
    with pytest.raises(ValueError, match="duplicate dictionary key"):
        Interpreter().interpret(ast)


def test_dynamic_duplicate_key_does_not_evaluate_replacement():
    interpreter = Interpreter()
    ast = parse(
        'drink key = "same"\ndrink mut effects = 0\nglass effect() { effects = effects + 1\nreturn effects }\ndrink data = {key: 1, "same": effect()}'
    )
    with pytest.raises(ValueError, match="duplicate dictionary key"):
        interpreter.interpret(ast)
    assert interpreter.env.get("effects") == 0


def test_dictionary_rejects_unhashable_key():
    with pytest.raises(TypeError, match="unhashable"):
        Interpreter().interpret(parse("drink data = {[1]: 2}"))


def test_dictionary_missing_subscript_is_explicit():
    with pytest.raises(KeyError):
        run('drink data = {}\ndata["missing"]')


def test_dictionary_checker_visits_every_key_and_value():
    errors = check_ast(parse('drink data = {"ok": 1, missing_key: missing_value}'))
    assert any("missing_key" in item.message for item in errors)
    assert any("missing_value" in item.message for item in errors)


@pytest.mark.parametrize(
    "source",
    [
        'drink data = {"quoted\\"key": [1, {"nested": 2}]}\ndata["quoted\\"key"][1]["nested"]',
        '({"key": 1})',
    ],
)
def test_dictionary_formatter_round_trip_preserves_program(source):
    ast = parse(source)
    formatted = format_program(ast)
    assert run(formatted) == run(source)


def test_dictionary_nested_generic_annotation_is_accepted():
    assert (
        run(
            'drink data: Dict[String, Reservoir[Int]] = {"values": [1, 2]}\ndata["values"][0]'
        )
        == 1
    )


@pytest.mark.parametrize(
    "source",
    [
        'drink values: Reservoir[Int] = [1, "wrong"]',
        'drink data: Dict[String, Int] = {"ok": 1, "bad": "wrong"}',
        'drink data: Dict[String, Reservoir[Int]] = {"values": [1, "wrong"]}',
        'glass check(values: Reservoir[Int]) { return 1 }\ncheck([1, "wrong"])',
        'glass values() -> Reservoir[Int] { return [1, "wrong"] }',
    ],
)
def test_heterogeneous_literal_does_not_hide_known_invalid_typed_element(source):
    assert any(item.code == "E021" for item in check_ast(parse(source)))


def test_dict_types_preserve_key_and_value_arguments():
    actual = type_from_name("Dict[String, Int]")
    assert isinstance(actual, DictType)
    assert isinstance(actual.key_type, StringType)
    assert isinstance(actual.value_type, IntType)
    assert not is_assignable(actual, type_from_name("Dict[Int, String]"))


def test_struct_annotation_and_assignment_are_checked():
    source = 'struct Point { x: Int }\ndrink point = new Point(1)\npoint.x = "wrong"'
    assert any(item.code == "E021" for item in check_ast(parse(source)))


def test_struct_nominal_annotations_are_distinct():
    source = "enum A { Value }\nenum B { Value }\ndrink value: A = B.Value"
    assert any(item.code == "E021" for item in check_ast(parse(source)))


def test_direct_struct_constructor_is_checked():
    source = 'struct Point { x: Int }\ndrink point = Point("wrong")'
    assert any(item.code == "E021" for item in check_ast(parse(source)))


def test_tuple_and_bytes_are_indexable_and_immutable():
    interpreter = Interpreter()
    interpreter.env.define("sequence", (2, 3))
    interpreter.env.define("octets", b"AB")
    assert interpreter.interpret(parse("sequence[1] + octets[0]")) == 68
    with pytest.raises(TypeError, match="index-assign"):
        interpreter.interpret(parse("sequence[0] = 4"))


@pytest.mark.parametrize("index", ["true", "1.5"])
def test_immutable_sequence_indices_require_integer(index):
    interpreter = Interpreter()
    interpreter.env.define("sequence", (2, 3))
    with pytest.raises(TypeError, match="Int"):
        interpreter.interpret(parse(f"sequence[{index}]"))


@pytest.mark.parametrize(
    "source", ["enum State { Open, Open }", "struct Point { x: Int\nx: Int }"]
)
def test_duplicate_nominal_members_are_rejected(source):
    ast = parse(source)
    assert check_ast(ast)
    with pytest.raises(TypeError, match="duplicate"):
        Interpreter().interpret(ast)


def test_nested_generic_struct_fields_validate_contents():
    source = 'struct Report { values: Dict[String, Reservoir[Int]] }\ndrink report = new Report({"counts": [1, 2]})\nreport.values["counts"][0]'
    assert run(source) == 1
    with pytest.raises(TypeError, match="requires Dict"):
        Interpreter().interpret(parse(source.replace("[1, 2]", '[1, "wrong"]')))


def test_imported_struct_field_types_use_declaration_scope(tmp_path):
    from utf.tarl.core import PolicyParser
    from utf.tarl.runtime import TarlRuntime

    (tmp_path / "record.thirsty").write_text(
        "enum Color { Red }\nstruct Paint { color: Color }\nglass make() { return new Paint(Color.Red) }",
        encoding="utf-8",
    )
    interpreter = (
        Interpreter()
        .attach_tarl(
            TarlRuntime(PolicyParser.parse('when action == "import" => ALLOW'))
        )
        .set_authority("type-test")
    )
    interpreter.source_directory = tmp_path
    result = interpreter.interpret(
        parse(
            'import "record.thirsty" as records\ndrink paint = records.make()\npaint.color = records.Color.Red\npaint.color == records.Color.Red'
        )
    )
    assert result is True


@pytest.mark.parametrize(
    "source",
    [
        "drink mut value = 1\nglass add(x: Int) -> Int { return x + 1 }\nvalue = add(value)\nvalue",
        "enum Color { Red, Blue }\nstruct Paint { color: Color }\ndrink paint = new Paint(Color.Red)\npaint.color == Color.Red",
        "drink mut total = 0\nrefill (n in [1, 2]) { total = total + n }\nrefill (total < 4) { total = total + 1 }\nthirsty (total > 4) { total = 10 } hydrated thirsty (total == 4) { total = 20 }\ntotal",
        'drink mut message = ""\nspillage { throw "handled" } error (failure) { message = failure }\nmessage',
        "drink value = none\nvalue",
        "drink value = quenched(2)\ncondense value",
        "glass double(x) { return x * 2 }\n2 | double",
        "1 - (2 - 3)",
        "24 / (6 / 2)",
        "(true or false) and false",
        "not (true and false)",
        "-(2 + 3)",
    ],
)
def test_formatter_preserves_supported_language_execution(source):
    assert run(format_program(parse(source))) == run(source)


@pytest.mark.parametrize(
    "source",
    [
        "interface Shape { area() -> Float; scale(amount: Int) -> Int }",
        "defend protection(rules) { alpha; beta }",
        'drink mut response = ""\nsip response',
    ],
)
def test_formatter_preserves_supported_parse_forms(source):
    formatted = format_program(parse(source))
    assert not parse(formatted).parse_failed
