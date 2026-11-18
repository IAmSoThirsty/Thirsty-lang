"""Static effect bound shared by the reference and Node stdout shield."""

from utf.thirsty_lang.ast import (
    BinaryOp,
    BlockStmt,
    CallExpr,
    ExprStmt,
    Identifier,
    IntLiteral,
    PourStmt,
    Program,
    SecurityBlock,
    StringLiteral,
    UnaryOp,
    VariableDecl,
)
from utf.thirsty_lang.token import TokenType


class ShieldProfileError(ValueError):
    def __init__(self, node, message: str):
        super().__init__(message)
        self.span = node.span


def module_shield(program: Program) -> SecurityBlock | None:
    """M1 is a sealed module. Other placements remain unsupported."""
    if (
        not program.parse_failed
        and program.header
        and program.header.mode == "governed"
        and len(program.stmts) == 1
        and type(program.stmts[0]) is SecurityBlock
        and program.stmts[0].block_type == "shield"
    ):
        return program.stmts[0]
    return None


def _local_integer(expr, names: set[str], depth: int = 0) -> bool:
    if depth > 8:
        return False
    if type(expr) is IntLiteral:
        return type(expr.value) is int and expr.value.bit_length() <= 64
    if type(expr) is Identifier:
        return expr.name in names
    if type(expr) is UnaryOp and expr.op is TokenType.MINUS:
        return _local_integer(expr.operand, names, depth + 1)
    return (
        type(expr) is BinaryOp
        and expr.op in (TokenType.PLUS, TokenType.MINUS)
        and _local_integer(expr.left, names, depth + 1)
        and _local_integer(expr.right, names, depth + 1)
    )


def public_record(stmt: PourStmt) -> str:
    from utf.thirsty_lang.shield import MAX_RECORD_BYTES

    if type(stmt.value) is not StringLiteral or type(stmt.value.value) is not str:
        raise ShieldProfileError(
            stmt, "shield stdout requires a fixed public string literal"
        )
    text = stmt.value.value
    try:
        if (
            len(text) >= MAX_RECORD_BYTES
            or len(text.encode("utf-8")) + 1 > MAX_RECORD_BYTES
        ):
            raise ShieldProfileError(
                stmt, "shield stdout record exceeds the byte limit"
            )
    except UnicodeEncodeError as error:
        raise ShieldProfileError(stmt, "invalid UTF-8 shield record") from error
    return text


def checked_body(block: SecurityBlock) -> BlockStmt:
    """Accept only closed integer calculations, literal output and holder surrender."""
    if type(block.body) is not BlockStmt or len(block.body.statements) > 64:
        raise ShieldProfileError(
            block, "shield requires a block of at most 64 statements"
        )
    names: set[str] = set()
    for stmt in block.body.statements:
        if type(stmt) is VariableDecl:
            if (
                stmt.is_mut
                or stmt.var_type not in (None, "Int")
                or stmt.name in ("surrender", "__error__")
                or len(stmt.name) > 128
                or stmt.name in names
                or not _local_integer(stmt.init_expr, names)
            ):
                raise ShieldProfileError(
                    stmt,
                    "shield local requires a fresh immutable Int and a bounded local integer expression",
                )
            names.add(stmt.name)
        elif type(stmt) is PourStmt:
            public_record(stmt)
        elif (
            type(stmt) is ExprStmt
            and type(stmt.expr) is CallExpr
            and type(stmt.expr.callee) is Identifier
            and stmt.expr.callee.name == "surrender"
            and not stmt.expr.args
        ):
            continue
        else:
            raise ShieldProfileError(
                stmt, "operation outside the stdout shield effect bound"
            )
    return block.body
