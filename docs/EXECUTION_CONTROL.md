# Execution control and lexical scope

Thirsty-Lang 0.9.1 gives each reference interpreter finite cooperative
execution limits, ownership of its active state, shared import scheduling and
explicit teardown. Native callables resolve lexical names in their defining
scope. Process isolation and the broader M4 portable-execution requirements
remain development milestones. [M4.1 verification record](operations/M4_EXECUTION_CONTROL_VERIFICATION.md)

## Host API and default limits

The reference interpreter accepts one additional keyword-only option:

```text
Interpreter(
    opt_level=0,
    debug_mode=False,
    *,
    allow_ungoverned=False,
    execution_limits=None,
)
```

`execution_limits=None` selects `ExecutionLimits()` with these finite defaults:

| Field | Default | Accepted value |
| --- | --- | --- |
| `max_steps` | `1_000_000` | Exact Python `int`, greater than zero |
| `timeout_seconds` | `30.0` | Exact Python `int` or `float`, positive and finite, representable by the timer calculation |
| `max_call_depth` | `64` | Exact Python `int`, greater than zero |

`ExecutionLimits` is an immutable dataclass. Booleans, numeric subclasses,
nonpositive values, infinite or NaN deadlines, and unrepresentable integer
deadlines are rejected with `ValueError`. Passing an object other than `None` or
an exact `ExecutionLimits` instance to `Interpreter` raises `TypeError`.
`interpreter.execution_limits` exposes the configured value.

The new public classes are exported by `utf.thirsty_lang`:

```python
from utf.thirsty_lang import (
    ExecutionBusyError,
    ExecutionClosedError,
    ExecutionError,
    ExecutionLimits,
    ExecutionStopped,
    Interpreter,
    Lexer,
    Parser,
)

source = "40 + 2"
lexer = Lexer(source)
parser = Parser(lexer.lex())
program = parser.parse()
if lexer.errors or parser.errors:
    raise ValueError("Invalid source")

limits = ExecutionLimits(
    max_steps=100_000,
    timeout_seconds=5.0,
    max_call_depth=32,
)
with Interpreter(execution_limits=limits) as interpreter:
    result = interpreter.interpret(program)
assert result == 42
```

Parsing in this example occurs before the execution budget starts. The context
manager owns the interpreter's lifetime; it does not combine separate calls in
its Python `with` block into one execution budget. Attaching a TARL runtime is
still necessary for operations whose governance gate requires a policy. The
arithmetic example performs no mediated external effect.

Source module headers, `force_mode`, and explicit host compatibility through
`allow_ungoverned=True` cannot turn off execution limits. Those settings retain
their existing governance and semantic-mode meanings.

## What the counters measure

A logical run begins when the host enters `interpret` or invokes an escaped
bound callable without an existing active run. Its state contains one start
time, a count of consumed steps, the current nested call depth, and an optional
latched stop reason.

A step is charged before each statement or expression dispatch, including nested
children reached through the interpreter's implementation dispatchers. Entering
an interpreter-bound callable also consumes a step. Consequently, empty loop
bodies still consume steps, and one large expression cannot avoid accounting by
placing its work below a single top-level expression node. These are interpreter
dispatch counts, not CPU instructions, byte counts, or a portable cost model.

`max_call_depth` limits active interpreter-bound callable entries, including
native functions, methods, constructors, and bound builtin wrappers. Arbitrary
Python operations inside a foreign callback are not counted as native calls.
Python can reach its own recursion ceiling before a host-selected large native
call limit; the execution layer converts an escaping `RecursionError` into a
latched stop with reason `host recursion limit exceeded`.

Elapsed time uses a monotonic clock. Checkpoints before and after executable
dispatches, foreign invocation boundaries, and governed handoffs observe the
deadline and cancellation. A stop is raised when the observed time is at or past
the deadline. This is cooperative observation: a running Python callback,
blocking OS operation, or large single arithmetic/allocation operation is not
preempted when the deadline passes.

The step counter permits exactly the configured number of charged steps. The
next attempted charge stops the run before that dispatch. Non-charging checks
still observe cancellation and deadline expiry. Step counts can exceed a newly
joined smaller limit when the caller already consumed more than that limit;
joining then stops before the new callee body executes.

