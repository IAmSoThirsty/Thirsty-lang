"""
Thirsty-Lang Type Checker / Semantic Analyzer
Lexical scoping, type checking, governance validation, and error reporting.
"""

from typing import cast

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
    TokenType,
    UnaryOp,
    VariableDecl,
    WhileStmt,
)
from utf.thirsty_lang.diagnostics import Diagnostic, make_error
from utf.thirsty_lang.execution import resolve_execution_mode
from utf.thirsty_lang.typesys import (
    AnyType,
    BoolType,
    ConstructorType,
    DictType,
    EnumType,
    ErrorType,
    FloatType,
    FunctionType,
    FunctionUnionType,
    InterfaceType,
    IntType,
    QuenchedType,
    ReservoirType,
    StringType,
    StructType,
    TaskType,
    Type,
    ValueChoiceType,
    VoidType,
    is_assignable,
    type_from_name,
    type_to_string,
    unify,
)

_SCALAR_LITERALS = (IntLiteral, FloatLiteral, StringLiteral, BoolLiteral, NoneLiteral)


def _closed_literal(expr: Expr) -> bool:
    """Whether a literal allocates all its collection children itself."""
    if isinstance(expr, ArrayLiteral):
        return all(_closed_literal(item) for item in expr.elements)
    if isinstance(expr, DictLiteral):
        return all(
            isinstance(key, _SCALAR_LITERALS) and _closed_literal(value)
            for key, value in expr.items
        )
    return isinstance(expr, _SCALAR_LITERALS)


def _plain_read(expr: Expr) -> bool:
    if isinstance(expr, Subscript):
        return _plain_read(expr.obj) and _plain_read(expr.index)
    if isinstance(expr, BinaryOp):
        return _plain_read(expr.left) and _plain_read(expr.right)
    return isinstance(expr, Identifier) or _closed_literal(expr)


def _alternatives(value: Type) -> tuple[Type, ...]:
    return value.alternatives if isinstance(value, ValueChoiceType) else (value,)


def _join_types(values: list[Type]) -> Type:
    result = values[0] if values else AnyType()
    for value in values[1:]:
        result = unify(result, value)
    return result


def _edit_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return _edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def _nearest_match(name: str, candidates: list[str], max_dist: int = 3) -> list[str]:
    return [c for c in candidates if _edit_distance(name, c) <= max_dist]


