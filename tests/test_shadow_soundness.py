"""Counterexamples and limits for current Shadow Thirst proof methods."""

from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from utf.shadow_thirst import convergence as conv
from utf.shadow_thirst.admission import (
    ENGINE_VERSION,
    AdmissionEngine,
    ChangeAdmissionRecord,
    EvidenceStatus,
)
from utf.shadow_thirst.core import (
    MutationParser,
    PromotionEngine,
    ShadowModule,
    _structural_signature,
    parse_block,
)
from utf.shadow_thirst.regression import analyze_security_regression
from utf.tarl.keystore import ROLE_PROOF_SIGNER, generate
from utf.thirsty_lang.ast import BlockStmt, IntLiteral, ReturnStmt


def block(source):
    parsed = parse_block(source)
    assert parsed is not None, source
    return parsed


def same_structure(left, right):
    return _structural_signature(block(left), {}) == _structural_signature(
        block(right), {}
    )


def record(left, right):
    return AdmissionEngine().evaluate(
        ShadowModule(name="regression", shadow_code=left, canonical_code=right)
    )


def convergence_evidence(result):
    return next(
        item for item in result.evidence if item.analyzer == "CanonicalConvergence"
    )


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("return a", "return b"),
        ("return first(input)", "return second(input)"),
        ("return device.open", "return device.close"),
        ("drink x = x; return x", "drink y = y; return y"),
        (
            "drink x = 1; { drink x = 2 } return x",
            "drink a = 1; { drink b = 2 } return b",
        ),
        ("for x in items {} return x", "for y in items {} return y"),
        (
            "drink x = 1; return glass() { return x }",
            "drink y = 1; return glass() { return x }",
        ),
        ("glass f(a) { return a } return f", "glass g(b) { return a } return g"),
        ("return true", "return 1"),
        ("drink __error__ = 1; return __error__", "drink x = 1; return x"),
    ],
)
def test_structural_signature_preserves_scope_and_external_identity(left, right):
    assert not same_structure(left, right)


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("drink x = compute(input); return x", "drink y = compute(input); return y"),
        (
            "drink x = 1; { drink x = 2 } return x",
            "drink a = 1; { drink b = 2 } return a",
        ),
        (
            "drink x = input; drink x = x + 1; return x",
            "drink a = input; drink b = a + 1; return b",
        ),
        ("for x in items { pour x }", "for y in items { pour y }"),
        ("glass f(a) { return a } return f", "glass f(a) { return a } return f"),
    ],
)
def test_structural_signature_retains_supported_local_renaming(left, right):
    assert same_structure(left, right)


def test_distinct_free_inputs_are_never_proven_equivalent():
    result = record("return a", "return b")
    assert convergence_evidence(result).status == EvidenceStatus.VIOLATED
    assert result.admission_decision == "REJECTED"


def test_free_inputs_use_lexical_scope_and_initializer_order():
    assert conv.free_variables(block("drink x = x; { drink y = 1 } return y + x")) == {
        "x",
        "y",
    }
    assert conv.free_variables(
        block("for item in items { drink x = item } return item")
    ) == {"items", "item"}


@pytest.mark.parametrize("numerator", [-9, -2, -1, 0, 1, 2, 9])
@pytest.mark.parametrize("divisor", [-3, -2, -1, 1, 2, 3])
def test_symbolic_remainder_matches_runtime_for_both_signs(numerator, divisor):
    pytest.importorskip("z3")
    source = block(f"return {numerator} % {divisor}")
    expected = numerator % divisor
    assert conv._run_block_guarded(source, {}) == (True, expected)
    assert (
        conv.z3_equivalence(source, block(f"return {expected}")).status == "equivalent"
    )


