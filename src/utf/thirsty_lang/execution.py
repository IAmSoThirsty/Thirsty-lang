"""Shared execution defaults; source semantics cannot grant host authority."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from dataclasses import dataclass
from math import isfinite
from threading import RLock, get_ident
from time import monotonic


class ExecutionError(RuntimeError):
    """Host execution control failure, outside guest exception handling."""


class ExecutionBusyError(ExecutionError):
    """A different execution already owns the requested interpreter state."""


class ExecutionClosedError(ExecutionError):
    """The interpreter's shared execution lifetime has ended."""


class ExecutionStopped(ExecutionError):
    """A cooperative limit or cancellation has terminated a logical run."""

    def __init__(self, reason: str, steps: int):
        self.reason = reason
        self.steps = steps
        super().__init__(f"execution stopped: {reason} (steps={steps})")


@dataclass(frozen=True)
class ExecutionLimits:
    """Finite host limits shared across a complete logical execution.

    Steps count AST dispatches and callable entry. Time is checked cooperatively;
    neither a step nor a deadline preempts a blocking foreign operation.
    """

    max_steps: int = 1_000_000
    timeout_seconds: float = 30.0
    max_call_depth: int = 64

    def __post_init__(self):
        for name in ("max_steps", "max_call_depth"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive Int")
        value = self.timeout_seconds
        try:
            valid_time = type(value) in (int, float) and value > 0 and isfinite(value)
        except OverflowError:
            valid_time = False
        if not valid_time:
            raise ValueError("timeout_seconds must be positive and finite")


_STATE_LOCK = RLock()
_CURRENT_RUN: ContextVar["_ExecutionRun | None"] = ContextVar(
    "thirsty_execution_run", default=None
)


class _ExecutionRun:
    def __init__(self):
        self.started = monotonic()
        self.steps = 0
        self.call_depth = 0
        self.max_steps: int | None = None
        self.max_call_depth: int | None = None
        self.deadline: float | None = None
        self.reason: str | None = None
        self.thread_id: int | None = get_ident()
        self.worker = False
        self.finished = False
        self.domains: list[ExecutionDomain] = []

    def check(self, *, step=False):
        # The lock serializes cancellation and ownership checks, not guest code.
        with _STATE_LOCK:
            if self.finished:
                raise ExecutionClosedError("execution context has already finished")
            if self.thread_id != get_ident():
                raise ExecutionBusyError("execution is active on another thread")
            if self.reason is None and self.deadline is not None:
                if monotonic() >= self.deadline:
                    self.reason = "deadline exceeded"
            if self.reason is None and step:
                if self.max_steps is not None and self.steps >= self.max_steps:
                    self.reason = "step limit exceeded"
                else:
                    self.steps += 1
            if self.reason is not None:
                raise ExecutionStopped(self.reason, self.steps)

    def join(self, domain: "ExecutionDomain"):
        with _STATE_LOCK:
            self.check()
            if domain._closed:
                raise ExecutionClosedError("interpreter execution is closed")
            if domain._active is not None and domain._active is not self:
                raise ExecutionBusyError("interpreter has another active execution")
            if domain not in self.domains:
                limits = domain.limits
                domain._active = self
                self.domains.append(domain)
                self.max_steps = min(
                    self.max_steps or limits.max_steps, limits.max_steps
                )
                self.max_call_depth = min(
                    self.max_call_depth or limits.max_call_depth, limits.max_call_depth
                )
                deadline = self.started + limits.timeout_seconds
                self.deadline = min(self.deadline or deadline, deadline)
            # A tighter definer limit accounts for work already done by callers.
            if self.reason is None:
                if self.max_steps is not None and self.steps > self.max_steps:
                    self.reason = "step limit exceeded"
                elif (
                    self.max_call_depth is not None
                    and self.call_depth > self.max_call_depth
                ):
                    self.reason = "call depth limit exceeded"
            self.check()

    def stop(self, reason: str):
        with _STATE_LOCK:
            if self.reason is None:
                self.reason = reason


class ExecutionDomain:
    """Owned state and scheduler for an interpreter and its file imports.

    One logical run owns every joined domain until its outermost call returns.
    Reentrancy is permitted on its current thread. Only cascade may transfer
    that thread ownership; copying a ContextVar context does not grant it.
    """

    def __init__(self, limits: ExecutionLimits | None = None):
        if limits is not None and type(limits) is not ExecutionLimits:
            raise TypeError("execution_limits must be an ExecutionLimits value")
        self.limits = limits if limits is not None else ExecutionLimits()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._active: _ExecutionRun | None = None
        self._closed = False

    @contextmanager
    def enter(self, *, call=False):
        run = _CURRENT_RUN.get()
        outer = run is None
        if run is None:
            run = _ExecutionRun()
        token = _CURRENT_RUN.set(run)
        entered_call = False
        try:
            run.join(self)
            if call:
                if run.call_depth >= (run.max_call_depth or 0):
                    run.stop("call depth limit exceeded")
                    run.check()
                run.call_depth += 1
                entered_call = True
                run.check(step=True)
            yield
            run.check()
        except RecursionError as error:
            # Python's own stack ceiling may be lower than a configured limit.
            run.stop("host recursion limit exceeded")
            raise ExecutionStopped(
                run.reason or "host recursion limit exceeded", run.steps
            ) from error
        except Exception:
            run.check()
            raise
        finally:
            if entered_call:
                run.call_depth -= 1
            _CURRENT_RUN.reset(token)
            if outer:
                with _STATE_LOCK:
                    run.finished = True
                    for domain in run.domains:
                        domain._active = None

    def checkpoint(self, *, step=False):
        run = _CURRENT_RUN.get()
        if run is not None:
            run.check(step=step)

    def cancel(self) -> bool:
        """Signal the active logical run. No running host operation is killed."""
        with _STATE_LOCK:
            if self._active is None:
                return False
            self._active.stop("cancelled")
            return True

    def close(self):
        """Close an idle domain; cancel and await active work before closing."""
        with _STATE_LOCK:
            if self._closed:
                return
            if self._active is not None:
                raise ExecutionBusyError(
                    "cannot close an active execution; cancel and await it first"
                )
            self._closed = True
        self.executor.shutdown(wait=True, cancel_futures=True)

    def cascade(self, function, *args):
        run = _CURRENT_RUN.get()
        if run is None:
            with self.enter():
                return self.cascade(function, *args)
        run.check()
        if run.worker:
            # Cascade returns the awaited value. Work-first nesting preserves
            # that contract without blocking every worker on another worker.
            result = function(*args)
            run.check()
            return result
        context = copy_context()
        caller_thread = get_ident()
        with _STATE_LOCK:
            run.thread_id = None

        def execute():
            with _STATE_LOCK:
                run.thread_id = get_ident()
                run.worker = True
            try:
                run.check()
                result = function(*args)
                run.check()
                return result
            finally:
                with _STATE_LOCK:
                    run.worker = False
                    run.thread_id = None

        try:
            future = self.executor.submit(context.run, execute)
            try:
                return future.result()
            except BaseException:
                # Interrupting the waiting caller must not free mutable state
                # while its worker is still using it. Await this same handle.
                if not future.done():
                    run.stop("caller interrupted")
                    while not future.done():
                        try:
                            future.result()
                        except BaseException:
                            continue
                raise
        finally:
            with _STATE_LOCK:
                run.thread_id = caller_thread


EXECUTION_MODES = frozenset({"core", "governed", "strict", "pure"})


def resolve_execution_mode(
    declared_mode: str | None = None,
    mode: str | None = None,
    *,
    allow_ungoverned: bool = False,
    force_mode: bool = False,
) -> tuple[str, bool]:
    """Return semantic mode and the minimum required governance posture.

    Only an explicit trusted-host opt-out can permit ungoverned execution.
    A governed request or declaration strengthens even that opt-out. Strict
    initialization and pure-effect semantics remain separate from governance.
    """
    if type(allow_ungoverned) is not bool or type(force_mode) is not bool:
        raise TypeError("execution posture options must be Bool values")
    for candidate in (declared_mode, mode):
        if candidate is not None and (
            type(candidate) is not str or candidate not in EXECUTION_MODES
        ):
            raise ValueError(f"unsupported execution mode: {candidate!r}")
    requested = (
        mode if mode is not None else ("core" if allow_ungoverned else "governed")
    )
    semantic = requested if force_mode or declared_mode is None else declared_mode
    governed = (
        not allow_ungoverned or requested == "governed" or declared_mode == "governed"
    )
    return semantic, governed
