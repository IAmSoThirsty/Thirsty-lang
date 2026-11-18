"""Finite execution budgets survive calls, callbacks, imports, and cancellation."""

from dataclasses import FrozenInstanceError

import pytest

from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
from utf.thirsty_lang import execution
from utf.thirsty_lang import interpreter as interpreter_module
from utf.thirsty_lang.execution import (
    ExecutionDomain,
    ExecutionLimits,
    ExecutionStopped,
)
from utf.thirsty_lang.interpreter import Interpreter
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

    def make(*, optimization=0, unsafe=False, **limits):
        interpreter = Interpreter(
            opt_level=optimization,
            allow_ungoverned=unsafe,
            execution_limits=ExecutionLimits(**limits),
        )
        runtime = TarlRuntime(PolicyParser.parse("when true => ALLOW"))
        interpreter.attach_tarl(runtime).set_authority("execution-limits-test")
        interpreters.append(interpreter)
        runtimes.append(runtime)
        return interpreter

    yield make
    for interpreter in interpreters:
        interpreter.close()
    for runtime in runtimes:
        runtime.shutdown()


@pytest.fixture
def clock(monkeypatch):
    current = [100.0]
    monkeypatch.setattr(execution, "monotonic", lambda: current[0])
    return current


def assert_stop(error, reason):
    assert error.value.reason == reason
    assert type(error.value.steps) is int
    assert error.value.steps >= 0


def test_execution_limits_have_finite_immutable_defaults():
    limits = ExecutionLimits()
    assert limits.max_steps == 1_000_000
    assert limits.timeout_seconds == 30.0
    assert limits.max_call_depth == 64
    with pytest.raises(FrozenInstanceError):
        limits.max_steps = 2


@pytest.mark.parametrize("field", ["max_steps", "max_call_depth"])
@pytest.mark.parametrize("value", [0, -1, True, False, 1.5, "2", None])
def test_integer_limits_require_exact_positive_integers(field, value):
    with pytest.raises(ValueError, match=field):
        ExecutionLimits(**{field: value})


@pytest.mark.parametrize(
    "value", [0, -1, True, False, float("inf"), -float("inf"), float("nan"), "2", None]
)
def test_deadlines_require_positive_finite_numeric_seconds(value):
    with pytest.raises(ValueError, match="timeout_seconds"):
        ExecutionLimits(timeout_seconds=value)


def test_unrepresentable_deadline_is_a_validation_error():
    with pytest.raises(ValueError, match="timeout_seconds"):
        ExecutionLimits(timeout_seconds=10**10000)


def test_numeric_subclasses_do_not_control_limit_validation():
    class HostInt(int):
        pass

    class HostFloat(float):
        pass

    for options in (
        {"max_steps": HostInt(2)},
        {"max_call_depth": HostInt(2)},
        {"timeout_seconds": HostInt(2)},
        {"timeout_seconds": HostFloat(2)},
    ):
        with pytest.raises(ValueError):
            ExecutionLimits(**options)


@pytest.mark.parametrize("value", [False, {}, 5, "unlimited"])
def test_interpreter_rejects_non_limit_objects(value):
    with pytest.raises(TypeError, match="execution_limits"):
        Interpreter(execution_limits=value)


def test_latched_step_stop_cannot_be_caught_and_reset_inside_a_run():
    domain = ExecutionDomain(ExecutionLimits(max_steps=2))
    try:
        with pytest.raises(ExecutionStopped) as outer:
            with domain.enter():
                domain.checkpoint(step=True)
                domain.checkpoint(step=True)
                with pytest.raises(ExecutionStopped) as first:
                    domain.checkpoint(step=True)
                assert_stop(first, "step limit exceeded")
                assert first.value.steps == 2
                with pytest.raises(ExecutionStopped) as second:
                    domain.checkpoint()
                assert_stop(second, "step limit exceeded")
                assert second.value.steps == 2
                # Even a host swallowing the exception cannot exit successfully.
        assert_stop(outer, "step limit exceeded")
        with domain.enter():
            domain.checkpoint(step=True)
    finally:
        domain.close()


@pytest.mark.parametrize(
    "source",
    [
        "[" + ",".join("1" for _ in range(40)) + "]",
        " + ".join("1" for _ in range(40)),
        "({" + ",".join(f'"k{index}": 1' for index in range(40)) + "})",
    ],
    ids=["array-children", "binary-children", "dictionary-children"],
)
@pytest.mark.parametrize("unsafe", [False, True])
def test_nested_expression_dispatch_consumes_budget(source, unsafe, make_interpreter):
    interpreter = make_interpreter(max_steps=12, unsafe=unsafe)
    original = interpreter.env
    with pytest.raises(ExecutionStopped) as error:
        interpreter.interpret(parse(source))
    assert_stop(error, "step limit exceeded")
    assert error.value.steps == 12
    assert interpreter.env is original
    assert interpreter.interpret(parse("7")) == 7


