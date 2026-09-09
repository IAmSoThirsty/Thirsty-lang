"""Governed call data must match its authorization snapshot at handoff."""

from unittest.mock import Mock

import pytest

from utf.tarl.authority import VerifiedAuthority
from utf.tarl.context import prepare_context
from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
from utf.tarl.spec import TarlVerdict
from utf.thirsty_lang.interpreter import GovernanceViolation, Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser


def parse(source):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors, lexer.errors
    assert not parser.errors, parser.errors
    return program


@pytest.fixture
def make_interpreter():
    interpreters = []
    runtimes = []

    def make(*, optimization=0, policy="when true => ALLOW", unsafe=False):
        interpreter = Interpreter(opt_level=optimization, allow_ungoverned=unsafe)
        interpreters.append(interpreter)
        if policy is not None:
            runtime = TarlRuntime(PolicyParser.parse(policy))
            runtimes.append(runtime)
            interpreter.attach_tarl(runtime).set_authority("value-integrity")
        return interpreter

    yield make
    for interpreter in interpreters:
        interpreter.executor.shutdown(wait=True)
    for runtime in runtimes:
        runtime.shutdown()


def assert_denied(error, interpreter):
    assert error.value.proof is not None
    assert error.value.proof.verdict is TarlVerdict.DENY
    assert interpreter._last_proof is error.value.proof


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("route", ["direct", "cascade", "host"])
@pytest.mark.parametrize("stage", ["contract", "source", "schema", "policy", "audit"])
def test_callback_argument_mutation_denies_before_body(
    optimization, route, stage, make_interpreter, monkeypatch
):
    interpreter = make_interpreter(optimization=optimization)
    values = {"items": [1]}
    hit = Mock()
    mutations = []
    enabled = [True]

    def mutate():
        if enabled[0]:
            mutations.append(stage)
            values["items"][0] = 99
        return True

    interpreter.env.define("hit", hit)
    interpreter.env.define("values", values)
    interpreter.env.define("predicate", mutate if stage == "contract" else lambda: True)
    interpreter.interpret(
        parse("glass take(data) requires predicate() { hit()\nreturn data.items[0] }")
    )
    original_env = interpreter.env
    runtime = interpreter.tarl_runtime
    policy_proofs = []
    evaluate = runtime.evaluate_with_proof

    def evaluate_and_capture(context, *args, **kwargs):
        result = evaluate(context, *args, **kwargs)
        policy_proofs.append(result[1])
        if stage == "policy":
            mutate()
        return result

    monkeypatch.setattr(runtime, "evaluate_with_proof", evaluate_and_capture)
    if stage == "source":
        runtime.register_source("probe", mutate)
    elif stage == "schema":
        ensure = runtime.ensure_context_schema

        def ensure_and_mutate():
            result = ensure()
            mutate()
            return result

        monkeypatch.setattr(runtime, "ensure_context_schema", ensure_and_mutate)
    elif stage == "audit":

        class Audit:
            def store(self, proof, expires_at=None):
                mutate()
                return 1

        runtime.set_archive(Audit()).set_require_audit()

    with pytest.raises(GovernanceViolation, match="context changed") as error:
        if route == "host":
            interpreter.env.get("take")(values)
        else:
            interpreter.interpret(
                parse("cascade take(values)" if route == "cascade" else "take(values)")
            )
    assert_denied(error, interpreter)
    assert interpreter.env is original_env
    assert mutations == [stage]
    hit.assert_not_called()
    trace = error.value.proof.trace[0]
    assert (
        trace["expected_context_hash"]
        == prepare_context({"data": {"items": [1]}}).original_context_hash
    )
    assert (
        trace["observed_context_hash"]
        == prepare_context({"data": {"items": [99]}}).original_context_hash
    )
    if policy_proofs:
        assert trace["prior_policy_hash"] == policy_proofs[-1].policy_hash
        assert trace["prior_context_hash"] == policy_proofs[-1].context_hash
        assert policy_proofs[-1].verdict is TarlVerdict.ALLOW
    enabled[0] = False
    values["items"][0] = 1
    assert interpreter.interpret(parse("take(values)")) == 1
    hit.assert_called_once_with()


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("route", ["direct", "cascade"])
@pytest.mark.parametrize("mutating_owner", ["definer", "caller"])
def test_foreign_policies_cannot_authorize_different_argument_states(
    optimization, route, mutating_owner, make_interpreter
):
    definer = make_interpreter(optimization=optimization)
    caller = make_interpreter(optimization=optimization)
    values = [1]
    hit = Mock()
    definer.env.define("hit", hit)
    callback = definer.interpret(
        parse("glass take(data) requires true { hit()\nreturn data[0] }\ntake")
    )
    owner = definer if mutating_owner == "definer" else caller
    source_calls = []

    def source():
        source_calls.append(True)
        values[0] = 99
        return True

    owner.tarl_runtime.register_source("mutator", source)
    caller.env.define("callback", callback)
    caller.env.define("values", values)
    with pytest.raises(GovernanceViolation, match="context changed") as error:
        caller.interpret(
            parse(
                "cascade callback(values)" if route == "cascade" else "callback(values)"
            )
        )
    assert error.value.proof.verdict is TarlVerdict.DENY
    assert owner._last_proof is error.value.proof
    assert source_calls == [True]
    hit.assert_not_called()