## Caller, definer, and import composition

Calls, same-thread callbacks, nested `interpret`, cascades, and file imports
participate in the current logical run. They do not receive fresh counters or a
fresh start time. A callable also joins the execution domains retained by its
defining restriction frames. This retains caller and definer ownership alongside
the existing composition of governance restrictions.

For every newly joined domain, the effective step limit and call-depth limit
become the smallest limits joined so far. Its deadline is the shared run start
plus that domain's configured timeout; the earliest joined deadline wins. Work
already performed by the caller counts toward the new limit. For example, a
callee with a five-second timeout entered six seconds into a longer caller run
stops before its body.

These limits remain in force until the outermost run returns, even if the tighter
callee has already returned. All joined domains remain owned for that same
duration. Returning from a callee cannot restore a larger caller budget or free
the callee's state for a concurrent host call while the enclosing run continues.

An independent host call after completion starts a new run with new counters and
the domains it actually joins. This permits ordinary long-lived interpreter
sessions. It is not an aggregate quota across a session, host process, collection
of independent interpreters, or a series of separate host calls.

Imported `.thirsty` interpreters share the importing graph's execution domain,
four-worker executor, limits, and lifetime. Their environments remain separate;
their existing shared policy and authority bindings remain shared. Imported
top-level execution and exported callables cannot use an independent executor or
budget to avoid the importing graph's active run.

## Ownership, reentry, and cascade

One logical run owns each joined interpreter domain. A second execution that
tries to enter owned state receives `ExecutionBusyError` before its language body
or requested interpreter-mode change executes. The ownership check protects the
mutable interpreter environment and execution state across public execution and
bound-callable entrypoints.

Same-thread reentry is permitted as part of the current run. A callback can call
another retained native function or reenter `interpret` without deadlocking an
interpreter lock. Nested `interpret` on an already active interpreter restores
the caller's semantic mode and governance-floor state on return or failure. A
top-level call retains the existing behavior of selecting its program's mode.

`cascade call(...)` continues to return the awaited result. At the outer cascade,
the runtime explicitly hands the run's thread ownership to its executor worker
and waits for that worker. A cascade encountered by the active worker executes
its nested work on that worker before returning. It does not occupy every pool
worker with tasks that wait for another task in the same pool. Nested calls still
consume the shared call-depth and step budgets.

The explicit handoff preserves context and restores ownership when the worker
finishes or submission fails. Cancellation does not release the state while a
worker is still running. If the waiting caller is interrupted, the execution
layer signals a stop and awaits that same worker before releasing ownership. A
blocking foreign callback can therefore delay cancellation and teardown.

Copying a Python `ContextVar` context is not a thread-ownership grant. A copied
active run used on another thread raises `ExecutionBusyError`. Reusing a copied
context after its run has finished raises `ExecutionClosedError`; it cannot
revive the completed run. Copying context on the owning thread during the live
run remains reentry, with the same limits.

## Stops, cancellation, and teardown

`ExecutionError` is the common runtime-error base. The specific outcomes are:

| Exception | Meaning |
| --- | --- |
| `ExecutionBusyError` | Another execution owns the requested domain, or the host tried to close an active domain |
| `ExecutionClosedError` | The interpreter/import graph is closed, or a copied execution context has finished |
| `ExecutionStopped` | A limit, cancellation, or converted host recursion failure stopped the current run |

`ExecutionStopped.reason` identifies the stop and `.steps` reports consumed
dispatch/call-entry steps. Current reasons include `step limit exceeded`,
`deadline exceeded`, `call depth limit exceeded`, `host recursion limit exceeded`,
and `cancelled`. An interrupted cascade waiter signals `caller interrupted` for
the worker. Unwinding execution checkpoints can surface that latched
`ExecutionStopped` to the caller instead of the original interruption.

The first stop reason remains latched for the logical run. Swallowing its Python
exception inside a host callback cannot resume language execution or make the
outer run return successfully. The same applies when a callback cancels or
crosses its deadline and then raises an ordinary exception: the pending stop
remains observable. Contract and policy callback stops are not converted into a
successful authorization or a catchable guest failure.

