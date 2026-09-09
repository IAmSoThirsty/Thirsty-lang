"""Callable parameter bindings cannot silently replace each other or receivers."""

import pytest

from utf.thirsty_lang.checker import check_ast
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser


def check(source, *, method_params=None):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors and not parser.errors, (lexer.errors, parser.errors)
    if method_params is not None:
        # `this` is a source keyword; explicit-this parameters are a public AST
        # embedding convention, not additional parser syntax.
        program.stmts[0].methods[0].params = [
            (name, None) for name in method_params.split(", ") if name
        ]
    return check_ast(program)


@pytest.mark.parametrize(
    "template",
    [
        "glass take({params}) {{ return value }}",
        "glass take({params}) requires true {{ return value }}",
        "morph take({params}) {{ return value }}",
        "drink take = glass({params}) {{ return value }}",
        "fountain Box {{ glass take({params}) {{ return value }} }}",
        "fountain Box {{ glass take({params}) requires true {{ return value }} }}",
    ],
)
@pytest.mark.parametrize("params", ["value, value", "value: Int, value: String"])
def test_duplicate_parameters_report_binding_diagnostic(template, params):
    diagnostics = check(template.format(params=params))
    duplicates = [item for item in diagnostics if item.code == "E010"]
    assert len(duplicates) == 1
    assert "value" in duplicates[0].message
    assert duplicates[0].span[0] >= 1


@pytest.mark.parametrize("name", ["init", "take"])
@pytest.mark.parametrize("contract", ["", " requires true"])
@pytest.mark.parametrize("params", ["self, this", "value, this", "this, this"])
def test_method_parameters_cannot_replace_implicit_receiver(name, contract, params):
    diagnostics = check(
        f"fountain Box {{ glass {name}(){contract} {{ return this }} }}",
        method_params=params,
    )
    assert any(
        item.code == "E901" and "bound receiver" in item.message for item in diagnostics
    )


@pytest.mark.parametrize("contract", ["", " requires true"])
def test_duplicate_explicit_self_is_rejected(contract):
    diagnostics = check(
        f"fountain Box {{ glass take(self, self){contract} {{ return this }} }}"
    )
    assert any(item.code == "E010" and "self" in item.message for item in diagnostics)


@pytest.mark.parametrize(
    "params", ["", "self", "this", "self, value", "this, self", "value, self"]
)
def test_supported_method_receiver_conventions_remain_valid(params):
    assert (
        check("fountain Box { glass take() { return this } }", method_params=params)
        == []
    )


@pytest.mark.parametrize(
    "source",
    [
        "glass take(value, self) { return self }",
        "glass take(result) { return result }",
        "glass take(value) { glass inner(value) { return value }\nreturn inner(value) }",
        "drink take = glass(value) { drink inner = glass(value) { return value }\nreturn inner(value) }",
    ],
)
def test_distinct_and_nested_parameter_scopes_remain_valid(source):
    assert check(source) == []