@pytest.mark.parametrize("route", ["direct", "cascade"])
def test_final_credential_callback_cannot_mutate_authorized_values(
    route, make_interpreter
):
    definer = make_interpreter()
    caller = make_interpreter()
    values = [1]
    hit = Mock()
    definer.env.define("hit", hit)
    policy_checks = []

    class Audit:
        def store(self, proof, expires_at=None):
            policy_checks.append(proof)
            return len(policy_checks)

    definer.tarl_runtime.set_archive(Audit())
    caller.tarl_runtime.set_archive(Audit())
    mutated = []

    def revalidate(_now):
        if len(policy_checks) == 2:
            values[0] = 99
            mutated.append(True)
        return None

    credential = VerifiedAuthority("same", (), _revalidate=revalidate)
    definer.set_verified_authority(credential)
    caller.set_verified_authority(credential)
    caller.env.define(
        "callback",
        definer.interpret(
            parse("glass take(data) requires true { hit()\nreturn data[0] }\ntake")
        ),
    )
    caller.env.define("values", values)
    with pytest.raises(GovernanceViolation, match="context changed") as error:
        caller.interpret(
            parse(
                "cascade callback(values)" if route == "cascade" else "callback(values)"
            )
        )
    assert error.value.proof.verdict is TarlVerdict.DENY
    assert mutated
    assert len(policy_checks) == 2
    hit.assert_not_called()


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("host_value", [(7,), b"value", object(), lambda: 7])
@pytest.mark.parametrize("contract", ["requires true", "ensures true"])
def test_unsupported_result_never_reaches_caller(
    optimization, host_value, contract, make_interpreter
):
    interpreter = make_interpreter(optimization=optimization)
    hit = Mock()
    interpreter.env.define("hit", hit)
    interpreter.env.define("host_value", host_value)
    source = (
        f"glass make() {contract} {{ hit()\nreturn host_value }}\n"
        "drink escaped = make()"
    )
    with pytest.raises(GovernanceViolation, match="unsupported") as error:
        interpreter.interpret(parse(source))
    assert_denied(error, interpreter)
    assert not interpreter.env.has("escaped")
    hit.assert_called_once_with()  # Entry passed; exit denial cannot undo body effects.
    assert any(
        item["kind"] == "projection-rejected" for item in error.value.proof.trace
    )
    assert error.value.proof.trace[0]["phase"] == "exit"


