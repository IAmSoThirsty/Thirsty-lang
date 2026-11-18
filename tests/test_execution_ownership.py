"""Logical execution ownership protects scopes across calls and cascade workers."""

import json
import subprocess
import sys
from contextvars import copy_context
from pathlib import Path
from threading import Event, Thread, get_ident

import pytest

from utf.thirsty_lang import execution
from utf.thirsty_lang.interpreter import Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser


def parse(source):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors and not parser.errors, (lexer.errors, parser.errors)
    return program


@pytest.fixture
def make_interpreter():
    interpreters = []

    def make(**options):
        interpreter = Interpreter(**options)
        interpreters.append(interpreter)
        return interpreter

    yield make
    for interpreter in interpreters:
        interpreter.close()


def start_call(callback, *args):
    outcome = {}

    def run():
        try:
            outcome["value"] = callback(*args)
        except BaseException as error:
            outcome["error"] = error

    thread = Thread(target=run, daemon=True)
    thread.start()
    return thread, outcome


def finish_call(thread, outcome):
    thread.join(5)
    assert not thread.is_alive(), "bounded test worker did not complete"
    if "error" in outcome:
        raise outcome["error"]
    return outcome["value"]


def paused_callback():
    entered, release = Event(), Event()

    def pause():
        entered.set()
        assert release.wait(5), "test did not release its blocked callback"

    return pause, entered, release


_CALLABLES = [
    pytest.param(
        "glass hold(value, pause) { pause()\nreturn value }\nhold", id="function"
    ),
    pytest.param(
        "drink hold = glass(value, pause) { pause()\nreturn value }\nhold",
        id="lambda",
    ),
    pytest.param(
        "morph hold(value, pause) { pause()\nreturn value }\nhold", id="morph"
    ),
    pytest.param(
        "fountain Box { glass hold(value, pause) { pause()\nreturn value } }\n"
        "drink box = new Box()\nbox.hold",
        id="bound-method",
    ),
]


@pytest.mark.parametrize("source", _CALLABLES)
@pytest.mark.parametrize("allow_ungoverned", [False, True])
def test_competing_escaped_calls_are_rejected_before_binding_or_body(
    source, allow_ungoverned, make_interpreter
):
    interpreter = make_interpreter(allow_ungoverned=allow_ungoverned)
    callback = interpreter.interpret(parse(source))
    original_environment = interpreter.env
    pause, entered, release = paused_callback()
    first, outcome = start_call(callback, 1, pause)
    effects = []
    try:
        assert entered.wait(5)
        active_environment = interpreter.env
        with pytest.raises(execution.ExecutionBusyError):
            callback(2, lambda: effects.append("second body"))
        assert effects == []
        assert interpreter.env is active_environment
    finally:
        release.set()
        assert finish_call(first, outcome) == 1
    assert interpreter.env is original_environment
    assert callback(3, lambda: None) == 3


@pytest.mark.parametrize("active_entry", ["interpret", "escaped"])
@pytest.mark.parametrize("requested_mode", ["core", "pure", "strict", "governed"])
def test_competing_interpret_cannot_change_mode_environment_or_proof(
    active_entry, requested_mode, make_interpreter
):
    interpreter = make_interpreter()
    callback = interpreter.interpret(
        parse("glass hold(pause) { pause()\nreturn 7 }\nhold")
    )
    pause, entered, release = paused_callback()
    interpreter.env.define("pause", pause)
    original_environment = interpreter.env
    original_mode = interpreter.mode
    original_governed = interpreter._execution_governed
    original_proof = interpreter._last_proof
    first, outcome = (
        start_call(callback, pause)
        if active_entry == "escaped"
        else start_call(interpreter.interpret, parse("pause()\n7"))
    )
    try:
        assert entered.wait(5)
        active_environment = interpreter.env
        with pytest.raises(execution.ExecutionBusyError):
            interpreter.interpret(
                parse("drink contamination = 99\ncontamination"), mode=requested_mode
            )
        assert interpreter.env is active_environment
        assert not interpreter.env.has("contamination")
        assert interpreter.mode == original_mode
        assert interpreter._execution_governed is original_governed
        assert interpreter._last_proof is original_proof
    finally:
        release.set()
        assert finish_call(first, outcome) == 7
    assert interpreter.env is original_environment


