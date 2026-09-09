"""Malformed source stays non-executable through copied tokens and tool APIs."""

from dataclasses import replace

import pytest

from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
from utf.thirsty_lang import cli, formatter
from utf.thirsty_lang.checker import check_ast
from utf.thirsty_lang.interpreter import GovernanceViolation, Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser
from utf.thirsty_lang.token import Token, TokenType

HEADERS = ("", "core", "governed", "strict", "pure")
LEXICAL_FAILURES = (
    pytest.param("@", "E001", id="invalid-character"),
    pytest.param("!", "E001", id="invalid-negation"),
    pytest.param('"unterminated', "E002", id="unterminated-string"),
    pytest.param('"unterminated' + "\\", "E002", id="trailing-backslash"),
    pytest.param("/* outer /* inner */", "E003", id="unterminated-comment"),
)


def source_with(mode, body):
    return (f"module sample: {mode}\n" if mode else "") + body


@pytest.mark.parametrize("mode", HEADERS)
@pytest.mark.parametrize("suffix,code", LEXICAL_FAILURES)
@pytest.mark.parametrize("copy_kind", ["original", "list", "slice", "replace-eof"])
def test_lexical_failures_survive_token_copies(mode, suffix, code, copy_kind):
    lexer = Lexer(source_with(mode, f"drink value = 1\n{suffix}"))
    tokens = lexer.lex()
    expected = tuple(lexer.errors)
    assert expected and expected[0].code == code
    assert tokens[-1].type == TokenType.EOF
    assert tokens[-1].lexical_errors == expected
    if copy_kind == "list":
        tokens = list(tokens)
    elif copy_kind == "slice":
        tokens = tokens[:]
    elif copy_kind == "replace-eof":
        tokens = tokens[:-1] + [replace(tokens[-1])]
    # Parser ownership must not depend on the lexer's mutable diagnostic list.
    lexer.errors.clear()
    parser = Parser(tokens)
    program = parser.parse()
    assert program.parse_failed
    assert all(error in parser.errors for error in expected)
    assert parser.errors[0].span == expected[0].span


@pytest.mark.parametrize("mode", HEADERS)
@pytest.mark.parametrize("suffix,code", LEXICAL_FAILURES)
@pytest.mark.parametrize("posture", ["default", "permissive-policy", "compatibility"])
def test_lexical_failure_prevents_recovered_execution(mode, suffix, code, posture):
    parser = Parser(Lexer(source_with(mode, f"mark()\n{suffix}")).lex())
    program = parser.parse()
    assert any(error.code == code for error in parser.errors)
    effects = []
    if posture == "compatibility":
        runner = Interpreter(allow_ungoverned=True)
    else:
        runner = Interpreter()
    if posture == "permissive-policy":
        runner.attach_tarl(TarlRuntime(PolicyParser.parse("when true => ALLOW")))
        runner.set_authority("operator")
    runner.env.define("mark", lambda: effects.append("executed"))
    with pytest.raises((GovernanceViolation, RuntimeError), match="failed to parse"):
        runner.interpret(program)
    assert effects == []


@pytest.mark.parametrize("mode", ["wrong", "CORE", "unknown", "42", ""])
def test_unknown_or_missing_header_mode_is_an_explicit_error(mode):
    parser = Parser(Lexer(f"module sample: {mode}\ndrink value = 1").lex())
    program = parser.parse()
    assert program.parse_failed
    assert any(
        error.code == "E901" and "Expected mode" in error.message
        for error in parser.errors
    )


@pytest.mark.parametrize("mode", HEADERS)
@pytest.mark.parametrize("suffix,code", LEXICAL_FAILURES)
def test_failed_ast_cannot_be_checked_formatted_or_compiled(mode, suffix, code):
    program = Parser(
        Lexer(source_with(mode, f"drink value = 1\n{suffix}")).lex()
    ).parse()
    assert program.parse_failed
    assert any(error.code == "E901" for error in check_ast(program))
    for format_program in (formatter.format_program, formatter.format):
        with pytest.raises(ValueError, match="malformed|failed to parse"):
            format_program(program)
    for compile_program in (cli._transpile_to_js, cli._transpile_to_llvm_ir):
        with pytest.raises(ValueError, match="malformed"):
            compile_program(program)


@pytest.mark.parametrize("suffix,code", LEXICAL_FAILURES)
def test_file_check_reports_lexical_failure(tmp_path, suffix, code):
    source = tmp_path / "bad.thirsty"
    source.write_text(f"drink value = 1\n{suffix}", encoding="utf-8")
    program, diagnostics, _ = cli._lex_parse_check(str(source))
    assert program.parse_failed
    assert any(error.code == code for error in diagnostics)


def test_valid_token_contract_and_known_modes_remain_unchanged():
    original = Token(TokenType.INT, "1", 2, 3)
    assert original.lexical_errors == ()
    assert repr(original) == "Token(INT, '1', L2:3)"
    tokens = Lexer("1").lex()
    assert tokens == [Token(TokenType.INT, "1"), Token(TokenType.EOF, "", 1, 2)]
    for mode in HEADERS:
        parser = Parser(Lexer(source_with(mode, "drink value = 1")).lex())
        program = parser.parse()
        assert not parser.errors
        assert not program.parse_failed
        if mode:
            assert program.header.mode == mode


def test_unknown_escape_retains_existing_literal_semantics():
    lexer = Lexer(r'"\q"')
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors and not parser.errors
    assert not program.parse_failed
    assert Interpreter().interpret(program) == "q"
