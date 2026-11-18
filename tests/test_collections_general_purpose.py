"""Ordinary container behavior and a complete Thirsty-Lang data application."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from utf.thirsty_lang import module_system as ms
from utf.thirsty_lang.checker import check_ast
from utf.thirsty_lang.interpreter import Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "src/utf/examples/data_report/main.thirsty"


def collections():
    return ms.STDLIB_MODULES["thirst::collections"]()


def test_dictionary_construction_order_copies_and_conflict_handling():
    c = collections()
    original = c["dict"]([["b", 2], ["a", 1]])
    assert c["keys"](original) == ["b", "a"]
    assert c["values"](original) == [2, 1]
    assert c["items"](original) == [("b", 2), ("a", 1)]
    assert c["has"](original, "a") and not c["has"](original, "missing")
    assert c["with_item"](original, "c", 3) == {"b": 2, "a": 1, "c": 3}
    assert original == {"b": 2, "a": 1}
    assert c["merge"](original, {"c": 3}) == {"b": 2, "a": 1, "c": 3}
    with pytest.raises(ValueError, match="Duplicate"):
        c["merge"](original, {"a": 9})
    assert c["merge"](original, {"a": 9}, True) == {"b": 2, "a": 9}
    with pytest.raises(TypeError):
        c["merge"]({}, {}, 1)
    with pytest.raises(TypeError):
        c["keys"]([])
    for invalid in ([1], [["key"]], [["key", 1, 2]], [["a", 1], ["a", 2]]):
        with pytest.raises(ValueError):
            c["dict"](invalid)


def test_ordered_immutable_set_semantics_and_operations():
    c = collections()
    left, right = c["set"]([3, 1, 3, 2]), c["set"]([2, 4])
    assert c["to_list"](left) == [3, 1, 2]
    assert left == c["set"]([2, 1, 3])
    assert left != c["set"]([1])
    assert 3 in left and 7 not in left and len(left) == 3
    assert c["to_list"](c["set_union"](left, right)) == [3, 1, 2, 4]
    assert c["to_list"](c["set_intersection"](left, right)) == [2]
    assert c["to_list"](c["set_difference"](left, right)) == [3, 1]
    nested = c["set"]([c["tuple"]([1, "x"]), left, left])
    assert len(nested) == 2
    assert repr(left) == "set([3, 1, 2])"
    with pytest.raises(TypeError):
        c["set_union"](left, [1])
    for invalid in ([[1]], [{}], [float("nan")], [float("inf")], [lambda: None]):
        with pytest.raises((TypeError, ValueError)):
            c["set"](invalid)
    with pytest.raises(TypeError):
        left[0] = 5


def test_tuple_and_bytes_conversions_are_explicit_and_lossless():
    c = collections()
    source = [1, 2]
    immutable = c["tuple"](source)
    source.append(3)
    assert immutable == (1, 2)
    with pytest.raises(TypeError):
        immutable[0] = 9
    binary = c["bytes"]([0, 255, 65])
    assert binary == b"\x00\xffA"
    assert c["to_list"](binary) == [0, 255, 65]
    assert c["decode_utf8"](c["encode_utf8"]("water \u03a9")) == "water \u03a9"
    with pytest.raises(UnicodeDecodeError):
        c["decode_utf8"]([255])
    with pytest.raises(TypeError):
        c["encode_utf8"](123)
    for invalid in ([-1], [256], [True], [1.5]):
        with pytest.raises(ValueError):
            c["bytes"](invalid)
    assert c["dict"]() == {}
    assert c["tuple"]() == ()
    assert len(c["set"]()) == 0
    assert c["bytes"]() == b""


def test_general_purpose_type_tags_do_not_expose_host_attributes():
    c = collections()
    values = [
        None,
        True,
        1,
        1.5,
        "x",
        [],
        {},
        (),
        b"",
        c["set"](),
        lambda: None,
        object(),
    ]
    assert [c["kind"](value) for value in values] == [
        "none",
        "bool",
        "int",
        "float",
        "string",
        "list",
        "dict",
        "tuple",
        "bytes",
        "set",
        "function",
        "object",
    ]


def test_transforms_grouping_and_numeric_aggregation():
    c = collections()
    records = [{"group": "b", "n": 2}, {"group": "a", "n": 4}, {"group": "b", "n": 3}]
    groups = c["group_by"](lambda row: row["group"], records)
    assert c["keys"](groups) == ["b", "a"]
    assert c["sum"](c["map"](lambda row: row["n"], groups["b"])) == 5
    assert c["filter"](lambda row: row["n"] > 2, records) == records[1:]
    assert c["sort"](records, False, lambda row: row["n"]) == [
        records[0],
        records[2],
        records[1],
    ]
    assert c["reduce"](lambda acc, item: (acc or 0) + item, [1, 2], None) == 3
    assert c["reduce"](lambda a, b: a + b, [], 0) == 0
    with pytest.raises(TypeError):
        c["reduce"](lambda a, b: a + b, [])
    for value in ([True], ["2"], [float("nan")], [float("inf")], [1e308, 1e308]):
        with pytest.raises((TypeError, ValueError)):
            c["sum"](value)
    assert c["sum"]([]) == 0
    assert c["sum"]([1, 0.5]) == 1.5
    assert c["sum"]([10**100, 1]) == 10**100 + 1
    for name in ("map", "filter", "reduce", "group_by"):
        with pytest.raises(TypeError):
            c[name]("not callable", [])
    with pytest.raises(TypeError):
        c["map"](lambda x: x, "not a sequence")
    with pytest.raises(TypeError):
        c["sort"]([1], 1)
    with pytest.raises(TypeError):
        c["sort"]([1], False, 1)
    assert c["flatten"]([(1, 2), [3]]) == [1, 2, 3]
    assert c["zip"]((1, 2), b"ab") == [(1, 97), (2, 98)]


def test_new_container_values_work_in_language(capsys):
    source = """module containers: core