def test_copied_context_does_not_authorize_a_competing_thread(make_interpreter):
    interpreter = make_interpreter()
    callback = interpreter.interpret(
        parse("glass hold(value, pause) { pause()\nreturn value }\nhold")
    )
    entered, release = Event(), Event()
    contexts = []

    def pause():
        contexts.append(copy_context())
        entered.set()
        assert release.wait(5)

    first, outcome = start_call(callback, 1, pause)
    effects = []
    try:
        assert entered.wait(5)
        active_environment = interpreter.env
        with pytest.raises(execution.ExecutionBusyError):
            contexts[0].run(callback, 2, lambda: effects.append("competing"))
        assert effects == []
        assert interpreter.env is active_environment
    finally:
        release.set()
        assert finish_call(first, outcome) == 1


def test_stale_copied_context_cannot_revive_completed_execution(make_interpreter):
    interpreter = make_interpreter()
    callback = interpreter.interpret(
        parse("glass apply(callback) { return callback() }\napply")
    )
    contexts = []
    callback(lambda: contexts.append(copy_context()))
    # A retained context still names its completed logical run. It must not
    # resurrect that authority; a normal call outside the stale context works.
    effects = []
    with pytest.raises(execution.ExecutionClosedError):
        contexts[0].run(callback, lambda: effects.append("stale body"))
    assert effects == []
    assert callback(lambda: 43) == 43


def test_same_thread_reentrant_callable_is_part_of_current_execution(make_interpreter):
    interpreter = make_interpreter()
    interpreter.interpret(
        parse(
            "glass inner(value) { return value + 1 }\n"
            "glass outer(value, callback) { callback()\nreturn value }"
        )
    )
    inner = interpreter.env.get("inner")
    outer = interpreter.env.get("outer")
    environment = interpreter.env
    results = []
    assert outer(7, lambda: results.append(inner(41))) == 7
    assert results == [42]
    assert interpreter.env is environment


@pytest.mark.parametrize("nested_mode", ["core", "strict", "pure", "governed"])
def test_same_thread_reentrant_interpret_restores_enclosing_semantics(
    nested_mode, make_interpreter
):
    interpreter = make_interpreter(allow_ungoverned=True)
    observations = []

    def reenter():
        environment = interpreter.env
        previous = (interpreter.mode, interpreter._execution_governed)
        assert interpreter.interpret(parse("21 * 2"), mode=nested_mode) == 42
        observations.append((interpreter.mode, interpreter._execution_governed))
        assert interpreter.env is environment
        assert observations[-1] == previous
        return 7

    interpreter.env.define("reenter", reenter)
    assert interpreter.interpret(parse("reenter()"), mode="strict") == 7
    assert observations == [("strict", False)]
    assert interpreter.mode == "strict"


def test_independent_interpreters_can_run_concurrently(make_interpreter):
    first_interpreter = make_interpreter()
    second_interpreter = make_interpreter()
    callback = first_interpreter.interpret(
        parse("glass hold(pause) { pause()\nreturn 1 }\nhold")
    )
    pause, entered, release = paused_callback()
    first, outcome = start_call(callback, pause)
    try:
        assert entered.wait(5)
        assert second_interpreter.interpret(parse("6 * 7")) == 42
    finally:
        release.set()
        assert finish_call(first, outcome) == 1


@pytest.mark.parametrize("active_owner", ["parent", "imported"])
def test_import_graph_shares_execution_ownership(
    active_owner, make_interpreter, tmp_path
):
    interpreter = make_interpreter(allow_ungoverned=True)
    module = tmp_path / "worker.thirsty"
    module.write_text(
        "glass hold(value, pause) { pause()\nreturn value }\n", encoding="utf-8"
    )
    interpreter.source_directory = tmp_path
    interpreter.interpret(
        parse(
            'import "worker.thirsty" as worker\n'
            "glass local(value, pause) { pause()\nreturn value }"
        )
    )
    imported = interpreter.env.get("worker")["hold"]
    parent = interpreter.env.get("local")
    active, competing = (
        (parent, imported) if active_owner == "parent" else (imported, parent)
    )
    pause, entered, release = paused_callback()
    first, outcome = start_call(active, 1, pause)
    effects = []
    try:
        assert entered.wait(5)
        with pytest.raises(execution.ExecutionBusyError):
            competing(2, lambda: effects.append("competing"))
        assert effects == []
    finally:
        release.set()
        assert finish_call(first, outcome) == 1
    assert competing(3, lambda: None) == 3


