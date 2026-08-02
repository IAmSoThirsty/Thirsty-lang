"""Hostile regression tests for the authoritative TARL context boundary."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from utf.tarl.broker import CapabilityBroker
from utf.tarl.context import (
    CONTEXT_REPRESENTATION_ID,
    ContextRepresentationError,
    load_context_json,
)
from utf.tarl.core import PolicyParser, SafeExpr, evaluate_policy
from utf.tarl.runtime import TarlRuntime
from utf.tarl.schema import ContextSchema, FieldSpec
from utf.tarl.spec import TarlVerdict
from utf.thirsty_lang import cli as thirsty_cli
from utf.thirsty_lang.interpreter import Interpreter
from utf.thirsty_lang.proof_obligations import (
    derive_context_schema,
    load_explicit_context_schema,
)


def _allow_if(condition: str, context: dict) -> object:
    return evaluate_policy(
        context,
        policy_text=(
            "policy hostile_context\n"
            f"when {condition} => ALLOW\n"
            "when true => DENY\n"
        ),
    )


@pytest.mark.parametrize(
    ("condition", "context"),
    [
        ('user.role != "admin"', {"user": {"role": False}}),
        ("feature.enabled == 0", {"feature": {"enabled": False}}),
        ('not user.role', {"user": {"role": "admin"}}),
        ('user.role and true', {"user": {"role": "admin"}}),
        ('user.role NOT IN ["admin"]', {"user": {"role": False}}),
        ('LOWER(user.role) == "admin"', {"user": {"role": 1}}),
        ("flags > expected", {"flags": [1], "expected": [0]}),
    ],
)
def test_incompatible_values_cannot_be_coerced_into_allow(condition, context):
    decision = _allow_if(condition, context)
    assert decision.verdict == TarlVerdict.DENY
    assert decision.rule_index == 0
    assert "fail-closed" in decision.reason


def test_resolved_false_is_distinct_from_missing_and_from_numeric_zero():
    assert SafeExpr.evaluate(
        "feature.enabled == false", {"feature": {"enabled": False}}
    )
    with pytest.raises(Exception, match="cannot compare bool and int"):
        SafeExpr.evaluate(
            "feature.enabled == 0", {"feature": {"enabled": False}}
        )
    with pytest.raises(Exception, match="context path 'feature.enabled'"):
        SafeExpr.evaluate("feature.enabled == false", {})


@pytest.mark.parametrize(
    ("condition", "value"),
    [
        ("risk != 0", "NaN"),
        ("risk > 0", "Infinity"),
        ("risk < 0", "-Infinity"),
        ("risk > 0", "1e309"),
        ("risk < 0", "-1e309"),
    ],
)
def test_numeric_strings_cannot_authorize_numeric_comparisons(condition, value):
    with pytest.raises(Exception, match="cannot (compare|order) str and int"):
        SafeExpr.evaluate(condition, {"risk": value})
    decision = _allow_if(condition, {"risk": value})
    assert decision.verdict == TarlVerdict.DENY
    assert "cannot" in decision.reason
    assert "str and int" in decision.reason


@pytest.mark.parametrize(
    ("condition", "context"),
    [
        ('false and user.role != "admin"', {}),
        ('true or user.role == "admin"', {}),
        ('false and LOWER(user.role) == "admin"', {"user": {"role": 1}}),
        ('true or LOWER(user.role) == "admin"', {"user": {"role": 1}}),
    ],
)
def test_boolean_short_circuit_cannot_hide_invalid_context(condition, context):
    policy = PolicyParser.parse(
        "policy hidden_invalid\n"
        f"when {condition} => DENY\n"
        "when true => ALLOW\n"
    )
    decision = evaluate_policy(context, policy=policy)
    assert decision.verdict == TarlVerdict.DENY
    assert decision.rule_index == 0
    assert "fail-closed" in decision.reason


@pytest.mark.parametrize(
    ("quantifier", "users"),
    [
        ("ANY", [{"role": "admin"}, "malformed"]),
        ("ANY", ["malformed", {"role": "admin"}]),
        ("ALL", [{"role": "guest"}, "malformed"]),
        ("ALL", ["malformed", {"role": "guest"}]),
    ],
)
def test_quantifier_order_cannot_hide_malformed_elements(quantifier, users):
    decision = _allow_if(
        f'{quantifier}(users, u -> u.role == "admin")',
        {"users": users},
    )
    assert decision.verdict == TarlVerdict.DENY
    assert "context path 'u.role' cannot be resolved" in decision.reason


@pytest.mark.parametrize("quantifier", ["ALL", "ANY"])
def test_empty_quantifier_collection_is_not_authorization_evidence(quantifier):
    condition = f'{quantifier}(users, u -> user.role == "admin")'
    policy = PolicyParser.parse(
        "policy empty_quantifier\n"
        f"when {condition} => DENY\n"
        "when true => ALLOW\n"
    )
    decision = evaluate_policy({"users": []}, policy=policy)
    assert decision.verdict == TarlVerdict.DENY
    assert decision.rule_index == 0
    assert "empty collection" in decision.reason


def test_quantifier_cannot_shadow_the_trusted_clock():
    condition = "ANY(times, __tarl_trusted_now -> CURRENT_HOUR == 9)"
    with pytest.raises(SafeExpr.ParseError, match="Reserved lambda variable"):
        SafeExpr.evaluate(
            condition,
            {"times": ["2026-08-02T09:00:00"]},
            now=datetime(2026, 8, 2, 8, tzinfo=UTC),
        )


def test_elapsed_since_and_proof_timestamp_use_the_trusted_clock():
    trusted_now = datetime(2026, 1, 1, tzinfo=UTC)
    policy = PolicyParser.parse(
        "policy elapsed\n"
        "when ELAPSED_SINCE(timestamp) > 3600 => ALLOW\n"
        "when true => DENY\n"
    )
    runtime = TarlRuntime(policy).set_context_schema(
        ContextSchema(fields=[FieldSpec("timestamp", kinds=("string",))])
    )
    runtime.set_clock(lambda: trusted_now)
    runtime.set_signing_key("clock-key", b"clock-secret")

    decision, proof = runtime.evaluate_with_proof(
        {"timestamp": "2026-01-01T00:00:00+00:00"}
    )
    assert decision.verdict == TarlVerdict.DENY
    assert proof.evaluated_at == "2026-01-01T00:00:00Z"
    assert proof.context_schema_validation_status == "passed"


def test_time_bound_verdict_expiry_uses_the_trusted_clock():
    trusted_now = datetime(2026, 1, 1, tzinfo=UTC)
    policy = PolicyParser.parse(
        "policy timed\n"
        "when true => ESCALATE for: 5m\n"
    )
    runtime = TarlRuntime(policy).set_context_schema(ContextSchema())
    runtime.set_clock(lambda: trusted_now)

    decision, proof = runtime.evaluate_with_proof({})
    assert decision.expires_at == "2026-01-01T00:05:00+00:00"
    assert proof.evaluated_at == "2026-01-01T00:00:00Z"


def test_current_time_builtin_decision_is_never_reused_from_cache():
    clock = {"now": datetime(2026, 1, 1, tzinfo=UTC)}
    policy = PolicyParser.parse(
        "policy current_hour\n"
        "when CURRENT_HOUR == 10 => ALLOW\n"
        "when true => DENY\n"
    )
    runtime = TarlRuntime(policy).set_clock(lambda: clock["now"])

    assert runtime.evaluate({}).verdict == TarlVerdict.DENY
    clock["now"] = datetime(2026, 1, 1, 10, tzinfo=UTC)
    assert runtime.evaluate({}).verdict == TarlVerdict.ALLOW
    assert runtime.cache.size == 0


def test_elapsed_since_decision_is_never_reused_from_cache():
    clock = {"now": datetime(2026, 1, 1, tzinfo=UTC)}
    policy = PolicyParser.parse(
        "policy elapsed_cache\n"
        "when ELAPSED_SINCE(timestamp) > 3600 => ALLOW\n"
        "when true => DENY\n"
    )
    runtime = TarlRuntime(policy).set_context_schema(
        ContextSchema(fields=[FieldSpec("timestamp", kinds=("string",))])
    )
    runtime.set_clock(lambda: clock["now"])
    context = {"timestamp": "2026-01-01T00:00:00+00:00"}

    assert runtime.evaluate(context).verdict == TarlVerdict.DENY
    clock["now"] = datetime(2026, 1, 1, 2, tzinfo=UTC)
    assert runtime.evaluate(context).verdict == TarlVerdict.ALLOW
    assert runtime.cache.size == 0


def test_caller_and_schema_cannot_shadow_temporal_builtins():
    policy = PolicyParser.parse(
        "policy temporal\n"
        "when CURRENT_HOUR == 8 => ALLOW\n"
        "when true => DENY\n"
    )
    runtime = TarlRuntime(policy)
    runtime.set_clock(lambda: datetime(2026, 1, 1, 8, tzinfo=UTC))
    decision = runtime.evaluate({"CURRENT_HOUR": 23})
    assert decision.verdict == TarlVerdict.DENY
    assert "reserved identifier 'CURRENT_HOUR'" in decision.reason

    with pytest.raises(ValueError, match="reserved identifier"):
        FieldSpec("CURRENT_HOUR", kinds=("number",))


def test_non_finite_arithmetic_results_cannot_collapse_into_allow():
    condition = "submitted * submitted == approved * approved"
    context = {"submitted": 1e308, "approved": 5e307}
    with pytest.raises(Exception, match="non-finite arithmetic result"):
        SafeExpr.evaluate(condition, context)
    decision = _allow_if(condition, context)
    assert decision.verdict == TarlVerdict.DENY
    assert "non-finite arithmetic result" in decision.reason


def test_membership_match_cannot_hide_incompatible_collection_values():
    decision = _allow_if(
        "role IN trusted_roles",
        {"role": "admin", "trusted_roles": ["admin", False]},
    )
    assert decision.verdict == TarlVerdict.DENY
    assert "membership collection contains an incompatible bool value" in (
        decision.reason
    )


def test_nested_boolean_and_number_values_are_not_python_equal():
    context = {"flags": [True], "expected": [1]}
    assert SafeExpr.evaluate("flags == expected", context) is False
    assert _allow_if("flags == expected", context).verdict == TarlVerdict.DENY


@pytest.mark.parametrize(
    "value",
    [
        ("admin",),
        {"admin"},
        frozenset({"admin"}),
        object(),
        math.nan,
        math.inf,
        -math.inf,
    ],
)
def test_non_json_context_values_are_denied(value):
    decision = evaluate_policy(
        {"role": value},
        policy_text="policy p\nwhen true => ALLOW\n",
    )
    assert decision.verdict == TarlVerdict.DENY
    assert "context representation violation" in decision.reason


def test_python_object_cannot_normalize_itself_during_snapshot():
    class MasqueradingValue:
        def __deepcopy__(self, memo):
            return "admin"

    decision = _allow_if(
        'user.role == "admin"', {"user": {"role": MasqueradingValue()}}
    )
    assert decision.verdict == TarlVerdict.DENY
    assert "unsupported type MasqueradingValue" in decision.reason


def test_hostile_non_string_key_fails_inside_the_context_boundary():
    class HostileKey:
        def __hash__(self):
            return 1

        def __str__(self):
            raise RuntimeError("string conversion must not run")

    decision = evaluate_policy(
        {HostileKey(): "admin"},
        policy_text="policy p\nwhen true => ALLOW\n",
    )
    assert decision.verdict == TarlVerdict.DENY
    assert decision.reason == (
        "context representation violation: object keys must be strings"
    )


def test_circular_context_is_denied_without_escaping_the_runtime():
    context: dict = {}
    context["self"] = context
    decision = evaluate_policy(
        context,
        policy_text="policy p\nwhen true => ALLOW\n",
    )
    assert decision.verdict == TarlVerdict.DENY
    assert "circular object reference" in decision.reason


@pytest.mark.parametrize(
    "raw",
    [
        '{"role":"guest","role":"admin"}',
        '{"risk":NaN}',
        '{"risk":Infinity}',
        '{"risk":-Infinity}',
    ],
)
def test_json_loader_rejects_ambiguous_or_non_finite_input(raw):
    with pytest.raises(ContextRepresentationError):
        load_context_json(raw)


def test_caller_cannot_inject_a_registered_source_namespace():
    runtime = TarlRuntime(
        PolicyParser.parse(
            "policy source_gate\n"
            'when role IN source:trusted_roles => ALLOW\n'
            "when true => DENY\n"
        )
    )
    decision = runtime.evaluate(
        {"role": "admin", "source:trusted_roles": ["admin"]}
    )
    assert decision.verdict == TarlVerdict.DENY
    assert "reserved source field 'source:trusted_roles'" in decision.reason


def test_registered_source_must_use_the_authoritative_json_domain():
    runtime = TarlRuntime(
        PolicyParser.parse(
            "policy source_gate\n"
            'when role IN source:trusted_roles => ALLOW\n'
            "when true => DENY\n"
        )
    ).register_source("trusted_roles", {"admin"})
    decision = runtime.evaluate({"role": "admin"})
    assert decision.verdict == TarlVerdict.DENY
    assert "unsupported type set" in decision.reason


@pytest.mark.parametrize("name", ["", "bad-name", "bad:name", 1])
def test_registered_source_names_match_the_policy_tokenizer(name):
    runtime = TarlRuntime(PolicyParser.parse("policy p\nwhen true => DENY\n"))
    with pytest.raises(ValueError, match="registered source name"):
        runtime.register_source(name, ["admin"])


def _source_bound_proof():
    runtime = TarlRuntime(
        PolicyParser.parse(
            "policy source_gate\n"
            'when role IN source:trusted_roles => ALLOW\n'
            "when true => DENY\n"
        )
    )
    runtime.set_context_schema(
        ContextSchema(fields=[FieldSpec("role", kinds=("string",))])
    )
    runtime.register_source("trusted_roles", ["admin"])
    runtime.set_signing_key("source-key", b"source-secret")
    return runtime.evaluate_with_proof({"role": "admin"})[1]


def test_tarl_verify_cli_requires_the_exact_source_enriched_context(
    monkeypatch, tmp_path, capsys
):
    proof_path = tmp_path / "source-proof.json"
    proof_path.write_text(_source_bound_proof().to_json(), encoding="utf-8")

    base_args = [
        "tarl",
        "verify",
        str(proof_path),
        "--hmac-key",
        "source-key:" + b"source-secret".hex(),
        "--context",
        '{"role":"admin"}',
        "--json",
    ]
    monkeypatch.setattr("sys.argv", base_args)
    with pytest.raises(SystemExit) as missing:
        from utf.tarl import cli as tarl_cli

        tarl_cli.main()
    assert missing.value.code == 1
    assert json.loads(capsys.readouterr().out)["checks"][
        "evaluated_context_binding"
    ] is False

    monkeypatch.setattr(
        "sys.argv",
        base_args[:-1]
        + [
            "--evaluated-context",
            '{"role":"admin","source:trusted_roles":["admin"]}',
            "--json",
        ],
    )
    with pytest.raises(SystemExit) as accepted:
        tarl_cli.main()
    assert accepted.value.code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["valid"] is True
    assert result["checks"]["evaluated_context_binding"] is True


def test_context_schema_cannot_configure_allow_on_validation_failure():
    with pytest.raises(ValueError, match="on_violation cannot be ALLOW"):
        ContextSchema(on_violation=TarlVerdict.ALLOW)
    with pytest.raises(ValueError, match="on_violation cannot be ALLOW"):
        ContextSchema.from_dict({"on_violation": "ALLOW"})


def test_broker_cannot_advance_on_schema_inadmissible_allow():
    policy = PolicyParser.parse("policy p\nwhen LEN(mystery) > 0 => ALLOW\n")
    unbound = CapabilityBroker(TarlRuntime(policy), authority="admin")
    denied = unbound.request("write", "record", mystery=["present"])
    assert denied.allowed is False
    assert denied.verdict == TarlVerdict.DENY
    assert "positive verdict inadmissible" in denied.reason

    bound_runtime = TarlRuntime(policy).set_context_schema(
        ContextSchema(fields=[FieldSpec("mystery", kinds=("list",))])
    )
    accepted = CapabilityBroker(bound_runtime, authority="admin").request(
        "write", "record", mystery=["present"]
    )
    assert accepted.allowed is True
    assert accepted.proof.context_schema_validation_status == "passed"


def test_governed_runtime_cannot_advance_on_schema_inadmissible_allow():
    policy = PolicyParser.parse("policy p\nwhen LEN(mystery) > 0 => ALLOW\n")
    decl = SimpleNamespace(
        name="promote",
        requires_expr=None,
        invariant_expr=None,
        ensures_expr=None,
    )

    interpreter = Interpreter()
    interpreter.mode = "governed"
    interpreter.set_authority("admin")
    interpreter.attach_tarl(TarlRuntime(policy))
    allowed, reason, proof = interpreter._enforce_governance(
        {"mystery": ["present"]}, decl, phase="entry"
    )
    assert allowed is False
    assert proof.verdict == TarlVerdict.DENY
    assert "positive verdict inadmissible" in reason

    interpreter.attach_tarl(
        TarlRuntime(policy).set_context_schema(
            ContextSchema(fields=[FieldSpec("mystery", kinds=("list",))])
        )
    )
    allowed, _reason, proof = interpreter._enforce_governance(
        {"mystery": ["present"]}, decl, phase="entry"
    )
    assert allowed is True
    assert proof.context_schema_validation_status == "passed"


_CLI_GOVERNED_PROGRAM = (
    "module context_gate: governed\n"
    "glass authorize_step(mystery) requires true {\n"
    '    return "advanced"\n'
    "}\n"
    'drink result = authorize_step("yes")\n'
    "pour result\n"
)
_CLI_INCOMPLETE_POLICY = (
    "policy context_gate\n"
    'when action == "write" => ALLOW\n'
    "when LEN(mystery) > 0 => ALLOW\n"
    "when true => DENY\n"
)


def _write_cli_fixture(tmp_path, name: str, content: str) -> str:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path)


def _run_thirsty_cli(monkeypatch, *args: str) -> None:
    monkeypatch.setattr("sys.argv", ["thirsty", *args])
    thirsty_cli.main()


def test_cli_governed_run_rejects_incomplete_derived_context_schema(
    monkeypatch, tmp_path, capsys
):
    program = _write_cli_fixture(
        tmp_path, "context-gate.thirsty", _CLI_GOVERNED_PROGRAM
    )
    policy = _write_cli_fixture(
        tmp_path, "context-gate.tarl", _CLI_INCOMPLETE_POLICY
    )
    assert derive_context_schema(_CLI_INCOMPLETE_POLICY).complete is False

    with pytest.raises(SystemExit) as denied:
        _run_thirsty_cli(
            monkeypatch,
            "run",
            program,
            "--thirst-level",
            "governed",
            "--authority",
            "admin",
            "--policy",
            policy,
        )

    assert denied.value.code == 2
    captured = capsys.readouterr()
    assert "positive verdict inadmissible" in captured.err
    assert "advanced" not in captured.out


def test_cli_governed_run_accepts_matching_explicit_context_schema(
    monkeypatch, tmp_path, capsys
):
    program = _write_cli_fixture(
        tmp_path, "context-gate.thirsty", _CLI_GOVERNED_PROGRAM
    )
    policy = _write_cli_fixture(
        tmp_path, "context-gate.tarl", _CLI_INCOMPLETE_POLICY
    )
    schema = _write_cli_fixture(
        tmp_path,
        "context-schema.json",
        json.dumps(
            {
                "fields": [
                    {
                        "name": "action",
                        "kinds": ["string"],
                        "required": True,
                    },
                    {
                        "name": "mystery",
                        "kinds": ["string"],
                        "required": False,
                    },
                ]
            }
        ),
    )

    _run_thirsty_cli(
        monkeypatch,
        "run",
        program,
        "--thirst-level",
        "governed",
        "--authority",
        "admin",
        "--policy",
        policy,
        "--context-schema",
        schema,
    )

    captured = capsys.readouterr()
    assert "advanced" in captured.out
    assert captured.err == ""


def test_derived_context_schema_refreshes_after_set_policy():
    first_policy = PolicyParser.parse(
        'policy first\nwhen role == "admin" => ALLOW\nwhen true => DENY\n'
    )
    second_policy = PolicyParser.parse(
        "policy second\nwhen amount > 0 => ALLOW\nwhen true => DENY\n"
    )
    runtime = TarlRuntime(first_policy)

    assert runtime.ensure_context_schema() is True
    first_decision, first_proof = runtime.evaluate_with_proof(
        {"role": "admin"}
    )
    runtime.set_policy(second_policy)
    assert runtime.ensure_context_schema() is True
    second_decision, second_proof = runtime.evaluate_with_proof({"amount": 1})

    expected_second = ContextSchema.from_dict(
        derive_context_schema(second_policy.source).to_dict()
    )
    assert first_decision.verdict == TarlVerdict.ALLOW
    assert second_decision.verdict == TarlVerdict.ALLOW
    assert first_proof.context_schema_hash != second_proof.context_schema_hash
    assert second_proof.context_schema_hash == expected_second.fingerprint()
    assert second_proof.context_schema_validation_status == "passed"


def test_policy_text_override_binds_schema_derived_for_the_override():
    base_policy = PolicyParser.parse(
        'policy base\nwhen role == "admin" => ALLOW\nwhen true => DENY\n'
    )
    override_text = (
        "policy override\n"
        "when amount > 100 => ALLOW\n"
        "when true => DENY\n"
    )
    runtime = TarlRuntime(base_policy)
    assert runtime.ensure_context_schema() is True
    base_schema_hash = ContextSchema.from_dict(
        derive_context_schema(base_policy.source).to_dict()
    ).fingerprint()

    decision, proof = runtime.evaluate_with_proof(
        {"role": "admin", "amount": 200},
        policy_text=override_text,
    )
    override_schema_hash = ContextSchema.from_dict(
        derive_context_schema(override_text).to_dict()
    ).fingerprint()

    assert decision.verdict == TarlVerdict.ALLOW
    assert proof.context_schema_validation_status == "passed"
    assert proof.context_schema_hash == override_schema_hash
    assert proof.context_schema_hash != base_schema_hash


def test_incomplete_policy_text_override_fails_closed():
    base_policy = PolicyParser.parse(
        'policy base\nwhen role == "admin" => ALLOW\nwhen true => DENY\n'
    )
    runtime = TarlRuntime(base_policy)
    assert runtime.ensure_context_schema() is True
    override_text = "policy override\nwhen LEN(mystery) > 0 => ALLOW\n"

    decision, proof = runtime.evaluate_with_proof(
        {"role": "admin", "mystery": ["present"]},
        policy_text=override_text,
    )
    assert decision.verdict == TarlVerdict.DENY
    assert "could not be derived completely" in decision.reason
    assert proof.context_schema_validation_status == "error"


@pytest.mark.parametrize(
    "schema_document",
    [
        {
            "representation_id": CONTEXT_REPRESENTATION_ID,
            "representation": {"id": "attacker.flat-dotted.v1"},
            "fields": [],
        },
        {
            "representation": {
                "id": CONTEXT_REPRESENTATION_ID,
                "path_model": "flat-dotted-keys",
                "normalization": "none",
            },
            "fields": [],
        },
        {"on_violation": "ALLOW", "fields": []},
        {"normalization_algorithm": "flatten", "fields": []},
        {"status": "incomplete", "fields": []},
        {
            "fields": [
                {
                    "name": "role",
                    "kinds": ["string"],
                    "coerce": True,
                }
            ]
        },
        {
            "fields": [
                {
                    "name": "role",
                    "kind": "string",
                    "kinds": ["string"],
                }
            ]
        },
    ],
)
def test_explicit_schema_loader_rejects_metadata_laundering(
    schema_document, tmp_path
):
    path = tmp_path / "context-schema.json"
    path.write_text(json.dumps(schema_document), encoding="utf-8")
    with pytest.raises(ValueError):
        load_explicit_context_schema(str(path))


def test_explicit_schema_loader_rejects_duplicate_metadata(tmp_path):
    path = tmp_path / "context-schema.json"
    path.write_text(
        '{"representation":{"path_model":"nested-objects",'
        '"path_model":"flat-dotted-keys"},"fields":[]}',
        encoding="utf-8",
    )
    with pytest.raises(ContextRepresentationError, match="duplicate key"):
        load_explicit_context_schema(str(path))


@pytest.mark.parametrize(
    "schema_document",
    [
        {
            "fields": [
                {"name": "role", "kinds": ["string"], "required": 1}
            ]
        },
        {
            "fields": [
                {"name": "role", "kinds": ["string"]},
                {"name": "role", "kinds": ["string"]},
            ]
        },
        {"fields": [{"name": "role", "kinds": ["unknown"]}]},
    ],
)
def test_explicit_schema_loader_does_not_silently_coerce_fields(
    schema_document, tmp_path
):
    path = tmp_path / "context-schema.json"
    path.write_text(json.dumps(schema_document), encoding="utf-8")
    with pytest.raises(ValueError):
        load_explicit_context_schema(str(path))


def test_explicit_schema_loader_preserves_escalation_verdict(tmp_path):
    path = tmp_path / "context-schema.json"
    path.write_text(
        json.dumps({"on_violation": "ESCALATE", "fields": []}),
        encoding="utf-8",
    )
    schema = load_explicit_context_schema(str(path)).to_dict()
    assert schema["on_violation"] == "ESCALATE"
    assert ContextSchema.from_dict(schema).on_violation == TarlVerdict.ESCALATE
