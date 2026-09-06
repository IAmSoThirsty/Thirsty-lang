"""
Layered convergence checking for Shadow Thirst.

`CanonicalConvergenceAnalyzer` asks one question: does the shadow block compute
the *same thing* as the validated canonical block? Three layers answer it, from
cheapest/strongest to most general:

  1. **Structural** (fast pre-check, in ``core.py``) — alpha-renamed AST equality.
     Same shape up to variable naming ⇒ provably the same computation. This is a
     sound *sufficient* condition: a pass here needs no further work.

  2. **Z3 symbolic** (this module, requires ``thirsty-lang[analysis]``) — for the
     straight-line integer-arithmetic subset, translate each block's returned
     value to a Z3 term over shared symbolic inputs and ask the solver whether
     they can ever differ. ``UNSAT`` ⇒ equivalent *for all inputs* (a real
     proof); ``SAT`` ⇒ a concrete diverging input (a counterexample). Reuses the
     translation strategy of :mod:`utf.tarl.analyzer`.

  3. **Execute-and-compare** (this module, no extra deps) — run the supported
     scalar, call-free subset in a metered reference interpreter over seeded
     inputs. Operation, AST and value limits bound execution. This is sampled
     evidence, never a universal proof or a general-purpose host sandbox.

The verdict shape (:class:`AnalysisResult`) and levels are unchanged; this module
only decides ``passed`` and the message/counterexample.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field
from typing import Any

from utf.thirsty_lang.ast import (
    AssignStmt,
    BinaryOp,
    BlockStmt,
    BoolLiteral,
    CallExpr,
    ExprStmt,
    FloatLiteral,
    ForStmt,
    Identifier,
    IfStmt,
    ImportStmt,
    IntLiteral,
    NoneLiteral,
    PourStmt,
    ReturnStmt,
    SipStmt,
    ThrowStmt,
    TimesStmt,
    UnaryOp,
    VariableDecl,
    WhileStmt,
)
from utf.thirsty_lang.interpreter import Interpreter, ReturnException
from utf.thirsty_lang.token import TokenType

# ── Z3 availability (mirrors utf.tarl.analyzer) ───────────────────────────────

# z3-solver ships no type stubs; annotate the handle ``Any`` and import first so
# the success path types as Any (no "None has no attribute …" storm), falling
# back to None when the optional extra is absent.
_z3: Any
try:
    import z3 as _z3  # type: ignore[no-redef,import-untyped,import-not-found]

    _Z3_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without the extra
    _z3 = None
    _Z3_AVAILABLE = False


@dataclass
class ConvergenceVerdict:
    """Outcome of a single convergence layer.

    ``status`` is one of:
      - ``"equivalent"`` — proven/observed equal (``passed`` ⇒ True)
      - ``"diverge"``    — proven/observed different; ``counterexample`` set
      - ``"unsupported"`` — this layer can't model the blocks; try the next
      - ``"unavailable"`` — the layer's dependency (z3) is absent
    """

    status: str
    detail: str = ""
    counterexample: dict | None = None
    assumptions: dict[str, str] = field(default_factory=dict)


# ── free-variable / bound-name analysis ───────────────────────────────────────


def _walk(node):
    import dataclasses

    if node is None or not dataclasses.is_dataclass(node):
        return
    yield node
    for f in dataclasses.fields(node):
        if f.name == "span":
            continue
        value = getattr(node, f.name)
        if dataclasses.is_dataclass(value):
            yield from _walk(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if dataclasses.is_dataclass(item):
                    yield from _walk(item)


def free_variables(block) -> set:
    """Read names unresolved by preceding declarations in their lexical scope."""
    free: set[str] = set()

    def visit(node, scopes):
        if isinstance(node, Identifier):
            if not any(node.name in scope for scope in reversed(scopes)):
                free.add(node.name)
        elif isinstance(node, BlockStmt):
            local = [*scopes, set()]
            for stmt in node.statements:
                visit(stmt, local)
        elif isinstance(node, VariableDecl):
            visit(node.init_expr, scopes)
            scopes[-1].add(node.name)
        elif isinstance(node, ForStmt):
            visit(node.iterable, scopes)
            visit(node.body, [*scopes, {node.variable.name}])
        elif isinstance(node, CallExpr):
            # Calls are unsupported by both semantic layers. Keep data reads
            # useful to callers without treating a direct callee as an Int.
            if not isinstance(node.callee, Identifier):
                visit(node.callee, scopes)
            for arg in node.args:
                visit(arg, scopes)
        elif dataclasses.is_dataclass(node):
            for f in dataclasses.fields(node):
                if f.name != "span":
                    visit(getattr(node, f.name), scopes)
        elif isinstance(node, (list, tuple)):
            for item in node:
                visit(item, scopes)

    visit(block, [set()])
    return free


# ── Layer 2: Z3 symbolic equivalence (integer-arithmetic subset) ──────────────


class _SymUnsupported(Exception):
    """The block uses a construct outside the symbolic subset."""


_CMP_OPS = {
    TokenType.EQEQ: lambda a, b: a == b,
    TokenType.NE: lambda a, b: a != b,
    TokenType.LT: lambda a, b: a < b,
    TokenType.GT: lambda a, b: a > b,
    TokenType.LE: lambda a, b: a <= b,
    TokenType.GE: lambda a, b: a >= b,
}


def _sym_expr(expr, store, zvars, ctx, defined):
    """Translate ``expr`` to a Z3 term in ``ctx``, or raise ``_SymUnsupported``.

    ``store`` maps already-bound names to terms; ``zvars`` is the shared pool of
    free-input symbols (so the same name in shadow and canonical is the same
    Z3 constant). All terms are built in the explicit ``ctx`` — never the global
    z3 context — so each query is fully isolated and GC-clean.
    """
    if isinstance(expr, IntLiteral):
        return _z3.IntVal(expr.value, ctx)
    if isinstance(expr, BoolLiteral):
        return _z3.BoolVal(expr.value, ctx)
    if isinstance(expr, Identifier):
        if expr.name == "__error__":
            raise _SymUnsupported("reserved interpreter error identifier")
        if expr.name in store:
            return store[expr.name]
        if expr.name in zvars:
            return zvars[expr.name]
        raise _SymUnsupported(f"unbound name {expr.name}")
    if isinstance(expr, UnaryOp):
        v = _sym_expr(expr.operand, store, zvars, ctx, defined)
        if expr.op == TokenType.MINUS and _z3.is_int(v):
            return -v
        if expr.op == TokenType.NOT and _z3.is_bool(v):
            return _z3.Not(v)
        raise _SymUnsupported("unary op")
    if isinstance(expr, BinaryOp):
        a = _sym_expr(expr.left, store, zvars, ctx, defined)
        b = _sym_expr(expr.right, store, zvars, ctx, defined)
        op = expr.op
        if op in (TokenType.AND, TokenType.OR):
            if not (_z3.is_bool(a) and _z3.is_bool(b)):
                raise _SymUnsupported("boolean operators require Boolean operands")
            return _z3.And(a, b) if op == TokenType.AND else _z3.Or(a, b)
        if not (_z3.is_int(a) and _z3.is_int(b)):
            raise _SymUnsupported("arithmetic/comparison requires Integer operands")
        if op == TokenType.PLUS:
            return a + b
        if op == TokenType.MINUS:
            return a - b
        if op == TokenType.STAR:
            return a * b
        if op == TokenType.SLASH:
            # Integer division is not faithfully modelled; defer to execution.
            raise _SymUnsupported("division")
        if op == TokenType.PERCENT:
            defined.append(b != 0)
            # Python's remainder has the divisor's sign; Z3's mod is always
            # nonnegative. The zero case is rejected before solving equality.
            return _z3.If(b > 0, a % b, -((-a) % (-b)))
        if op in _CMP_OPS:
            return _CMP_OPS[op](a, b)
        raise _SymUnsupported(f"binop {op}")
    raise _SymUnsupported(f"expr {type(expr).__name__}")


def _sym_block_return(block, zvars, ctx, defined):
    """Symbolically evaluate a straight-line block to its returned term.

    Supports a sequence of ``drink``/assignment statements followed by a
    ``return``. Any control flow or unmodelled statement raises
    ``_SymUnsupported``.
    """
    if not isinstance(block, BlockStmt):
        raise _SymUnsupported("not a block")
    store: dict = {}
    mutable: set[str] = set()
    for stmt in block.statements:
        if isinstance(stmt, VariableDecl):
            if stmt.init_expr is None:
                raise _SymUnsupported("uninitialised decl")
            store[stmt.name] = _sym_expr(stmt.init_expr, store, zvars, ctx, defined)
            if stmt.is_mut:
                mutable.add(stmt.name)
            else:
                mutable.discard(stmt.name)
        elif isinstance(stmt, AssignStmt) and isinstance(stmt.target, Identifier):
            if stmt.target.name not in mutable:
                raise _SymUnsupported("assignment is external or immutable")
            store[stmt.target.name] = _sym_expr(stmt.value, store, zvars, ctx, defined)
        elif isinstance(stmt, ReturnStmt):
            if stmt.value is None:
                raise _SymUnsupported("bare return")
            return _sym_expr(stmt.value, store, zvars, ctx, defined)
        else:
            raise _SymUnsupported(f"stmt {type(stmt).__name__}")
    raise _SymUnsupported("no return")


def z3_equivalence(shadow_block, canonical_block) -> ConvergenceVerdict:
    """Prove or refute equivalence of the two blocks' return values via Z3.

    Each call uses an isolated :class:`z3.Context` with resource/time limits.
    Python-visible solver errors and unknown results cause abstention. Free
    inputs are modeled as integers and that assumption is returned explicitly;
    it must not be treated as proof over unconstrained language inputs. Native
    process crashes are outside this in-process solver's containment boundary.
    """
    if not _Z3_AVAILABLE:
        return ConvergenceVerdict("unavailable", "z3-solver not installed")
    if not _bounded_ast(shadow_block) or not _bounded_ast(canonical_block):
        return ConvergenceVerdict("unsupported", "AST exceeds analysis limits")
    inputs = free_variables(shadow_block) | free_variables(canonical_block)
    try:
        ctx = _z3.Context()
        zvars = {n: _z3.Int(n, ctx) for n in inputs}
        defined: list = []
        try:
            s_ret = _sym_block_return(shadow_block, zvars, ctx, defined)
            c_ret = _sym_block_return(canonical_block, zvars, ctx, defined)
        except _SymUnsupported as exc:
            return ConvergenceVerdict("unsupported", str(exc))
        solver = _z3.Solver(ctx=ctx)
        solver.set(timeout=1000, rlimit=100000)
        if defined:
            solver.add(_z3.Not(_z3.And(*defined)))
            if solver.check() != _z3.unsat:
                return ConvergenceVerdict(
                    "unsupported", "arithmetic may raise for an admitted input"
                )
            solver.reset()
            solver.set(timeout=1000, rlimit=100000)
        solver.add(s_ret != c_ret)
        result = solver.check()
        if result == _z3.unsat:
            return ConvergenceVerdict(
                "equivalent",
                "Z3 proved equal return value for Integer inputs",
                assumptions=dict.fromkeys(sorted(inputs), "Int"),
            )
        if result == _z3.sat:
            model = solver.model()
            ce = {}
            for name, var in zvars.items():
                try:
                    val = model.eval(var, model_completion=True)
                    ce[name] = val.as_long() if _z3.is_int_value(val) else str(val)
                except Exception:
                    pass
            return ConvergenceVerdict(
                "diverge", "Z3 found a diverging input", counterexample=ce
            )
        return ConvergenceVerdict("unsupported", "z3 returned unknown")
    except Exception as exc:  # incl. native OSError from a flaky z3 build
        return ConvergenceVerdict("unsupported", f"z3 unavailable: {exc}")


# ── Layer 3: execute-and-compare over seeded inputs ───────────────────────────

# A deterministic spread of integer vectors. Mixes small/edge/negative values so
# that off-by-one and sign divergences surface without a fuzzing budget.
_SEED_VALUES = (0, 1, 2, 3, 5, 7, -1, -2, 10, 13)

_NO_RETURN = object()

_MAX_AST_NODES = 1000
_MAX_AST_DEPTH = 64
_MAX_STEPS = 10000
_MAX_INTEGER_BITS = 4096


def _bounded_ast(block) -> bool:
    """Bound work before recursive visitors or native symbolic translation."""
    pending = [(block, 0)]
    count = 0
    while pending:
        node, depth = pending.pop()
        count += 1
        if count > _MAX_AST_NODES or depth > _MAX_AST_DEPTH:
            return False
        if isinstance(node, IntLiteral) and node.value.bit_length() > _MAX_INTEGER_BITS:
            return False
        if dataclasses.is_dataclass(node):
            pending.extend(
                (getattr(node, f.name), depth + 1)
                for f in dataclasses.fields(node)
                if f.name != "span"
            )
        elif isinstance(node, (list, tuple)):
            if len(node) > _MAX_AST_NODES:
                return False
            pending.extend((item, depth + 1) for item in node)
    return True


def is_effect_free(block) -> bool:
    """True if ``block`` performs no observable I/O / import / throw effect.

    Calls, including aliases and member calls, are unresolved effects. The
    sampling layer further restricts the accepted AST and assignment surface.
    """
    for n in _walk(block):
        if isinstance(n, (PourStmt, SipStmt, ImportStmt, ThrowStmt, CallExpr)):
            return False
        if isinstance(n, AssignStmt) and not isinstance(n.target, Identifier):
            return False
    return True


_SAMPLED_NODES = {
    BlockStmt,
    VariableDecl,
    AssignStmt,
    ReturnStmt,
    ExprStmt,
    IfStmt,
    WhileStmt,
    TimesStmt,
    Identifier,
    BinaryOp,
    UnaryOp,
    IntLiteral,
    FloatLiteral,
    BoolLiteral,
    NoneLiteral,
}


class _BoundedInterpreter(Interpreter):
    """Meter the reference interpreter's scalar-only, call-free subset.

    No supplied object or guest operation can invoke a host callable, allocate
    a collection, or bypass the operation counter. Integer operands are bounded
    before every operation; their product is at most twice that bit limit.
    This is a restricted evaluator, not a general-purpose sandbox.
    """

    def __init__(self):
        super().__init__()
        self.steps = _MAX_STEPS

    def _step(self):
        self.steps -= 1
        if self.steps < 0:
            raise RuntimeError("sampling operation budget exhausted")

    @staticmethod
    def _scalar(value):
        if type(value) is int:
            if value.bit_length() > _MAX_INTEGER_BITS:
                raise RuntimeError("sampling integer budget exhausted")
        elif type(value) is float:
            if not math.isfinite(value):
                raise RuntimeError("sampling requires finite numbers")
        elif value is not None and type(value) is not bool:
            raise RuntimeError("sampling requires scalar values")
        return value

    def _execute(self, stmt):
        self._step()
        return super()._execute(stmt)

    def _evaluate_impl(self, expr):
        self._step()
        return self._scalar(super()._evaluate_impl(expr))


def _run_block(block, bindings):
    """Run a bounded scalar block with ``bindings`` defined; return value.

    Returns the value carried by a ``return``, or ``_NO_RETURN`` if the block
    falls off the end. Raises on any interpreter error (caller decides).
    """
    if not isinstance(block, BlockStmt) or not _bounded_ast(block):
        raise ValueError("unsupported or oversized sampling block")
    if any(type(node) not in _SAMPLED_NODES for node in _walk(block)):
        raise ValueError(
            "sampling supports only scalar expressions and local control flow"
        )
    # Assigning a free variable changes external state, which cannot be judged
    # from the returned value alone. Scope-aware free-variable analysis includes
    # assignment targets, so reject that surface before executing anything.
    external = free_variables(block)
    if any(
        isinstance(node, AssignStmt)
        and (not isinstance(node.target, Identifier) or node.target.name in external)
        for node in _walk(block)
    ):
        raise ValueError("sampling does not support external assignment")
    it = _BoundedInterpreter()
    for name, value in bindings.items():
        it.env.define(name, it._scalar(value), is_mut=False)
    try:
        for stmt in block.statements:
            it._execute(stmt)
    except ReturnException as exc:
        return exc.value
    return _NO_RETURN


def _run_block_guarded(block, bindings):
    """Run a block with enforced operation/value budgets; returns (ok, value)."""
    try:
        return True, _run_block(block, bindings)
    except Exception:
        return False, None


def _seed_vectors(names, limit=8):
    """Deterministic input vectors for the given free-variable names."""
    names = sorted(names)
    if not names:
        return [{}]
    vectors = []
    for i in range(min(limit, len(_SEED_VALUES))):
        # Stagger each variable so they don't all move together.
        vectors.append(
            {
                name: _SEED_VALUES[(i + j) % len(_SEED_VALUES)]
                for j, name in enumerate(names)
            }
        )
    return vectors


def execute_and_compare(shadow_block, canonical_block) -> ConvergenceVerdict:
    """Run both blocks over seeded inputs and compare returned values."""
    if not isinstance(shadow_block, BlockStmt) or not isinstance(
        canonical_block, BlockStmt
    ):
        return ConvergenceVerdict("unsupported", "missing block AST")
    # Return-value comparison is only sound for effect-free blocks.
    if not (_bounded_ast(shadow_block) and _bounded_ast(canonical_block)):
        return ConvergenceVerdict("unsupported", "AST exceeds analysis limits")
    if not (is_effect_free(shadow_block) and is_effect_free(canonical_block)):
        return ConvergenceVerdict(
            "unsupported", "block has observable effects; not sampled"
        )
    names = free_variables(shadow_block) | free_variables(canonical_block)
    compared = 0
    for bindings in _seed_vectors(names):
        s_ok, s_val = _run_block_guarded(shadow_block, bindings)
        c_ok, c_val = _run_block_guarded(canonical_block, bindings)
        if not (s_ok and c_ok):
            return ConvergenceVerdict(
                "unsupported", "a sampled input failed or exceeded an execution budget"
            )
        compared += 1
        if s_val is _NO_RETURN or c_val is _NO_RETURN:
            if s_val is not c_val:
                return ConvergenceVerdict(
                    "diverge",
                    "one block returns a value while the other does not",
                    counterexample=dict(bindings) or {"<no-inputs>": True},
                )
            continue
        if type(s_val) is not type(c_val) or s_val != c_val:
            return ConvergenceVerdict(
                "diverge",
                f"diverging output (shadow={s_val!r}, canonical={c_val!r})",
                counterexample=dict(bindings) or {"<no-inputs>": True},
            )
    if compared == 0:
        return ConvergenceVerdict("unsupported", "no input vector ran cleanly")
    return ConvergenceVerdict(
        "equivalent", f"identical output on {compared} sampled input(s)"
    )