def test_negative_remainder_counterexample_is_rejected():
    result = record("return 1 % -2", "return 1")
    assert convergence_evidence(result).status == EvidenceStatus.VIOLATED
    assert result.admission_decision == "REJECTED"


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("return 3 - 2", "return 1"),
        ("return not true", "return false"),
        ("return true and false", "return false"),
        ("return true or false", "return true"),
        ("return 1 < 2", "return true"),
        ("return 1 >= 2", "return false"),
    ],
)
def test_supported_boolean_and_numeric_symbolic_results_match_runtime(left, right):
    pytest.importorskip("z3")
    assert conv._run_block_guarded(block(left), {}) == conv._run_block_guarded(
        block(right), {}
    )
    assert conv.z3_equivalence(block(left), block(right)).status == "equivalent"


@pytest.mark.parametrize(
    "source",
    [
        "return 1 and 2",
        "return not 1",
        "return true + 1",
        "drink x; return x",
        "return",
        "drink x = 1",
    ],
)
def test_unmodeled_numeric_and_statement_forms_do_not_produce_symbolic_proofs(source):
    pytest.importorskip("z3")
    assert conv.z3_equivalence(block(source), block("return 1")).status == "unsupported"


def test_solver_absence_or_failure_cannot_produce_proof(monkeypatch):
    pytest.importorskip("z3")
    left, right = block("return x + x"), block("return x * 2")
    with monkeypatch.context() as patch:
        patch.setattr(conv, "_Z3_AVAILABLE", False)
        assert conv.z3_equivalence(left, right).status == "unavailable"

    def broken_context():
        raise OSError("solver failed")

    monkeypatch.setattr(conv._z3, "Context", broken_context)
    assert conv.z3_equivalence(left, right).status == "unsupported"


def test_solver_unknown_is_not_equivalence(monkeypatch):
    z3 = pytest.importorskip("z3")
    original_solver = z3.Solver

    def inconclusive_solver(**kwargs):
        solver = original_solver(**kwargs)
        solver.check = lambda: z3.unknown
        return solver

    monkeypatch.setattr(z3, "Solver", inconclusive_solver)
    assert (
        conv.z3_equivalence(block("return x + x"), block("return 2 * x")).status
        == "unsupported"
    )


@pytest.mark.parametrize(
    "source", ["return 1 % 0", "return 1 % divisor", "drink x = 1 % 0; return 0"]
)
def test_symbolic_layer_abstains_when_arithmetic_can_raise(source):
    pytest.importorskip("z3")
    assert conv.z3_equivalence(block(source), block("return 0")).status == "unsupported"


@pytest.mark.parametrize("source", ["drink x = 1; x = 2; return x", "x = 2; return x"])
def test_symbolic_layer_does_not_ignore_assignment_errors_or_external_effects(source):
    pytest.importorskip("z3")
    assert conv.z3_equivalence(block(source), block("return 2")).status == "unsupported"
    assert (
        conv.execute_and_compare(block(source), block("return 2")).status
        == "unsupported"
    )


def test_symbolic_layer_supports_local_mutable_assignment():
    pytest.importorskip("z3")
    assert (
        conv.z3_equivalence(
            block("drink mut x = 1; x = 2; return x"), block("return 2")
        ).status
        == "equivalent"
    )


def test_reserved_runtime_identifier_cannot_be_modeled_as_an_ordinary_local():
    result = record("drink __error__ = 1; return __error__", "return 1")
    assert convergence_evidence(result).status == EvidenceStatus.UNKNOWN
    assert result.admission_decision == "FLAGGED"


def test_integer_domain_proof_does_not_become_unconditional_admission_proof():
    pytest.importorskip("z3")
    left, right = "return x + x", "return 2 * x"
    symbolic = conv.z3_equivalence(block(left), block(right))
    assert symbolic.assumptions == {"x": "Int"}
    result = record(left, right)
    evidence = convergence_evidence(result)
    assert evidence.status == EvidenceStatus.OBSERVED
    assert evidence.details["symbolic_assumptions"] == {"x": "Int"}
    assert result.admission_decision == "FLAGGED"