@pytest.mark.parametrize("unsafe", [False, True])
@pytest.mark.parametrize("receiver", ["self", "implicit"])
def test_all_method_receiver_conventions_preserve_valid_contracts(
    unsafe, receiver, make_interpreter
):
    interpreter = make_interpreter(
        unsafe=unsafe, policy=None if unsafe else "when true => ALLOW"
    )
    hit = Mock(return_value=None)
    predicate = Mock(return_value=True)
    interpreter.env.define("hit", hit)
    interpreter.env.define("predicate", predicate)
    params = "self" if receiver == "self" else ""
    interpreter.interpret(
        parse(
            f"fountain Box {{ glass take({params}) requires predicate() {{ hit() }} }}\n(new Box()).take()"
        )
    )
    hit.assert_called_once_with()
    predicate.assert_called_once_with()
    assert interpreter._last_proof.verdict is TarlVerdict.ALLOW
    assert interpreter._last_proof.context_conflict_status == "none"


@pytest.mark.parametrize("unsafe", [False, True])
@pytest.mark.parametrize("invalid", [object(), (1,), {1: "value"}, float("nan")])
def test_invalid_context_can_never_make_an_allow_certificate(
    unsafe, invalid, make_interpreter
):
    interpreter = make_interpreter(unsafe=unsafe, policy=None)
    proof = interpreter._make_decision_proof(
        source="contract:probe:exit",
        context={"result": invalid},
        verdict=TarlVerdict.ALLOW,
        matched_condition="",
        trace=[],
    )
    assert proof.verdict is TarlVerdict.DENY
    assert proof.normalization_algorithm_id == "rejected"
    allowed, _reason, proof = interpreter._enforce_governance(
        {"result": invalid}, phase="exit", enforce_mode_guard=False
    )
    assert not allowed
    assert proof.verdict is TarlVerdict.DENY


@pytest.mark.parametrize("optimization", range(4))
def test_body_mutation_gets_a_fresh_exit_snapshot(optimization, make_interpreter):
    interpreter = make_interpreter(optimization=optimization)
    values = [1]
    interpreter.env.define("values", values)
    result = interpreter.interpret(
        parse(
            "glass change(data) requires data[0] == 1 ensures result[0] == 2 "
            "{ data[0] = 2\nreturn data }\nchange(values)"
        )
    )
    assert result is values
    assert result == [2]
    proof = interpreter._last_proof
    assert proof.verdict is TarlVerdict.ALLOW
    assert proof.context_conflict_status == "none"
    assert (
        proof.original_context_hash
        == prepare_context({"data": [2], "result": [2]}).original_context_hash
    )


def test_exit_contract_mutation_denies_before_return(make_interpreter):
    interpreter = make_interpreter()
    result = [1]
    interpreter.env.define("result_value", result)

    def mutate():
        result[0] = 99
        return True

    interpreter.env.define("predicate", mutate)
    with pytest.raises(GovernanceViolation, match="exit context changed") as error:
        interpreter.interpret(
            parse(
                "glass make() ensures predicate() { return result_value }\ndrink escaped = make()"
            )
        )
    assert_denied(error, interpreter)
    assert result == [99]
    assert not interpreter.env.has("escaped")


def test_policy_allow_must_bind_exact_submitted_context(make_interpreter, monkeypatch):
    interpreter = make_interpreter(
        policy="when ANY(data, value -> value == 99) => ALLOW\nwhen true => DENY"
    )
    hit = Mock()
    values = [1]
    interpreter.env.define("hit", hit)
    interpreter.env.define("values", values)
    interpreter.interpret(
        parse("glass take(data) requires true { hit()\nreturn data[0] }")
    )
    evaluate = interpreter.tarl_runtime.evaluate_with_proof

    def mutate_policy_copy(context):
        context["data"][0] = 99
        return evaluate(context)

    monkeypatch.setattr(
        interpreter.tarl_runtime, "evaluate_with_proof", mutate_policy_copy
    )
    with pytest.raises(GovernanceViolation, match="context.*bind") as error:
        interpreter.interpret(parse("take(values)"))
    assert_denied(error, interpreter)
    assert values == [1]
    hit.assert_not_called()


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("expression", ["Row(7)", "State.Ready", "new Box()"])
def test_native_result_exit_proof_binds_projected_value(
    optimization, expression, make_interpreter
):
    from utf.thirsty_lang.governed_values import project_governed_context

    interpreter = make_interpreter(optimization=optimization)
    result = interpreter.interpret(
        parse(
            "struct Row { value: Int }\nenum State { Ready }\nfountain Box { value = 7 }\n"
            f"glass make() ensures true {{ return {expression} }}\nmake()"
        )
    )
    proof = interpreter._last_proof
    assert proof.verdict is TarlVerdict.ALLOW
    assert proof.context_conflict_status == "none"
    assert (
        proof.original_context_hash
        == prepare_context(
            project_governed_context({"result": result})
        ).original_context_hash
    )


