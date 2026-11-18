"""
Thirsty-Lang Tree-Walking Interpreter
Evaluates Thirsty-Lang AST programs with full environment scoping,
governance enforcement, tail-call optimization, and async support.
"""

from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from pathlib import Path
from threading import RLock
from typing import Any

from utf.thirsty_lang.ast import (
    ArmorExpr,
    ArrayLiteral,
    AssignStmt,
    BinaryOp,
    BlockStmt,
    BoolLiteral,
    CallExpr,
    CascadeCall,
    ClassDecl,
    CleanupStmt,
    CombineExpr,
    CondenseExpr,
    DefendStrat,
    DictLiteral,
    DripExpr,
    EnumDecl,
    ErrorLiteral,
    EvaporateExpr,
    Expr,
    ExprStmt,
    FloatLiteral,
    FloodExpr,
    ForStmt,
    FunctionDecl,
    GovernedFunctionDecl,
    GuardExpr,
    Identifier,
    IfStmt,
    ImportStmt,
    InterfaceDecl,
    IntLiteral,
    LambdaExpr,
    MemberAccess,
    MorphDef,
    NewExpr,
    NoneLiteral,
    PipeExpr,
    PipelineExpr,
    PourStmt,
    Program,
    QuenchedLiteral,
    ReturnStmt,
    SanitizeExpr,
    SecurityBlock,
    ShadowThirstMutation,
    SipStmt,
    SliceExpr,
    SpillageStmt,
    Stmt,
    StringLiteral,
    StructDecl,
    Subscript,
    SymbolExpr,
    SymbolStmt,
    ThrowStmt,
    TimesStmt,
    UnaryOp,
    VariableDecl,
    WhileStmt,
)
from utf.thirsty_lang.execution import (
    ExecutionDomain,
    ExecutionError,
    ExecutionLimits,
    resolve_execution_mode,
)
from utf.thirsty_lang.governed_values import NativeValueRegistry
from utf.thirsty_lang.module_system import (
    BUILTINS,
    SENSITIVE_STDLIB_CAPABILITIES,
    resolve_import,
    validate_stdlib_exports,
)
from utf.thirsty_lang.sequences import get_index, get_slice, set_index
from utf.thirsty_lang.token import TokenType

_PURE_EXECUTION: ContextVar[bool] = ContextVar("thirsty_pure_execution", default=False)


@dataclass(frozen=True)
class _ExecutionFrame:
    owner: Any
    governed: bool
    pure: bool
    strict: bool


_EXECUTION_FRAMES: ContextVar[tuple[_ExecutionFrame, ...]] = ContextVar(
    "thirsty_execution_frames", default=()
)


def _merge_execution_frames(frames):
    merged: dict[int, _ExecutionFrame] = {}
    for frame in frames:
        key = id(frame.owner)
        previous = merged.get(key)
        merged[key] = (
            frame
            if previous is None
            else _ExecutionFrame(
                frame.owner,
                previous.governed or frame.governed,
                previous.pure or frame.pure,
                previous.strict or frame.strict,
            )
        )
    return tuple(merged.values())


@contextmanager
def _execution_scope(frames):
    combined = _merge_execution_frames((*_EXECUTION_FRAMES.get(), *frames))
    token = _EXECUTION_FRAMES.set(combined)
    pure_token = _PURE_EXECUTION.set(
        _PURE_EXECUTION.get() or any(frame.pure for frame in combined)
    )
    try:
        yield
    finally:
        _PURE_EXECUTION.reset(pure_token)
        _EXECUTION_FRAMES.reset(token)


@dataclass
class _ExecutionRestrictions:
    """Live configuration shared by a module and all its imported closures."""

    tarl_runtime: Any = None
    authority: Any = None
    verified_authority: Any = None
    path_guard: Any = None
    authority_authenticated: bool = False
    authority_grants: tuple[str, ...] = ()
    hardened: bool = False
    locked_imports: Any = None
    revision: int = 0
    lock: Any = field(default_factory=RLock, repr=False, compare=False)
    native_values: NativeValueRegistry = field(default_factory=NativeValueRegistry)


@dataclass
class StructInstance:
    """A nominal record; fields can be assigned but cannot be added silently."""

    declaration: StructDecl
    fields: dict[str, Any]
    type_environment: "Environment"
    native_identity: Any = field(default=None, repr=False, compare=False)


class ReturnException(Exception):
    """Used for control flow to unwind non-tail-called returns."""

    def __init__(self, value):
        self.value = value


class SpillageException(Exception):
    """Represents an error thrown via throw/spillage."""

    def __init__(self, value):
        self.value = value
        super().__init__(str(value))


class GovernanceViolation(Exception):
    """Raised when a governed function is denied at runtime.

    Carries the governed function name, a human-readable reason, and the
    optional ``TarlProof`` produced when the denial came from the policy
    engine, so callers (the CLI) can surface the proof certificate.
    """

    def __init__(self, name: str, reason: str, proof=None):
        self.name = name
        self.reason = reason
        self.proof = proof
        super().__init__(f"governance denied: {name}: {reason}")


class Environment:
    """Scoped variable storage."""

    def __init__(self, parent: "Environment | None" = None):
        self.parent = parent
        self.vars: dict[str, object] = {}
        self.mutable: dict[str, bool] = {}

    def define(self, name: str, value: object, is_mut: bool = False):
        self.vars[name] = value
        self.mutable[name] = is_mut

    def get(self, name: str) -> object:
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name)
        raise NameError(f"Undefined variable: '{name}'")

    def set(self, name: str, value: object):
        if name in self.vars:
            if not self.mutable.get(name, False):
                raise TypeError(f"Cannot assign to immutable variable: '{name}'")
            self.vars[name] = value
            return
        if self.parent:
            self.parent.set(name, value)
            return
        raise NameError(f"Undefined variable: '{name}'")

    def has(self, name: str) -> bool:
        return name in self.vars or bool(self.parent and self.parent.has(name))

    def enter_scope(self) -> "Environment":
        return Environment(self)

    def __repr__(self):
        return f"Environment({list(self.vars.keys())})"


class FountainInstance:
    """Instance of a fountain (class)."""

    def __init__(self, cls_decl: ClassDecl, env: Environment):
        self.cls_decl = cls_decl
        self.declaration_env = env
        self.fields: dict[str, Any] = {}
        self.methods: dict[str, Any] = {}
        self.execution_frames: tuple[_ExecutionFrame, ...] = ()
        self.interpreter: Any = None
        self.native_identity: Any = None
        for field_spec in cls_decl.fields:
            self.fields[field_spec[0]] = None
        for method in cls_decl.methods:
            self.methods[method.name] = method

    def get_field(self, name: str) -> object:
        if name in self.fields:
            return self.fields[name]
        raise NameError(f"Undefined field: '{name}'")

    def set_field(self, name: str, value: object):
        if name in self.fields:
            self.fields[name] = value
        else:
            raise NameError(f"Undefined field: '{name}'")