@pytest.mark.parametrize(
    "source", ["return input @", "drink x = ; return input", "return (input"]
)
def test_parse_block_rejects_recovered_or_lexically_invalid_source(source):
    assert parse_block(source) is None
    result = record(source, "return input")
    assert convergence_evidence(result).status == EvidenceStatus.UNKNOWN
    assert result.admission_decision != "ELIGIBLE"
    legacy, _ = PromotionEngine().evaluate(
        ShadowModule(name="invalid", shadow_code=source, canonical_code=source)
    )
    assert legacy == "REJECT"


def test_nested_block_hash_covers_the_complete_analyzed_block():
    source = "mutation m { validated_canonical { shadow { thirsty (x > 0) { return 1 } return 2 } canonical { return 2 } } }"
    module = MutationParser.parse(source)
    assert module.shadow_code == "thirsty (x > 0) { return 1 } return 2"
    result = AdmissionEngine().evaluate(module)
    assert (
        result.candidate_sha256
        == hashlib.sha256(module.shadow_code.encode()).hexdigest()
    )
    changed = MutationParser.parse(
        source.replace("} return 2 } canonical", "} return 3 } canonical")
    )
    assert (
        AdmissionEngine().evaluate(changed).candidate_sha256 != result.candidate_sha256
    )


def test_admission_reparses_hashed_source_instead_of_trusting_supplied_ast():
    module = ShadowModule(
        name="forged", shadow_code="return 2", canonical_code="return 1"
    )
    module.shadow_ast = block("return 1")
    assert AdmissionEngine().evaluate(module).admission_decision == "REJECTED"


def test_outer_mutation_parse_failure_cannot_be_recovered_as_eligible_blocks():
    source = "mutation m { validated_canonical { shadow { return 1 } canonical { return 1 } } } @"
    module = MutationParser.parse(source)
    assert module.parse_failed
    assert AdmissionEngine().evaluate(module).admission_decision != "ELIGIBLE"


def test_source_size_limits_apply_before_parsing(monkeypatch):
    from utf.shadow_thirst import core

    monkeypatch.setattr(core, "_MAX_SOURCE_CHARS", 10)
    assert parse_block("return 1234567890") is None
    with pytest.raises(ValueError, match="source-size"):
        MutationParser.parse("mutation huge {}")


@pytest.mark.parametrize("signed", [False, True])
def test_old_records_retain_authenticity_but_require_reanalysis(signed):
    original = record("return input", "return input")
    original.engine_version = "0.1.0"
    old_item = convergence_evidence(original)
    original.evidence[original.evidence.index(old_item)] = replace(
        old_item, method="alpha-renamed-ast-equivalence/v1"
    )
    signer = generate("historical-shadow", ROLE_PROOF_SIGNER) if signed else None
    if signer:
        original.sign(signer)
    else:
        original.seal_unsigned()
    parsed = ChangeAdmissionRecord.from_dict(original.to_dict())
    key = signer.public_only() if signer else None
    assert parsed.verify(key)[0] is False
    valid, reason = parsed.verify(key, historical=True)
    assert valid and "semantic assurance was not verified" in reason
    parsed.mutation_name = "tampered"
    assert parsed.verify(key, historical=True)[0] is False


def test_current_engine_cannot_relabel_obsolete_proof_as_current():
    result = record("return input", "return input")
    assert result.engine_version == ENGINE_VERSION
    old_item = convergence_evidence(result)
    result.evidence[result.evidence.index(old_item)] = replace(
        old_item, method="alpha-renamed-ast-equivalence/v1"
    )
    result.seal_unsigned()
    assert result.verify()[0] is False


@pytest.mark.parametrize(
    "source",
    [
        "return invoke(input)",
        "drink f = print; f(1); return 1",
        "return target.method()",
    ],
)
def test_unknown_calls_are_neither_sampled_nor_declared_effect_free(source):
    candidate = block(source)
    assert not conv.is_effect_free(candidate)
    assert (
        conv.execute_and_compare(candidate, block("return 1")).status == "unsupported"
    )
    finding = analyze_security_regression(
        ShadowModule(name="unknown", shadow_code=source, canonical_code=source)
    )
    assert finding.status == "UNKNOWN"


