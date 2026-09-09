"""
Thirsty-Lang AST-based Code Formatter
Pretty-prints Thirsty-Lang AST nodes with proper indentation and canonical style.
"""

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
    ModuleHeader,
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
    ThrowStmt,
    TimesStmt,
    UnaryOp,
    VariableDecl,
    WhileStmt,
)
from utf.thirsty_lang.token import TokenType

INDENT = "    "


def format_program(node: Program) -> str:
    """Format an entire program."""
    if getattr(node, "parse_failed", False):
        raise ValueError("module failed to parse; refusing to format recovered source")
    parts = []
    if node.header:
        parts.append(format_module_header(node.header))
        parts.append("")
    parts.extend(_format_statements(node.stmts, 0))
    return "\n".join(parts)


def _format_statements(statements: list, indent: int) -> list[str]:
    """Keep statement boundaries when newlines alone cannot terminate an expr."""
    parts = [format_stmt(stmt, indent) for stmt in statements]
    for index, stmt in enumerate(statements[:-1]):
        # '[' and '(' can continue an expression as indexing/calling; '-' can
        # become subtraction. Only statement forms that consume a terminator
        # may receive one (direct cascade/block forms do not).
        if isinstance(
            stmt,
            (
                VariableDecl,
                AssignStmt,
                ExprStmt,
                ReturnStmt,
                PourStmt,
                SipStmt,
                ThrowStmt,
            ),
        ) and parts[index + 1].lstrip().startswith(("[", "(", "-")):
            parts[index] += ";"
    return parts


def format_module_header(node: ModuleHeader) -> str:
    return f"module {node.name}: {node.mode}"


