"""Permanent regression gate for TARL context resolution and proof binding.

Missing is not false. Invalid is not false. Unresolved is not evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from utf.tarl import cli as tarl_cli
from utf.tarl.broker import CapabilityBroker
from utf.tarl.composer import PolicyComposer
from utf.tarl.context import ContextResolutionError, hash_rejected_context
from utf.tarl.core import PolicyParser, SafeExpr, evaluate_policy
from utf.tarl.runtime import TarlRuntime
from utf.tarl.schema import ContextSchema, FieldSpec
from utf.tarl.spec import TarlVerdict
from utf.tarl.verifier import ProofVerifier, canonical_context_hash
from utf.thirsty_lang.interpreter import GovernanceViolation, Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser
from utf.thirsty_lang.proof_obligations import derive_context_schema

FIXTURES = Path(__file__).parent / "fixtures" / "tarl_context_coherence"
DOTTED_POLICY = (FIXTURES / "dotted-context.tarl").read_text(encoding="utf-8")
SIMPLE_POLICY = (FIXTURES / "simple-context.tarl").read_text(encoding="utf-8")
NEGATED_POLICY = (
    "policy access_control\n"
    'when user.role != "admin" => ALLOW\n'
    "when true => DENY\n"
)


def _matrix_cases():
    fixture = json.loads((FIXTURES / "matrix.json").read_text(encoding="utf-8"))
    policies = {
        "dotted-context.tarl": DOTTED_POLICY,
        "simple-context.tarl": SIMPLE_POLICY,
    }
    return [
        (case["id"], policies[case["policy"]], case["context"], case["expected"])
        for case in fixture["cases"]
    ]


def _decision(condition: str, context: dict) -> object:
    policy = (
        "policy resolution_integrity\n"
        f"when {condition} => ALLOW\n"
        "when true => DENY\n"
    )
    return evaluate_policy(context, policy_text=policy)


@pytest.mark.parametrize(
    ("condition", "context"),
    [
        ('user.role == "admin"', {}),
        ('user.role != "admin"', {}),
        ('user.role != "admin"', {"user": "admin"}),
        ("not user.role", {}),
        ("user.role == false", {}),
        ('user.role in ["admin"]', {}),
        ('LOWER(user.role) == "admin"', {}),
    ],
)
def test_unresolved_dotted_paths_fail_closed(condition, context):
    decision = _decision(condition, context)
    assert decision.verdict == TarlVerdict.DENY
    assert decision.rule_index == 0
    assert "context path 'user.role'" in decision.reason


@pytest.mark.parametrize(
    ("condition", "context"),
    [
        ('user.role == "admin"', {}),
        ('user.role != "admin"', {}),
        ('user.role != "admin"', {"user": "admin"}),
        ("not user.role", {}),
        ("user.role == false", {}),
        ('user.role in ["admin"]', {}),
        ('LOWER(user.role) == "admin"', {}),
    ],
)
def test_safe_expr_keeps_unresolved_out_of_boolean_algebra(condition, context):
    with pytest.raises(Exception, match="context path 'user.role'"):
        SafeExpr.evaluate(condition, context)


def test_resolved_false_remains_a_real_boolean_value():
    context = {"feature": {"enabled": False}}
    assert SafeExpr.evaluate("feature.enabled == false", context) is True
    decision = _decision("feature.enabled == false", context)
    assert decision.verdict == TarlVerdict.ALLOW


def test_missing_simple_identifier_is_not_false_either():
    decision = _decision('role != "admin"', {})
    assert decision.verdict == TarlVerdict.DENY
    assert decision.rule_index == 0
    assert "context path 'role'" in decision.reason


@pytest.mark.parametrize(
    "condition",
    [
        'LOWER(user.role) == "admin"',
        'LEN(user.role) != 0',
    ],
)
def test_resolved_wrong_value_type_fails_closed(condition):
    decision = _decision(condition, {"user": {"role": False}})
    assert decision.verdict == TarlVerdict.DENY
    assert "condition type error" in decision.reason


@pytest.mark.parametrize(
    ("context", "reason"),
    [
        ({"user.role": "admin"}, "dotted key 'user.role' is not permitted"),
        (
            {"user.role": "admin", "user": {"role": "admin"}},
            "context representation conflict: user.role is supplied in both flat and nested form",
        ),
        (
            {"user.role": "guest", "user": {"role": "admin"}},
            "context representation conflict: user.role has contradictory flat and nested values",
        ),
    ],
)
def test_non_authoritative_or_ambiguous_context_is_denied(context, reason):
    decision = evaluate_policy(context, policy_text=DOTTED_POLICY)
    assert decision.verdict == TarlVerdict.DENY
    assert decision.reason == reason


def test_preserved_four_case_matrix():
    cases = _matrix_cases()[:4]
    assert [
        evaluate_policy(context, policy_text=policy).verdict
        for _case_id, policy, context, _expected in cases
    ] == [
        TarlVerdict(expected)
        for _case_id, _policy, _context, expected in cases
    ]


@pytest.mark.parametrize(
    ("case_id", "policy_text", "context", "expected"), _matrix_cases()
)
def test_permanent_matrix_through_safe_expr(
    case_id, policy_text, context, expected
):
    condition = PolicyParser.parse(policy_text).rules[0].condition
    if case_id in {
        "flat-dotted-key-only",
        "flat-and-nested-equal",
        "flat-and-nested-conflicting",
        "missing-intermediate-object",
        "wrong-intermediate-type",
    }:
        with pytest.raises(ContextResolutionError):
            SafeExpr.evaluate(condition, context)
        return
    assert SafeExpr.evaluate(condition, context) is (
        expected == TarlVerdict.ALLOW.value
    )


@pytest.mark.parametrize(
    ("_case_id", "policy_text", "context", "expected"), _matrix_cases()
)
def test_permanent_matrix_through_evaluate_policy(
    _case_id, policy_text, context, expected
):
    assert evaluate_policy(context, policy_text=policy_text).verdict == (
        TarlVerdict(expected)
    )


@pytest.mark.parametrize(
    ("_case_id", "policy_text", "context", "expected"), _matrix_cases()
)
def test_permanent_matrix_through_runtime(
    _case_id, policy_text, context, expected
):
    runtime = TarlRuntime(PolicyParser.parse(policy_text))
    assert runtime.evaluate(context).verdict == TarlVerdict(expected)


@pytest.mark.parametrize(
    ("case_id", "policy_text", "context", "expected"), _matrix_cases()
)
def test_permanent_matrix_through_schema_and_proof_obligations(
    case_id, policy_text, context, expected
):
    derived = derive_context_schema(policy_text).to_dict()
    schema = ContextSchema.from_dict(derived)
    violations = schema.validate(context)
    valid_cases = {
        "nested-object-only",
        "simple-identifier-allow",
        "simple-identifier-deny",
    }
    assert (violations == []) is (case_id in valid_cases)

    runtime = TarlRuntime(PolicyParser.parse(policy_text)).set_context_schema(schema)
    assert runtime.evaluate(context).verdict == TarlVerdict(expected)


@pytest.mark.parametrize(
    ("case_id", "policy_text", "context", "expected"), _matrix_cases()
)
def test_permanent_matrix_through_proof_creation_and_verification(
    case_id, policy_text, context, expected
):
    schema = ContextSchema.from_dict(derive_context_schema(policy_text).to_dict())
    runtime = TarlRuntime(PolicyParser.parse(policy_text)).set_context_schema(schema)
    runtime.set_signing_key("matrix-key", b"matrix-secret")
    decision, proof = runtime.evaluate_with_proof(context)
    assert decision.verdict == proof.verdict == TarlVerdict(expected)

    verifier = ProofVerifier().add_hmac_key("matrix-key", b"matrix-secret")
    authoritative = case_id in {
        "nested-object-only",
        "simple-identifier-allow",
        "simple-identifier-deny",
    }
    result = verifier.verify(
        proof, expected_context=context if authoritative else None
    )
    assert result.valid is True
    assert result.checks["context_coherence"] is True


@pytest.mark.parametrize(
    ("_case_id", "policy_text", "context", "expected"), _matrix_cases()
)
def test_permanent_matrix_through_tarl_eval(
    _case_id,
    policy_text,
    context,
    expected,
    monkeypatch,
    tmp_path,
    capsys,
):
    policy_path = tmp_path / "matrix.tarl"
    policy_path.write_text(policy_text, encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "tarl",
            "eval",
            str(policy_path),
            "--context",
            json.dumps(context, separators=(",", ":")),
            "--json",
        ],
    )
    tarl_cli.main()
    result = json.loads(capsys.readouterr().out)
    assert result["verdict"] == expected


@pytest.mark.parametrize(
    ("_case_id", "policy_text", "context", "expected"), _matrix_cases()
)
def test_permanent_matrix_through_governed_runtime(
    _case_id, policy_text, context, expected
):
    interpreter = Interpreter()
    interpreter.mode = "governed"
    schema = ContextSchema.from_dict(derive_context_schema(policy_text).to_dict())
    runtime = TarlRuntime(PolicyParser.parse(policy_text)).set_context_schema(
        schema
    )
    interpreter.attach_tarl(runtime)
    interpreter.set_authority("matrix-authority")
    decl = SimpleNamespace(
        name="matrix_action",
        requires_expr=None,
        invariant_expr=None,
        ensures_expr=None,
    )
    allowed, _reason, proof = interpreter._enforce_governance(
        context, decl, phase="entry"
    )
    assert allowed is (expected == TarlVerdict.ALLOW.value)
    assert proof.verdict == TarlVerdict(expected)


def test_schema_and_evaluator_resolve_the_same_nested_path():
    schema = ContextSchema(
        fields=[FieldSpec("user.role", kinds=("string",), required=True)]
    )
    nested = {"user": {"role": "admin"}}
    assert schema.validate(nested) == []

    runtime = TarlRuntime(PolicyParser.parse(DOTTED_POLICY)).set_context_schema(schema)
    assert runtime.evaluate(nested).verdict == TarlVerdict.ALLOW
    assert runtime.evaluate({"user.role": "admin"}).verdict == TarlVerdict.DENY


def test_derived_schema_declares_the_authoritative_representation():
    schema = derive_context_schema(DOTTED_POLICY).to_dict()
    assert schema["representation"]["id"] == "tarl.context.nested-json.v1"
    assert schema["representation"]["normalization"] == "none"
    assert schema["fields"] == [
        {"name": "user.role", "kinds": ["string"], "required": True}
    ]


def test_runtime_proof_binds_the_exact_evaluated_context():
    context = {"user": {"role": "admin"}}
    schema = ContextSchema.from_dict(derive_context_schema(DOTTED_POLICY).to_dict())
    runtime = TarlRuntime(PolicyParser.parse(DOTTED_POLICY)).set_context_schema(
        schema
    )
    runtime.set_signing_key("context-key", b"context-secret")
    decision, proof = runtime.evaluate_with_proof(context)

    expected_hash = canonical_context_hash(context)
    assert decision.verdict == TarlVerdict.ALLOW
    assert proof.context_hash == expected_hash
    assert proof.original_context_hash == expected_hash
    assert proof.canonical_context_hash == expected_hash
    assert proof.context_representation_id == "tarl.context.nested-json.v1"
    assert proof.normalization_algorithm_id == "identity"
    assert proof.normalization_version == "1"
    assert proof.context_conflict_status == "none"
    assert proof.context_schema_hash == schema.fingerprint()
    assert proof.context_schema_representation_id == (
        proof.context_representation_id
    )
    assert proof.context_schema_validation_status == "passed"

    verifier = ProofVerifier()
    verifier.add_hmac_key("context-key", b"context-secret")
    result = verifier.verify(proof, expected_context=context)
    assert result.valid is True
    assert result.checks["context_coherence"] is True
    assert result.checks["context_binding"] is True


def test_conflicting_context_produces_deny_proof_not_allow_proof():
    context = {"user.role": "guest", "user": {"role": "admin"}}
    runtime = TarlRuntime(PolicyParser.parse(DOTTED_POLICY))
    decision, proof = runtime.evaluate_with_proof(context)
    assert decision.verdict == TarlVerdict.DENY
    assert proof.verdict == TarlVerdict.DENY
    assert proof.context_conflict_status == "conflict"
    assert proof.original_context_hash == hash_rejected_context(context)


def test_positive_proof_metadata_tampering_is_inadmissible():
    schema = ContextSchema.from_dict(derive_context_schema(DOTTED_POLICY).to_dict())
    runtime = TarlRuntime(PolicyParser.parse(DOTTED_POLICY)).set_context_schema(
        schema
    )
    runtime.set_signing_key("context-key", b"context-secret")
    _decision_result, proof = runtime.evaluate_with_proof(
        {"user": {"role": "admin"}}
    )
    proof.context_representation_id = "attacker.flat-dotted.v1"

    result = ProofVerifier().add_hmac_key(
        "context-key", b"context-secret"
    ).verify(proof)
    assert result.valid is False
    assert result.checks["context_coherence"] is False
    assert result.checks["signature"] is False


def test_unresolved_registered_source_cannot_be_negated_into_allow():
    policy = PolicyParser.parse(
        "policy source_gate\n"
        'when role NOT IN source:trusted_roles => ALLOW\n'
        "when true => DENY\n"
    )
    runtime = TarlRuntime(policy)
    decision = runtime.evaluate({"role": "admin"})
    assert decision.verdict == TarlVerdict.DENY
    assert "source:trusted_roles" in decision.reason


def test_failed_registered_source_cannot_be_negated_into_allow():
    def unavailable():
        raise RuntimeError("directory unavailable")

    policy = PolicyParser.parse(
        "policy source_gate\n"
        'when role NOT IN source:trusted_roles => ALLOW\n'
        "when true => DENY\n"
    )
    runtime = TarlRuntime(policy).register_source("trusted_roles", unavailable)
    decision = runtime.evaluate({"role": "admin"})
    assert decision.verdict == TarlVerdict.DENY
    assert "registered source 'trusted_roles' could not be resolved" in (
        decision.reason
    )


def test_broker_rejects_caller_override_of_authority_context():
    policy = PolicyParser.parse(
        "policy broker_gate\n"
        'when authority == "attacker" => ALLOW\n'
        "when true => DENY\n"
    )
    broker = CapabilityBroker(TarlRuntime(policy), authority="trusted")
    result = broker.request("write", "record", authority="attacker")
    assert result.allowed is False
    assert result.verdict == TarlVerdict.DENY
    assert "context layer conflict: field 'authority'" in result.reason


def test_composer_rejects_caller_override_of_include_result():
    included = PolicyParser.parse("policy trusted\nwhen true => DENY\n")
    gateway = PolicyParser.parse(
        "policy gateway\n"
        "INCLUDE trusted AS trust\n"
        'when trust.verdict == "ALLOW" => ALLOW\n'
        "when true => DENY\n"
    )
    decision = (
        PolicyComposer()
        .register(included)
        .register(gateway)
        .evaluate("gateway", {"trust": {"verdict": "ALLOW"}})
    )
    assert decision.verdict == TarlVerdict.DENY
    assert "context layer conflict: field 'trust'" in decision.reason


def test_governed_call_rejects_argument_collision_with_authority_context():
    interpreter = Interpreter()
    interpreter.mode = "governed"
    interpreter.attach_tarl(
        TarlRuntime(PolicyParser.parse("policy p\nwhen true => ALLOW\n"))
    )
    interpreter.set_authority("trusted")
    decl = SimpleNamespace(
        name="colliding_action",
        requires_expr=None,
        invariant_expr=None,
        ensures_expr=None,
    )
    allowed, reason, proof = interpreter._enforce_governance(
        {"authority": "attacker"}, decl, phase="entry"
    )
    assert allowed is False
    assert "context layer conflict: field 'authority'" in reason
    assert proof.verdict == TarlVerdict.DENY


def test_tarl_eval_cli_rejects_conflicting_context(
    monkeypatch, tmp_path, capsys
):
    policy_path = tmp_path / "dotted-context.tarl"
    policy_path.write_text(DOTTED_POLICY, encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "tarl",
            "eval",
            str(policy_path),
            "--context",
            '{"user.role":"guest","user":{"role":"admin"}}',
            "--json",
        ],
    )
    tarl_cli.main()
    result = json.loads(capsys.readouterr().out)
    assert result["verdict"] == "DENY"
    assert result["reason"] == (
        "context representation conflict: user.role has contradictory flat "
        "and nested values"
    )


def test_tarl_eval_cli_rejects_duplicate_json_keys(
    monkeypatch, tmp_path, capsys
):
    policy_path = tmp_path / "simple-context.tarl"
    policy_path.write_text(SIMPLE_POLICY, encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "tarl",
            "eval",
            str(policy_path),
            "--context",
            '{"role":"guest","role":"admin"}',
            "--json",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        tarl_cli.main()
    assert exc.value.code == 1
    assert "context representation conflict: duplicate key 'role'" in (
        capsys.readouterr().err
    )


def test_tarl_verify_binds_the_original_context(
    monkeypatch, tmp_path, capsys
):
    context = {"user": {"role": "admin"}}
    schema = ContextSchema.from_dict(derive_context_schema(DOTTED_POLICY).to_dict())
    runtime = TarlRuntime(PolicyParser.parse(DOTTED_POLICY)).set_context_schema(
        schema
    )
    runtime.set_signing_key("context-key", b"context-secret")
    _decision_result, proof = runtime.evaluate_with_proof(context)
    proof_path = tmp_path / "proof.json"
    proof_path.write_text(proof.to_json(), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "tarl",
            "verify",
            str(proof_path),
            "--hmac-key",
            "context-key:" + b"context-secret".hex(),
            "--context",
            json.dumps(context, separators=(",", ":")),
            "--json",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        tarl_cli.main()
    assert exc.value.code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["valid"] is True
    assert result["checks"]["context_coherence"] is True
    assert result["checks"]["context_binding"] is True


def test_governed_thirsty_runtime_rejects_malformed_dotted_context():
    source = (
        "module demo: governed\n"
        "glass inspect(user) requires true { return 1 }\n"
    )
    program = Parser(Lexer(source).lex()).parse()
    interpreter = Interpreter()
    interpreter.attach_tarl(TarlRuntime(PolicyParser.parse(NEGATED_POLICY)))
    interpreter.set_authority("admin")
    interpreter.interpret(program)

    with pytest.raises(GovernanceViolation) as exc:
        interpreter.env.get("inspect")("admin")
    assert "context path 'user.role'" in exc.value.reason
    assert exc.value.proof.verdict == TarlVerdict.DENY