class Interpreter:
    """Tree-walking interpreter with TCO, governance, and async support."""

    def __init__(
        self,
        opt_level: int = 0,
        debug_mode: bool = False,
        *,
        allow_ungoverned: bool = False,
        execution_limits: ExecutionLimits | None = None,
    ):
        semantic, governed = resolve_execution_mode(allow_ungoverned=allow_ungoverned)
        self._allow_ungoverned = allow_ungoverned
        self._execution_governed = governed
        self._restrictions = _ExecutionRestrictions()
        self.source_directory = Path.cwd()
        self._import_stack: tuple[Path, ...] = ()
        self.env = Environment()
        self.opt_level = opt_level
        self.debug_mode = debug_mode
        self.tco_enabled = opt_level >= 1
        self.mode = semantic
        self._execution_domain = ExecutionDomain(execution_limits)
        self._last_span = None
        # Governance wiring (Part A): optional policy engine + authority context.
        self.tarl_runtime = None
        self.authority = None
        # The verified credential (if any) behind ``authority``, retained so the
        # capability broker can be built with the same authenticity it sees here.
        self._verified_authority: Any = None
        # Optional filesystem confinement for governed file capabilities; when
        # set, ``thirst::fs`` targets are confined to these roots (C042).
        self.path_guard: Any = None
        # Authority provenance: a bare string authority is self-asserted
        # (authenticated=False, no grants); a verified signed claim sets these.
        self.authority_authenticated = False
        self.authority_grants: tuple[str, ...] = ()
        # Hardened posture: when True, governed gates additionally require an
        # authenticated authority and Ed25519-signed proofs, or they fail closed.
        self.hardened = False
        self._last_proof: Any = None
        self._register_builtins()
        if self.opt_level >= 2:
            self._inline_simple_builtins()
        if self.opt_level >= 3:
            self._precompute_constants()

    @property
    def executor(self):
        """The scheduler shared with file imports; prefer close() for teardown."""
        return self._execution_domain.executor

    @property
    def execution_limits(self) -> ExecutionLimits:
        return self._execution_domain.limits

    def cancel(self) -> bool:
        """Cooperatively stop this interpreter's active logical execution."""
        return self._execution_domain.cancel()

    def close(self):
        """Close the idle interpreter/import graph, preserving borrowed TARL."""
        self._execution_domain.close()

    def __enter__(self):
        with self._execution_domain.enter():
            return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _governance_is_required(self) -> bool:
        return (
            not self._allow_ungoverned
            or self._execution_governed
            or self.mode == "governed"
            or self.hardened
            or self.tarl_runtime is not None
            or any(
                frame.owner is self and frame.governed
                for frame in _EXECUTION_FRAMES.get()
            )
        )

    def _execution_frame(self) -> _ExecutionFrame:
        return _ExecutionFrame(
            self,
            self._governance_is_required(),
            self.mode == "pure" or _PURE_EXECUTION.get(),
            self.mode == "strict"
            or any(frame.strict for frame in _EXECUTION_FRAMES.get()),
        )

    def _policy_binding_key(self):
        authority = self.authority
        authority_key = authority if type(authority) is str else id(authority)
        grants = self.authority_grants
        grants_key = (
            grants
            if type(grants) is tuple and all(type(item) is str for item in grants)
            else id(grants)
        )
        return (
            id(self.tarl_runtime),
            authority_key,
            id(self._verified_authority),
            bool(self.authority_authenticated),
            grants_key,
            bool(self.hardened),
            id(self.path_guard),
        )

    def _bind_callable(self, function, frames=None):
        """Retain defining restrictions while adding those of every caller."""
        captured = _merge_execution_frames(
            (*_EXECUTION_FRAMES.get(), self._execution_frame())
            if frames is None
            else frames
        )

        @wraps(function)
        def bound(*args, **kwargs):
            with self._execution_domain.enter(call=True), ExitStack() as claims:
                for frame in captured:
                    claims.enter_context(frame.owner._execution_domain.enter())
                with _execution_scope(captured):
                    return function(*args, **kwargs)

        return bound

    def _active_import_locks(self):
        locks = []
        seen = set()
        for frame in (*_EXECUTION_FRAMES.get(), self._execution_frame()):
            locked = frame.owner.locked_imports
            if locked is not None and id(locked) not in seen:
                seen.add(id(locked))
                locks.append(locked)
        return locks

    @property
    def tarl_runtime(self):
        return self._restrictions.tarl_runtime

    @tarl_runtime.setter
    def tarl_runtime(self, value):
        with self._restrictions.lock:
            self._restrictions.tarl_runtime = value
            self._restrictions.revision += 1

    @property
    def authority(self):
        return self._restrictions.authority

    @authority.setter
    def authority(self, value):
        with self._restrictions.lock:
            self._restrictions.authority = value
            self._restrictions.revision += 1

    @property
    def _verified_authority(self):
        return self._restrictions.verified_authority

    @_verified_authority.setter
    def _verified_authority(self, value):
        with self._restrictions.lock:
            self._restrictions.verified_authority = value
            self._restrictions.revision += 1

    @property
    def authority_authenticated(self):
        return self._restrictions.authority_authenticated

    @authority_authenticated.setter
    def authority_authenticated(self, value):
        with self._restrictions.lock:
            self._restrictions.authority_authenticated = value
            self._restrictions.revision += 1

    @property
    def authority_grants(self):
        return self._restrictions.authority_grants

    @authority_grants.setter
    def authority_grants(self, value):
        with self._restrictions.lock:
            self._restrictions.authority_grants = value
            self._restrictions.revision += 1

    @property
    def hardened(self):
        return self._restrictions.hardened

    @hardened.setter
    def hardened(self, value):
        with self._restrictions.lock:
            self._restrictions.hardened = value
            self._restrictions.revision += 1

    @property
    def path_guard(self):
        return self._restrictions.path_guard

    @path_guard.setter
    def path_guard(self, value):
        with self._restrictions.lock:
            self._restrictions.path_guard = value
            self._restrictions.revision += 1

    @property
    def locked_imports(self):
        return self._restrictions.locked_imports

    @locked_imports.setter
    def locked_imports(self, value):
        with self._restrictions.lock:
            self._restrictions.locked_imports = value
            self._restrictions.revision += 1

    def set_locked(self, context) -> "Interpreter":
        """Bind a content-verifying import context, including for child modules."""
        self.locked_imports = context
        return self

    def _authorization_snapshot(self):
        restrictions = self._restrictions
        with restrictions.lock:
            return restrictions, restrictions.revision, self.mode

    def _changed_authorization(self, snapshot, action: str, target: str):
        restrictions, revision, mode = snapshot
        with restrictions.lock:
            changed = (
                self._restrictions is not restrictions
                or restrictions.revision != revision
                or self.mode != mode
            )
        if not changed:
            return None
        from utf.tarl.spec import TarlVerdict

        reason = "authority binding changed during authorization"
        proof = self._make_decision_proof(
            source="<fail-closed: authority binding changed>",
            context={"action": action, "target": str(target)},
            verdict=TarlVerdict.DENY,
            matched_condition="",
            trace=[
                {"kind": "authority-binding-change", "matched": False, "reason": reason}
            ],
        )
        self._last_proof = proof
        return GovernanceViolation(f"{action} {target}", reason, proof)

    def _precompute_constants(self):
        """Opt level 3: Pre-compute constant expressions at init time."""
        self._const_cache = {}

    def _inline_simple_builtins(self):
        """Opt level 2: Inline simple builtin functions for faster execution."""
        self._inlineable_builtins = set()
        for name in ("length", "size", "abs", "print", "pour", "push", "pop", "flood"):
            if name in self.env.vars:
                self._inlineable_builtins.add(name)

    def _register_builtins(self):
        """Register builtin functions in the global environment."""
        builtins_map = {
            **BUILTINS,
            "print": self._builtin_print,
            "pour": self._builtin_pour,
        }
        self._builtin_callables = {}
        for name, func in builtins_map.items():
            bound = self._bind_callable(func, frames=())
            self._builtin_callables[id(bound)] = bound
            self.env.define(name, bound, is_mut=False)

    def _builtin_print(self, *args):
        self._gate_capability("write", "stdout")
        print(*args)
        return args[-1] if args else None

    def _builtin_pour(self, *args):
        self._gate_capability("write", "stdout")
        print(*args)
        return args[-1] if args else None

    def interpret(
        self, ast: Program, mode: str | None = None, force_mode: bool = False
    ) -> object:
        """Interpret an entire Program AST.

        Governance is required unless the trusted host explicitly opted out.
        ``force_mode`` selects source semantics in place of the declared mode;
        neither option can remove a declared or inherited governance floor.
        """
        nested = any(frame.owner is self for frame in _EXECUTION_FRAMES.get())
        with self._execution_domain.enter():
            previous_mode = self.mode, self._execution_governed
            try:
                return self._interpret_program(ast, mode, force_mode)
            finally:
                if nested:
                    self.mode, self._execution_governed = previous_mode

    def _interpret_program(self, ast, mode, force_mode):
        self.mode, self._execution_governed = resolve_execution_mode(
            ast.header.mode if ast.header else None,
            mode,
            allow_ungoverned=self._allow_ungoverned,
            force_mode=force_mode,
        )
        if (
            self.hardened or getattr(self.tarl_runtime, "_require_audit", False)
        ) and not self._governance_is_required():
            raise GovernanceViolation(
                "<module>",
                "hardened or required-audit execution requires governed mode",
            )
        # Fail-closed: a governed program the parser flagged as malformed must
        # not execute. The parser already discarded its statements; refuse the
        # whole program with a denial proof rather than running an empty body.
        if self._governance_is_required() and getattr(ast, "parse_failed", False):
            from utf.tarl.spec import TarlVerdict

            proof = self._make_decision_proof(
                source="<fail-closed: governed module failed to parse>",
                context={"action": "execute", "reason": "parse_failed"},
                verdict=TarlVerdict.DENY,
                matched_condition="",
                trace=[
                    {
                        "kind": "fail-closed",
                        "action": "execute",
                        "reason": "governed module had parse errors; "
                        "execution refused",
                    }
                ],
            )
            self._last_proof = proof
            raise GovernanceViolation(
                "<module>",
                "fail-closed: governed module failed to parse; refusing to "
                "execute recovered statements",
                proof,
            )
        if getattr(ast, "parse_failed", False):
            raise RuntimeError("module failed to parse; refusing recovered statements")
        result = None
        pure_token = _PURE_EXECUTION.set(_PURE_EXECUTION.get() or self.mode == "pure")
        try:
            with _execution_scope((self._execution_frame(),)):
                for stmt in ast.stmts:
                    result = self._execute(stmt)
                    if isinstance(result, (ReturnException, SpillageException)):
                        break
        except ReturnException as e:
            result = e.value
        finally:
            _PURE_EXECUTION.reset(pure_token)
        return result

    def _with_debug(self, stmt_or_expr, context: str = ""):
        """Wrapper that adds source-location tracking in debug mode."""
        if not self.debug_mode:
            return None  # No wrapping needed
        span = getattr(stmt_or_expr, "span", None)
        if span:
            self._last_span = span
        return f"at line {span[0]}, column {span[1]}" if span else None

    def _execute(self, stmt: Stmt) -> object:
        """Execute a statement. Returns a value for expressions or None."""
        pure_token = _PURE_EXECUTION.set(_PURE_EXECUTION.get() or self.mode == "pure")
        try:
            if self.debug_mode:
                try:
                    return self._execute_impl(stmt)
                except Exception as e:
                    loc = self._with_debug(stmt)
                    loc_msg = f" at {loc}" if loc else ""
                    if loc_msg:
                        e.add_note(loc_msg)
                    raise
            else:
                return self._execute_impl(stmt)
        finally:
            _PURE_EXECUTION.reset(pure_token)

    def _evaluate(self, expr: Expr) -> Any:
        """Evaluate an expression and return its value."""
        pure_token = _PURE_EXECUTION.set(_PURE_EXECUTION.get() or self.mode == "pure")
        try:
            if self.debug_mode:
                try:
                    return self._evaluate_impl(expr)
                except Exception as e:
                    loc = self._with_debug(expr)
                    loc_msg = f" at {loc}" if loc else ""
                    if loc_msg:
                        e.add_note(loc_msg)
                    raise
            else:
                return self._evaluate_impl(expr)
        finally:
            _PURE_EXECUTION.reset(pure_token)

    def _execute_impl(self, stmt: Stmt) -> object:
        """Execute a statement. Returns a value for expressions or None."""
        self._execution_domain.checkpoint(step=True)
        try:
            return self._execute_node(stmt)
        finally:
            self._execution_domain.checkpoint()

    def _execute_node(self, stmt: Stmt) -> object:
        if isinstance(stmt, BlockStmt):
            return self._execute_block(stmt)
        elif isinstance(stmt, ExprStmt):
            return self._evaluate(stmt.expr)
        elif isinstance(stmt, VariableDecl):
            return self._execute_variable_decl(stmt)
        elif isinstance(stmt, AssignStmt):
            return self._execute_assign(stmt)
        elif isinstance(stmt, SymbolStmt):
            return self._execute_symbol_stmt(stmt)
        elif isinstance(stmt, IfStmt):
            return self._execute_if(stmt)
        elif isinstance(stmt, WhileStmt):
            return self._execute_while(stmt)
        elif isinstance(stmt, ForStmt):
            return self._execute_for(stmt)
        elif isinstance(stmt, TimesStmt):
            return self._execute_times(stmt)
        elif isinstance(stmt, ReturnStmt):
            return self._execute_return(stmt)
        elif isinstance(stmt, PourStmt):
            return self._execute_pour(stmt)
        elif isinstance(stmt, SipStmt):
            return self._execute_sip(stmt)
        elif isinstance(stmt, ImportStmt):
            return self._execute_import(stmt)
        elif isinstance(stmt, FunctionDecl):
            return self._execute_function_decl(stmt)
        elif isinstance(stmt, ClassDecl):
            return self._execute_class_decl(stmt)
        elif isinstance(stmt, SpillageStmt):
            return self._execute_spillage(stmt)
        elif isinstance(stmt, CleanupStmt):
            return self._execute_cleanup(stmt)
        elif isinstance(stmt, ThrowStmt):
            return self._execute_throw(stmt)
        elif isinstance(stmt, SecurityBlock):
            return self._execute_security_block(stmt)
        elif isinstance(stmt, CascadeCall):
            return self._execute_cascade(stmt)
        elif isinstance(stmt, MorphDef):
            return self._execute_morph(stmt)
        elif isinstance(stmt, DefendStrat):
            raise NotImplementedError(
                "defend strategies have no enforcement implementation"
            )
        elif isinstance(stmt, EnumDecl):
            if len(stmt.variants) != len(set(stmt.variants)):
                raise TypeError(f"duplicate variant in enum '{stmt.name}'")
            enum_type = Enum(stmt.name, {variant: variant for variant in stmt.variants})  # type: ignore[misc]
            enum_type._thirsty_native_identity = self._restrictions.native_values.register(  # type: ignore[attr-defined]
                enum_type, "enum", stmt.name
            )
            self.env.define(stmt.name, enum_type)
            return enum_type
        elif isinstance(stmt, StructDecl):
            return self._execute_struct_decl(stmt)
        elif isinstance(stmt, InterfaceDecl):
            raise NotImplementedError("interface contracts are not yet enforced")
        elif isinstance(stmt, GovernedFunctionDecl):
            return self._execute_governed_function_decl(stmt)
        elif isinstance(stmt, ShadowThirstMutation):
            return self._execute_shadow_thirst(stmt)
        raise NotImplementedError(f"unsupported statement: {type(stmt).__name__}")

    def _execute_block(self, block: BlockStmt) -> object:
        old_env = self.env
        self.env = self.env.enter_scope()
        result = None
        try:
            for stmt in block.statements:
                result = self._execute(stmt)
                if isinstance(result, (ReturnException, SpillageException)):
                    break
        finally:
            self.env = old_env
        return result

    def _execute_variable_decl(self, stmt: VariableDecl) -> object:
        if (
            self.mode == "strict"
            or any(frame.strict for frame in _EXECUTION_FRAMES.get())
        ) and stmt.init_expr is None:
            raise RuntimeError(
                f"'strict' module requires '{stmt.name}' to be initialized"
            )
        value = None
        if stmt.init_expr:
            value = self._evaluate(stmt.init_expr)
        self.env.define(stmt.name, value, is_mut=stmt.is_mut)
        return None  # drink is a statement, not an expression — no value propagation

    def _execute_assign(self, stmt: AssignStmt) -> object:
        if isinstance(stmt.target, SliceExpr):
            raise NotImplementedError("slice assignment is not supported")
        value = self._evaluate(stmt.value)
        if isinstance(stmt.target, Identifier):
            self.env.set(stmt.target.name, value)
        elif isinstance(stmt.target, MemberAccess):
            obj = self._evaluate(stmt.target.obj)
            if isinstance(obj, FountainInstance):
                obj.set_field(stmt.target.member, value)
            elif isinstance(obj, StructInstance):
                self._set_struct_field(obj, stmt.target.member, value)
            elif isinstance(obj, dict):
                obj[stmt.target.member] = value
            else:
                raise TypeError(
                    f"Cannot assign member '{stmt.target.member}' on "
                    f"{type(obj).__name__}"
                )
        elif isinstance(stmt.target, Subscript):
            obj = self._evaluate(stmt.target.obj)
            index = self._evaluate(stmt.target.index)
            set_index(obj, index, value)
        else:
            raise TypeError(f"invalid assignment target: {type(stmt.target).__name__}")
        return value

    def _execute_symbol_stmt(self, stmt: SymbolStmt) -> object:
        self.env.define(stmt.symbol_name, stmt.symbol_name, is_mut=False)
        return None

    def _execute_if(self, stmt: IfStmt) -> object:
        condition = self._evaluate(stmt.condition)
        if condition:
            return self._execute(stmt.then_block)
        elif stmt.else_block:
            if isinstance(stmt.else_block, IfStmt):
                return self._execute_if(stmt.else_block)
            return self._execute(stmt.else_block)
        return None

    def _execute_while(self, stmt: WhileStmt) -> object:
        result = None
        while self._evaluate(stmt.condition):
            result = self._execute(stmt.body)
            if isinstance(result, (ReturnException, SpillageException)):
                return result
        return result

    def _execute_for(self, stmt: ForStmt) -> object:
        iterable = self._evaluate(stmt.iterable)
        result = None
        for item in iterable:
            old_env = self.env
            self.env = self.env.enter_scope()
            self.env.define(stmt.variable.name, item, is_mut=False)
            try:
                result = self._execute(stmt.body)
                if isinstance(result, (ReturnException, SpillageException)):
                    return result
            finally:
                self.env = old_env
        return result

    def _execute_times(self, stmt: TimesStmt) -> object:
        count = self._evaluate(stmt.count)
        result = None
        for _ in range(int(count)):
            result = self._execute(stmt.body)
            if isinstance(result, (ReturnException, SpillageException)):
                return result
        return result

    def _execute_return(self, stmt: ReturnStmt) -> object:
        value = self._evaluate(stmt.value) if stmt.value else None
        raise ReturnException(value)

    def _execute_pour(self, stmt: PourStmt) -> object:
        if self.mode == "pure":
            raise RuntimeError("I/O ('pour') is not allowed in a 'pure' module")
        self._gate_capability("write", "stdout")
        value = self._evaluate(stmt.value)
        print(value)
        return None  # pour handles its own output — no value propagation

    def _execute_sip(self, stmt: SipStmt) -> object:
        if self.mode == "pure":
            raise RuntimeError("I/O ('sip') is not allowed in a 'pure' module")
        self._gate_capability("read", "stdin")
        value = self._invoke(input)
        if isinstance(stmt.target, Identifier):
            self.env.set(stmt.target.name, value)
        return value

    def _make_decision_proof(
        self,
        *,
        source: str,
        context: dict,
        verdict,
        matched_condition: str,
        trace: list,
    ):
        """Build an (unsigned) ``TarlProof`` for a governance decision made
        outside the policy engine — a fail-closed capability denial or a
        design-by-contract verdict. Same certificate shape as a policy proof
        (``rule_index = -1``, no rule), so every governed decision carries a
        proof. Unsigned; see utf/tarl/spec.py:TarlProof for the signing model.
        """
        import hashlib
        from datetime import UTC, datetime

        from utf.tarl.context import (
            ContextResolutionError,
            prepare_context,
            rejected_context_binding,
        )
        from utf.tarl.spec import TarlProof, TarlVerdict

        policy_hash = "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
        try:
            prepared = prepare_context(context)
        except ContextResolutionError as exc:
            prepared = rejected_context_binding(
                context, conflict_status=exc.conflict_status
            )
            if verdict is TarlVerdict.ALLOW:
                verdict = TarlVerdict.DENY
                matched_condition = str(exc)
                trace = [
                    *trace,
                    {"kind": "fail-closed", "reason": str(exc), "matched": False},
                ]
        context_hash = prepared.canonical_context_hash or prepared.original_context_hash
        return TarlProof(
            policy_hash=policy_hash,
            context_hash=context_hash,
            rule_index=-1,
            matched_condition=matched_condition,
            verdict=verdict,
            evaluated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            trace=trace,
            signature="",
            key_id="",
            original_context_hash=prepared.original_context_hash,
            canonical_context_hash=prepared.canonical_context_hash,
            context_representation_id=prepared.context_representation_id,
            normalization_algorithm_id=prepared.normalization_algorithm_id,
            normalization_version=prepared.normalization_version,
            context_conflict_status=prepared.context_conflict_status,
        )

    def _gate_capability(
        self, action: str, target: str, *, path: str | None = None
    ) -> None:
        """Require all defining and calling policies before a mediated effect."""
        self._execution_domain.checkpoint()
        frames = _merge_execution_frames(
            (*_EXECUTION_FRAMES.get(), self._execution_frame())
        )
        if action != "import" and (
            _PURE_EXECUTION.get() or any(frame.pure for frame in frames)
        ):
            raise RuntimeError(
                f"effect '{action}' on '{target}' is not allowed in a 'pure' module"
            )
        owners = []
        representatives: dict[tuple, Interpreter] = {}
        aliases = []
        for frame in frames:
            owner = frame.owner
            if not (frame.governed or owner._governance_is_required()):
                continue
            # Identical policy/authority/guard bindings represent one decision,
            # even when separate interpreters carry those bindings. Different
            # credentials or guards must still authorize independently.
            key = owner._policy_binding_key()
            representative = representatives.get(key)
            if representative is None:
                representatives[key] = owner
                owners.append(owner)
            else:
                aliases.append((owner, representative))
        snapshots = [
            (owner, owner._authorization_snapshot())
            for owner in (*owners, *(alias for alias, _ in aliases))
        ]
        try:
            for owner in owners:
                owner._gate_capability_local(action, target, path=path)
            for owner, representative in aliases:
                owner._last_proof = representative._last_proof
            # A later policy callback cannot revoke or replace an earlier
            # binding and still release this compound authorization to an effect.
            for owner, snapshot in snapshots:
                changed = owner._changed_authorization(snapshot, action, target)
                violation = changed or owner._hardened_precheck(action, target)
                if violation is not None:
                    raise violation
            # Credential revalidation may call trusted host code. Check every
            # original binding again after all such callbacks have returned.
            for owner, snapshot in snapshots:
                violation = owner._changed_authorization(snapshot, action, target)
                if violation is not None:
                    raise violation
        except GovernanceViolation as denied:
            self._last_proof = denied.proof
            raise
        self._execution_domain.checkpoint()

    def _gate_capability_local(
        self, action: str, target: str, *, path: str | None = None
    ) -> None:
        """Capability gate for sensitive operations (imports, I/O) in governed
        mode. Fail-closed: in governed mode a gated capability is denied unless
        a TARL policy engine + authority are attached AND return ALLOW. With no
        policy engine wired, governed mode cannot authorize the capability, so
        it is denied with a proof — governed mode never implies authority.
        Deny-by-default (no matching rule → DENY) comes from the engine itself.
        Explicit host opt-out is handled by the compound gate above; a source
        header cannot disable an active governance requirement.

        The actual policy evaluation is delegated to a
        :class:`~utf.tarl.broker.CapabilityBroker` so in-language stdlib effects
        and out-of-language adapters share one mediation path (invariant #7,
        "no adapter side doors"). ``path`` (when given) is brokered through the
        path guard so the policy sees the confined canonical filesystem target.
        """
        from utf.tarl.broker import CapabilityDenied
        from utf.tarl.spec import TarlVerdict

        authorization_snapshot = self._authorization_snapshot()
        ctx = {"action": action, "target": str(target), **self._authority_context()}
        # Hardened-mode prerequisites (authenticated authority + Ed25519 proofs)
        # fail closed before any policy is consulted.
        hardened_violation = self._hardened_precheck(action, target)
        if hardened_violation is not None:
            raise hardened_violation
        # Fail-closed: governed but no policy engine/authority to grant it.
        if self.tarl_runtime is None or self.authority is None:
            proof = self._make_decision_proof(
                source="<fail-closed: governed mode without policy engine>",
                context=ctx,
                verdict=TarlVerdict.DENY,
                matched_condition="",
                trace=[
                    {
                        "kind": "fail-closed",
                        "action": action,
                        "target": str(target),
                        "reason": "no policy engine wired to authorize "
                        "capability in governed mode",
                    }
                ],
            )
            self._last_proof = proof
            raise GovernanceViolation(
                f"{action} {target}",
                "fail-closed: governed mode requires a policy engine to "
                "authorize this capability (run with --policy)",
                proof,
            )
        broker = self.make_broker()
        try:
            if path is not None and self.path_guard is not None:
                decision = broker.require_path(action, path)
            else:
                decision = broker.require(action, target)
        except CapabilityDenied as denied:
            proof = denied.decision.proof
            self._last_proof = proof
            raise GovernanceViolation(
                f"{action} {target}",
                denied.decision.reason or f"capability denied ({proof.verdict})",
                proof,
            ) from None
        except (GovernanceViolation, ExecutionError):
            raise
        except Exception as exc:
            # Resource exhaustion / evaluator failure must DENY, never fail open
            # (C037), and must surface as a governance denial that spillage
            # cannot swallow — not a raw exception.
            proof = self._make_decision_proof(
                source="<fail-closed: policy evaluation error>",
                context=ctx,
                verdict=TarlVerdict.DENY,
                matched_condition="",
                trace=[
                    {
                        "kind": "fail-closed",
                        "action": action,
                        "target": str(target),
                        "reason": f"policy evaluation error: {exc}",
                    }
                ],
            )
            self._last_proof = proof
            raise GovernanceViolation(
                f"{action} {target}",
                f"fail-closed: policy evaluation error: {exc}",
                proof,
            ) from exc
        self._last_proof = decision.proof
        changed = self._changed_authorization(authorization_snapshot, action, target)
        if changed is not None:
            raise changed

    def _wrap_imported_module_capabilities(
        self, module_path: str, module: object
    ) -> Any:
        """Wrap sensitive stdlib module functions with runtime capability gates.

        Capability actions come from the single-source-of-truth table
        ``SENSITIVE_STDLIB_CAPABILITIES`` in ``module_system`` so every sensitive
        callable carries an explicit ``read``/``write``/``network``/``execute``
        action; the gate routing here only consumes that metadata.
        """
        if module_path.endswith(".thirsty"):
            return module
        validate_stdlib_exports(module_path, module)
        if not isinstance(module, dict):
            raise ImportError("stdlib module must be a dictionary")

        policy = dict(SENSITIVE_STDLIB_CAPABILITIES.get(module_path, {}))

        wrapped = {
            name: self._bind_callable(function) for name, function in module.items()
        }
        for name, action in policy.items():
            fn = module[name]

            # Filesystem targets carry a real path in arg 0 — broker them through
            # the path guard so traversal/symlink escapes fail closed (C042).
            is_fs = module_path == "thirst::fs"

            def guarded(*args, __fn=fn, __name=name, __action=action, __is_fs=is_fs):
                target_detail = args[0] if args else ""
                target = f"{module_path}.{__name}"
                if target_detail != "":
                    target = f"{target}:{target_detail}"
                path = (
                    target_detail
                    if __is_fs
                    and isinstance(target_detail, str)
                    and target_detail != ""
                    else None
                )
                self._gate_capability(__action, target, path=path)
                return __fn(*args)

            wrapped[name] = self._bind_callable(guarded)
        return wrapped

    def _import_thirsty_file(self, path: str) -> dict:
        """Import a ``.thirsty`` source file under the caller's governance.

        Run source on a child interpreter sharing live caller restrictions and
        all active execution frames. Module headers select semantics while
        inherited governance, pure, and strict requirements remain in force, so

          * top-level gated effects (e.g. ``pour``) hit the capability gate
            during import, and
          * the returned function closures gate when invoked from governed code.

        Returns the imported module's new top-level bindings as a dict (the same
        shape stdlib modules use). File execution deliberately bypasses the
        global ``ModuleCache`` to avoid reusing closures under another binding.
        """
        from utf.thirsty_lang.lexer import Lexer
        from utf.thirsty_lang.parser import Parser

        source_path = Path(path)
        if not source_path.is_absolute():
            source_path = Path(self.source_directory) / source_path
        source_path = source_path.resolve()
        self._gate_capability("import", str(source_path), path=str(source_path))
        if source_path in self._import_stack:
            raise ImportError(f"Cyclic file import: {source_path}")
        if not source_path.is_file():
            raise ImportError(f"File not found: {path}")
        locks = self._active_import_locks()
        if locks:
            checked_sources = [
                self._invoke(locked.read_source, source_path) for locked in locks
            ]
            source = checked_sources[0]
            if any(candidate != source for candidate in checked_sources[1:]):
                raise ImportError("active import locks disagree about source bytes")
        else:
            source = self._invoke(source_path.read_text, encoding="utf-8")
        lexer = Lexer(source)
        tokens = lexer.lex()
        if lexer.errors:
            raise ImportError(f"Failed to import '{path}': {lexer.errors[0]}")
        parser = Parser(tokens)
        ast = parser.parse()
        if parser.errors:
            raise ImportError(f"Failed to import '{path}': {parser.errors[0]}")

        child = Interpreter(
            self.opt_level, self.debug_mode, allow_ungoverned=self._allow_ungoverned
        )
        child._execution_domain.close()
        child._execution_domain = self._execution_domain
        child._restrictions = self._restrictions
        child.source_directory = source_path.parent
        child._import_stack = (*self._import_stack, source_path)
        baseline = set(child.env.vars)  # builtins to exclude from the module
        # The active caller frame retains its restrictions while the child's
        # declared pure/strict semantics can strengthen them.
        child.interpret(ast, mode=self.mode)
        return {
            name: value
            for name, value in child.env.vars.items()
            if name not in baseline
        }

    def _execute_import(self, stmt: ImportStmt) -> object:
        try:
            module: object
            if stmt.module_path.endswith(".thirsty"):
                module = self._import_thirsty_file(stmt.module_path)
            else:
                self._gate_capability("import", stmt.module_path)
                for locked in self._active_import_locks():
                    self._invoke(locked.verify_stdlib, stmt.module_path)
                module = self._invoke(resolve_import, stmt.module_path)
            module = self._wrap_imported_module_capabilities(stmt.module_path, module)
            alias = stmt.alias or stmt.module_path
            self.env.define(alias, module, is_mut=False)
            return module
        except (GovernanceViolation, ExecutionError):
            # A denied effect during imported-module execution is a governance
            # decision, not an import error — it must propagate, never be
            # swallowed into a SpillageException that handlers could catch.
            raise
        except Exception as e:
            raise ImportError(f"Failed to import '{stmt.module_path}': {e}") from e

    @staticmethod
    def _require_call_arity(name: str, expected: int, got: int) -> None:
        if expected != got:
            raise TypeError(f"'{name}' expects {expected} arguments, got {got}")

    @staticmethod
    def _require_parameter_bindings(name, params, *, bound_receiver=False):
        """Reject ambiguous bindings before a callable changes its environment."""
        seen = set()
        for parameter, _ in params:
            if parameter in seen:
                raise TypeError(f"duplicate parameter '{parameter}' in '{name}'")
            seen.add(parameter)
        remaining = params
        if bound_receiver and params and params[0][0] in ("self", "this"):
            remaining = params[1:]
        if bound_receiver and any(parameter == "this" for parameter, _ in remaining):
            raise TypeError(
                f"parameter 'this' conflicts with bound receiver in '{name}'"
            )

    def _make_closure(self, params, body, name="<lambda>"):
        # Capture the defining environment so the function closes over its
        # lexical scope (enclosing locals), rather than over whatever scope
        # happens to be active at call time.
        def_env = self.env

        def fn(*args):
            self._require_parameter_bindings(name, params)
            self._require_call_arity(name, len(params), len(args))
            old_env = self.env
            self.env = def_env.enter_scope()
            for (pname, _), val in zip(params, args, strict=True):
                self.env.define(pname, val, is_mut=False)
            result = None
            try:
                result = self._execute(body)
            except ReturnException as e:
                result = e.value
            finally:
                self.env = old_env
            return result

        return self._bind_callable(fn)

    def _execute_function_decl(self, stmt: FunctionDecl) -> object:
        fn = self._make_closure(stmt.params, stmt.body, stmt.name)
        self.env.define(stmt.name, fn, is_mut=False)
        return fn

    def _execute_class_decl(self, stmt: ClassDecl) -> object:
        declaration_env = self.env
        initializers = [method for method in stmt.methods if method.name == "init"]
        native_identity = self._restrictions.native_values.register(
            stmt, "fountain", stmt.name, tuple(field[0] for field in stmt.fields)
        )

        def constructor(*args):
            if not initializers:
                self._require_call_arity(stmt.name, 0, len(args))
            for method in initializers:
                self._require_parameter_bindings(
                    method.name, method.params, bound_receiver=True
                )
                expected = len(method.params)
                if method.params and method.params[0][0] in ("self", "this"):
                    expected -= 1
                self._require_call_arity(stmt.name, expected, len(args))
            instance = FountainInstance(stmt, declaration_env)
            instance.native_identity = native_identity
            instance.execution_frames = _merge_execution_frames(
                (*_EXECUTION_FRAMES.get(), self._execution_frame())
            )
            instance.interpreter = self
            old_env = self.env
            self.env = declaration_env.enter_scope()
            self.env.define("this", instance, is_mut=False)
            try:
                # Apply field default initializers before running init.
                for field_spec in stmt.fields:
                    default_expr = field_spec[2] if len(field_spec) > 2 else None
                    if default_expr is not None:
                        instance.fields[field_spec[0]] = self._evaluate(default_expr)
                for method in initializers:
                    self._call_user_fn(method, list(args), this_obj=instance)
            finally:
                self.env = old_env
            return instance

        bound = self._bind_callable(constructor)
        self.env.define(stmt.name, bound, is_mut=False)
        return bound

    def _execute_struct_decl(self, stmt: StructDecl) -> object:
        declaration_env = self.env
        names = [name for name, _ in stmt.fields]
        if len(names) != len(set(names)):
            raise TypeError(f"duplicate field in struct '{stmt.name}'")
        native_identity = self._restrictions.native_values.register(
            stmt, "struct", stmt.name, tuple(names)
        )

        def constructor(*args):
            if len(args) != len(stmt.fields):
                raise TypeError(
                    f"'{stmt.name}' expects {len(stmt.fields)} fields, got {len(args)}"
                )
            instance = StructInstance(stmt, {}, declaration_env)
            instance.native_identity = native_identity
            for (name, _), value in zip(stmt.fields, args, strict=True):
                self._set_struct_field(instance, name, value)
            return instance

        constructor._thirsty_struct_declaration = stmt  # type: ignore[attr-defined]
        bound = self._bind_callable(constructor)
        self.env.define(stmt.name, bound, is_mut=False)
        return bound

    def _set_struct_field(self, instance: StructInstance, name: str, value: Any):
        declared = dict(instance.declaration.fields)
        if name not in declared:
            raise NameError(f"'{instance.declaration.name}' has no field '{name}'")
        annotation = declared[name]
        if annotation and not self._matches_field_type(
            value, annotation, instance.type_environment
        ):
            raise TypeError(f"field '{name}' requires {annotation}")
        instance.fields[name] = value

    def _matches_field_type(
        self, value: Any, annotation: str, environment: Environment
    ) -> bool:
        """Validate supported record annotations in the declaration's lexical scope."""
        if "[" in annotation and annotation.endswith("]"):
            base, remainder = annotation.split("[", 1)
            arguments = []
            depth = 0
            start = 0
            for offset, char in enumerate(remainder[:-1]):
                if char == "[":
                    depth += 1
                elif char == "]":
                    depth -= 1
                elif char == "," and depth == 0:
                    arguments.append(remainder[start:offset].strip())
                    start = offset + 1
            arguments.append(remainder[start:-1].strip())
            if base.lower() == "reservoir" and len(arguments) == 1:
                return isinstance(value, list) and all(
                    self._matches_field_type(item, arguments[0], environment)
                    for item in value
                )
            if base.lower() == "dict" and len(arguments) == 2:
                return isinstance(value, dict) and all(
                    self._matches_field_type(key, arguments[0], environment)
                    and self._matches_field_type(item, arguments[1], environment)
                    for key, item in value.items()
                )
            return False
        # Resolve nominal declarations in the same lexical order as the
        # checker, including an explicitly shadowed primitive type name.
        binding = environment.get(annotation) if environment.has(annotation) else None
        declaration = getattr(binding, "_thirsty_struct_declaration", None)
        if isinstance(declaration, StructDecl):
            return (
                isinstance(value, StructInstance) and value.declaration is declaration
            )
        if isinstance(binding, type) and issubclass(binding, Enum):
            return isinstance(value, binding)
        primitive_types = {
            "int": lambda v: type(v) is int,
            "float": lambda v: type(v) in (int, float),
            "bool": lambda v: type(v) is bool,
            "string": lambda v: isinstance(v, str),
            "any": lambda v: True,
        }
        primitive = primitive_types.get(annotation.lower())
        if primitive is not None:
            return primitive(value)
        return False

    def _execute_spillage(self, stmt: SpillageStmt) -> object:
        try:
            return self._execute(stmt.body)
        except (ReturnException, GovernanceViolation, ExecutionError):
            # Control flow (return) and governance denials are not errors —
            # they must propagate, never be caught by spillage handlers.
            raise
        except SpillageException as exc:
            for error_var, handler in stmt.handlers:
                return self._run_spillage_handler(error_var, exc.value, handler)
            raise
        except Exception as exc:
            for error_var, handler in stmt.handlers:
                return self._run_spillage_handler(error_var, exc, handler)
            raise

    def _run_spillage_handler(self, error_var, err_value, handler) -> object:
        """Run a spillage error handler, binding the thrown value to the
        handler's optional name (``error (name) { ... }``)."""
        if error_var is None:
            return self._execute(handler)
        old_env = self.env
        self.env = self.env.enter_scope()
        self.env.define(error_var, err_value, is_mut=False)
        try:
            return self._execute(handler)
        finally:
            self.env = old_env

    def _execute_cleanup(self, stmt: CleanupStmt) -> object:
        try:
            return self._execute(stmt.body)
        finally:
            self._execute(stmt.finalizer)

    def _execute_throw(self, stmt: ThrowStmt) -> object:
        value = self._evaluate(stmt.value)
        raise SpillageException(value)

    def _execute_security_block(self, stmt: SecurityBlock) -> object:
        raise NotImplementedError(
            f"security block '{stmt.block_type}' has no enforcement implementation"
        )

    def _execute_cascade(self, stmt: CascadeCall) -> object:
        """cascade <call> — async call with await: runs on the pool and
        resolves to the call's value (not a Future)."""
        if isinstance(stmt.expr, CallExpr):
            callee = self._evaluate(stmt.expr.callee)
            args = [self._evaluate(a) for a in stmt.expr.args]
            if callable(callee):
                return self._execution_domain.cascade(callee, *args)
            # Callee and arguments have already been evaluated in source order.
            # Falling through would evaluate them a second time before failing.
            raise TypeError(f"Cannot call non-callable: {callee}")
        return self._evaluate(stmt.expr)

    def _execute_morph(self, stmt: MorphDef) -> object:
        declaration_env = self.env

        def transform(*args):
            self._require_parameter_bindings(stmt.name, stmt.params)
            self._require_call_arity(stmt.name, len(stmt.params), len(args))
            old_env = self.env
            self.env = declaration_env.enter_scope()
            for (pname, _), val in zip(stmt.params, args, strict=True):
                self.env.define(pname, val, is_mut=False)
            result = None
            try:
                result = self._execute(stmt.body)
            except ReturnException as e:
                result = e.value
            finally:
                self.env = old_env
            return result

        bound = self._bind_callable(transform)
        self.env.define(stmt.name, bound, is_mut=False)
        return bound

    def _execute_shadow_thirst(self, stmt: ShadowThirstMutation) -> object:
        if stmt.canonical_block:
            return self._execute(stmt.canonical_block)
        return None

    def attach_tarl(self, runtime) -> "Interpreter":
        """Wire a TARL policy engine for governed-function routing.

        ``runtime`` is a ``utf.tarl.runtime.TarlRuntime``.  Passing it here
        (rather than importing at module load) keeps thirsty_lang decoupled
        from tarl unless governance is actually used.  Returns self.
        """
        self.tarl_runtime = runtime
        return self

    def set_authority(self, authority) -> "Interpreter":
        """Set a *self-asserted* authority (a bare string subject).

        This carries no authenticity: ``authority_authenticated`` stays False and
        no grants are bound. In hardened mode such an authority cannot pass a
        gated capability. Use :meth:`set_verified_authority` for a signed
        credential. Passing a ``VerifiedAuthority`` here is also accepted.
        """
        from utf.tarl.authority import VerifiedAuthority

        if isinstance(authority, VerifiedAuthority):
            return self.set_verified_authority(authority)
        with self._restrictions.lock:
            self.authority = authority
            self.authority_authenticated = False
            self.authority_grants = ()
            self._verified_authority = None
        return self

    def set_verified_authority(self, verified) -> "Interpreter":
        """Bind an authenticated authority resolved from a signed claim.

        ``verified`` is a ``utf.tarl.authority.VerifiedAuthority``. Its subject,
        grants, and authenticity flag are injected into every governance context.
        """
        with self._restrictions.lock:
            self.authority = verified.subject
            self.authority_authenticated = bool(verified.authenticated)
            self.authority_grants = tuple(verified.grants)
            self._verified_authority = verified
        return self

    def set_hardened(self, hardened: bool = True) -> "Interpreter":
        """Enable the hardened posture (authenticated authority + Ed25519 proofs
        required at every governed gate, else fail closed)."""
        self.hardened = hardened
        return self

    def set_path_guard(self, roots) -> "Interpreter":
        """Confine governed ``thirst::fs`` targets to ``roots`` (C042).

        ``roots`` is an iterable of allowed directory roots, or a ready
        ``utf.tarl.pathguard.PathGuard``. Once set, file capabilities are
        brokered on the *canonical* path, so traversal/symlink escapes fail
        closed before the policy is consulted. With no guard set, file targets
        are brokered as-is (unchanged behaviour)."""
        from utf.tarl.pathguard import PathGuard

        if roots is None or isinstance(roots, PathGuard):
            self.path_guard = roots
        else:
            self.path_guard = PathGuard(list(roots))
        return self

    def make_broker(self):
        """Build a :class:`~utf.tarl.broker.CapabilityBroker` bound to this
        interpreter's runtime, authority, hardened posture, and path guard.

        This is the *single* mediation point: the in-language capability gate
        (:meth:`_gate_capability`) and any out-of-language adapters (FFI, MCP/
        agent tools, subprocess wrappers) all broker through an identically
        configured broker, so there is one enforcement path, not two."""
        from utf.tarl.broker import CapabilityBroker

        authority = (
            self._verified_authority
            if self._verified_authority is not None
            else (self.authority or "")
        )
        return CapabilityBroker(
            self.tarl_runtime,
            authority=authority,
            require_authenticated=self.hardened,
            path_guard=self.path_guard,
        )

    def _authority_context(self) -> dict:
        """Authority fields merged into every governance evaluation context."""
        return {
            "authority": self.authority or "",
            "authority_subject": self.authority or "",
            "authority_authenticated": self.authority_authenticated,
            "authority_grants": list(self.authority_grants),
        }

    def _hardened_precheck(self, action: str, target: str):
        """Hardened-mode gate prerequisites, evaluated before policy routing.

        Returns a fail-closed ``GovernanceViolation`` to raise, or None when the
        prerequisites hold. Enforces: an authenticated authority, and a runtime
        configured to emit Ed25519-signed proofs (non-repudiable audit).
        """
        from utf.tarl.spec import TarlVerdict

        reason = None
        if self.authority_authenticated and self._verified_authority is not None:
            try:
                now = (
                    self.tarl_runtime._now() if self.tarl_runtime is not None else None
                )
                reason = self._verified_authority.authorization_error(now)
            except Exception as exc:
                reason = f"authority validity check failed: {exc}"
        if reason is None and self.hardened and not self.authority_authenticated:
            reason = (
                "hardened mode requires an authenticated (signed) "
                "authority; a self-asserted authority is not sufficient"
            )
        elif (
            reason is None
            and self.hardened
            and getattr(self.tarl_runtime, "_signing_alg", "") != "ed25519"
        ):
            reason = (
                "hardened mode requires Ed25519-signed proofs; configure "
                "an Ed25519 signing key on the runtime"
            )
        if reason is None:
            return None
        proof = self._make_decision_proof(
            source="<fail-closed: hardened-mode prerequisite>",
            context={
                **self._authority_context(),
                "action": action,
                "target": str(target),
            },
            verdict=TarlVerdict.DENY,
            matched_condition="",
            trace=[
                {
                    "kind": "fail-closed",
                    "action": action,
                    "target": str(target),
                    "reason": reason,
                }
            ],
        )
        self._last_proof = proof
        return GovernanceViolation(f"{action} {target}", reason, proof)

    def _execute_governed_function_decl(self, stmt: GovernedFunctionDecl):
        """Define a top-level governed function with full contract enforcement."""
        declaration_env = self.env

        def fn(*args):
            self._require_parameter_bindings(stmt.name, stmt.params)
            self._require_call_arity(stmt.name, len(stmt.params), len(args))
            old_env = self.env
            self.env = declaration_env.enter_scope()
            context = {}
            for (pname, _), val in zip(stmt.params, args, strict=True):
                self.env.define(pname, val, is_mut=False)
                context[pname] = val
            try:
                return self._run_governed(stmt, context, top_level=True)
            finally:
                self.env = old_env

        bound = self._bind_callable(fn)
        self.env.define(stmt.name, bound, is_mut=False)
        return bound

    def _run_governed(self, decl: GovernedFunctionDecl, context: dict, top_level: bool):
        """Enforce entry contracts, run the body, then enforce exit contracts.

        Params are assumed already bound in the current scope. ``top_level``
        gates the cross-mode guard (E053): it applies to module-level governed
        functions, not to method contracts (which are design-by-contract
        assertions valid in any mode).
        """
        allowed, reason, proof = self._enforce_governance(
            context, decl, phase="entry", enforce_mode_guard=top_level
        )
        if proof is not None:
            self._last_proof = proof
        if not allowed:
            raise GovernanceViolation(decl.name, reason, proof)
        self._execution_domain.checkpoint()

        result = None
        try:
            result = self._execute(decl.body)
        except ReturnException as e:
            result = e.value

        # Exit contracts: bind `result` so ensures/invariant can reference it.
        self.env.define("result", result, is_mut=False)
        exit_ctx = dict(context)
        exit_ctx["result"] = result
        allowed, reason, proof = self._enforce_governance(
            exit_ctx, decl, phase="exit", enforce_mode_guard=top_level
        )
        if proof is not None:
            self._last_proof = proof
        if not allowed:
            raise GovernanceViolation(decl.name, reason, proof)
        self._execution_domain.checkpoint()
        return result

    def _eval_predicate(self, expr, annotation, label):
        """Evaluate a governance predicate; return (ok, reason)."""
        try:
            if self._evaluate(expr):
                return (True, "")
            return (False, f"{label} failed: {annotation or '<expr>'}")
        except ExecutionError:
            raise
        except Exception as exc:
            return (False, f"{label} error: {exc}")

    def _contract_predicates(self, decl, phase):
        """Yield (expr, annotation, label) for the contract predicates that
        apply at this boundary: requires + invariant on entry, ensures +
        invariant on exit. Empty when ``decl`` carries no contract.
        """
        if decl is None:
            return
        if phase == "entry":
            if getattr(decl, "requires_expr", None) is not None:
                yield (decl.requires_expr, decl.requires_annotation, "precondition")
            if getattr(decl, "invariant_expr", None) is not None:
                yield (
                    decl.invariant_expr,
                    decl.invariant_annotation,
                    "invariant (entry)",
                )
        else:
            if getattr(decl, "ensures_expr", None) is not None:
                yield (decl.ensures_expr, decl.ensures_annotation, "postcondition")
            if getattr(decl, "invariant_expr", None) is not None:
                yield (
                    decl.invariant_expr,
                    decl.invariant_annotation,
                    "invariant (exit)",
                )

    def _make_contract_proof(
        self, decl, phase, context, verdict, matched_condition, trace
    ):
        """Proof certificate for a design-by-contract verdict (Fix: every
        governed boundary decision carries a proof, not just policy ones)."""
        from utf.tarl.spec import TarlVerdict
        from utf.thirsty_lang.governed_values import (
            GovernedValueError,
            project_governed_context,
        )

        name = getattr(decl, "name", "<anon>") if decl is not None else "<anon>"
        source = f"contract:{name}:{phase}"
        try:
            proof_context = project_governed_context(context)
        except GovernedValueError as exc:
            # This certificate binds a bounded rejection diagnostic, not a
            # representation of an unsupported host object or its repr hooks.
            verdict = TarlVerdict.DENY
            proof_context = {
                "action": name,
                "phase": phase,
                "context_projection_error": str(exc),
            }
            trace = [*trace, {"kind": "projection-rejected", "reason": str(exc)}]
        return self._make_decision_proof(
            source=source,
            context=proof_context,
            verdict=verdict,
            matched_condition=matched_condition,
            trace=trace,
        )

    def _governed_context_denial(
        self,
        context,
        decl,
        phase,
        reason,
        *,
        expected_hash=None,
        observed_hash=None,
        prior_proof=None,
    ):
        """Bind a failed value snapshot check to a separate DENY certificate."""
        from utf.tarl.spec import TarlVerdict

        trace = {
            "kind": "governed-context-integrity",
            "phase": phase,
            "matched": False,
            "reason": reason,
            "expected_context_hash": expected_hash,
            "observed_context_hash": observed_hash,
        }
        if prior_proof is not None:
            trace["prior_policy_hash"] = prior_proof.policy_hash
            trace["prior_context_hash"] = prior_proof.context_hash
        proof = self._make_contract_proof(
            decl, phase, context, TarlVerdict.DENY, reason, [trace]
        )
        self._last_proof = proof
        return False, reason, proof

    def _check_governed_context(
        self, context, decl, phase, expected_hash, prior_proof=None
    ):
        """Recheck exact admitted JSON data after callback-capable checks."""
        from utf.tarl.context import ContextResolutionError, prepare_context
        from utf.thirsty_lang.governed_values import (
            GovernedValueError,
            project_governed_context,
        )

        try:
            observed_hash = prepare_context(
                project_governed_context(context)
            ).original_context_hash
        except (ContextResolutionError, GovernedValueError) as exc:
            return self._governed_context_denial(
                context,
                decl,
                phase,
                str(exc),
                expected_hash=expected_hash,
                prior_proof=prior_proof,
            )
        if observed_hash != expected_hash:
            return self._governed_context_denial(
                context,
                decl,
                phase,
                f"governed {phase} context changed during authorization",
                expected_hash=expected_hash,
                observed_hash=observed_hash,
                prior_proof=prior_proof,
            )
        return None

    def _enforce_governance(
        self, context: dict, decl=None, phase="entry", enforce_mode_guard=True
    ):
        """Check local contracts and every active caller's function policy."""
        frames = _merge_execution_frames(
            (self._execution_frame(), *_EXECUTION_FRAMES.get())
        )
        owners = [self]
        seen_bindings = {self._policy_binding_key()}
        for frame in frames:
            owner = frame.owner
            if not (frame.governed or owner._governance_is_required()):
                continue
            key = owner._policy_binding_key()
            if key not in seen_bindings:
                seen_bindings.add(key)
                owners.append(owner)
        snapshots = [
            (frame.owner, frame.owner._authorization_snapshot()) for frame in frames
        ]
        name = decl.name if decl is not None else "<call>"
        try:
            from utf.tarl.context import ContextResolutionError, prepare_context
            from utf.thirsty_lang.governed_values import (
                GovernedValueError,
                project_governed_context,
            )

            if phase == "entry" and decl is not None and "result" in context:
                return self._governed_context_denial(
                    context,
                    decl,
                    phase,
                    "reserved governed parameter name 'result' conflicts with the exit result binding",
                )
            try:
                context_hash = prepare_context(
                    project_governed_context(context)
                ).original_context_hash
            except (ContextResolutionError, GovernedValueError) as exc:
                return self._governed_context_denial(context, decl, phase, str(exc))
            allowed, reason, proof = self._enforce_governance_local(
                context,
                decl,
                phase,
                enforce_mode_guard,
                expected_context_hash=context_hash,
            )
            if not allowed:
                return allowed, reason, proof
            context_denial = self._check_governed_context(
                context, decl, phase, context_hash, proof
            )
            if context_denial is not None:
                return context_denial
            if phase != "entry":
                return allowed, reason, proof
            for owner in owners[1:]:
                allowed, reason, caller_proof = owner._enforce_governance_local(
                    context,
                    decl,
                    "entry",
                    False,
                    check_contracts=False,
                    expected_context_hash=context_hash,
                )
                owner._last_proof = caller_proof
                if caller_proof is not None:
                    proof = caller_proof
                if not allowed:
                    return False, reason, proof
                context_denial = self._check_governed_context(
                    context, decl, phase, context_hash, proof
                )
                if context_denial is not None:
                    return context_denial
            for owner, snapshot in snapshots:
                violation = owner._changed_authorization(snapshot, name, name)
                violation = violation or owner._hardened_precheck(name, name)
                if violation is not None:
                    return False, violation.reason, violation.proof
            for owner, snapshot in snapshots:
                violation = owner._changed_authorization(snapshot, name, name)
                if violation is not None:
                    return False, violation.reason, violation.proof
            context_denial = self._check_governed_context(
                context, decl, phase, context_hash, proof
            )
            if context_denial is not None:
                return context_denial
            return True, reason, proof
        except GovernanceViolation as denied:
            return False, denied.reason, denied.proof
        except ExecutionError:
            raise
        except Exception as error:
            from utf.tarl.spec import TarlVerdict

            reason = f"governance evaluation failed: {error}"
            proof = self._make_decision_proof(
                source="<fail-closed: governed call evaluation error>",
                context={"action": name},
                verdict=TarlVerdict.DENY,
                matched_condition="",
                trace=[{"kind": "fail-closed", "reason": reason}],
            )
            return False, reason, proof

    def _enforce_governance_local(
        self,
        context: dict,
        decl=None,
        phase="entry",
        enforce_mode_guard=True,
        *,
        check_contracts=True,
        expected_context_hash: str,
    ):
        """Decide whether a governed call boundary is allowed.

        Returns ``(allowed, reason, proof)``. Design-by-contract predicates
        (requires/invariant at entry; ensures/invariant at exit) hold unless a
        declared predicate fails. The TARL layer adds deny-by-default access
        control when a policy engine + authority are configured. Every decision
        on a contract-bearing boundary carries a proof — ALLOW and DENY alike.
        """
        from utf.tarl.spec import TarlVerdict

        authorization_snapshot = self._authorization_snapshot()
        authorization_runtime = self.tarl_runtime
        proof = None
        if phase == "entry":
            # Cross-mode guard (E053): top-level governed fn from core is denied.
            if (
                decl is not None
                and enforce_mode_guard
                and not self._governance_is_required()
            ):
                return (False, "governed function invoked outside governed mode", None)

        # Design-by-contract predicates for this phase.
        trace = []
        predicates = self._contract_predicates(decl, phase) if check_contracts else ()
        for expr, ann, label in predicates:
            ok, reason = self._eval_predicate(expr, ann, label)
            trace.append(
                {
                    "predicate": label,
                    "annotation": ann or "<expr>",
                    "phase": phase,
                    "result": "pass" if ok else "fail",
                }
            )
            if not ok:
                deny = self._make_contract_proof(
                    decl, phase, context, TarlVerdict.DENY, ann or "", trace
                )
                self._last_proof = deny
                return (False, reason, deny)
            context_denial = self._check_governed_context(
                context, decl, phase, expected_context_hash, proof
            )
            if context_denial is not None:
                return context_denial
        if trace:  # contract was checked and held → certify it
            proof = self._make_contract_proof(
                decl, phase, context, TarlVerdict.ALLOW, "", trace
            )

        if phase == "entry":
            # TARL policy routing (deny-by-default access control). A policy
            # proof supersedes the contract proof as the boundary certificate.
            if (
                self._governance_is_required()
                and decl is not None
                and (self.tarl_runtime is None or self.authority is None)
            ):
                reason = "governed function requires a policy engine and authority"
                deny = self._make_contract_proof(
                    decl,
                    phase,
                    context,
                    TarlVerdict.DENY,
                    reason,
                    trace + [{"kind": "fail-closed", "phase": phase, "reason": reason}],
                )
                self._last_proof = deny
                return (False, reason, deny)
            if self.tarl_runtime is not None and self.authority is not None:
                from utf.tarl.context import (
                    ContextResolutionError,
                    compose_context_layers,
                    prepare_context,
                )
                from utf.thirsty_lang.governed_values import (
                    GovernedValueError,
                    project_governed_context,
                )

                # Hardened-mode prerequisites fail closed before policy routing.
                action_name = decl.name if decl is not None else "<call>"
                hardened_violation = self._hardened_precheck(action_name, action_name)
                if hardened_violation is not None:
                    return (False, hardened_violation.reason, hardened_violation.proof)
                context_denial = self._check_governed_context(
                    context, decl, phase, expected_context_hash, proof
                )
                if context_denial is not None:
                    return context_denial
                action_context = {"action": decl.name if decl is not None else "<call>"}
                try:
                    policy_ctx = compose_context_layers(
                        ("function arguments", project_governed_context(context)),
                        ("verified authority", self._authority_context()),
                        ("governed action", action_context),
                    )
                except (ContextResolutionError, GovernedValueError) as exc:
                    deny_trace = trace + [
                        {
                            "kind": "context-layer-conflict",
                            "phase": phase,
                            "matched": False,
                            "reason": str(exc),
                        }
                    ]
                    deny = self._make_contract_proof(
                        decl,
                        phase,
                        context,
                        TarlVerdict.DENY,
                        str(exc),
                        deny_trace,
                    )
                    self._last_proof = deny
                    return (False, str(exc), deny)
                ensure_schema = getattr(
                    self.tarl_runtime, "ensure_context_schema", None
                )
                if callable(ensure_schema):
                    ensure_schema()
                context_denial = self._check_governed_context(
                    context, decl, phase, expected_context_hash, proof
                )
                if context_denial is not None:
                    return context_denial
                policy_context_hash = prepare_context(policy_ctx).original_context_hash
                decision, proof = self.tarl_runtime.evaluate_with_proof(policy_ctx)
                context_denial = self._check_governed_context(
                    context, decl, phase, expected_context_hash, proof
                )
                if context_denial is not None:
                    return context_denial
                if decision.verdict == TarlVerdict.ALLOW:
                    from utf.tarl.verifier import (
                        positive_context_authority_admissible,
                    )

                    if not positive_context_authority_admissible(proof):
                        reason = (
                            "positive verdict inadmissible: exact context "
                            "schema validation was not proof-bound"
                        )
                        deny_trace = trace + [
                            {
                                "kind": "inadmissible-positive-verdict",
                                "phase": phase,
                                "matched": False,
                                "reason": reason,
                            }
                        ]
                        deny = self._make_contract_proof(
                            decl,
                            phase,
                            context,
                            TarlVerdict.DENY,
                            reason,
                            deny_trace,
                        )
                        self._last_proof = deny
                        return (False, reason, deny)
                    if proof.original_context_hash != policy_context_hash:
                        return self._governed_context_denial(
                            context,
                            decl,
                            phase,
                            "policy proof context does not bind submitted function arguments",
                            expected_hash=policy_context_hash,
                            observed_hash=proof.original_context_hash,
                            prior_proof=proof,
                        )
                if decision.verdict != TarlVerdict.ALLOW:
                    return (
                        False,
                        decision.reason or f"policy verdict: {decision.verdict}",
                        proof,
                    )
                # Providers and durable audit writes can take time or revoke a
                # credential. Revalidate once more at the handoff to execution.
                final_violation = self._changed_authorization(
                    authorization_snapshot, action_name, action_name
                )
                if final_violation is None:
                    final_violation = self._hardened_precheck(action_name, action_name)
                if final_violation is None:
                    final_violation = self._changed_authorization(
                        authorization_snapshot, action_name, action_name
                    )
                if final_violation is not None:
                    archive = getattr(authorization_runtime, "_archive", None)
                    if archive is not None and final_violation.proof is not None:
                        try:
                            archive.store(final_violation.proof)
                        except Exception:
                            # A failed denial record never turns into permission.
                            pass
                    return (False, final_violation.reason, final_violation.proof)
        changed = self._changed_authorization(
            authorization_snapshot, getattr(decl, "name", "<call>"), "<function>"
        )
        if changed is not None:
            return (False, changed.reason, changed.proof)
        return (True, "allowed", proof)

    def _call_user_fn(
        self, func_decl: FunctionDecl, args: list, this_obj: object = None
    ) -> object:
        params = list(func_decl.params)
        self._require_parameter_bindings(
            func_decl.name, params, bound_receiver=this_obj is not None
        )
        receiver_name = None
        if this_obj is not None and params and params[0][0] in ("self", "this"):
            receiver_name = params.pop(0)[0]
        self._require_call_arity(func_decl.name, len(params), len(args))
        old_env = self.env
        declaration_env = (
            this_obj.declaration_env
            if isinstance(this_obj, FountainInstance)
            else self.env
        )
        self.env = declaration_env.enter_scope()
        # Bind the receiver for fountain methods. Two conventions are supported:
        #   * the `this` keyword (no receiver parameter declared), and
        #   * an explicit leading `self`/`this` parameter.
        # `this` is always bound so `this.field` resolves; if the method also
        # declares a leading self parameter, it receives the instance and is
        # not consumed from the caller's positional arguments.
        context = {}
        if this_obj is not None:
            self.env.define("this", this_obj, is_mut=False)
            context[receiver_name or "this"] = this_obj
            if receiver_name is not None:
                self.env.define(receiver_name, this_obj, is_mut=False)
        for (pname, _), val in zip(params, args, strict=True):
            self.env.define(pname, val, is_mut=False)
            context[pname] = val
        try:
            if isinstance(func_decl, GovernedFunctionDecl):
                # Method contracts: DBC enforcement, no cross-mode guard.
                return self._run_governed(func_decl, context, top_level=False)
            result = None
            try:
                result = self._execute(func_decl.body)
            except ReturnException as e:
                result = e.value
            return result
        finally:
            self.env = old_env

    def _evaluate_impl(self, expr: Expr) -> Any:
        """Evaluate an expression and return its value."""
        self._execution_domain.checkpoint(step=True)
        try:
            return self._evaluate_node(expr)
        finally:
            self._execution_domain.checkpoint()

    def _evaluate_node(self, expr: Expr) -> Any:
        if isinstance(expr, IntLiteral):
            return expr.value
        elif isinstance(expr, FloatLiteral):
            return expr.value
        elif isinstance(expr, StringLiteral):
            return expr.value
        elif isinstance(expr, BoolLiteral):
            return expr.value
        elif isinstance(expr, NoneLiteral):
            return None
        elif isinstance(expr, ErrorLiteral):
            return Exception(expr.value)
        elif isinstance(expr, QuenchedLiteral):
            return {
                "type": expr.type_param,
                "value": self._evaluate(expr.value) if expr.value else None,
            }
        elif isinstance(expr, AssignStmt):
            raise RuntimeError("assignment cannot be used as an expression")
        elif isinstance(expr, Identifier):
            if expr.name == "__error__":
                raise RuntimeError("cannot execute a parser recovery placeholder")
            value = self.env.get(expr.name)
            if (
                id(value) in self._builtin_callables
                and self._builtin_callables[id(value)] is value
            ):
                return self._bind_callable(value)
            if getattr(value, "__self__", None) is self and getattr(
                value, "__func__", None
            ) in (Interpreter._builtin_print, Interpreter._builtin_pour):
                return self._bind_callable(value)
            return value
        elif isinstance(expr, BinaryOp):
            return self._evaluate_binary(expr)
        elif isinstance(expr, UnaryOp):
            return self._evaluate_unary(expr)
        elif isinstance(expr, LambdaExpr):
            return self._make_closure(expr.params, expr.body)
        elif isinstance(expr, CallExpr):
            return self._evaluate_call(expr)
        elif isinstance(expr, PipeExpr):
            return self._evaluate_pipe(expr)
        elif isinstance(expr, GuardExpr):
            return self._evaluate_guard(expr)
        elif isinstance(expr, FloodExpr):
            return self._evaluate_flood(expr)
        elif isinstance(expr, DripExpr):
            return self._evaluate_drip(expr)
        elif isinstance(expr, EvaporateExpr):
            return self._evaluate_evaporate(expr)
        elif isinstance(expr, CondenseExpr):
            return self._evaluate_condense(expr)
        elif isinstance(expr, ArrayLiteral):
            return [self._evaluate_impl(e) for e in expr.elements]
        elif isinstance(expr, DictLiteral):
            result = {}
            for key_expr, value_expr in expr.items:
                key = self._evaluate(key_expr)
                if key in result:
                    raise ValueError(f"duplicate dictionary key: {key!r}")
                result[key] = self._evaluate(value_expr)
            return result
        elif isinstance(expr, MemberAccess):
            return self._evaluate_member(expr)
        elif isinstance(expr, SanitizeExpr):
            raise NotImplementedError(
                "sanitize requires an explicit validator or encoding"
            )
        elif isinstance(expr, ArmorExpr):
            raise NotImplementedError("armor has no protection implementation")
        elif isinstance(expr, NewExpr):
            return self._evaluate_new(expr)
        elif isinstance(expr, CascadeCall):
            return self._execute_cascade(expr)
        elif isinstance(expr, SymbolExpr):
            return expr.symbol_name
        elif isinstance(expr, PipelineExpr):
            return self._evaluate_pipeline(expr)
        elif isinstance(expr, CombineExpr):
            return self._evaluate_combine(expr)
        elif isinstance(expr, Subscript):
            return self._evaluate_subscript(expr)
        elif isinstance(expr, SliceExpr):
            return self._evaluate_slice(expr)
        raise NotImplementedError(f"unsupported expression: {type(expr).__name__}")

    def _evaluate_subscript(self, expr: Subscript) -> object:
        """obj[index] — index a reservoir (list), dict, or string."""
        obj = self._evaluate_impl(expr.obj)
        index = self._evaluate_impl(expr.index)
        return get_index(obj, index)

    def _evaluate_slice(self, expr: SliceExpr) -> object:
        """Evaluate receiver and provided bounds once, then validate and slice."""
        obj = self._evaluate_impl(expr.obj)
        start = self._evaluate_impl(expr.start) if expr.start is not None else None
        stop = self._evaluate_impl(expr.stop) if expr.stop is not None else None
        step = self._evaluate_impl(expr.step) if expr.step is not None else None
        return get_slice(obj, start, stop, step)

    def _evaluate_binary(self, expr: BinaryOp) -> object:
        left = self._evaluate_impl(expr.left)
        op = expr.op
        if op == TokenType.AND:
            return left and self._evaluate_impl(expr.right)
        if op == TokenType.OR:
            return left or self._evaluate_impl(expr.right)
        right = self._evaluate_impl(expr.right)
        if type(left) is bool or type(right) is bool:
            if op not in (TokenType.EQEQ, TokenType.NE) or type(left) is not type(
                right
            ):
                raise TypeError(
                    "Bool operands support only Boolean equality and logical operators"
                )
        if op == TokenType.EQEQ:
            return left == right
        elif op == TokenType.NE:
            return left != right
        elif op == TokenType.LT:
            return left < right
        elif op == TokenType.LE:
            return left <= right
        elif op == TokenType.GT:
            return left > right
        elif op == TokenType.GE:
            return left >= right
        elif op == TokenType.PLUS:
            return left + right
        elif op == TokenType.MINUS:
            return left - right
        elif op == TokenType.STAR:
            return left * right
        elif op == TokenType.SLASH:
            return left / right
        elif op == TokenType.PERCENT:
            return left % right
        raise NotImplementedError(f"unsupported binary operator: {op}")

    def _evaluate_unary(self, expr: UnaryOp) -> object:
        operand = self._evaluate_impl(expr.operand)
        if expr.op == TokenType.MINUS:
            if type(operand) is bool:
                raise TypeError("Bool operands do not support arithmetic negation")
            return -operand
        elif expr.op == TokenType.NOT:
            return not operand
        raise NotImplementedError(f"unsupported unary operator: {expr.op}")

    def _evaluate_call(self, expr: CallExpr) -> object:
        callee = self._evaluate_impl(expr.callee)
        args = [self._evaluate_impl(a) for a in expr.args]
        if callable(callee):
            return self._invoke(callee, *args)
        raise TypeError(f"Cannot call non-callable: {callee}")

    def _evaluate_pipe(self, expr: PipeExpr) -> object:
        left = self._evaluate_impl(expr.left)
        right = self._evaluate_impl(expr.right)
        if callable(right):
            return self._invoke(right, left)
        return left

    def _evaluate_guard(self, expr: GuardExpr) -> object:
        condition = self._evaluate_impl(expr.condition)
        if condition:
            return self._evaluate_impl(expr.expr)
        return None

    def _evaluate_flood(self, expr: FloodExpr) -> object:
        """flood <target> — fill a reservoir from a value.

        If the target is already a reservoir (list) it is returned as-is;
        otherwise the value is wrapped into a fresh single-element reservoir.
        """
        target = self._evaluate_impl(expr.target)
        if isinstance(target, list):
            return target
        return [target]

    def _evaluate_drip(self, expr: DripExpr) -> object:
        target = self._evaluate_impl(expr.target)
        if isinstance(target, list) and target:
            return target.pop()
        return None

    def _evaluate_evaporate(self, expr: EvaporateExpr) -> object:
        """evaporate <target> — release a resource; empties a reservoir/map."""
        target = self._evaluate_impl(expr.target)
        if isinstance(target, (list, dict)):
            target.clear()
        return None

    def _evaluate_condense(self, expr: CondenseExpr) -> object:
        target = self._evaluate_impl(expr.target)
        if isinstance(target, dict):
            return target.get("value")
        return None

    def _evaluate_member(self, expr: MemberAccess) -> object:
        """obj.member — read a fountain field, bind a method, or index a map."""
        obj = self._evaluate_impl(expr.obj)
        name = expr.member
        if isinstance(obj, type) and issubclass(obj, Enum):
            if name not in obj.__members__:
                raise NameError(f"'{obj.__name__}' has no variant '{name}'")
            return obj[name]
        if isinstance(obj, StructInstance):
            if name not in obj.fields:
                raise NameError(f"'{obj.declaration.name}' has no field '{name}'")
            return obj.fields[name]
        if isinstance(obj, FountainInstance):
            if name in obj.fields:
                return obj.fields[name]
            method = obj.methods.get(name)
            if method is not None:
                # Bound method: the instance is bound as `this`, and the call
                # arguments map to the method's declared params.
                owner = obj.interpreter or self
                return owner._bind_callable(
                    lambda *a: owner._call_user_fn(method, list(a), this_obj=obj),
                    frames=obj.execution_frames or (owner._execution_frame(),),
                )
            raise NameError(f"'{obj.cls_decl.name}' has no member '{name}'")
        if isinstance(obj, dict):
            return obj.get(name)
        raise TypeError(f"Cannot access member '{name}' on {type(obj).__name__}")

    def _evaluate_new(self, expr: NewExpr) -> object:
        constructor = self.env.get(expr.class_name)
        args = [self._evaluate_impl(a) for a in expr.args]
        if callable(constructor):
            return self._invoke(constructor, *args)
        raise TypeError(f"Cannot instantiate non-callable: {expr.class_name}")

    def _evaluate_pipeline(self, expr: PipelineExpr) -> object:
        """TSCG pipeline ``left -> right``: feed the left value into the right
        operand when it is callable (same shape as the ``|`` pipe operator).

        ``PipelineExpr`` is a binary node (``left``/``right``); an earlier
        version walked a non-existent ``.steps`` list and raised AttributeError
        on any ``->`` expression.
        """
        left = self._evaluate_impl(expr.left)
        right = self._evaluate_impl(expr.right)
        if callable(right):
            return self._invoke(right, left)
        return right

    def _invoke(self, function, *args, **kwargs):
        self._execution_domain.checkpoint()
        try:
            return function(*args, **kwargs)
        finally:
            self._execution_domain.checkpoint()

    def _evaluate_combine(self, expr: CombineExpr) -> object:
        left = self._evaluate_impl(expr.left)
        right = self._evaluate_impl(expr.right)
        # Logical combine requires BOTH operands to be bool. A mixed
        # bool/non-bool must NOT coerce — silently doing so let a malformed
        # governance predicate authorize execution (fail-open). (review F3)
        if isinstance(left, bool) and isinstance(right, bool):
            if expr.op == "^":
                return left and right
            if expr.op == "||":
                return left or right
        # Structured composition: dicts merge, reservoirs concatenate.
        if isinstance(left, dict) and isinstance(right, dict):
            merged = dict(left)
            merged.update(right)
            return merged
        if isinstance(left, list) and isinstance(right, list):
            return left + right
        # No silent drop of the left operand: an unsupported combination is a
        # hard error (governed evaluation treats it as fail-closed). (review F3)
        raise TypeError(
            f"operator '{expr.op}' cannot combine "
            f"{type(left).__name__} and {type(right).__name__}"
        )