@pytest.mark.parametrize("kind", ["record", "receiver"])
@pytest.mark.parametrize("route", ["direct", "cascade"])
def test_native_alias_mutation_is_rechecked_before_body(kind, route, make_interpreter):
    interpreter = make_interpreter()
    hit = Mock()
    interpreter.env.define("hit", hit)
    if kind == "record":
        source = (
            "struct Row { value: Int }\ndrink data = Row(1)\n"
            "glass take(record) requires true { hit()\nreturn record.value }"
        )
        call = "take(data)"
    else:
        source = (
            "fountain Box { value = 1\n"
            "glass take(self) requires true { hit()\nreturn self.value } }\n"
            "drink data = new Box()"
        )
        call = "data.take()"
    interpreter.interpret(parse(source))
    data = interpreter.env.get("data")
    mutations = []

    def mutate():
        data.fields["value"] = 99
        mutations.append(True)
        return True

    interpreter.tarl_runtime.register_source("probe", mutate)
    with pytest.raises(GovernanceViolation, match="context changed") as error:
        interpreter.interpret(parse("cascade " + call if route == "cascade" else call))
    assert_denied(error, interpreter)
    assert mutations == [True]
    hit.assert_not_called()


@pytest.mark.parametrize("phase", ["entry", "exit"])
def test_projection_denial_certificate_never_calls_host_value_repr(
    phase, make_interpreter
):
    interpreter = make_interpreter()
    hooks = []

    class HostValue:
        def __repr__(self):
            hooks.append("repr")
            raise AssertionError("host representation hooks must not run")

        def __deepcopy__(self, memo):
            hooks.append("deepcopy")
            raise AssertionError("host copy hooks must not run")

    interpreter.env.define("host_value", HostValue())
    if phase == "entry":
        source = "glass take(value) requires true { return 1 }\ntake(host_value)"
    else:
        source = "glass take() ensures true { return host_value }\ntake()"
    with pytest.raises(GovernanceViolation) as error:
        interpreter.interpret(parse(source))
    assert_denied(error, interpreter)
    assert hooks == []


@pytest.mark.parametrize("route", ["direct", "cascade", "host"])
def test_governed_result_parameter_collision_denies_at_entry(
    route, make_interpreter, monkeypatch
):
    interpreter = make_interpreter()
    predicate = Mock(return_value=True)
    hit = Mock()
    interpreter.env.define("predicate", predicate)
    interpreter.env.define("hit", hit)
    interpreter.interpret(
        parse("glass take(result) requires predicate() { hit()\nreturn result }")
    )
    evaluate = Mock(wraps=interpreter.tarl_runtime.evaluate_with_proof)
    monkeypatch.setattr(interpreter.tarl_runtime, "evaluate_with_proof", evaluate)
    with pytest.raises(
        GovernanceViolation, match="reserved governed parameter"
    ) as error:
        if route == "host":
            interpreter.env.get("take")(1)
        else:
            interpreter.interpret(
                parse("cascade take(1)" if route == "cascade" else "take(1)")
            )
    assert_denied(error, interpreter)
    predicate.assert_not_called()
    hit.assert_not_called()
    evaluate.assert_not_called()
    assert error.value.proof.trace[0]["phase"] == "entry"