import "thirst::collections" as c
drink pair = c.tuple([7, 8])
drink data = c.bytes([65, 66])
pour pair[1]
pour data[0]
pour c.decode_utf8(data)
for value in c.set([3, 1, 3]) { pour value }
"""
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors and not parser.errors and not check_ast(program)
    # This fixture exercises guest container semantics under an intentional
    # host-core opt-out. The real application below uses an explicit policy.
    interpreter = Interpreter(allow_ungoverned=True)
    try:
        interpreter.interpret(program)
    finally:
        interpreter.executor.shutdown(wait=True)
    assert capsys.readouterr().out.splitlines() == ["8", "65", "AB", "3", "1"]


def run_report(tmp_path, raw, *, allow_file=True):
    path = tmp_path / "orders.json"
    path.write_text(raw, encoding="utf-8")
    allowed = [
        ("import", f"thirst::{namespace}")
        for namespace in ("collections", "json", "fs", "env")
    ] + [
        ("read", "thirst::env.get:THIRSTY_REPORT_INPUT"),
        ("write", "stdout"),
    ]
    if allow_file:
        allowed.append(("read", f"thirst::fs.read_file:{path}"))
    policy = tmp_path / "report-policy.tarl"
    policy.write_text(
        "\n".join(
            f"when action == {json.dumps(action)} and target == {json.dumps(target)} => ALLOW"
            for action, target in allowed
        )
        + "\nwhen true => DENY\n",
        encoding="utf-8",
    )
    environment = dict(
        os.environ, THIRSTY_REPORT_INPUT=str(path), PYTHONDONTWRITEBYTECODE="1"
    )
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "utf.thirsty_lang.cli",
            "run",
            str(EXAMPLE),
            "--policy",
            str(policy),
            "--authority",
            "test-report-reader",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )


def test_ordinary_data_application_end_to_end(tmp_path):
    raw = EXAMPLE.with_name("orders.json").read_text(encoding="utf-8")
    result = run_report(tmp_path, raw)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report == {
        "orders": 4,
        "units": 8,
        "revenue_cents": 8900,
        "categories": [
            {"category": "books", "orders": 2, "units": 3, "revenue_cents": 4400},
            {"category": "hardware", "orders": 2, "units": 5, "revenue_cents": 4500},
        ],
    }
    reversed_result = run_report(tmp_path, json.dumps(list(reversed(json.loads(raw)))))
    assert reversed_result.returncode == 0
    assert json.loads(reversed_result.stdout) == report


@pytest.mark.parametrize(
    "raw,reason",
    [
        ("{}", "array of orders"),
        ("[1]", "must be an object"),
        ('[{"id":"x"}]', "expected id"),
        (
            '[{"id":"x","category":"a","quantity":true,"unit_cents":1}]',
            "quantity must be an integer",
        ),
        ('[{"id":"x","category":"a","quantity":1,"unit_cents":-1}]', "unit_cents"),
        (
            '[{"id":"x","category":"a","quantity":1,"unit_cents":1},{"id":"x","category":"b","quantity":1,"unit_cents":1}]',
            "duplicate order id",
        ),
        (
            '[{"id":"x","id":"y","category":"a","quantity":1,"unit_cents":1}]',
            "Duplicate key",
        ),
        ("[NaN]", "Invalid JSON constant"),
        ("[1e9999]", "finite"),
    ],
)
def test_data_application_rejects_invalid_inputs_before_report(tmp_path, raw, reason):
    result = run_report(tmp_path, raw)
    assert result.returncode != 0
    assert reason in result.stderr
    assert result.stdout.strip() == ""


def test_json_rejects_silent_key_coercion_and_nonfinite_output():
    j = ms.STDLIB_MODULES["thirst::json"]()
    with pytest.raises(TypeError, match="keys"):
        j["stringify"]({1: "integer", "1": "string"})
    with pytest.raises(ValueError):
        j["stringify"]({"bad": float("nan")})
    assert j["parse"]("1.25") == 1.25


def test_data_application_bounds_file_input_before_json_parsing(tmp_path):
    result = run_report(tmp_path, "x" * 1048577)
    assert result.returncode != 0
    assert "exceeds max_bytes" in result.stderr
    assert result.stdout.strip() == ""


def test_file_read_budget_is_bytes_and_utf8_is_explicit(tmp_path):
    fs = ms.STDLIB_MODULES["thirst::fs"]()
    path = tmp_path / "utf8.txt"
    path.write_bytes("\u03a9".encode("utf-8"))
    assert fs["read_file"](str(path), 2) == "\u03a9"
    with pytest.raises(ValueError, match="exceeds max_bytes"):
        fs["read_file"](str(path), 1)
    for limit in (-1, True, 1.0, 67108865):
        with pytest.raises(ValueError):
            fs["read_file"](str(path), limit)
    path.write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        fs["read_file"](str(path), 1)


def test_data_application_denied_input_read_produces_no_report(tmp_path):
    result = run_report(tmp_path, "[]", allow_file=False)
    assert result.returncode == 2
    assert "governance denied" in result.stderr.lower()
    assert result.stdout == ""