class Scope:
    """A lexical scope with variable bindings and type information."""

    def __init__(self, parent: "Scope | None" = None):
        self.parent = parent
        self.bindings: dict[str, dict] = {}  # name -> {type, is_mut, kind}

    def declare(self, name: str, info: dict) -> bool:
        """Declare a new binding. Returns False if already declared in this scope."""
        if name in self.bindings:
            return False
        self.bindings[name] = info
        return True

    def lookup(self, name: str) -> dict | None:
        """Look up a binding in this scope or enclosing scopes."""
        if name in self.bindings:
            return self.bindings[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def is_mutable(self, name: str) -> bool:
        info = self.lookup(name)
        return info is not None and info.get("is_mut", False)


class Checker:
    """Semantic analysis and type checking for Thirsty-Lang AST."""

    def __init__(
        self,
        effect_warnings: bool = False,
        *,
        mode: str | None = None,
        allow_ungoverned: bool = False,
    ):
        self.scope = Scope()
        self.errors: list[Diagnostic] = []
        self.current_function_return_type: Type | None = None
        self._requested_mode = mode
        self._allow_ungoverned = allow_ungoverned
        _, self.in_governed_mode = resolve_execution_mode(
            mode=mode, allow_ungoverned=allow_ungoverned
        )
        self.imported_names: dict[str, str] = {}  # alias -> module_path
        self._hoisted: set = set()  # top-level fn/class names
        self._governed_names: set = set()  # governed function names
        self._prechecked_nominals: set[int] = set()
        self.effect_warnings = effect_warnings
        self._literal_shapes: dict[str, Expr] = {}

    def enter_scope(self):
        self._literal_shapes.clear()
        self.scope = Scope(self.scope)

    def exit_scope(self):
        self._literal_shapes.clear()
        if self.scope.parent:
            self.scope = self.scope.parent

    def check_all(self, ast: Program) -> list[Diagnostic]:
        """Type-check an entire Program AST."""
        self.errors = []
        self._literal_shapes.clear()
        self._prechecked_nominals = set()
        if getattr(ast, "parse_failed", False):
            self.errors.append(
                make_error("E901", span=ast.span, detail="module failed to parse")
            )
            return self.errors
        try:
            _, self.in_governed_mode = resolve_execution_mode(
                ast.header.mode if ast.header else None,
                self._requested_mode,
                allow_ungoverned=self._allow_ungoverned,
            )
        except (TypeError, ValueError) as error:
            self.errors.append(make_error("E901", span=ast.span, detail=str(error)))
            return self.errors
        from utf.thirsty_lang.shield_profile import (
            ShieldProfileError,
            checked_body,
            module_shield,
        )

        shield = module_shield(ast)
        if shield is not None:
            try:
                checked_body(shield)
            except ShieldProfileError as error:
                self.errors.append(Diagnostic("E901", str(error), error.span, "error"))
            return self.errors
        # Register mode
        if ast.header:
            # Register module name
            self.scope.declare(
                "__module__", {"type": StringType(), "is_mut": False, "kind": "module"}
            )
        # Register builtins
        self._register_builtins()
        # Hoist top-level function/class names so forward references resolve.
        self._hoist_declarations(ast.stmts)
        # Check all statements
        for stmt in ast.stmts:
            self._check_stmt(stmt)
        if self.effect_warnings:
            from utf.thirsty_lang.proof_obligations import (
                effect_warning_diagnostics,
            )

            self.errors.extend(effect_warning_diagnostics(ast))
        return self.errors

    def _hoist_declarations(self, stmts):
        """Pre-declare top-level functions/classes (enables forward references
        and mutual recursion) and record which functions are governed."""
        self._hoisted = set()
        self._governed_names = set()
        # Register nominal identities before resolving any function signature.
        # Struct placeholders allow recursive/forward field annotations to
        # refer to the same descriptor later populated below. Runtime order
        # is unchanged: this is compile-time type information only.
        for stmt in stmts:
            if isinstance(stmt, (EnumDecl, StructDecl)):
                self._declare_nominal(stmt)
        for stmt in stmts:
            if isinstance(stmt, EnumDecl):
                self._check_enum_decl(stmt)
                self._prechecked_nominals.add(id(stmt))
            elif isinstance(stmt, StructDecl):
                # Populate forward field information provisionally. The actual
                # declaration is checked again in source order, after preceding
                # constructor aliases exist. Report its diagnostics there once.
                diagnostics = self.errors
                self.errors = []
                try:
                    self._check_struct_decl(stmt)
                finally:
                    self.errors = diagnostics
        for stmt in stmts:
            name = getattr(stmt, "name", None)
            if isinstance(stmt, (FunctionDecl, GovernedFunctionDecl)):
                if name in self._hoisted:
                    self.errors.append(make_error("E010", span=stmt.span, name=name))
                    continue
                # Register the real signature (param + return types) so that
                # forward references, self-recursion, and mutual recursion all
                # see the correct arity while bodies are being checked.
                param_types = [
                    self._resolve_type(ptype, stmt) if ptype else AnyType()
                    for _pname, ptype in stmt.params
                ]
                # No explicit return type → gradual default of Any (not Void),
                # so a value-returning un-annotated function flows into typed
                # operators and self-recursion type-checks. (review F2)
                ret_type = (
                    self._resolve_type(stmt.return_type, stmt)
                    if stmt.return_type
                    else AnyType()
                )
                if not self.scope.declare(
                    stmt.name,
                    {
                        "type": FunctionType(param_types, ret_type),
                        "is_mut": False,
                        "kind": "function",
                    },
                ):
                    self.errors.append(make_error("E010", span=stmt.span, name=name))
                    continue
                self._hoisted.add(name)
                if isinstance(stmt, GovernedFunctionDecl):
                    self._governed_names.add(name)
            elif isinstance(stmt, ClassDecl):
                if name in self._hoisted:
                    self.errors.append(make_error("E010", span=stmt.span, name=name))
                    continue
                if not self.scope.declare(
                    stmt.name, {"type": AnyType(), "is_mut": False, "kind": "class"}
                ):
                    self.errors.append(make_error("E010", span=stmt.span, name=name))
                    continue
                self._hoisted.add(name)

    def _register_builtins(self):
        builtins = [
            "length",
            "contains",
            "split",
            "abs",
            "min",
            "max",
            "push",
            "pop",
            "size",
            "get",
            "flood",
            "condense",
            "evaporate",
            "strain",
            "transmute",
            "distill",
            "pour",
            "sip",
            "print",
        ]
        for name in builtins:
            self.scope.declare(
                name, {"type": AnyType(), "is_mut": False, "kind": "builtin"}
            )

    def _literal_slot(self, expr: Expr) -> Expr | None:
        if isinstance(expr, Identifier):
            return self._literal_shapes.get(expr.name)
        if isinstance(expr, (ArrayLiteral, DictLiteral)) and _closed_literal(expr):
            return expr
        if not isinstance(expr, Subscript) or not isinstance(
            expr.index, _SCALAR_LITERALS
        ):
            return None
        parent = self._literal_slot(expr.obj)
        key = None if isinstance(expr.index, NoneLiteral) else expr.index.value
        if isinstance(parent, ArrayLiteral) and type(key) is int:
            if -len(parent.elements) <= key < len(parent.elements):
                return parent.elements[key]
        if isinstance(parent, DictLiteral):
            for slot, value in parent.items:
                if isinstance(slot, NoneLiteral) and key is None:
                    return value
                if (
                    isinstance(
                        slot, (IntLiteral, FloatLiteral, StringLiteral, BoolLiteral)
                    )
                    and slot.value == key
                ):
                    return value
        return None

    def _check_stmt(self, stmt: Stmt):
        # Calls, escaping effects, unknown writes and control-flow joins end the
        # straight-line facts about literal positions. A same-kind scalar write
        # at a known position preserves the slot's type.
        if self._literal_shapes:
            if isinstance(stmt, (ExprStmt, VariableDecl, ReturnStmt, PourStmt)):
                read = (
                    stmt.expr
                    if isinstance(stmt, ExprStmt)
                    else (
                        stmt.init_expr if isinstance(stmt, VariableDecl) else stmt.value
                    )
                )
                keep = read is not None and _plain_read(read)
            elif isinstance(stmt, AssignStmt) and isinstance(stmt.target, Subscript):
                keep = isinstance(stmt.value, _SCALAR_LITERALS) and type(
                    self._literal_slot(stmt.target)
                ) is type(stmt.value)
            else:
                keep = False
            if not keep:
                self._literal_shapes.clear()
        if isinstance(stmt, VariableDecl):
            self._check_variable_decl(stmt)
        elif isinstance(stmt, FunctionDecl):
            self._check_function_decl(stmt)
        elif isinstance(stmt, ClassDecl):
            self._check_class_decl(stmt)
        elif isinstance(stmt, IfStmt):
            self._check_if_stmt(stmt)
        elif isinstance(stmt, WhileStmt):
            self._check_while_stmt(stmt)
        elif isinstance(stmt, ForStmt):
            self._check_for_stmt(stmt)
        elif isinstance(stmt, TimesStmt):
            self._check_times_stmt(stmt)
        elif isinstance(stmt, BlockStmt):
            self._check_block(stmt)
        elif isinstance(stmt, ReturnStmt):
            self._check_return_stmt(stmt)
        elif isinstance(stmt, PourStmt):
            self._check_expr(stmt.value)
        elif isinstance(stmt, SipStmt):
            self._check_expr(stmt.target)
        elif isinstance(stmt, AssignStmt):
            self._check_assign_stmt(stmt)
        elif isinstance(stmt, SymbolStmt):
            self._check_symbol_stmt(stmt)
        elif isinstance(stmt, ImportStmt):
            self._check_import_stmt(stmt)
        elif isinstance(stmt, ExprStmt):
            self._check_expr(stmt.expr)
        elif isinstance(stmt, CascadeCall):
            self._check_expr(stmt)
        elif isinstance(stmt, SecurityBlock):
            reason = (
                "stdout shield must be the only top-level statement in an explicitly governed module"
                if stmt.block_type == "shield"
                else f"security block '{stmt.block_type}' has no enforcement implementation"
            )
            self._unsupported(
                stmt,
                reason,
            )
            self._check_block(stmt.body)
        elif isinstance(stmt, SpillageStmt):
            self._check_block(stmt.body)
            for error_var, handler in stmt.handlers:
                self.enter_scope()
                if error_var:
                    self.scope.declare(
                        error_var, {"type": AnyType(), "is_mut": False, "kind": "error"}
                    )
                self._check_block(handler)
                self.exit_scope()
        elif isinstance(stmt, CleanupStmt):
            self._check_block(stmt.body)
            self._check_block(stmt.finalizer)
        elif isinstance(stmt, ThrowStmt):
            self._check_expr(stmt.value)
        elif isinstance(stmt, MorphDef):
            self._check_function_decl(
                FunctionDecl(
                    span=stmt.span,
                    name=stmt.name,
                    params=stmt.params,
                    return_type=None,
                    body=stmt.body,
                )
            )
        elif isinstance(stmt, DefendStrat):
            self._unsupported(
                stmt, "defend strategies have no enforcement implementation"
            )
        elif isinstance(stmt, EnumDecl):
            if id(stmt) not in self._prechecked_nominals:
                self._check_enum_decl(stmt)
        elif isinstance(stmt, StructDecl):
            if id(stmt) not in self._prechecked_nominals:
                self._check_struct_decl(stmt)
        elif isinstance(stmt, InterfaceDecl):
            self._check_interface_decl(stmt)
            self._unsupported(stmt, "interface contracts are not yet enforced")
        elif isinstance(stmt, GovernedFunctionDecl):
            self._check_governed_function_decl(stmt)
        elif isinstance(stmt, ShadowThirstMutation):
            if stmt.canonical_block:
                self._check_block(stmt.canonical_block)
        else:
            self._unsupported(stmt, f"unsupported statement: {type(stmt).__name__}")

    def _resolve_type(self, name: str, node: Stmt | Expr | None = None) -> Type:
        primitive = {
            "int": "Int",
            "float": "Float",
            "bool": "Bool",
            "string": "String",
            "void": "Void",
            "any": "Any",
        }

        def resolve_leaf(leaf: str) -> Type | None:
            info = self.scope.lookup(leaf)
            value_type = info.get("type") if info else None
            if isinstance(value_type, ConstructorType):
                return value_type.instance_type
            if isinstance(value_type, (EnumType, StructType)) and info:
                if info.get("kind") not in ("enum", "struct"):
                    raise ValueError(f"'{leaf}' names an instance, not a nominal type")
            if isinstance(value_type, (FunctionUnionType, ValueChoiceType)) and any(
                isinstance(item, ConstructorType) for item in value_type.alternatives
            ):
                raise ValueError(f"'{leaf}' does not identify one nominal type")
            if info and isinstance(
                info.get("type"), (EnumType, StructType, InterfaceType)
            ):
                return cast(Type, info["type"])
            if leaf in primitive:
                return type_from_name(primitive[leaf])
            return None

        try:
            return type_from_name(name, resolve_leaf)
        except ValueError as exc:
            self.errors.append(
                Diagnostic(
                    "E901",
                    f"Invalid type annotation: {exc}",
                    node.span if node is not None else (1, 1, 1, 1),
                    "error",
                )
            )
            return ErrorType()

    def _unsupported(self, node, reason: str):
        self.errors.append(Diagnostic("E901", reason, node.span, "error"))

    def _check_variable_decl(self, stmt: VariableDecl):
        expected = self._resolve_type(stmt.var_type, stmt) if stmt.var_type else None
        # Check duplicate
        if not self.scope.declare(
            stmt.name,
            {"type": expected or AnyType(), "is_mut": stmt.is_mut, "kind": "variable"},
        ):
            self.errors.append(make_error("E010", span=stmt.span, name=stmt.name))
            return
        # Check init expression
        if stmt.init_expr:
            expr_type = self._check_expr(stmt.init_expr)
            if expected is not None:
                if not self._is_expr_assignable(stmt.init_expr, expr_type, expected):
                    self.errors.append(
                        make_error(
                            "E021",
                            span=stmt.span,
                            found=type_to_string(expr_type),
                            expected=type_to_string(expected),
                        )
                    )
            # Update binding type
            self.scope.bindings[stmt.name] = {
                "type": expected if expected is not None else expr_type,
                "is_mut": stmt.is_mut,
                "kind": "variable",
            }

            if (
                expected is None
                and isinstance(stmt.init_expr, (ArrayLiteral, DictLiteral))
                and _closed_literal(stmt.init_expr)
            ):
                self._literal_shapes[stmt.name] = stmt.init_expr

    def _check_function_decl(self, stmt: FunctionDecl):
        # Top-level names are pre-declared by the hoist pass; only declare (and
        # duplicate-check) names that weren't hoisted (e.g. class methods).
        already_hoisted = (
            stmt.name in self._hoisted
            and self.scope.bindings.get(stmt.name) is not None
        )
        if not already_hoisted:
            if not self.scope.declare(
                stmt.name,
                {
                    "type": FunctionType([], AnyType()),
                    "is_mut": False,
                    "kind": "function",
                },
            ):
                self.errors.append(make_error("E010", span=stmt.span, name=stmt.name))
                return
        # Resolve the whole signature in the declaration scope before value
        # parameters can shadow nominal type names used later in that signature.
        param_types = [
            self._resolve_type(ptype, stmt) if ptype else AnyType()
            for _, ptype in stmt.params
        ]
        ret_type = (
            self._resolve_type(stmt.return_type, stmt)
            if stmt.return_type
            else AnyType()
        )
        self.enter_scope()
        for (pname, _), parameter_type in zip(stmt.params, param_types, strict=True):
            if not self.scope.declare(
                pname, {"type": parameter_type, "is_mut": False, "kind": "param"}
            ):
                self.errors.append(make_error("E010", span=stmt.span, name=pname))
        # Set return type context. No annotation → Any (gradual default), so
        # returns are unconstrained rather than forced to Void. (review F2)
        old_return_type = self.current_function_return_type
        self.current_function_return_type = ret_type
        # Check body
        self._check_block(stmt.body)
        self.current_function_return_type = old_return_type
        self.exit_scope()
        # Update binding with proper function type
        self.scope.bindings[stmt.name] = {
            "type": FunctionType(param_types, ret_type),
            "is_mut": False,
            "kind": "function",
        }

    def _is_expr_assignable(self, expr: Expr, actual: Type, expected: Type) -> bool:
        """Contextual construction may widen fresh values, never shared children."""
        if isinstance(expected, ValueChoiceType):
            if not isinstance(
                expr,
                (ArrayLiteral, DictLiteral, QuenchedLiteral, SliceExpr, CascadeCall),
            ):
                return is_assignable(actual, expected)
            # A fresh collection may use any compatible construction target.
            # Failed alternatives must not leak speculative diagnostics.
            for alternative in expected.alternatives:
                before = len(self.errors)
                if self._is_expr_assignable(expr, actual, alternative):
                    return True
                del self.errors[before:]
            return False
        pairs: list[tuple[Expr, Type]] = []
        if isinstance(expr, SliceExpr) and isinstance(expected, ReservoirType):
            # Slices copy their outer list only. A scalar element can widen,
            # but a child list/dict remains shared and must stay invariant.
            # Literal sources still check every element, without running bounds.
            source = self._check_expr(expr.obj)
            if isinstance(expr.obj, (ArrayLiteral, SliceExpr)):
                return self._is_expr_assignable(expr.obj, source, expected)
            if all(isinstance(item, ReservoirType) for item in _alternatives(source)):
                return all(
                    is_assignable(item.inner_type, expected.inner_type)
                    for item in _alternatives(source)
                    if isinstance(item, ReservoirType)
                )
            return is_assignable(actual, expected)
        elif isinstance(expr, QuenchedLiteral) and isinstance(expected, QuenchedType):
            if expr.value is None or isinstance(expr.value, NoneLiteral):
                return True
            pairs = [(expr.value, expected.inner_type)]
        elif isinstance(expr, ArrayLiteral) and isinstance(expected, ReservoirType):
            pairs = [(element, expected.inner_type) for element in expr.elements]
        elif isinstance(expr, DictLiteral) and isinstance(expected, DictType):
            pairs = [(key, expected.key_type) for key, _ in expr.items]
            pairs += [(value, expected.value_type) for _, value in expr.items]
        elif isinstance(expr, CascadeCall):
            return self._is_expr_assignable(expr.expr, actual, expected)
        elif isinstance(expr, BinaryOp) and expr.op in (TokenType.AND, TokenType.OR):
            return all(
                self._is_expr_assignable(operand, self._check_expr(operand), expected)
                for operand in (expr.left, expr.right)
            )
        else:
            return is_assignable(actual, expected)
        valid = True
        for element, element_expected in pairs:
            element_actual = self._check_expr(element)
            if not self._is_expr_assignable(element, element_actual, element_expected):
                valid = False
                self.errors.append(
                    make_error(
                        "E021",
                        span=element.span,
                        found=type_to_string(element_actual),
                        expected=type_to_string(element_expected),
                    )
                )
        return valid

    def _check_class_decl(self, stmt: ClassDecl):
        already_hoisted = (
            stmt.name in self._hoisted
            and self.scope.bindings.get(stmt.name) is not None
        )
        if not already_hoisted:
            if not self.scope.declare(
                stmt.name, {"type": AnyType(), "is_mut": False, "kind": "class"}
            ):
                self.errors.append(make_error("E010", span=stmt.span, name=stmt.name))
        self.enter_scope()
        for field_spec in stmt.fields:
            fname, ftype = field_spec[0], field_spec[1]
            t = self._resolve_type(ftype, stmt) if ftype else AnyType()
            self.scope.declare(fname, {"type": t, "is_mut": True, "kind": "field"})
            default_expr = field_spec[2] if len(field_spec) > 2 else None
            if default_expr is not None:
                actual = self._check_expr(default_expr)
                if ftype and not self._is_expr_assignable(default_expr, actual, t):
                    self.errors.append(
                        make_error(
                            "E021",
                            span=default_expr.span,
                            found=type_to_string(actual),
                            expected=type_to_string(t),
                        )
                    )
        for method in stmt.methods:
            params = method.params
            positional = (
                params[1:] if params and params[0][0] in ("self", "this") else params
            )
            if any(name == "this" for name, _ in positional):
                self._unsupported(
                    method, "Method parameter 'this' conflicts with the bound receiver"
                )
            self._check_function_decl(method)
        self.exit_scope()

    def _check_if_stmt(self, stmt: IfStmt):
        cond_type = self._check_expr(stmt.condition)
        if not isinstance(cond_type, BoolType) and not isinstance(cond_type, AnyType):
            self.errors.append(
                make_error(
                    "E024", span=stmt.condition.span, found=type_to_string(cond_type)
                )
            )
        self._check_block(stmt.then_block)
        if stmt.else_block:
            if isinstance(stmt.else_block, IfStmt):
                self._check_if_stmt(stmt.else_block)
            else:
                self._check_block(stmt.else_block)

    def _check_while_stmt(self, stmt: WhileStmt):
        cond_type = self._check_expr(stmt.condition)
        if not isinstance(cond_type, BoolType) and not isinstance(cond_type, AnyType):
            self.errors.append(
                make_error(
                    "E024", span=stmt.condition.span, found=type_to_string(cond_type)
                )
            )
        self._check_block(stmt.body)

    def _check_for_stmt(self, stmt: ForStmt):
        iterable_type = self._check_expr(stmt.iterable)
        element_type = _join_types(
            [self._iterated_type(item, stmt) for item in _alternatives(iterable_type)]
        )
        self.enter_scope()
        self.scope.declare(
            stmt.variable.name,
            {"type": element_type, "is_mut": False, "kind": "loop_var"},
        )
        self._check_block(stmt.body)
        self.exit_scope()

    def _iterated_type(self, iterable_type: Type, stmt: ForStmt) -> Type:
        element_type: Type = AnyType()
        if isinstance(iterable_type, ReservoirType):
            element_type = iterable_type.inner_type
        elif isinstance(iterable_type, DictType):
            element_type = iterable_type.key_type
        elif isinstance(iterable_type, StringType):
            element_type = StringType()
        elif not isinstance(iterable_type, (AnyType, ErrorType)):
            self.errors.append(
                make_error(
                    "E025", span=stmt.iterable.span, found=type_to_string(iterable_type)
                )
            )
        return element_type

    def _check_times_stmt(self, stmt: TimesStmt):
        # The count is evaluated to an int at runtime; just resolve the
        # expression (catches unknown identifiers) and check the body.
        self._check_expr(stmt.count)
        self._check_block(stmt.body)

    def _check_block(self, stmt: Stmt):
        if isinstance(stmt, BlockStmt):
            self.enter_scope()
            for s in stmt.statements:
                self._check_stmt(s)
            self.exit_scope()
        else:
            self._check_stmt(stmt)

    def _check_return_stmt(self, stmt: ReturnStmt):
        if stmt.value:
            val_type = self._check_expr(stmt.value)
            if self.current_function_return_type and not isinstance(
                self.current_function_return_type, VoidType
            ):
                if not self._is_expr_assignable(
                    stmt.value, val_type, self.current_function_return_type
                ):
                    self.errors.append(
                        make_error(
                            "E023",
                            span=stmt.span,
                            found=type_to_string(val_type),
                            expected=type_to_string(self.current_function_return_type),
                        )
                    )
        elif self.current_function_return_type and not isinstance(
            self.current_function_return_type, VoidType
        ):
            # returning nothing from non-void function
            self.errors.append(
                make_error(
                    "E023",
                    span=stmt.span,
                    found="Void",
                    expected=type_to_string(self.current_function_return_type),
                )
            )

    def _check_assign_stmt(self, stmt: AssignStmt):
        actual = self._check_expr(stmt.value)
        expected: Type = AnyType()
        expected_types: list[Type] | None = None
        if isinstance(stmt.target, Identifier):
            name = stmt.target.name
            info = self.scope.lookup(name)
            if info is None:
                # Check "did you mean?"
                all_names = list(self.scope.bindings.keys()) if self.scope else []
                s: Scope | None = self.scope
                while s:
                    all_names.extend(s.bindings.keys())
                    s = s.parent
                suggestions = _nearest_match(name, all_names)
                msg = f"Unknown identifier: '{name}'"
                if suggestions:
                    msg += f" Did you mean: {', '.join(suggestions)}?"
                self.errors.append(Diagnostic("E011", msg, stmt.span, "error"))
                return
            if not info.get("is_mut", False):
                self.errors.append(make_error("E020", span=stmt.span, name=name))
            expected = info.get("type", AnyType())
        elif isinstance(stmt.target, SliceExpr):
            self._unsupported(stmt.target, "Slice assignment is not supported")
            self._check_expr(stmt.target)
            return
        elif isinstance(stmt.target, Subscript):
            expected_types = self._subscript_targets(stmt.target, assignment=True)
        elif isinstance(stmt.target, MemberAccess):
            object_type = self._check_expr(stmt.target.obj)
            expected_types = [
                self._check_member_type(item, stmt.target, assignment=True)
                for item in _alternatives(object_type)
            ]
        else:
            expected = self._check_expr(stmt.target)
        for target_type in expected_types if expected_types is not None else [expected]:
            if not self._is_expr_assignable(stmt.value, actual, target_type):
                self.errors.append(
                    make_error(
                        "E021",
                        span=stmt.span,
                        found=type_to_string(actual),
                        expected=type_to_string(target_type),
                    )
                )

    def _check_symbol_stmt(self, stmt: SymbolStmt):
        if not self.scope.declare(
            stmt.symbol_name, {"type": StringType(), "is_mut": False, "kind": "symbol"}
        ):
            self.errors.append(
                make_error("E010", span=stmt.span, name=stmt.symbol_name)
            )

    def _check_import_stmt(self, stmt: ImportStmt):
        alias = stmt.alias or stmt.module_path
        self.scope.declare(
            alias, {"type": AnyType(), "is_mut": False, "kind": "module"}
        )

    def _declare_nominal(
        self, stmt: EnumDecl | StructDecl
    ) -> EnumType | StructType | None:
        info = self.scope.bindings.get(stmt.name)
        if info is not None:
            descriptor = info.get("type")
            if isinstance(descriptor, ConstructorType):
                descriptor = descriptor.instance_type
            if (
                isinstance(descriptor, (EnumType, StructType))
                and descriptor.declaration_id is stmt
            ):
                return descriptor
            return None
        nominal: EnumType | StructType = (
            EnumType(stmt.name, stmt.variants, declaration_id=stmt)
            if isinstance(stmt, EnumDecl)
            else StructType(stmt.name, declaration_id=stmt)
        )
        self.scope.declare(
            stmt.name,
            {
                "type": ConstructorType(nominal),
                "is_mut": False,
                "kind": "enum" if isinstance(stmt, EnumDecl) else "struct",
            },
        )
        return nominal

    def _check_enum_decl(self, stmt: EnumDecl):
        if len(stmt.variants) != len(set(stmt.variants)):
            self._unsupported(stmt, f"duplicate variant in enum '{stmt.name}'")
        if self._declare_nominal(stmt) is None:
            self.errors.append(make_error("E010", span=stmt.span, name=stmt.name))

    def _check_struct_decl(self, stmt: StructDecl):
        descriptor = self._declare_nominal(stmt)
        if not isinstance(descriptor, StructType):
            self.errors.append(make_error("E010", span=stmt.span, name=stmt.name))
            return
        field_types = {}
        for fname, ftype in stmt.fields:
            if fname in field_types:
                self._unsupported(
                    stmt, f"duplicate field '{fname}' in struct '{stmt.name}'"
                )
            field_types[fname] = self._resolve_type(ftype, stmt) if ftype else AnyType()
        descriptor.field_types.update(field_types)

    def _check_interface_decl(self, stmt: InterfaceDecl):
        method_sigs = {}
        for mname, params, _ret_type in stmt.methods:
            method_sigs[mname] = [
                self._resolve_type(p[1], stmt) if p[1] else AnyType() for p in params
            ]
        if not self.scope.declare(
            stmt.name,
            {
                "type": InterfaceType(stmt.name, method_sigs, declaration_id=stmt),
                "is_mut": False,
                "kind": "interface",
            },
        ):
            self.errors.append(make_error("E010", span=stmt.span, name=stmt.name))

    def _check_governed_function_decl(self, stmt: GovernedFunctionDecl):
        # The parser only builds a GovernedFunctionDecl when at least one
        # contract clause (requires / ensures / invariant) is present, so the
        # "missing contract" case is structurally impossible here — no runtime
        # check needed. Type-check the function body like any other.
        self._check_function_decl(
            FunctionDecl(
                name=stmt.name,
                params=stmt.params,
                return_type=stmt.return_type,
                body=stmt.body,
                span=stmt.span,
            )
        )

    def _check_subscript(self, expr: Subscript, *, assignment: bool = False) -> Type:
        targets = self._subscript_targets(expr, assignment=assignment)
        slot = None if assignment else self._literal_slot(expr)
        return self._check_expr(slot) if slot is not None else _join_types(targets)

    def _subscript_targets(self, expr: Subscript, *, assignment: bool) -> list[Type]:
        collection_type = self._check_expr(expr.obj)
        index_type = self._check_expr(expr.index)
        return [
            self._subscript_type(item, index_type, expr, assignment=assignment)
            for item in _alternatives(collection_type)
        ]

    def _subscript_type(
        self,
        collection_type: Type,
        index_type: Type,
        expr: Subscript,
        *,
        assignment: bool,
    ) -> Type:
        if isinstance(collection_type, DictType):
            if not self._is_expr_assignable(
                expr.index, index_type, collection_type.key_type
            ):
                self.errors.append(
                    make_error(
                        "E021",
                        span=expr.index.span,
                        found=type_to_string(index_type),
                        expected=type_to_string(collection_type.key_type),
                    )
                )
            return collection_type.value_type
        if isinstance(collection_type, (ReservoirType, StringType)):
            if not isinstance(index_type, (IntType, AnyType, ErrorType)):
                self._unsupported(expr.index, "Sequence index must be an Int")
            if isinstance(collection_type, ReservoirType):
                return collection_type.inner_type
            if assignment:
                self._unsupported(expr, "String indices cannot be assigned")
            return StringType()
        if isinstance(collection_type, (AnyType, ErrorType)):
            return collection_type
        self._unsupported(expr.obj, "Indexing requires a sequence or dictionary")
        return ErrorType()

    def _check_call_signature(self, callee_type, args, arg_types, call, callee) -> Type:
        """Validate one invocation against every possible known callable."""
        if isinstance(callee_type, ValueChoiceType):
            return _join_types(
                [
                    self._check_call_signature(item, args, arg_types, call, callee)
                    for item in callee_type.alternatives
                ]
            )
        signatures: tuple[FunctionType, ...]
        if isinstance(callee_type, FunctionType):
            signatures = (callee_type,)
        elif isinstance(callee_type, ConstructorType):
            signatures = (callee_type.signature,)
        elif isinstance(callee_type, FunctionUnionType):
            signatures = tuple(
                item.signature if isinstance(item, ConstructorType) else item
                for item in callee_type.alternatives
            )
        elif isinstance(callee_type, (AnyType, TaskType)):
            return AnyType()
        elif isinstance(callee_type, ErrorType):
            return callee_type
        else:
            self.errors.append(
                make_error("E031", span=call.span, found=type_to_string(callee_type))
            )
            return ErrorType()
        for expected in sorted({len(item.param_types) for item in signatures}):
            if expected != len(args):
                self.errors.append(
                    make_error(
                        "E030",
                        span=call.span,
                        name=str(callee),
                        expected=expected,
                        got=len(args),
                    )
                )
        result = signatures[0].return_type
        for signature in signatures:
            for arg, actual, expected_type in zip(
                args, arg_types, signature.param_types, strict=False
            ):
                if not self._is_expr_assignable(arg, actual, expected_type):
                    self.errors.append(
                        make_error(
                            "E021",
                            span=arg.span,
                            found=type_to_string(actual),
                            expected=type_to_string(expected_type),
                        )
                    )
            result = unify(result, signature.return_type)
        return result

    def _check_member_type(
        self, object_type: Type, expr: MemberAccess, *, assignment: bool = False
    ) -> Type:
        """Member access respects constructor/instance identity through choices."""
        if isinstance(object_type, (AnyType, TaskType)):
            return AnyType()
        if isinstance(object_type, DictType):
            if not is_assignable(StringType(), object_type.key_type):
                self._unsupported(
                    expr, "Dictionary member access requires a String key"
                )
            # Native dictionary members use .get(), so absence yields none.
            return (
                object_type.value_type
                if assignment
                else unify(object_type.value_type, VoidType())
            )
        if isinstance(object_type, ErrorType):
            return object_type
        if isinstance(object_type, (FunctionUnionType, ValueChoiceType)):
            members = [
                self._check_member_type(item, expr, assignment=assignment)
                for item in object_type.alternatives
            ]
            if any(isinstance(item, ErrorType) for item in members):
                return ErrorType()
            result = members[0]
            for member in members[1:]:
                result = unify(result, member)
            return result
        if isinstance(object_type, ConstructorType):
            instance_type = object_type.instance_type
            if isinstance(instance_type, EnumType):
                if expr.member in instance_type.variants:
                    return instance_type
                self._unsupported(
                    expr, f"'{instance_type.name}' has no variant '{expr.member}'"
                )
            else:
                self._unsupported(expr, "Struct fields require an instance")
        elif isinstance(object_type, StructType):
            if expr.member in object_type.field_types:
                return object_type.field_types[expr.member]
            self._unsupported(
                expr, f"'{object_type.name}' has no field '{expr.member}'"
            )
        elif isinstance(object_type, EnumType):
            self._unsupported(expr, "Enum variant access requires a constructor")
        else:
            self._unsupported(
                expr, f"Type {type_to_string(object_type)} does not expose members"
            )
        return ErrorType()

    def _check_binary_types(
        self, expr: BinaryOp, left_type: Type, right_type: Type
    ) -> Type:
        numeric_operands = isinstance(left_type, (IntType, FloatType)) and isinstance(
            right_type, (IntType, FloatType)
        )
        boolean_operand = isinstance(left_type, BoolType) or isinstance(
            right_type, BoolType
        )
        if boolean_operand and expr.op not in (TokenType.AND, TokenType.OR):
            boolean_equality = expr.op in (TokenType.EQEQ, TokenType.NE) and all(
                isinstance(operand, (BoolType, AnyType, ErrorType))
                for operand in (left_type, right_type)
            )
            if not boolean_equality:
                self._unsupported(
                    expr,
                    "Bool operands support only Boolean equality and logical operators",
                )
                return ErrorType()
        # Comparison ops return Bool
        if expr.op in (
            TokenType.EQEQ,
            TokenType.NE,
            TokenType.LT,
            TokenType.GT,
            TokenType.LE,
            TokenType.GE,
        ):
            if (
                not isinstance(left_type, type(right_type))
                and not numeric_operands
                and not isinstance(left_type, AnyType)
                and not isinstance(right_type, AnyType)
            ):
                self.errors.append(
                    make_error(
                        "E022",
                        span=expr.span,
                        op=expr.op.name,
                        expected=type_to_string(left_type),
                        found=type_to_string(right_type),
                    )
                )
            return BoolType()
        # Concatenation allocates fresh outer slots; nested references stay shared.
        if (
            expr.op == TokenType.PLUS
            and isinstance(left_type, ReservoirType)
            and isinstance(right_type, ReservoirType)
        ):
            return ReservoirType(unify(left_type.inner_type, right_type.inner_type))
        # Arithmetic ops
        if (
            not is_assignable(right_type, left_type)
            and not numeric_operands
            and not isinstance(left_type, AnyType)
            and not isinstance(right_type, AnyType)
        ):
            self.errors.append(
                make_error(
                    "E022",
                    span=expr.span,
                    op=expr.op.name,
                    expected=type_to_string(left_type),
                    found=type_to_string(right_type),
                )
            )
        if expr.op == TokenType.SLASH and numeric_operands:
            return FloatType()
        if isinstance(left_type, FloatType) or isinstance(right_type, FloatType):
            return FloatType()
        return left_type

    def _check_expr(self, expr: Expr) -> Type:
        """Type-check an expression and return its Type."""
        if isinstance(expr, IntLiteral):
            return IntType()
        elif isinstance(expr, FloatLiteral):
            return FloatType()
        elif isinstance(expr, StringLiteral):
            return StringType()
        elif isinstance(expr, BoolLiteral):
            return BoolType()
        elif isinstance(expr, NoneLiteral):
            return VoidType()
        elif isinstance(expr, ErrorLiteral):
            return ErrorType()
        elif isinstance(expr, QuenchedLiteral):
            if expr.value is not None:
                self._check_expr(expr.value)
            inner = (
                self._resolve_type(expr.type_param, expr)
                if expr.type_param
                else AnyType()
            )
            return QuenchedType(inner)
        elif isinstance(expr, AssignStmt):
            self.errors.append(
                Diagnostic(
                    "E901",
                    "Assignment cannot be used as an expression",
                    expr.span,
                    "error",
                )
            )
            return ErrorType()
        elif isinstance(expr, Identifier):
            if expr.name == "__error__":
                return ErrorType()
            # `this` is bound at runtime inside fountain methods; its members are
            # resolved dynamically, so treat the receiver as Any rather than
            # flagging it as an unknown identifier.
            if expr.name == "this":
                return AnyType()
            info = self.scope.lookup(expr.name)
            if info is None:
                suggestions: list[str] = []
                s: Scope | None = self.scope
                while s:
                    suggestions.extend(s.bindings.keys())
                    s = s.parent
                matches = _nearest_match(expr.name, list(set(suggestions)))
                msg = f"Unknown identifier: '{expr.name}'"
                if matches:
                    msg += f" Did you mean: {', '.join(matches)}?"
                self.errors.append(Diagnostic("E011", msg, expr.span, "error"))
                return ErrorType()
            return cast(Type, info.get("type", AnyType()))
        elif isinstance(expr, BinaryOp):
            left_type = self._check_expr(expr.left)
            right_type = self._check_expr(expr.right)
            if expr.op in (TokenType.AND, TokenType.OR):
                return unify(left_type, right_type)
            return _join_types(
                [
                    self._check_binary_types(expr, left, right)
                    for left in _alternatives(left_type)
                    for right in _alternatives(right_type)
                ]
            )
        elif isinstance(expr, LambdaExpr):
            self.enter_scope()
            for pname, ptype in expr.params:
                t = self._resolve_type(ptype, expr) if ptype else AnyType()
                if not self.scope.declare(
                    pname, {"type": t, "is_mut": False, "kind": "param"}
                ):
                    self.errors.append(make_error("E010", span=expr.span, name=pname))
            self._check_block(expr.body)
            self.exit_scope()
            return AnyType()
        elif isinstance(expr, UnaryOp):
            operand_type = self._check_expr(expr.operand)
            if expr.op == TokenType.NOT:
                return BoolType()
            if expr.op == TokenType.MINUS and not all(
                isinstance(item, (IntType, FloatType, AnyType, ErrorType))
                for item in _alternatives(operand_type)
            ):
                self._unsupported(expr, "Arithmetic negation requires Int or Float")
                return ErrorType()
            return operand_type
        elif isinstance(expr, CallExpr):
            # E053: a governed function may not be called from core mode.
            if (
                isinstance(expr.callee, Identifier)
                and expr.callee.name in self._governed_names
                and not self.in_governed_mode
            ):
                self.errors.append(
                    make_error("E053", span=expr.span, name=expr.callee.name)
                )
            callee_type = self._check_expr(expr.callee)
            arg_types = [self._check_expr(arg) for arg in expr.args]
            return self._check_call_signature(
                callee_type, expr.args, arg_types, expr, expr.callee
            )
        elif isinstance(expr, PipeExpr):
            left_type = self._check_expr(expr.left)
            right_type = self._check_expr(expr.right)
            return _join_types(
                [
                    (
                        self._check_call_signature(
                            item, [expr.left], [left_type], expr, expr.right
                        )
                        if isinstance(
                            item, (FunctionType, ConstructorType, FunctionUnionType)
                        )
                        else (
                            AnyType()
                            if isinstance(item, (AnyType, TaskType))
                            else left_type
                        )
                    )
                    for item in _alternatives(right_type)
                ]
            )
        elif isinstance(expr, GuardExpr):
            cond_type = self._check_expr(expr.condition)
            if not isinstance(cond_type, BoolType) and not isinstance(
                cond_type, AnyType
            ):
                self.errors.append(
                    make_error(
                        "E024",
                        span=expr.condition.span,
                        found=type_to_string(cond_type),
                    )
                )
            return unify(self._check_expr(expr.expr), VoidType())
        elif isinstance(expr, FloodExpr):
            return _join_types(
                [
                    item if isinstance(item, ReservoirType) else ReservoirType(item)
                    for item in _alternatives(self._check_expr(expr.target))
                ]
            )
        elif isinstance(expr, DripExpr):
            return _join_types(
                [
                    (
                        unify(item.inner_type, VoidType())
                        if isinstance(item, ReservoirType)
                        else item if isinstance(item, AnyType) else VoidType()
                    )
                    for item in _alternatives(self._check_expr(expr.target))
                ]
            )
        elif isinstance(expr, EvaporateExpr):
            self._check_expr(expr.target)
            return VoidType()
        elif isinstance(expr, CondenseExpr):
            return _join_types(
                [
                    (
                        unify(item.value_type, VoidType())
                        if isinstance(item, DictType)
                        else item if isinstance(item, AnyType) else VoidType()
                    )
                    for item in _alternatives(self._check_expr(expr.target))
                ]
            )
        elif isinstance(expr, ArrayLiteral):
            element_types = [self._check_expr(element) for element in expr.elements]
            elem = element_types[0] if element_types else AnyType()
            for element_type in element_types[1:]:
                elem = unify(elem, element_type)
            return ReservoirType(elem)
        elif isinstance(expr, DictLiteral):
            key_types = []
            value_types = []
            literal_keys: set = set()
            for key, value in expr.items:
                key_types.append(self._check_expr(key))
                value_types.append(self._check_expr(value))
                if isinstance(
                    key,
                    (IntLiteral, FloatLiteral, StringLiteral, BoolLiteral, NoneLiteral),
                ):
                    literal_value = None if isinstance(key, NoneLiteral) else key.value
                    if literal_value in literal_keys:
                        self._unsupported(
                            key, f"duplicate dictionary key: {literal_value!r}"
                        )
                    literal_keys.add(literal_value)
            key_type = key_types[0] if key_types else AnyType()
            value_type = value_types[0] if value_types else AnyType()
            for next_type in key_types[1:]:
                key_type = unify(key_type, next_type)
            for next_type in value_types[1:]:
                value_type = unify(value_type, next_type)
            return DictType(key_type, value_type)
        elif isinstance(expr, MemberAccess):
            object_type = self._check_expr(expr.obj)
            return self._check_member_type(object_type, expr)
        elif isinstance(expr, Subscript):
            return self._check_subscript(expr)
        elif isinstance(expr, SliceExpr):
            collection_type = self._check_expr(expr.obj)
            for bound in (expr.start, expr.stop, expr.step):
                if bound is not None:
                    bound_type = self._check_expr(bound)
                    if not isinstance(
                        bound_type, (IntType, VoidType, AnyType, ErrorType)
                    ):
                        self._unsupported(bound, "Slice bound must be an Int or none")
            if all(
                isinstance(item, (ReservoirType, StringType, AnyType, ErrorType))
                for item in _alternatives(collection_type)
            ):
                return collection_type
            self._unsupported(
                expr.obj, "Slicing requires a sequence (list, string, tuple, or bytes)"
            )
            return ErrorType()
        elif isinstance(expr, SanitizeExpr):
            self._unsupported(
                expr, "sanitize requires an explicit validator or encoding"
            )
            return self._check_expr(expr.expr)
        elif isinstance(expr, ArmorExpr):
            self._unsupported(expr, "armor has no protection implementation")
            return self._check_expr(expr.expr)
        elif isinstance(expr, NewExpr):
            info = self.scope.lookup(expr.class_name)
            argument_types = [self._check_expr(arg) for arg in expr.args]
            if info is None:
                self.errors.append(
                    make_error("E011", span=expr.span, name=expr.class_name)
                )
                return ErrorType()
            return self._check_call_signature(
                info.get("type", AnyType()),
                expr.args,
                argument_types,
                expr,
                expr.class_name,
            )
        elif isinstance(expr, CascadeCall):
            # Cascade waits for completion and yields the expression's value.
            return self._check_expr(expr.expr)
        elif isinstance(expr, SymbolExpr):
            return StringType()
        elif isinstance(expr, PipelineExpr):
            left_type = self._check_expr(expr.left)
            right_type = self._check_expr(expr.right)
            return _join_types(
                [
                    (
                        self._check_call_signature(
                            item, [expr.left], [left_type], expr, expr.right
                        )
                        if isinstance(
                            item, (FunctionType, ConstructorType, FunctionUnionType)
                        )
                        else AnyType() if isinstance(item, TaskType) else item
                    )
                    for item in _alternatives(right_type)
                ]
            )
        elif isinstance(expr, CombineExpr):
            lt = self._check_expr(expr.left)
            rt = self._check_expr(expr.right)
            l_bool, r_bool = isinstance(lt, BoolType), isinstance(rt, BoolType)
            l_any, r_any = isinstance(lt, AnyType), isinstance(rt, AnyType)
            # A bool combined with a known non-bool is a malformed predicate:
            # reject it statically so it fails closed rather than coercing at
            # runtime. (review F3)
            if (l_bool and not r_bool and not r_any) or (
                r_bool and not l_bool and not l_any
            ):
                self.errors.append(
                    make_error(
                        "E022",
                        span=expr.span,
                        op=expr.op,
                        expected="Bool",
                        found=type_to_string(rt if l_bool else lt),
                    )
                )
                return BoolType()
            if l_bool and r_bool:
                return BoolType()
            return AnyType()
        self._unsupported(expr, f"unsupported expression: {type(expr).__name__}")
        return ErrorType()


def check_ast(
    ast: Program,
    effect_warnings: bool = False,
    *,
    mode: str | None = None,
    allow_ungoverned: bool = False,
) -> list[Diagnostic]:
    """Convenience function to type-check a Program AST."""
    checker = Checker(
        effect_warnings=effect_warnings, mode=mode, allow_ungoverned=allow_ungoverned
    )
    return checker.check_all(ast)