@pytest.mark.parametrize("optimization", range(4))
def test_finite_foreach_with_empty_body_cannot_avoid_budget(
    optimization, make_interpreter
):
    interpreter = make_interpreter(max_steps=15, optimization=optimization)
    interpreter.env.define("items", list(range(100)))
    with pytest.raises(ExecutionStopped) as error:
        interpreter.interpret(parse("refill (item in items) {}"))
    assert_stop(error, "step limit exceeded")
    assert error.value.steps == 15
    assert not interpreter.env.has("item")


@pytest.mark.parametrize("source", ["times 100 {}", "refill (next()) {}"])
def test_other_finite_empty_loops_consume_steps(source, make_interpreter):
    interpreter = make_interpreter(max_steps=15)
    remaining = iter([True] * 100 + [False])
    interpreter.env.define("next", lambda: next(remaining))
    with pytest.raises(ExecutionStopped) as error:
        interpreter.interpret(parse(source))
    assert_stop(error, "step limit exceeded")
    assert error.value.steps == 15


def test_escaped_native_callable_entry_itself_consumes_a_step(make_interpreter):
    interpreter = make_interpreter(max_steps=1)
    interpreter.interpret(parse("glass target() {}"))
    # Declaration needs one statement dispatch. The independent call consumes
    # its one step on entry before its otherwise-empty body can dispatch.
    with pytest.raises(ExecutionStopped) as error:
        interpreter.env.get("target")()
    assert_stop(error, "step limit exceeded")
    assert error.value.steps == 1


@pytest.mark.parametrize("cascade", [False, True])
def test_recursive_calls_share_a_finite_call_depth_limit(cascade, make_interpreter):
    call = "cascade descend(n - 1)" if cascade else "descend(n - 1)"
    program = parse(
        "glass descend(n) {\n"
        "thirsty (n == 0) { return 0 }\n"
        f"return 1 + ({call})\n}}\ndescend(30)"
    )
    interpreter = make_interpreter(max_call_depth=8)
    original = interpreter.env
    with pytest.raises(ExecutionStopped) as error:
        interpreter.interpret(program)
    assert_stop(error, "call depth limit exceeded")
    assert interpreter.env is original
    assert interpreter.env.get("descend")(2) == 2


@pytest.mark.parametrize("raises", [False, True])
@pytest.mark.parametrize("cascade", [False, True])
def test_callback_cancellation_stops_before_guest_handler_or_following_statement(
    raises, cascade, make_interpreter
):
    interpreter = make_interpreter()
    events = []

    def stop():
        events.append("callback")
        assert interpreter.cancel() is True
        if raises:
            raise ValueError("foreign failure after cancellation")
        return 1

    interpreter.env.define("stop", stop)
    interpreter.env.define("hit", lambda: events.append("guest"))
    call = "cascade stop()" if cascade else "stop()"
    program = parse(f"spillage {{ {call} }} error {{ hit() }}\nhit()")
    original = interpreter.env
    assert interpreter.cancel() is False
    with pytest.raises(ExecutionStopped) as error:
        interpreter.interpret(program)
    assert_stop(error, "cancelled")
    assert events == ["callback"]
    assert interpreter.env is original
    assert interpreter.cancel() is False
    assert interpreter.interpret(parse("7")) == 7


def test_host_cannot_swallow_cancel_and_resume_guest_in_reentrant_interpret(
    make_interpreter,
):
    interpreter = make_interpreter()
    events = []
    interpreter.env.define("hit", lambda: events.append("guest"))

    def callback():
        assert interpreter.cancel()
        with pytest.raises(ExecutionStopped) as nested:
            interpreter.interpret(parse("hit()"))
        assert_stop(nested, "cancelled")
        return 7

    interpreter.env.define("callback", callback)
    with pytest.raises(ExecutionStopped) as error:
        interpreter.interpret(parse("callback()"))
    assert_stop(error, "cancelled")
    assert events == []


@pytest.mark.parametrize("stop_kind", ["cancel", "steps"])
def test_guest_cleanup_cannot_resume_execution_after_a_latched_stop(
    stop_kind, make_interpreter
):
    interpreter = make_interpreter(max_steps=20)
    events = []

    def stop():
        assert interpreter.cancel()
        return None

    interpreter.env.define("stop", stop)
    interpreter.env.define("hit", lambda: events.append("finalizer"))
    body = "stop()" if stop_kind == "cancel" else "times 100 {}"
    with pytest.raises(ExecutionStopped) as error:
        interpreter.interpret(parse(f"cleanup {{ {body} }} finally {{ hit() }}"))
    reason = "cancelled" if stop_kind == "cancel" else "step limit exceeded"
    assert_stop(error, reason)
    assert events == []
    assert interpreter.interpret(parse("7")) == 7


