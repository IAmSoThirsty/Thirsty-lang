"""Slicing must preserve effect visibility and conservative compiler/proof gates."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from utf.shadow_thirst import cli as shadow_cli
from utf.shadow_thirst import convergence
from utf.shadow_thirst.admission import (
    ENGINE_VERSION,
    AdmissionEngine,
    ChangeAdmissionRecord,
    EvidenceStatus,
    _convergence_evidence,
)
from utf.shadow_thirst.core import (
    CanonicalConvergenceAnalyzer,
    ShadowModule,
    _structural_signature,
    astwalk,
    parse_block,
)
from utf.shadow_thirst.regression import analyze_security_regression
from utf.tarl.keystore import ROLE_PROOF_SIGNER, generate
from utf.thirsty_lang import cli
from utf.thirsty_lang.ast import (
    BlockStmt,
    CallExpr,
    Identifier,
    IntLiteral,
    ReturnStmt,
    SliceExpr,
)
from utf.thirsty_lang.interpreter import Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.package_manager import runtime_source_integrity
from utf.thirsty_lang.parser import Parser
from utf.thirsty_lang.proof_obligations import extract_proof_obligations


def parse(source):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors and not parser.errors
    return program


def block(source):
    result = parse_block(source)
    assert result is not None
    return result


@pytest.mark.parametrize(
    "expression", ["values[1:3]", "values[:3]", "values[1:]", "values[::-1]"]
)
@pytest.mark.parametrize("backend", [cli._transpile_to_js, cli._transpile_to_llvm_ir])
def test_compilers_explicitly_reject_slices(expression, backend):
    with pytest.raises(ValueError, match="target does not support SliceExpr"):
        backend(parse("drink main = " + expression))


@pytest.mark.parametrize("target", ["js", "llvm-ir"])
def test_slice_build_rejection_emits_no_artifact_or_manifest(target, tmp_path):
    source = tmp_path / "slice.thirsty"
    source.write_text(
        "drink values = [1, 2, 3]\ndrink main = values[1:]", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="target does not support"):
        cli.cmd_build(
            SimpleNamespace(
                file=str(source),
                target=target,
                allow_governance_loss=True,
                emit_manifest=True,
            )
        )
    assert list(tmp_path.iterdir()) == [source]


def test_pyodide_keeps_slice_source_and_runtime_binding(tmp_path):
    source = 'drink main = "</script>abcdef"[1:8:2]'
    output = cli._build_pyodide(source, str(tmp_path / "slice"))
    html = Path(output).read_text(encoding="utf-8")
    embedded = html.split("const SOURCE = ", 1)[1].split(";\n", 1)[0]
    assert json.loads(embedded) == source
    assert "</script>" not in embedded
    assert runtime_source_integrity() in html


@pytest.mark.parametrize(
    ("source", "names"),
    [
        ("return values[start:stop:step]", {"values", "start", "stop", "step"}),
        ("return values[:stop]", {"values", "stop"}),
        ("return values[start:]", {"values", "start"}),
        ("return values[::-1]", {"values"}),
    ],
)
def test_slice_walk_and_free_inputs_include_every_bound(source, names):
    parsed = block(source)
    assert any(type(node) is SliceExpr for node in astwalk(parsed))
    assert {
        node.name for node in astwalk(parsed) if isinstance(node, Identifier)
    } == names
    assert convergence.free_variables(parsed) == names


@pytest.mark.parametrize(
    "changed",
    [
        "other[1:5:2]",
        "values[0:5:2]",
        "values[1:4:2]",
        "values[1:5:3]",
        "values[1:5:]",
        "values[:5:2]",
    ],
)
def test_slice_signature_preserves_object_and_each_bound(changed):
    left = block("return values[1:5:2]")
    right = block("return " + changed)
    assert _structural_signature(left, {}) != _structural_signature(right, {})
    record = AdmissionEngine().evaluate(
        ShadowModule(
            "slice",
            shadow_code="return values[1:5:2]",
            canonical_code="return " + changed,
        )
    )
    evidence = next(
        item for item in record.evidence if item.analyzer == "CanonicalConvergence"
    )
    assert evidence.status == EvidenceStatus.UNKNOWN
    assert record.admission_decision != "ELIGIBLE"


def test_alpha_equivalent_local_slice_names_preserve_structural_identity():
    left = block("drink a = 1; return values[a:stop:step]")
    right = block("drink b = 1; return values[b:stop:step]")
    assert _structural_signature(left, {}) == _structural_signature(right, {})


def test_slice_semantic_proof_layers_abstain_without_execution(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("slice analysis must not execute unmodeled expressions")

    monkeypatch.setattr(Interpreter, "_evaluate_impl", forbidden)
    left = block("return values[start:stop:step]")
    right = block("return values[start:stop:step]")
    assert convergence.z3_equivalence(left, right).status in {
        "unsupported",
        "unavailable",
    }
    assert convergence.execute_and_compare(left, right).status == "unsupported"


_EFFECT_SLICES = [
    'fs.read_file("input")[0:2:1]',
    'values[fs.read_file("input"):2:1]',
    'values[0:fs.read_file("input"):1]',
    'values[0:2:fs.read_file("input")]',
]


@pytest.mark.parametrize("expression", _EFFECT_SLICES)
def test_proof_obligations_see_effects_in_slice_receiver_and_bounds(
    expression, monkeypatch
):
    def forbidden(*_args, **_kwargs):
        pytest.fail("static proof extraction must not execute code")

    monkeypatch.setattr(Interpreter, "interpret", forbidden)
    source = (
        'module slice_demo: governed\nimport "thirst::fs" as fs\ndrink values = [1, 2, 3]\ndrink main = '
        + expression
    )
    report = extract_proof_obligations(parse(source), source, "slice.thirsty")
    assert report["side_effects_executed"] is False
    assert {"import", "read"} <= set(report["required_tarl_actions"])
    calls = report["stdlib_sensitive_calls"]
    assert len(calls) == 1
    assert calls[0]["module"] == "thirst::fs"
    assert calls[0]["function"] == "read_file"


@pytest.mark.parametrize("expression", _EFFECT_SLICES)
def test_shadow_security_sees_effects_in_slice_receiver_and_bounds(expression):
    prefix = 'import "thirst::fs" as fs; return '
    result = analyze_security_regression(
        ShadowModule(
            "slice",
            shadow_code=prefix + expression,
            canonical_code=prefix + "values[0:2:1]",
        )
    )
    assert result.status == "VIOLATED"
    assert "read:thirst::fs.read_file" in result.details["added_effects"]


@pytest.mark.parametrize(
    "expression", ["values[compute():]", "values[:compute()]", "values[::compute()]"]
)
def test_unresolved_slice_bound_calls_prevent_admission(expression):
    source = "return " + expression
    record = AdmissionEngine().evaluate(
        ShadowModule("slice", shadow_code=source, canonical_code=source)
    )
    evidence = {item.analyzer: item for item in record.evidence}
    assert evidence["SecurityRegression"].status == EvidenceStatus.UNKNOWN
    assert evidence["Determinism"].status == EvidenceStatus.UNKNOWN
    assert record.admission_decision != "ELIGIBLE"


@dataclass
class UnknownLiteral(IntLiteral):
    hidden_bound: object = None


def unknown_literal_block():
    hidden = CallExpr(
        span=(1, 1, 1, 1), callee=Identifier(span=(1, 1, 1, 1), name="effect"), args=[]
    )
    literal = UnknownLiteral(span=(1, 1, 1, 1), value=1, hidden_bound=hidden)
    return BlockStmt(
        span=(1, 1, 1, 1), statements=[ReturnStmt(span=(1, 1, 1, 1), value=literal)]
    )


def test_unknown_ast_subclass_never_becomes_a_structural_proof():
    parsed = unknown_literal_block()
    with pytest.raises(ValueError, match="does not support AST node UnknownLiteral"):
        _structural_signature(parsed, {})
    module = ShadowModule(
        "unknown",
        shadow_code="return 1",
        canonical_code="return 1",
        shadow_ast=parsed,
        canonical_ast=parsed,
    )
    assert _convergence_evidence(module).status == EvidenceStatus.UNKNOWN
    result = CanonicalConvergenceAnalyzer().analyze(module)
    assert not result.passed
    assert "Equivalence is unknown" in result.message


def test_unknown_ast_subclass_never_becomes_symbolic_or_sampled_evidence():
    parsed = unknown_literal_block()
    assert convergence.z3_equivalence(parsed, parsed).status in {
        "unsupported",
        "unavailable",
    }
    assert convergence.execute_and_compare(parsed, parsed).status == "unsupported"


@pytest.mark.parametrize("backend", [cli._transpile_to_js, cli._transpile_to_llvm_ir])
def test_compilers_reject_unknown_literal_subclasses(backend):
    program = parse("drink main = 1")
    # A nested literal would pass the JS call validator; rejecting the unknown
    # outer type must not depend on the extra field containing a forbidden call.
    program.stmts[0].init_expr = UnknownLiteral(
        span=(1, 1, 1, 1), value=1, hidden_bound=IntLiteral(span=(1, 1, 1, 1), value=2)
    )
    with pytest.raises(ValueError, match="target does not support UnknownLiteral"):
        backend(program)


def historical_record(version, method):
    record = AdmissionEngine().evaluate(
        ShadowModule("historical", shadow_code="return 1", canonical_code="return 1")
    )
    record.engine_version = version
    record.evidence = [
        (
            replace(item, method=method)
            if item.analyzer == "CanonicalConvergence"
            else item
        )
        for item in record.evidence
    ]
    return record.seal_unsigned()


@pytest.mark.parametrize("signed", [False, True])
@pytest.mark.parametrize(
    ("version", "method"),
    [
        ("0.1.0", "alpha-renamed-ast-equivalence/v1"),
        ("0.2.0", "alpha-renamed-ast-equivalence/v2"),
        ("0.2.0", "z3-symbolic-equivalence/v2"),
    ],
)
def test_pre_slice_records_are_historical_integrity_only(version, method, signed):
    record = historical_record(version, method)
    signer = generate("history", ROLE_PROOF_SIGNER) if signed else None
    if signer:
        record.sign(signer)
    restored = ChangeAdmissionRecord.from_dict(record.to_dict())
    public = signer.public_only() if signer else None
    valid, reason = restored.verify(public)
    assert not valid and "superseded admission engine" in reason
    valid, reason = restored.verify(public, historical=True)
    assert valid and "semantic assurance was not verified" in reason
    assert restored.execution_authorized is False
    restored.canonical_sha256 = "0" * 64
    assert restored.verify(public, historical=True)[0] is False


@pytest.mark.parametrize(
    "method", ["alpha-renamed-ast-equivalence/v2", "z3-symbolic-equivalence/v2"]
)
def test_old_methods_cannot_be_relabelled_as_the_current_engine(method):
    record = historical_record(ENGINE_VERSION, method)
    valid, reason = record.verify()
    assert not valid and "unsupported proof method" in reason


@pytest.mark.parametrize(
    ("candidate", "method"),
    [
        ("return 2", "alpha-renamed-ast-equivalence/v4"),
        ("return 1 + 1", "z3-symbolic-equivalence/v4"),
    ],
)
def test_new_proofs_identify_the_current_node_checks(candidate, method):
    if method.startswith("z3-"):
        pytest.importorskip("z3")
    record = AdmissionEngine().evaluate(
        ShadowModule("current", shadow_code=candidate, canonical_code="return 2")
    )
    assert record.engine_version == ENGINE_VERSION == "0.4.0"
    evidence = next(
        item for item in record.evidence if item.analyzer == "CanonicalConvergence"
    )
    assert evidence.status == EvidenceStatus.PROVEN
    assert evidence.method == method
    assert record.verify()[0] is True


def test_cli_refuses_old_current_assurance_by_default(tmp_path, capsys):
    record = historical_record("0.2.0", "alpha-renamed-ast-equivalence/v2")
    source = tmp_path / "old-admission.json"
    source.write_text(record.to_json(), encoding="utf-8")
    result = shadow_cli._run_verify_admission(
        SimpleNamespace(
            record_file=str(source), require_signature=False, public_key=None, json=True
        )
    )
    assert result == 1
    output = json.loads(capsys.readouterr().out)
    assert output["valid"] is False
    assert "reanalysis required" in output["reason"]
    assert output["execution_authorized"] is False