@pytest.mark.parametrize("optimization", [0, 3])
@pytest.mark.parametrize("depth", [2, 3, 4, 8])
def test_nested_awaited_cascade_finishes_beyond_executor_capacity(depth, optimization):
    # A subprocess bounds a genuine executor starvation regression: a hung
    # ThreadPoolExecutor joins workers during Python exit even for daemon callers.
    child = r"""
import json, sys
from utf.thirsty_lang.interpreter import Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser
source = (
    "glass descend(n) { thirsty (n == 0) { return 42 } "
    "return cascade descend(n - 1) }\ncascade descend(" + sys.argv[1] + ")"
)
lexer = Lexer(source)
parser = Parser(lexer.lex())
program = parser.parse()
assert not lexer.errors and not parser.errors, (lexer.errors, parser.errors)
interpreter = Interpreter(opt_level=int(sys.argv[2]))
environment = interpreter.env
try:
    result = interpreter.interpret(program)
    print(json.dumps({"result": result, "restored": interpreter.env is environment}))
finally:
    interpreter.executor.shutdown(wait=True)
"""
    completed = subprocess.run(
        [sys.executable, "-c", child, str(depth), str(optimization)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"result": 42, "restored": True}


def test_cascade_transfers_ownership_and_allows_worker_reentry(make_interpreter):
    interpreter = make_interpreter()
    interpreter.interpret(
        parse(
            "glass inner(value) { return value + 1 }\n"
            "glass outer(callback) { return cascade callback() }"
        )
    )
    outer = interpreter.env.get("outer")
    inner = interpreter.env.get("inner")
    caller_thread = get_ident()
    worker_threads = []

    def callback():
        worker_threads.append(get_ident())
        return inner(41)

    assert outer(callback) == 42
    assert len(worker_threads) == 1
    assert worker_threads[0] != caller_thread
    assert inner(42) == 43


def test_worker_context_is_not_left_active_after_failed_cascade(make_interpreter):
    interpreter = make_interpreter()
    callback = interpreter.interpret(
        parse("glass invoke(callback) { return cascade callback() }\ninvoke")
    )
    failure = ValueError("worker error")

    def fail():
        raise failure

    with pytest.raises(ValueError) as caught:
        callback(fail)
    assert caught.value is failure
    assert callback(lambda: 42) == 42
    assert interpreter.interpret(parse("43")) == 43


def test_cancel_does_not_release_ownership_before_live_worker_finishes(
    make_interpreter,
):
    interpreter = make_interpreter()
    callback = interpreter.interpret(
        parse("glass invoke(callback) { return cascade callback() }\ninvoke")
    )
    pause, entered, release = paused_callback()
    first, outcome = start_call(callback, pause)
    try:
        assert entered.wait(5)
        assert interpreter.cancel() is True
        assert first.is_alive()
        with pytest.raises(execution.ExecutionBusyError):
            interpreter.interpret(parse("drink raced = 1"))
        with pytest.raises(execution.ExecutionBusyError):
            interpreter.close()
        assert not interpreter.env.has("raced")
    finally:
        release.set()
        with pytest.raises(execution.ExecutionStopped) as caught:
            finish_call(first, outcome)
        assert caught.value.reason == "cancelled"
    assert interpreter.cancel() is False
    assert callback(lambda: 42) == 42


def test_rejected_worker_submission_restores_calling_ownership(
    make_interpreter, monkeypatch
):
    interpreter = make_interpreter()
    callback = interpreter.interpret(
        parse("glass invoke(callback) { return cascade callback() }\ninvoke")
    )
    failure = RuntimeError("executor rejected submission")

    def reject(*args, **kwargs):
        raise failure

    with monkeypatch.context() as patch:
        patch.setattr(interpreter.executor, "submit", reject)
        with pytest.raises(RuntimeError) as caught:
            callback(lambda: pytest.fail("unsubmitted callback ran"))
        assert caught.value is failure
    assert callback(lambda: 42) == 42


def test_interrupted_cascade_waiter_retains_ownership_until_worker_finishes(
    make_interpreter, monkeypatch
):
    interpreter = make_interpreter()
    callback = interpreter.interpret(
        parse("glass invoke(callback) { return cascade callback() }\ninvoke")
    )
    pause, entered, release = paused_callback()
    interrupted = Event()
    submit = interpreter.executor.submit

    class InterruptedFuture:
        def __init__(self, actual):
            self.actual = actual
            self.first_result = True

        def done(self):
            return self.actual.done()

        def result(self):
            if self.first_result:
                self.first_result = False
                assert entered.wait(5)
                interrupted.set()
                raise KeyboardInterrupt("simulated interrupted waiting caller")
            return self.actual.result()

    def submit_with_interrupted_wait(*args, **kwargs):
        return InterruptedFuture(submit(*args, **kwargs))

    with monkeypatch.context() as patch:
        patch.setattr(interpreter.executor, "submit", submit_with_interrupted_wait)
        first, outcome = start_call(callback, pause)
        try:
            assert interrupted.wait(5)
            assert first.is_alive()
            with pytest.raises(execution.ExecutionBusyError):
                interpreter.interpret(parse("drink raced = 1"))
            with pytest.raises(execution.ExecutionBusyError):
                interpreter.close()
            assert not interpreter.env.has("raced")
        finally:
            release.set()
            with pytest.raises(execution.ExecutionStopped) as caught:
                finish_call(first, outcome)
            assert caught.value.reason == "caller interrupted"
    assert callback(lambda: 42) == 42


def test_definer_remains_owned_until_whole_caller_execution_returns(make_interpreter):
    definer = make_interpreter()
    task = definer.interpret(parse("glass add(value) { return value + 1 }\nadd"))
    caller = make_interpreter()
    flow = caller.interpret(
        parse(
            "glass flow(task, pause) { drink value = task(1)\n"
            "pause()\nreturn value }\nflow"
        )
    )
    pause, entered, release = paused_callback()
    first, outcome = start_call(flow, task, pause)
    try:
        assert entered.wait(5)
        with pytest.raises(execution.ExecutionBusyError):
            task(2)
        with pytest.raises(execution.ExecutionBusyError):
            definer.close()
    finally:
        release.set()
        assert finish_call(first, outcome) == 2
    assert task(2) == 3


def test_failed_definer_claim_releases_only_the_competing_callers_domain(
    make_interpreter,
):
    definer = make_interpreter()
    task = definer.interpret(parse("glass hold(pause) { pause()\nreturn 7 }\nhold"))
    caller = make_interpreter()
    invoke = caller.interpret(parse("glass invoke(task) { return task() }\ninvoke"))
    pause, entered, release = paused_callback()
    first, outcome = start_call(task, pause)
    try:
        assert entered.wait(5)
        with pytest.raises(execution.ExecutionBusyError):
            invoke(task)
        assert caller.interpret(parse("42")) == 42
        with pytest.raises(execution.ExecutionBusyError):
            definer.interpret(parse("43"))
    finally:
        release.set()
        assert finish_call(first, outcome) == 7


def test_close_while_active_refuses_without_changing_execution(make_interpreter):
    interpreter = make_interpreter()
    callback = interpreter.interpret(
        parse("glass hold(pause) { pause()\nreturn 7 }\nhold")
    )
    pause, entered, release = paused_callback()
    first, outcome = start_call(callback, pause)
    try:
        assert entered.wait(5)
        with pytest.raises(execution.ExecutionBusyError):
            interpreter.close()
    finally:
        release.set()
        assert finish_call(first, outcome) == 7
    assert callback(lambda: None) == 7
    interpreter.close()
    interpreter.close()
    with pytest.raises(execution.ExecutionClosedError):
        callback(lambda: pytest.fail("closed callable body ran"))
    with pytest.raises(execution.ExecutionClosedError):
        interpreter.interpret(parse("1"))