Guest `spillage` handlers cannot catch execution-control exceptions. A `cleanup`
finalizer does not receive replacement fuel or permission to resume guest code
after a latched stop. Ordinary cleanup behavior remains available before such a
stop. Resource owners must therefore use host-level teardown for resources that
must be released after execution exhaustion.

`interpreter.cancel()` signals the active logical run and returns `True` if the
domain is active. It returns `False` when idle. It does not kill a worker, wait for
completion, close the interpreter, undo effects, or promise that a blocking
foreign operation has returned. Repeated cancellation of a still-active run is
allowed and does not replace an earlier stop reason.

`interpreter.close()` is idempotent while idle. It marks the whole import graph
closed and shuts down its shared executor. Subsequent `interpret` and escaped
callable entry are rejected. Closing active execution raises
`ExecutionBusyError` without silently abandoning that execution. A host that
needs to stop live work must signal cancellation, wait for its existing call or
worker handle to finish, and then close the interpreter. Context-manager exit
uses this same close behavior.

Joined domains remain active until the outer logical run finishes. Consequently,
a context manager created inside a running guest callback cannot close that
joined interpreter on its inner exit; arrange its lifetime outside the outer
run, or explicitly close it after that run has finished.

An attached `TarlRuntime` is borrowed. `Interpreter.close()` does not shut it
down, close its archive, or take ownership of the host's policy resources. The
host that created those resources retains responsibility for their lifetimes.
The CLI registers its own interpreter, runtime, and archive resources for
teardown as each is acquired, including setup failures and execution errors.
TARL's existing `shutdown()` uses `wait=False`; invoking it is not evidence that
all policy workers or external providers have terminated.

No stop, denial, exception, or close operation rolls back state mutations,
callback effects, output, filesystem operations, or audit records that already
occurred. A new independent run is allowed after a stopped run returns, but it
sees any retained state unless the host explicitly replaces it.

## Lexical scope is preserved across callable forms

Ordinary functions and lambdas already captured their defining environments.
M4.1 extends the same lookup contract to governed functions, morphs, and fountain
methods. Governed function bodies and contract expressions now enter a child of
their captured declaration environment. Fountain instances retain their class
declaration environment; field defaults, initializers, and later method calls
use that environment with the actual receiver bound for the invocation.

This prevents a caller-local name from replacing a free variable in a function,
method, or contract. For example, the following call denies its precondition:

```thirsty
drink permitted = false
glass target() requires permitted { return 7 }
glass caller(permitted) { return target() }
caller(true)
```

The caller's argument cannot replace the `permitted` visible where `target` was
declared. The same rule applies to free variables in `ensures` and `invariant`.
Escaped functions and bound methods retain enclosing local scopes after their
factory returns, and distinct factory calls retain distinct scopes. Receiver
binding, exact arity, evaluation order, and restoration of the caller environment
remain in force.

Lexical environments are retained by reference, not copied or frozen. This
repair does not make captured containers immutable, authenticate code or closure
provenance, or add every free variable to a policy proof. See
[governed value contexts](GOVERNED_VALUE_CONTEXT.md) for the separate projection
and proof boundary. Lookup scope and active governance restrictions remain
separate: retaining lexical names does not remove caller restrictions.

## CLI and REPL behavior

`thirsty run` and `thirsty repl` accept `--max-steps`, `--timeout-seconds`, and
`--max-call-depth`. Omitted values use the defaults above. Invalid values fail
before interpreter/runtime/archive acquisition. `--unsafe-core` does not disable
these limits.

The `thirsty run` route for `.thirstofgods` currently rejects explicitly supplied
limit options instead of dropping them during delegation. The Gods reference
interpreter path uses its default limits and closes its owned interpreter.
The generated Pyodide interpreter launcher also uses explicit interpreter
lifetime management. These facts do not prove browser responsiveness,
cross-target resource equivalence, or complete Gods/compiled-target containment.