def format_stmt(node: Stmt, indent: int = 0) -> str:
    """Format a statement node."""
    prefix = INDENT * indent

    if isinstance(node, BlockStmt):
        return format_block(node, indent)

    elif isinstance(node, VariableDecl):
        mut = "mut " if node.is_mut else ""
        var_type = f": {node.var_type}" if node.var_type else ""
        init = f" = {format_expr(node.init_expr, 0)}" if node.init_expr else ""
        return f"{prefix}drink {mut}{node.name}{var_type}{init}"

    elif isinstance(node, FunctionDecl):
        params = ", ".join(f"{n}: {t}" if t else n for n, t in node.params)
        ret = f" -> {node.return_type}" if node.return_type else ""
        body = (
            format_block(node.body, indent + 1)
            if isinstance(node.body, BlockStmt)
            else format_stmt(node.body, indent + 1)
        )
        return f"{prefix}glass {node.name}({params}){ret} {{\n{body}\n{prefix}}}"

    elif isinstance(node, ClassDecl):
        methods = "\n".join(format_stmt(m, indent + 1) for m in node.methods)

        def _fmt_field(spec):
            n, t = spec[0], spec[1]
            default = spec[2] if len(spec) > 2 else None
            line = f"{INDENT * (indent + 1)}drink {n}: {t}"
            if default is not None:
                line += f" = {format_expr(default)}"
            return line

        fields_str = "\n".join(_fmt_field(f) for f in node.fields)
        body_parts = [p for p in [fields_str, methods] if p]
        body = "\n".join(body_parts)
        return f"{prefix}fountain {node.name} {{\n{body}\n{prefix}}}"

    elif isinstance(node, IfStmt):
        cond = format_expr(node.condition, 0)
        then_block = (
            format_block(node.then_block, indent + 1)
            if isinstance(node.then_block, BlockStmt)
            else format_stmt(node.then_block, indent + 1)
        )
        result = f"{prefix}thirsty ({cond}) {{\n{then_block}\n{prefix}}}"
        if node.else_block:
            if isinstance(node.else_block, IfStmt):
                result += f" hydrated {format_else_if(node.else_block, indent)}"
            else:
                else_block = (
                    format_block(node.else_block, indent + 1)
                    if isinstance(node.else_block, BlockStmt)
                    else format_stmt(node.else_block, indent + 1)
                )
                result += f" hydrated {{\n{else_block}\n{prefix}}}"
        return result

    elif isinstance(node, WhileStmt):
        cond = format_expr(node.condition, 0)
        body = (
            format_block(node.body, indent + 1)
            if isinstance(node.body, BlockStmt)
            else format_stmt(node.body, indent + 1)
        )
        return f"{prefix}refill ({cond}) {{\n{body}\n{prefix}}}"

    elif isinstance(node, ForStmt):
        var = (
            node.variable.name
            if isinstance(node.variable, Identifier)
            else str(node.variable)
        )
        iterable = format_expr(node.iterable, 0)
        body = (
            format_block(node.body, indent + 1)
            if isinstance(node.body, BlockStmt)
            else format_stmt(node.body, indent + 1)
        )
        return f"{prefix}refill ({var} in {iterable}) {{\n{body}\n{prefix}}}"

    elif isinstance(node, TimesStmt):
        count = format_expr(node.count, 0)
        body = (
            format_block(node.body, indent + 1)
            if isinstance(node.body, BlockStmt)
            else format_stmt(node.body, indent + 1)
        )
        return f"{prefix}times {count} {{\n{body}\n{prefix}}}"

    elif isinstance(node, ReturnStmt):
        val = format_expr(node.value, 0) if node.value else ""
        return f"{prefix}return {val}"

    elif isinstance(node, PourStmt):
        val = format_expr(node.value, 0)
        return f"{prefix}pour {val}"

    elif isinstance(node, SipStmt):
        target = f" {format_expr(node.target, 0)}" if node.target else ""
        return f"{prefix}sip{target}"

    elif isinstance(node, AssignStmt):
        target = format_expr(node.target, 0)
        value = format_expr(node.value, 0)
        return f"{prefix}{target} = {value}"

    elif isinstance(node, ImportStmt):
        alias = f" as {node.alias}" if node.alias else ""
        return f"{prefix}import '{node.module_path}'{alias}"

    elif isinstance(node, ExprStmt):
        expression = format_expr(node.expr, 0)
        if isinstance(node.expr, DictLiteral):
            expression = f"({expression})"
        return f"{prefix}{expression}"

    elif isinstance(node, SecurityBlock):
        body = (
            format_block(node.body, indent + 1)
            if isinstance(node.body, BlockStmt)
            else format_stmt(node.body, indent + 1)
        )
        return f"{prefix}{node.block_type} {{\n{body}\n{prefix}}}"

    elif isinstance(node, SpillageStmt):
        body = (
            format_block(node.body, indent + 1)
            if isinstance(node.body, BlockStmt)
            else format_stmt(node.body, indent + 1)
        )
        handlers_str = ""
        for error_type, handler in node.handlers:
            h = (
                format_block(handler, indent + 2)
                if isinstance(handler, BlockStmt)
                else format_stmt(handler, indent + 2)
            )
            binding = f" ({error_type})" if error_type else ""
            handlers_str += f"\n{prefix}error{binding} {{\n{h}\n{prefix}}}"
        return f"{prefix}spillage {{\n{body}\n{prefix}}}{handlers_str}"

    elif isinstance(node, CleanupStmt):
        body = (
            format_block(node.body, indent + 1)
            if isinstance(node.body, BlockStmt)
            else format_stmt(node.body, indent + 1)
        )
        finalizer = (
            format_block(node.finalizer, indent + 1)
            if isinstance(node.finalizer, BlockStmt)
            else format_stmt(node.finalizer, indent + 1)
        )
        return f"{prefix}cleanup {{\n{body}\n{prefix}}} finally {{\n{finalizer}\n{prefix}}}"

    elif isinstance(node, ThrowStmt):
        val = format_expr(node.value, 0)
        return f"{prefix}throw {val}"

    elif isinstance(node, CascadeCall):
        return f"{prefix}cascade {format_expr(node.expr, 0)}"

    elif isinstance(node, GovernedFunctionDecl):
        params = ", ".join(f"{n}: {t}" if t else n for n, t in node.params)
        ret = f" -> {node.return_type}" if node.return_type else ""
        clauses = ""
        if node.requires_annotation:
            clauses += f" requires {node.requires_annotation}"
        if node.ensures_annotation:
            clauses += f" ensures {node.ensures_annotation}"
        if node.invariant_annotation:
            clauses += f" invariant {node.invariant_annotation}"
        body = (
            format_block(node.body, indent + 1)
            if isinstance(node.body, BlockStmt)
            else format_stmt(node.body, indent + 1)
        )
        return (
            f"{prefix}glass {node.name}({params}){ret}{clauses} {{\n{body}\n{prefix}}}"
        )

    elif isinstance(node, MorphDef):
        params = ", ".join(f"{n}: {t}" if t else n for n, t in node.params)
        body = (
            format_block(node.body, indent + 1)
            if isinstance(node.body, BlockStmt)
            else format_stmt(node.body, indent + 1)
        )
        return f"{prefix}morph {node.name}({params}) {{\n{body}\n{prefix}}}"

    elif isinstance(node, DefendStrat):
        actions_str = "; ".join(format_expr(action) for action in node.actions)
        policy = f"({node.policy})" if node.policy else ""
        return f"{prefix}defend {node.name}{policy} {{ {actions_str} }}"

    elif isinstance(node, EnumDecl):
        variants_str = ", ".join(node.variants)
        return f"{prefix}enum {node.name} {{ {variants_str} }}"

    elif isinstance(node, StructDecl):
        fields_str = "; ".join(f"{n}: {t}" if t else n for n, t in node.fields)
        return f"{prefix}struct {node.name} {{ {fields_str} }}"

    elif isinstance(node, InterfaceDecl):
        method_lines = []
        for name, params, return_type in node.methods:
            parameters = ", ".join(f"{n}: {t}" if t else n for n, t in params)
            result_type = f" -> {return_type}" if return_type else ""
            method_lines.append(f"{name}({parameters}){result_type}")
        return f"{prefix}interface {node.name} {{ {'; '.join(method_lines)} }}"

    elif isinstance(node, ShadowThirstMutation):
        shadow = (
            format_block(node.shadow_block, indent + 2) if node.shadow_block else ""
        )
        invariant = (
            format_block(node.invariant_block, indent + 2)
            if node.invariant_block
            else ""
        )
        canonical = (
            format_block(node.canonical_block, indent + 2)
            if node.canonical_block
            else ""
        )
        parts = []
        if shadow:
            parts.append(
                f"{INDENT * (indent + 1)}shadow {{\n{shadow}\n{INDENT * (indent + 1)}}}"
            )
        if invariant:
            parts.append(
                f"{INDENT * (indent + 1)}invariant {{\n{invariant}\n{INDENT * (indent + 1)}}}"
            )
        if canonical:
            parts.append(
                f"{INDENT * (indent + 1)}canonical {{\n{canonical}\n{INDENT * (indent + 1)}}}"
            )
        body = "\n".join(parts)
        return f"{prefix}mutation {node.name} {{\n{body}\n{prefix}}}"

    return f"{prefix}(unknown node: {type(node).__name__})"