@pytest.mark.parametrize("unsafe", [False, True])
def test_method_result_parameter_collision_denies_even_in_compatibility(
    unsafe, make_interpreter
):
    interpreter = make_interpreter(
        unsafe=unsafe, policy=None if unsafe else "when true => ALLOW"
    )
    with pytest.raises(
        GovernanceViolation, match="reserved governed parameter"
    ) as error:
        interpreter.interpret(
            parse(
                "fountain Box { glass take(result) requires true { return result } }\n(new Box()).take(1)"
            )
        )
    assert_denied(error, interpreter)


def test_result_name_remains_available_to_uncontracted_functions(make_interpreter):
    interpreter = make_interpreter(policy=None)
    assert (
        interpreter.interpret(parse("glass take(result) { return result }\ntake(7)"))
        == 7
    )


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("kind", ["function", "lambda", "morph", "governed"])
@pytest.mark.parametrize("route", ["direct", "cascade", "host"])
def test_duplicate_parameters_reject_before_binding_and_callbacks(
    optimization, kind, route, make_interpreter, monkeypatch
):
    interpreter = make_interpreter(optimization=optimization)
    hit = Mock()
    predicate = Mock(return_value=True)
    interpreter.env.define("hit", hit)
    interpreter.env.define("predicate", predicate)
    interpreter.env.define("value", "outer")
    body = "hit()\nreturn value"
    if kind == "lambda":
        source = f"drink take = glass(value, value) {{ {body} }}"
    elif kind == "morph":
        source = f"morph take(value, value) {{ {body} }}"
    else:
        contract = " requires predicate()" if kind == "governed" else ""
        source = f"glass take(value, value){contract} {{ {body} }}"
    interpreter.interpret(parse(source + "\nglass good(value) { return value }"))
    original_env = interpreter.env
    evaluate = Mock(wraps=interpreter.tarl_runtime.evaluate_with_proof)
    monkeypatch.setattr(interpreter.tarl_runtime, "evaluate_with_proof", evaluate)
    callback = interpreter.env.get("take")
    events = []

    def lookup():
        events.append("callee")
        return callback

    def first():
        events.append("first")
        return 1

    def second():
        events.append("second")
        return 99

    interpreter.env.define("lookup", lookup)
    interpreter.env.define("first", first)
    interpreter.env.define("second", second)
    with pytest.raises(TypeError, match="duplicate parameter 'value'"):
        if route == "host":
            lookup()(first(), second())
        else:
            expression = "lookup()(first(), second())"
            interpreter.interpret(
                parse("cascade " + expression if route == "cascade" else expression)
            )
    assert events == ["callee", "first", "second"]
    assert interpreter.env is original_env
    assert interpreter.env.get("value") == "outer"
    assert interpreter._last_proof is None
    hit.assert_not_called()
    predicate.assert_not_called()
    evaluate.assert_not_called()
    assert interpreter.interpret(parse("good(7)")) == 7


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize(
    "params", ["self,self", "self,this", "this,this", "amount,this"]
)
@pytest.mark.parametrize("route", ["direct", "cascade", "host"])
def test_receiver_cannot_be_replaced_by_parameter_binding(
    optimization, params, route, make_interpreter, monkeypatch
):
    interpreter = make_interpreter(
        optimization=optimization,
        policy="when self.fields.value == 1 => ALLOW\nwhen true => DENY",
    )
    hit = Mock()
    predicate = Mock(return_value=True)
    interpreter.env.define("hit", hit)
    interpreter.env.define("predicate", predicate)
    program = parse(
        "fountain Box { value = 0\n"
        "glass take() requires predicate() { hit()\nreturn this.value } }\n"
        "drink original = new Box()\ndrink supplied = new Box()\n"
        "drink callback = original.take"
    )
    # Explicit `this` is a host AST convention; it is not parameter syntax.
    program.stmts[0].methods[0].params = [(name, None) for name in params.split(",")]
    interpreter.interpret(program)
    interpreter.env.get("original").fields["value"] = 99
    supplied = interpreter.env.get("supplied")
    supplied.fields["value"] = 1
    interpreter.env.define("self", "outer")
    original_env = interpreter.env
    evaluate = Mock(wraps=interpreter.tarl_runtime.evaluate_with_proof)
    monkeypatch.setattr(interpreter.tarl_runtime, "evaluate_with_proof", evaluate)
    arguments = [0, supplied] if params.startswith("amount") else [supplied]
    with pytest.raises(
        TypeError, match="duplicate parameter|conflicts with bound receiver"
    ):
        if route == "host":
            interpreter.env.get("callback")(*arguments)
        else:
            arguments_source = "0, supplied" if len(arguments) == 2 else "supplied"
            expression = f"callback({arguments_source})"
            interpreter.interpret(
                parse("cascade " + expression if route == "cascade" else expression)
            )
    assert interpreter.env is original_env
    assert interpreter.env.get("self") == "outer"
    assert interpreter.env.get("original").fields["value"] == 99
    assert supplied.fields["value"] == 1
    assert interpreter._last_proof is None
    hit.assert_not_called()
    predicate.assert_not_called()
    evaluate.assert_not_called()