The REPL retains declarations for checking later submissions while executing
only the newly submitted statements. Earlier side effects are not replayed to
rebuild state. Each accepted submission is an independent execution run. A
runtime-failed submission can leave partial state or effects, so the REPL requires
`.clear` before executing more input. `.clear` resets language/checker session
state; it does not undo effects, replenish the limits of a still-active run, close
all external resource handles, or remove the configured execution limits. A
second module header also requires a cleared session.

## Concrete boundaries still requiring work

- Lexer, parser, checker, and source-loading allocations do not share a complete
  frontend budget. Imported parsing occurs within an elapsed logical run but is
  not individually preemptible or charged by every parser operation.
- One arithmetic operation, string/list allocation, container copy, or host
  iterator callback can consume substantial time or memory between checkpoints.
  Dispatch accounting is not an allocation limit or an OS memory quota.
- Foreign callbacks and blocking I/O are cooperative boundaries. Cancellation
  does not terminate arbitrary Python, interrupt every OS call, or stop work
  independently created by a host callback.
- An ordinary TARL `register_source` callback resolves synchronously and retains
  the current logical run when it calls the interpreter on that thread. A
  trusted callback can instead submit a different, idle interpreter to its own
  host thread pool; that interpreter starts a separate run. The current runtime
  does not propagate descendant quotas through arbitrary host-created threads.
  Trying to enter the already-active interpreter on that foreign thread still
  receives `ExecutionBusyError`.
- TARL evaluation, data-source callbacks, signing, and audit persistence retain
  their own execution behavior. Interpreter checkpoints do not supply a hard
  deadline for all TARL internals or a proof that every internal task has ended.
- Output bytes, total network traffic, DNS/HTTP elapsed time, child processes,
  process descendants, and other OS resources do not yet share one enforced
  per-run quota and containment boundary.
- The interpreter's close operation owns its scheduler. It does not enumerate
  and close every standard-library socket, file, process, or foreign handle, and
  it does not own a borrowed TARL runtime or archive.
- Direct trusted Python access to `.env`, `.executor`, private dispatch methods,
  shared mutable objects, or interpreter internals is outside the public
  execution boundary. For example, `.executor.shutdown()` alone does not mark
  the interpreter closed, and private dispatch outside a logical run has no
  active run counter. Use public entrypoints and `close()` for the documented
  contract; this implementation is not isolation from its embedding Python host.
- Separate host runs and independent interpreter graphs have separate budgets.
  Process-wide quotas, authenticated closure/capture provenance, rollback,
  deterministic replay, and equivalent limits for every backend remain open.

These are separate follow-up requirements. They do not negate the observed
ownership and cooperative-stop behavior, and that behavior does not establish
their completion.

## Verification surfaces

The implementation is in `src/utf/thirsty_lang/execution.py`, the interpreter,
CLI entrypoints, and the Gods reference entrypoint. Four focused modules provide
the increment's dedicated regression evidence:

- [Execution ownership](../tests/test_execution_ownership.py): concurrent entry,
  same-thread reentry, copied/stale contexts, cascade beyond pool capacity,
  cancellation ownership, and close behavior.
- [Execution limits](../tests/test_execution_limits.py): exact validation, child
  expression dispatch, finite loops, recursive depth, fake-clock deadlines,
  cancellation through callbacks and governance, sticky composed limits,
  imports, and guest catch/cleanup refusal.
- [Lexical execution scope](../tests/test_lexical_execution_scope.py): defining
  environments across callable forms, caller-shadowed contracts, distinct
  escaped scopes, and constructor/default-initializer controls.
- [Entrypoint lifetime](../tests/test_execution_entrypoint_lifetime.py): resource
  acquisition/teardown, CLI limit forwarding and rejection, REPL behavior, and
  Gods interpreter lifetime.

A focused command for these surfaces is:

```text
.venv/Scripts/python.exe -m pytest tests/test_execution_ownership.py tests/test_execution_limits.py tests/test_lexical_execution_scope.py tests/test_execution_entrypoint_lifetime.py -q
```

This command is not the full-suite or release-equivalent gate. Consult the
[integration record](operations/M4_EXECUTION_CONTROL_VERIFICATION.md) for actual
completed commands, failures and repairs, artifact provenance, and remaining
requirements.