@pytest.mark.parametrize("raises", [False, True])
def test_contract_callback_cancellation_is_not_converted_to_contract_denial(
    raises, make_interpreter
):
    interpreter = make_interpreter()
    events = []

    def stop():
        assert interpreter.cancel()
        if raises:
            raise ValueError("contract callback failed")
        return True

    interpreter.env.define("stop", stop)
    interpreter.env.define("hit", lambda: events.append("body"))
    with pytest.raises(ExecutionStopped) as error:
        interpreter.interpret(
            parse("glass target() requires stop() { hit() }\ntarget()")
        )
    assert_stop(error, "cancelled")
    assert events == []


@pytest.mark.parametrize("target", ["body", "print"])
@pytest.mark.parametrize("raises", [False, True])
def test_policy_callback_cancellation_precedes_authorized_body_or_effect(
    target, raises, make_interpreter, monkeypatch, capsys
):
    interpreter = make_interpreter()
    events = []
    interpreter.env.define("hit", lambda: events.append("body"))
    evaluate = interpreter.tarl_runtime.evaluate_with_proof

    def evaluate_and_cancel(*args, **kwargs):
        result = evaluate(*args, **kwargs)
        assert interpreter.cancel()
        if raises:
            raise ValueError("policy callback failed after cancellation")
        return result

    monkeypatch.setattr(
        interpreter.tarl_runtime, "evaluate_with_proof", evaluate_and_cancel
    )
    source = (
        "glass target() requires true { hit() }\ntarget()"
        if target == "body"
        else 'print("must not be printed")'
    )
    with pytest.raises(ExecutionStopped) as error:
        interpreter.interpret(parse(source))
    assert_stop(error, "cancelled")
    assert events == []
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("raises", [False, True])
def test_deadline_is_checked_after_a_foreign_callback_without_real_sleep(
    raises, clock, make_interpreter
):
    interpreter = make_interpreter(timeout_seconds=5)
    events = []

    def elapsed():
        events.append("callback")
        clock[0] += 5
        if raises:
            raise ValueError("foreign failure after deadline")
        return 7

    interpreter.env.define("elapsed", elapsed)
    interpreter.env.define("hit", lambda: events.append("guest"))
    with pytest.raises(ExecutionStopped) as error:
        interpreter.interpret(parse("spillage { elapsed() } error { hit() }\nhit()"))
    assert_stop(error, "deadline exceeded")
    assert events == ["callback"]
    assert interpreter.interpret(parse("7")) == 7


def test_reentrant_interpret_does_not_reset_the_deadline(clock, make_interpreter):
    interpreter = make_interpreter(timeout_seconds=5)
    events = []

    def nested():
        clock[0] += 4
        return interpreter.interpret(parse("elapsed()"))

    def elapsed():
        clock[0] += 1
        events.append("elapsed")
        return 7

    interpreter.env.define("nested", nested)
    interpreter.env.define("elapsed", elapsed)
    with pytest.raises(ExecutionStopped) as error:
        interpreter.interpret(parse("nested()"))
    assert_stop(error, "deadline exceeded")
    assert events == ["elapsed"]


def test_tighter_definer_step_limit_accounts_for_previous_caller_work(
    make_interpreter,
):
    caller = make_interpreter(max_steps=500)
    definer = make_interpreter(max_steps=20)
    events = []
    definer.env.define("hit", lambda: events.append("body"))
    target = definer.interpret(parse("glass target() { hit() }\ntarget"))
    caller.env.define("target", target)
    with pytest.raises(ExecutionStopped) as error:
        caller.interpret(parse("1\n" * 30 + "target()"))
    assert_stop(error, "step limit exceeded")
    assert error.value.steps > 20
    assert events == []


def test_tighter_definer_step_limit_stays_after_the_definer_returns(make_interpreter):
    caller = make_interpreter(max_steps=500)
    definer = make_interpreter(max_steps=30)
    target = definer.interpret(parse("glass target() { return 7 }\ntarget"))
    caller.env.define("target", target)
    events = []
    caller.env.define("hit", lambda: events.append("after"))
    with pytest.raises(ExecutionStopped) as error:
        caller.interpret(parse("target()\n" + "1\n" * 30 + "hit()"))
    assert_stop(error, "step limit exceeded")
    assert error.value.steps == 30
    assert events == []
    # An independent run is allowed to use the caller's own larger limit.
    assert caller.interpret(parse("1\n" * 30 + "7")) == 7


