"""Run the portable collection corpus against an installed Thirsty-Lang interpreter."""

import unittest
from pathlib import Path

from utf.thirsty_lang.checker import Checker
from utf.thirsty_lang.interpreter import Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser


class PortableCollectionTests(unittest.TestCase):
    def load_case(self, name):
        source = Path(__file__).with_name(f"list-alias-{name}.thirsty")
        lexer = Lexer(source.read_text(encoding="utf-8"))
        parser = Parser(lexer.lex())
        program = parser.parse()
        self.assertEqual(lexer.errors, [])
        self.assertEqual(parser.errors, [])
        return program, Checker().check_all(program)

    def test_valid_alias(self):
        program, diagnostics = self.load_case("valid")
        self.assertEqual(diagnostics, [])
        with Interpreter() as machine:
            machine.interpret(program)
            self.assertEqual(machine.env.get("main"), 2)
            self.assertEqual(machine.env.get("rows"), [2])
            self.assertIs(machine.env.get("rows"), machine.env.get("alias"))

    def test_static_rejection(self):
        _, diagnostics = self.load_case("invalid")
        self.assertEqual(
            [(error.code, error.span[:2]) for error in diagnostics],
            [("E021", (4, 1))],
        )

    def test_dynamic_rejection(self):
        program, diagnostics = self.load_case("dynamic")
        self.assertEqual(diagnostics, [])
        with Interpreter() as machine:
            with self.assertRaisesRegex(TypeError, "requires Int"):
                machine.interpret(program)
            self.assertEqual(machine.env.get("rows"), [1])
            self.assertIs(machine.env.get("rows"), machine.env.get("alias"))


if __name__ == "__main__":
    unittest.main()