def test_unknown_invariant_call_cannot_claim_purity():
    result = AdmissionEngine().evaluate(
        ShadowModule(
            name="unknown-invariant",
            shadow_code="return 1",
            canonical_code="return 1",
            invariant_code="check()",
        )
    )
    item = next(item for item in result.evidence if item.analyzer == "PuritySpring")
    assert item.status == EvidenceStatus.UNKNOWN
    assert result.admission_decision == "FLAGGED"


def test_sampling_never_invokes_a_supplied_host_object():
    class HostObject:
        def __mul__(self, other):
            pytest.fail("host object was invoked")

    assert conv._run_block_guarded(block("return x * 2"), {"x": HostObject()}) == (
        False,
        None,
    )


def test_sampling_operation_budget_stops_infinite_loops_and_recovers(monkeypatch):
    monkeypatch.setattr(conv, "_MAX_STEPS", 25)
    assert conv._run_block_guarded(block("refill (true) {} return 1"), {}) == (
        False,
        None,
    )
    assert conv._run_block_guarded(
        block("times 99999999999999999999 {} return 1"), {}
    ) == (False, None)
    assert conv._run_block_guarded(block("return 1"), {}) == (True, 1)


def test_sampling_rejects_excessive_numeric_values_before_host_arithmetic():
    assert conv._run_block_guarded(block("return x * x"), {"x": 1 << 5000}) == (
        False,
        None,
    )
    assert conv._run_block_guarded(block("return x * x"), {"x": 1 << 3000}) == (
        False,
        None,
    )


def test_sampling_rejects_nonfinite_and_unsupported_values():
    assert conv._run_block_guarded(block("return x"), {"x": float("inf")}) == (
        False,
        None,
    )
    assert conv._run_block_guarded(block("return [1]"), {}) == (False, None)
    assert conv._run_block_guarded(None, {}) == (False, None)
    assert conv.execute_and_compare(None, block("return 1")).status == "unsupported"


def test_sampling_distinguishes_fallthrough_from_return():
    assert (
        conv.execute_and_compare(block("drink x = 1"), block("drink y = 2")).status
        == "equivalent"
    )
    assert (
        conv.execute_and_compare(block("drink x = 1"), block("return")).status
        == "diverge"
    )


def test_analysis_rejects_deep_or_oversized_asts():
    nested = block("return 1")
    for _ in range(100):
        nested = BlockStmt(span=(1, 1, 1, 1), statements=[nested])
    assert conv.execute_and_compare(nested, block("return 1")).status == "unsupported"
    huge = BlockStmt(
        span=(),
        statements=[ReturnStmt(span=(), value=IntLiteral(span=(), value=1 << 5000))],
    )
    assert conv.z3_equivalence(huge, block("return 1")).status in {
        "unsupported",
        "unavailable",
    }


def test_sampling_does_not_discard_inputs_that_raise():
    assert (
        conv.execute_and_compare(block("return x / x"), block("return 1")).status
        == "unsupported"
    )


def test_sampling_preserves_return_type():
    assert (
        conv.execute_and_compare(block("return true"), block("return 1")).status
        == "diverge"
    )


def test_sampling_supports_bounded_local_control_flow():
    assert conv._run_block_guarded(
        block("drink mut x = 0; refill (x < 3) { x = x + 1 } return x"), {}
    ) == (True, 3)


def test_empty_invariant_is_inapplicable_not_missing_proof():
    result = record("return input", "return input")
    assert (
        next(item for item in result.evidence if item.analyzer == "PuritySpring").status
        == EvidenceStatus.INAPPLICABLE
    )
    assert result.admission_decision == "ELIGIBLE"