def test_tighter_definer_deadline_is_measured_from_outer_run_start(
    clock, make_interpreter
):
    caller = make_interpreter(timeout_seconds=30)
    definer = make_interpreter(timeout_seconds=5)
    events = []
    definer.env.define("hit", lambda: events.append("body"))
    target = definer.interpret(parse("glass target() { hit() }\ntarget"))
    caller.env.define("target", target)

    def elapsed():
        clock[0] += 6
        return None

    caller.env.define("elapsed", elapsed)
    with pytest.raises(ExecutionStopped) as error:
        caller.interpret(parse("elapsed()\ntarget()"))
    assert_stop(error, "deadline exceeded")
    assert events == []


def test_tighter_definer_depth_limit_accounts_for_enclosing_calls(make_interpreter):
    caller = make_interpreter(max_call_depth=12)
    definer = make_interpreter(max_call_depth=2)
    events = []
    definer.env.define("hit", lambda: events.append("body"))
    target = definer.interpret(parse("glass target() { hit() }\ntarget"))
    caller.env.define("target", target)
    with pytest.raises(ExecutionStopped) as error:
        caller.interpret(
            parse(
                "glass third() { return target() }\n"
                "glass second() { return third() }\n"
                "glass first() { return second() }\nfirst()"
            )
        )
    assert_stop(error, "call depth limit exceeded")
    assert events == []


def test_reentrant_interpret_shares_used_steps(make_interpreter):
    interpreter = make_interpreter(max_steps=30)
    events = []

    def nested():
        events.append("nested")
        return interpreter.interpret(parse("1\n" * 10))

    interpreter.env.define("nested", nested)
    with pytest.raises(ExecutionStopped) as error:
        interpreter.interpret(parse("1\n" * 10 + "nested()\n7"))
    assert_stop(error, "step limit exceeded")
    assert error.value.steps == 30
    assert events == ["nested"]


def test_imported_modules_do_not_start_fresh_step_budgets(tmp_path, make_interpreter):
    (tmp_path / "first.thirsty").write_text(
        "1\n" * 12 + 'import "second.thirsty" as second', encoding="utf-8"
    )
    (tmp_path / "second.thirsty").write_text("1\n" * 12, encoding="utf-8")
    interpreter = make_interpreter(max_steps=40)
    interpreter.source_directory = tmp_path
    with pytest.raises(ExecutionStopped) as error:
        interpreter.interpret(parse('import "first.thirsty" as first'))
    assert_stop(error, "step limit exceeded")
    assert error.value.steps == 40
    assert interpreter.interpret(parse("7")) == 7


def test_imported_escaped_callable_shares_its_callers_used_steps(
    tmp_path, make_interpreter
):
    (tmp_path / "callback.thirsty").write_text(
        "glass target() {\n" + "1\n" * 15 + "return 7\n}", encoding="utf-8"
    )
    interpreter = make_interpreter(max_steps=45)
    interpreter.source_directory = tmp_path
    interpreter.interpret(parse('import "callback.thirsty" as callbacks'))
    with pytest.raises(ExecutionStopped) as error:
        interpreter.interpret(parse("1\n" * 15 + "callbacks.target()"))
    assert_stop(error, "step limit exceeded")
    assert error.value.steps == 45


def test_cancelled_input_does_not_update_the_existing_mutable_binding(
    make_interpreter, monkeypatch
):
    interpreter = make_interpreter()
    interpreter.interpret(parse('drink mut value = "original"'))
    inputs = []

    def cancelled_input():
        inputs.append("input")
        assert interpreter.cancel()
        return "replacement"

    monkeypatch.setattr("builtins.input", cancelled_input)
    with pytest.raises(ExecutionStopped) as error:
        interpreter.interpret(parse("sip value"))
    assert_stop(error, "cancelled")
    assert inputs == ["input"]
    assert interpreter.env.get("value") == "original"


def test_cancelled_stdlib_lock_verification_prevents_namespace_resolution(
    make_interpreter, monkeypatch
):
    interpreter = make_interpreter()
    verified = []

    class CancellingLock:
        def verify_stdlib(self, namespace):
            verified.append(namespace)
            assert interpreter.cancel()

    def forbidden_resolution(namespace):
        pytest.fail(f"resolved {namespace} after cancellation")

    interpreter.set_locked(CancellingLock())
    monkeypatch.setattr(interpreter_module, "resolve_import", forbidden_resolution)
    with pytest.raises(ExecutionStopped) as error:
        interpreter.interpret(parse('import "thirst::json" as json'))
    assert_stop(error, "cancelled")
    assert verified == ["thirst::json"]
    assert not interpreter.env.has("json")