@pytest.mark.parametrize(
    "params", ["self,self", "value,value", "self,this", "value,this", "this,this"]
)
@pytest.mark.parametrize("route", ["new", "alias", "cascade", "host"])
def test_invalid_initializer_bindings_reject_before_field_defaults(
    params, route, make_interpreter, monkeypatch
):
    interpreter = make_interpreter()
    default_value = Mock(return_value=7)
    predicate = Mock(return_value=True)
    hit = Mock(return_value=None)
    interpreter.env.define("default_value", default_value)
    interpreter.env.define("predicate", predicate)
    interpreter.env.define("hit", hit)
    program = parse(
        "fountain Box { value = default_value()\n"
        "glass init() requires predicate() { hit() } }\ndrink build = Box"
    )
    names = params.split(",")
    program.stmts[0].methods[0].params = [(name, None) for name in names]
    interpreter.interpret(program)
    original_env = interpreter.env
    evaluate = Mock(wraps=interpreter.tarl_runtime.evaluate_with_proof)
    monkeypatch.setattr(interpreter.tarl_runtime, "evaluate_with_proof", evaluate)
    arguments = [1] * (len(names) - int(names[0] in ("self", "this")))
    argument_source = ", ".join("1" for _ in arguments)
    expressions = {
        "new": f"new Box({argument_source})",
        "alias": f"build({argument_source})",
        "cascade": f"cascade build({argument_source})",
    }
    with pytest.raises(
        TypeError, match="duplicate parameter|conflicts with bound receiver"
    ):
        if route == "host":
            interpreter.env.get("build")(*arguments)
        else:
            interpreter.interpret(parse(expressions[route]))
    assert interpreter.env is original_env
    assert not interpreter.env.has("this")
    assert interpreter._last_proof is None
    default_value.assert_not_called()
    predicate.assert_not_called()
    hit.assert_not_called()
    evaluate.assert_not_called()


@pytest.mark.parametrize("params", ["amount,self", "this,self"])
@pytest.mark.parametrize("contract", [False, True])
def test_distinct_nonleading_self_preserves_actual_receiver_and_argument(
    params, contract, make_interpreter
):
    interpreter = make_interpreter(
        policy=(
            "when this.fields.value == 99 and self.fields.value == 1 => ALLOW\n"
            "when true => DENY"
        )
    )
    clause = " requires true" if contract else ""
    program = parse(
        "fountain Box { value = 0\n"
        f"glass take(){clause} {{ return this.value + self.value }} }}\n"
        "drink original = new Box()\ndrink supplied = new Box()"
    )
    program.stmts[0].methods[0].params = [(name, None) for name in params.split(",")]
    interpreter.interpret(program)
    interpreter.env.get("original").fields["value"] = 99
    interpreter.env.get("supplied").fields["value"] = 1
    argument_source = "0, supplied" if params.startswith("amount") else "supplied"
    assert interpreter.interpret(parse(f"original.take({argument_source})")) == 100
    if contract:
        assert interpreter._last_proof.verdict is TarlVerdict.ALLOW