def format_block(node: BlockStmt, indent: int = 0) -> str:
    """Format a block statement."""
    return "\n".join(_format_statements(node.statements, indent))


def format_else_if(node: IfStmt, indent: int = 0) -> str:
    """Format an else-if chain."""
    prefix = INDENT * indent
    cond = format_expr(node.condition, 0)
    then_block = (
        format_block(node.then_block, indent + 1)
        if isinstance(node.then_block, BlockStmt)
        else format_stmt(node.then_block, indent + 1)
    )
    result = f"thirsty ({cond}) {{\n{then_block}\n{prefix}}}"
    if node.else_block:
        if isinstance(node.else_block, IfStmt):
            result += f" hydrated {format_else_if(node.else_block, indent)}"
        else:
            else_block = (
                format_block(node.else_block, indent + 1)
                if isinstance(node.else_block, BlockStmt)
                else format_stmt(node.else_block, indent + 1)
            )
            result += f" hydrated {{\n{else_block}\n{prefix}}}"
    return result


def format_expr(node: Expr, precedence: int = 0) -> str:
    """Format an expression node with optional parenthesization."""
    if isinstance(node, LambdaExpr):
        params = ", ".join(f"{n}: {t}" if t else n for n, t in node.params)
        ret = f" -> {node.return_type}" if node.return_type else ""
        body = (
            format_block(node.body, 1)
            if isinstance(node.body, BlockStmt)
            else format_stmt(node.body, 1)
        )
        return f"glass({params}){ret} {{\n{body}\n}}"
    if isinstance(node, Subscript):
        return f"{format_expr(node.obj, 9)}[{format_expr(node.index, 0)}]"
    if isinstance(node, SliceExpr):
        bounds = [node.start, node.stop]
        if node.step is not None:
            bounds.append(node.step)
        content = ":".join(
            format_expr(bound, 0) if bound is not None else "" for bound in bounds
        )
        return f"{format_expr(node.obj, 9)}[{content}]"
    if isinstance(node, IntLiteral):
        return str(node.value)

    elif isinstance(node, FloatLiteral):
        return str(node.value)

    elif isinstance(node, StringLiteral):
        escaped = (
            node.value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\t", "\\t")
        )
        return f'"{escaped}"'

    elif isinstance(node, BoolLiteral):
        return "true" if node.value else "false"

    elif isinstance(node, NoneLiteral):
        return "none"

    elif isinstance(node, ErrorLiteral):
        return f"error({node.value})"

    elif isinstance(node, QuenchedLiteral):
        val = format_expr(node.value, 0) if node.value else "none"
        return f"quenched({val})"

    elif isinstance(node, Identifier):
        return node.name

    elif isinstance(node, BinaryOp):
        prec_map = {
            TokenType.OR: 3,
            TokenType.AND: 4,
            TokenType.EQEQ: 5,
            TokenType.NE: 5,
            TokenType.LT: 5,
            TokenType.GT: 5,
            TokenType.LE: 5,
            TokenType.GE: 5,
            TokenType.PLUS: 6,
            TokenType.MINUS: 6,
            TokenType.STAR: 7,
            TokenType.SLASH: 7,
            TokenType.PERCENT: 7,
        }
        op_prec = prec_map.get(node.op, 0)
        op_str = {
            TokenType.PLUS: " + ",
            TokenType.MINUS: " - ",
            TokenType.STAR: " * ",
            TokenType.SLASH: " / ",
            TokenType.PERCENT: " % ",
            TokenType.EQEQ: " == ",
            TokenType.NE: " != ",
            TokenType.LT: " < ",
            TokenType.GT: " > ",
            TokenType.LE: " <= ",
            TokenType.GE: " >= ",
            TokenType.AND: " and ",
            TokenType.OR: " or ",
        }.get(node.op, f" {node.op.name.lower()} ")
        left = format_expr(node.left, op_prec)
        right = format_expr(node.right, op_prec + 1)
        result = f"{left}{op_str}{right}"
        if precedence > op_prec:
            result = f"({result})"
        return result

    elif isinstance(node, UnaryOp):
        op_str = "-" if node.op == TokenType.MINUS else "not "
        operator_precedence = 8 if node.op == TokenType.MINUS else 4
        operand = format_expr(node.operand, operator_precedence + 1)
        result = f"{op_str}{operand}"
        if precedence > operator_precedence:
            result = f"({result})"
        return result

    elif isinstance(node, CallExpr):
        callee = format_expr(node.callee, 9)
        args = ", ".join(format_expr(a, 0) for a in node.args)
        return f"{callee}({args})"

    elif isinstance(node, PipeExpr):
        left = format_expr(node.left, 1)
        right = format_expr(node.right, 1)
        result = f"{left} | {right}"
        if precedence > 1:
            result = f"({result})"
        return result

    elif isinstance(node, GuardExpr):
        expr = format_expr(node.expr, 2)
        cond = format_expr(node.condition, 2)
        result = f"thirst {expr} quench {cond}"
        return result

    elif isinstance(node, ArrayLiteral):
        return "[" + ", ".join(format_expr(e, 0) for e in node.elements) + "]"

    elif isinstance(node, DictLiteral):
        return (
            "{"
            + ", ".join(
                f"{format_expr(k, 0)}: {format_expr(v, 0)}" for k, v in node.items
            )
            + "}"
        )

    elif isinstance(node, MemberAccess):
        return f"{format_expr(node.obj, 9)}.{node.member}"

    elif isinstance(node, FloodExpr):
        target = format_expr(node.target, 0)
        return f"flood({target})"

    elif isinstance(node, DripExpr):
        target = format_expr(node.target, 0)
        return f"drip({target})"

    elif isinstance(node, EvaporateExpr):
        target = format_expr(node.target, 0)
        return f"evaporate({target})"

    elif isinstance(node, CondenseExpr):
        target = format_expr(node.target, 0)
        return f"condense({target})"

    elif isinstance(node, NewExpr):
        args = ", ".join(format_expr(a, 0) for a in node.args)
        return f"new {node.class_name}({args})"

    elif isinstance(node, SanitizeExpr):
        return f"sanitize({format_expr(node.expr, 0)})"

    elif isinstance(node, ArmorExpr):
        return f"armor({format_expr(node.expr, 0)})"

    elif isinstance(node, SymbolExpr):
        return f"${node.symbol_name}"

    elif isinstance(node, PipelineExpr):
        left = format_expr(node.left, 1)
        right = format_expr(node.right, 1)
        result = f"{left} -> {right}"
        return result

    elif isinstance(node, CombineExpr):
        op = " ^ " if node.op == "^" else " || "
        left = format_expr(node.left, 1)
        right = format_expr(node.right, 1)
        result = f"{left}{op}{right}"
        return result

    return f"(unknown expr: {type(node).__name__})"


def format(ast: Program) -> str:
    """Top-level format function. Returns formatted source code string."""
    return format_program(ast) + "\n"
