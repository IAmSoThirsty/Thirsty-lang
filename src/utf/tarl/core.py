"""
T.A.R.L. Core — Phase 1+2: Condition Algebra and Policy Parser

Phase 1 — SafeExpr supports:
  - Nested attribute access: user.role.clearance
  - Full arithmetic: +, -, *, /, %
  - Set membership: value IN [...] / NOT IN [...]
  - Dynamic sources: source:name (resolved by TarlRuntime)
  - Temporal builtins: CURRENT_HOUR, CURRENT_DAY, CURRENT_WEEKDAY, etc.
  - String predicates: MATCHES, STARTS_WITH, ENDS_WITH, CONTAINS
  - Utility functions: LEN, LOWER, UPPER, ELAPSED_SINCE
  - Universal/existential quantifiers: ALL(col, v -> cond), ANY(...)

Phase 2 — PolicyParser supports:
  - EXTENDS / RESTRICTS composition
  - INCLUDE <name>|"<file>" [AS <alias>]
  - STOP keyword (blocks parent fallthrough in EXTENDS)
  - policy_set with combine UNION|INTERSECT|MAJORITY [...]
  - Temporal versioning stubs: valid_from, valid_until, supersedes, on_expiry
  - parse_all() for multi-policy files
"""

import datetime
import math
import re
from typing import Any, Optional

from utf.tarl.context import (
    ContextResolutionError,
    ContextResolutionState,
    PreparedContext,
    canonical_context_bytes,
    prepare_context,
    resolve_context_path,
)
from utf.tarl.spec import (
    DEFAULT_DENY,
    CompositionOp,
    SetOp,
    TarlDecision,
    TarlPolicy,
    TarlPolicyRef,
    TarlPolicySet,
    TarlRule,
    TarlVerdict,
)

# ── Token types ──────────────────────────────────────────────────────────────
INT = "INT"
FLOAT = "FLOAT"
STRING = "STRING"
BOOL_TRUE = "BOOL_TRUE"
BOOL_FALSE = "BOOL_FALSE"
IDENT = "IDENT"
SOURCE = "SOURCE"  # source:name — resolved by runtime
# Arithmetic
PLUS = "PLUS"
MINUS = "MINUS"
STAR = "STAR"
SLASH = "SLASH"
PERCENT = "PERCENT"
# Comparisons
EQEQ = "EQEQ"
NE = "NE"
LT = "LT"
GT = "GT"
LE = "LE"
GE = "GE"
# Logic
AND = "AND"
OR = "OR"
NOT = "NOT"
IN = "IN"
# Structure
DOT = "DOT"
COMMA = "COMMA"
ARROW = "ARROW"  # ->
LBRACKET = "LBRACKET"
RBRACKET = "RBRACKET"
LPAREN = "LPAREN"
RPAREN = "RPAREN"
EOF = "EOF"

_KEYWORDS = {
    "and": AND,
    "or": OR,
    "not": NOT,
    "in": IN,
    "true": BOOL_TRUE,
    "false": BOOL_FALSE,
}

_TEMPORAL_BUILTINS = frozenset(
    {
        "CURRENT_HOUR",
        "CURRENT_DAY",
        "CURRENT_WEEKDAY",
        "CURRENT_MONTH",
        "CURRENT_YEAR",
        "CURRENT_TIMESTAMP",
    }
)

_SAFE_FUNCTIONS = frozenset(
    {
        "MATCHES",
        "STARTS_WITH",
        "ENDS_WITH",
        "CONTAINS",
        "ELAPSED_SINCE",
        "LEN",
        "LOWER",
        "UPPER",
    }
)

_QUANTIFIERS = frozenset({"ALL", "ANY"})
_TRUSTED_NOW_KEY = "__tarl_trusted_now"


class ConditionTypeError(ContextResolutionError):
    """A condition could not be evaluated in a well-typed way."""

    def __init__(self, message: str) -> None:
        super().__init__(
            f"condition type error: {message}",
            state=ContextResolutionState.TYPE_ERROR,
        )


class ExprToken:
    __slots__ = ("type", "value", "pos")

    def __init__(self, type: str, value, pos: int = 0):
        self.type = type
        self.value = value
        self.pos = pos

    def __repr__(self) -> str:
        return f"ExprToken({self.type}, {self.value!r})"


def _strip_policy_comment(line: str) -> str:
    """Remove an inline TARL comment without touching quoted string data."""
    quote: str | None = None
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote is not None:
            escaped = True
            continue
        if char in {'"', "'"}:
            quote = None if quote == char else char if quote is None else quote
            continue
        if quote is None and (char == "#" or line[index : index + 2] == "//"):
            return line[:index]
    return line


class PolicyParser:
    """Parses TARL policy text into TarlPolicy / TarlPolicySet objects."""

    RULE_RE = re.compile(
        r"when\s+(.+?)\s*=>\s*(ALLOW|DENY|ESCALATE)" r"(?:\s+for:\s*(\S+))?\s*$"
    )
    # policy <name> [EXTENDS|RESTRICTS <parent>] [v<ver>] [:]
    POLICY_HEADER_RE = re.compile(
        r"policy\s+(\w+)"
        r"(?:\s+(EXTENDS|RESTRICTS)\s+(\w+))?"
        r"(?:\s+v([\w.]+))?"
        r"\s*:?"
    )
    POLICY_SET_HEADER_RE = re.compile(r"policy_set\s+(\w+)\s*:")
    # INCLUDE "path/to/file.tarl" AS alias
    # INCLUDE policy_name AS alias
    INCLUDE_RE = re.compile(r'INCLUDE\s+(?:"([^"]+)"|(\w+))' r"(?:\s+AS\s+(\w+))?")
    # combine UNION|INTERSECT|MAJORITY [p1, p2, ...]
    COMBINE_RE = re.compile(r"combine\s+(UNION|INTERSECT|MAJORITY)\s+\[([^\]]+)\]")
    # default: ALLOW|DENY|ESCALATE
    DEFAULT_RE = re.compile(r"default\s*:\s*(ALLOW|DENY|ESCALATE)")
    # valid_from|valid_until|supersedes|on_expiry: <value>
    METADATA_RE = re.compile(
        r"(valid_from|valid_until|supersedes|on_expiry)\s*:\s*(.+)"
    )
    # if_unresolved_after: <duration> => revert_to: <policy_name>
    IF_UNRESOLVED_RE = re.compile(
        r"if_unresolved_after:\s*(\S+)\s*=>\s*revert_to:\s*(\w+)"
    )

    @classmethod
    def parse_all(cls, text: str) -> list:
        """
        Parse text containing one or more policy/policy_set blocks.
        Returns a list of TarlPolicy and TarlPolicySet objects.
        Bare rules (no policy header) accumulate into an 'unnamed' policy.
        """
        results: list[Any] = []
        current_policy: TarlPolicy | None = None
        current_set: TarlPolicySet | None = None

        def _flush():
            nonlocal current_policy, current_set
            if current_policy is not None:
                try:
                    _policy_temporal_bounds(current_policy)
                except ConditionTypeError as exc:
                    raise SafeExpr.ParseError(
                        f"invalid temporal policy metadata: {exc}"
                    ) from exc
                results.append(current_policy)
                current_policy = None
            if current_set is not None:
                results.append(current_set)
                current_set = None

        for lineno, raw_line in enumerate(text.split("\n"), start=1):
            line = _strip_policy_comment(raw_line).strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue

            # ── policy_set header ─────────────────────────────────────────
            m_ps = cls.POLICY_SET_HEADER_RE.match(line)
            if m_ps:
                _flush()
                current_set = TarlPolicySet(name=m_ps.group(1))
                continue

            # ── policy header ─────────────────────────────────────────────
            m_ph = cls.POLICY_HEADER_RE.match(line)
            if m_ph:
                _flush()
                current_policy = TarlPolicy(source=line, name=m_ph.group(1))
                if m_ph.group(2):
                    current_policy.composition = CompositionOp(m_ph.group(2))
                    current_policy.parent = m_ph.group(3)
                if m_ph.group(4):
                    current_policy.version = m_ph.group(4)
                continue

            # ── policy_set body ───────────────────────────────────────────
            if current_set is not None:
                m_combine = cls.COMBINE_RE.match(line)
                if m_combine:
                    op = SetOp(m_combine.group(1))
                    names = [
                        n.strip() for n in m_combine.group(2).split(",") if n.strip()
                    ]
                    current_set.groups.append((op, names))
                    continue
                m_def = cls.DEFAULT_RE.match(line)
                if m_def:
                    current_set.default_verdict = TarlVerdict(m_def.group(1))
                continue

            # ── policy body ───────────────────────────────────────────────
            if current_policy is None:
                current_policy = TarlPolicy(source="", name="unnamed")

            if line == "STOP":
                current_policy.has_stop = True
                continue

            m_inc = cls.INCLUDE_RE.match(line)
            if m_inc:
                file_path = m_inc.group(1)
                pol_name = m_inc.group(2)
                alias = m_inc.group(3)
                ref = TarlPolicyRef(
                    name=file_path if file_path else pol_name,
                    alias=alias,
                    is_file=bool(file_path),
                )
                current_policy.includes.append(ref)
                continue

            m_iu = cls.IF_UNRESOLVED_RE.match(line)
            if m_iu:
                dur = _parse_duration(m_iu.group(1))
                if dur is None:
                    raise SafeExpr.ParseError(
                        f"line {lineno}: invalid if_unresolved_after duration"
                    )
                current_policy.if_unresolved_after = dur
                current_policy.revert_to = m_iu.group(2)
                continue
            if line.startswith("if_unresolved_after"):
                raise SafeExpr.ParseError(
                    f"line {lineno}: malformed if_unresolved_after directive"
                )

            m_meta = cls.METADATA_RE.match(line)
            if m_meta:
                key, val = m_meta.group(1), m_meta.group(2).strip()
                if key == "valid_from":
                    try:
                        _parse_policy_timestamp(val, key)
                    except ConditionTypeError as exc:
                        raise SafeExpr.ParseError(f"line {lineno}: {exc}") from exc
                    current_policy.valid_from = val
                elif key == "valid_until":
                    try:
                        _parse_policy_timestamp(val, key)
                    except ConditionTypeError as exc:
                        raise SafeExpr.ParseError(f"line {lineno}: {exc}") from exc
                    current_policy.valid_until = val
                elif key == "supersedes":
                    current_policy.supersedes = val
                elif key == "on_expiry":
                    try:
                        expiry_verdict = TarlVerdict(val.upper())
                    except ValueError as exc:
                        raise SafeExpr.ParseError(
                            f"line {lineno}: invalid on_expiry verdict {val!r}"
                        ) from exc
                    if expiry_verdict is TarlVerdict.ALLOW:
                        raise SafeExpr.ParseError(
                            f"line {lineno}: on_expiry cannot grant ALLOW"
                        )
                    current_policy.on_expiry = expiry_verdict
                continue
            if line.startswith(("valid_from", "valid_until", "on_expiry")):
                raise SafeExpr.ParseError(
                    f"line {lineno}: malformed temporal metadata directive"
                )

            m_rule = cls.RULE_RE.match(line)
            if m_rule:
                condition = m_rule.group(1).strip()
                cls.validate_condition(condition)
                verdict = TarlVerdict(m_rule.group(2).upper())
                duration = _parse_duration(m_rule.group(3)) if m_rule.group(3) else None
                if m_rule.group(3) and duration is None:
                    raise SafeExpr.ParseError(
                        f"line {lineno}: invalid rule duration " f"{m_rule.group(3)!r}"
                    )
                current_policy.rules.append(
                    TarlRule(
                        condition=condition,
                        verdict=verdict,
                        source_line=lineno,
                        duration_seconds=duration,
                    )
                )
                continue
            if line.startswith("when "):
                raise SafeExpr.ParseError(f"line {lineno}: malformed policy rule")

        _flush()
        return results

    @classmethod
    def validate_condition(cls, condition: str) -> None:
        """Parse a rule condition early so malformed policies fail closed."""
        tokens = cls._tokenize(condition)
        parser = SafeExpr(tokens)
        parser.parse_expr()
        if parser.current().type != EOF:
            raise SafeExpr.ParseError(f"Unexpected token: {parser.current()}")

    @classmethod
    def parse(cls, text: str, name: str = "unnamed") -> TarlPolicy:
        """
        Parse text and return the first TarlPolicy found.
        Backward-compatible: name is used when no policy header is present.
        """
        items = cls.parse_all(text)
        for item in items:
            if isinstance(item, TarlPolicy):
                if item.name == "unnamed" and name != "unnamed":
                    item.name = name
                item.source = text  # full source for proof hashing
                return item
        return TarlPolicy(source=text, name=name)

    @staticmethod
    def _tokenize(expr: str) -> list:
        tokens = []
        i = 0
        n = len(expr)
        while i < n:
            c = expr[i]

            # Whitespace
            if c in " \t":
                i += 1
                continue

            # Parentheses, brackets, comma
            if c == "(":
                tokens.append(ExprToken(LPAREN, "(", i))
                i += 1
            elif c == ")":
                tokens.append(ExprToken(RPAREN, ")", i))
                i += 1
            elif c == "[":
                tokens.append(ExprToken(LBRACKET, "[", i))
                i += 1
            elif c == "]":
                tokens.append(ExprToken(RBRACKET, "]", i))
                i += 1
            elif c == ",":
                tokens.append(ExprToken(COMMA, ",", i))
                i += 1
            elif c == ".":
                tokens.append(ExprToken(DOT, ".", i))
                i += 1

            # Two-char operators
            elif c == "=" and i + 1 < n and expr[i + 1] == "=":
                tokens.append(ExprToken(EQEQ, "==", i))
                i += 2
            elif c == "!" and i + 1 < n and expr[i + 1] == "=":
                tokens.append(ExprToken(NE, "!=", i))
                i += 2
            elif c == "<" and i + 1 < n and expr[i + 1] == "=":
                tokens.append(ExprToken(LE, "<=", i))
                i += 2
            elif c == ">" and i + 1 < n and expr[i + 1] == "=":
                tokens.append(ExprToken(GE, ">=", i))
                i += 2
            elif c == "-" and i + 1 < n and expr[i + 1] == ">":
                tokens.append(ExprToken(ARROW, "->", i))
                i += 2

            # Single-char comparison / arithmetic
            elif c == "<":
                tokens.append(ExprToken(LT, "<", i))
                i += 1
            elif c == ">":
                tokens.append(ExprToken(GT, ">", i))
                i += 1
            elif c == "+":
                tokens.append(ExprToken(PLUS, "+", i))
                i += 1
            elif c == "*":
                tokens.append(ExprToken(STAR, "*", i))
                i += 1
            elif c == "/":
                tokens.append(ExprToken(SLASH, "/", i))
                i += 1
            elif c == "%":
                tokens.append(ExprToken(PERCENT, "%", i))
                i += 1

            # Minus or negative number literal
            elif c == "-":
                nxt = expr[i + 1] if i + 1 < n else ""
                if nxt.isdigit():
                    start = i
                    i += 1
                    is_float = False
                    while i < n and (expr[i].isdigit() or expr[i] == "."):
                        if expr[i] == ".":
                            is_float = True
                        i += 1
                    s = expr[start:i]
                    tokens.append(
                        ExprToken(
                            FLOAT if is_float else INT,
                            float(s) if is_float else int(s),
                            start,
                        )
                    )
                else:
                    tokens.append(ExprToken(MINUS, "-", i))
                    i += 1

            # String literals
            elif c == '"':
                i += 1
                chars = []
                while i < n and expr[i] != '"':
                    if expr[i] == "\\" and i + 1 < n:
                        i += 1
                        chars.append(
                            {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}.get(
                                expr[i], expr[i]
                            )
                        )
                    else:
                        chars.append(expr[i])
                    i += 1
                i += 1
                tokens.append(ExprToken(STRING, "".join(chars), i))
            elif c == "'":
                i += 1
                chars = []
                while i < n and expr[i] != "'":
                    chars.append(expr[i])
                    i += 1
                i += 1
                tokens.append(ExprToken(STRING, "".join(chars), i))

            # Number literals
            elif c.isdigit():
                start = i
                is_float = False
                while i < n and (expr[i].isdigit() or expr[i] == "."):
                    if expr[i] == ".":
                        is_float = True
                    i += 1
                s = expr[start:i]
                tokens.append(
                    ExprToken(
                        FLOAT if is_float else INT,
                        float(s) if is_float else int(s),
                        start,
                    )
                )

            # Identifiers and keywords
            elif c.isalpha() or c == "_":
                start = i
                while i < n and (expr[i].isalnum() or expr[i] == "_"):
                    i += 1
                word = expr[start:i]

                # source:name — no whitespace allowed between source and :
                if word == "source" and i < n and expr[i] == ":":
                    i += 1
                    src_start = i
                    while i < n and (expr[i].isalnum() or expr[i] == "_"):
                        i += 1
                    tokens.append(ExprToken(SOURCE, expr[src_start:i], start))
                    continue

                word_lower = word.lower()
                if word_lower in _KEYWORDS:
                    ktype = _KEYWORDS[word_lower]
                    val = (
                        True
                        if ktype == BOOL_TRUE
                        else (False if ktype == BOOL_FALSE else word_lower)
                    )
                    tokens.append(ExprToken(ktype, val, start))
                else:
                    tokens.append(ExprToken(IDENT, word, start))

            else:
                raise ValueError(f"Unexpected character {c!r} at position {i}")

        tokens.append(ExprToken(EOF, None, i))
        return tokens


# ── Duration parsing / temporal utilities ────────────────────────────────────


def _parse_duration(s: str) -> int | None:
    """
    Parse a human-readable duration string into seconds.
    Supports units: s (seconds), m (minutes), h (hours), d (days), w (weeks).
    Compound forms like '1h30m' are supported. Returns None on parse error.

    Examples: '4h' → 14400, '30m' → 1800, '1d' → 86400, '1h30m' → 5400
    """
    if not s:
        return None
    units = {"w": 604800, "d": 86400, "h": 3600, "m": 60, "s": 1}
    total = 0
    num = ""
    for ch in s.strip():
        if ch.isdigit():
            num += ch
        elif ch in units:
            if not num:
                return None
            total += int(num) * units[ch]
            num = ""
        else:
            return None
    if num:  # trailing digits without unit → seconds
        total += int(num)
    return total if total > 0 else None


def _parse_policy_timestamp(value: object, field: str) -> datetime.datetime:
    """Parse a policy timestamp, preserving the documented UTC date shorthand."""
    if not isinstance(value, str) or not value.strip():
        raise ConditionTypeError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ConditionTypeError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.UTC)
    if parsed.utcoffset() is None:
        raise ConditionTypeError(f"{field} timezone is invalid")
    return parsed.astimezone(datetime.UTC)


def _policy_temporal_bounds(
    policy: "TarlPolicy",
) -> tuple[datetime.datetime | None, datetime.datetime | None]:
    """Return the validated inclusive start and exclusive authority cutoff."""
    if policy.on_expiry is TarlVerdict.ALLOW:
        raise ConditionTypeError("on_expiry cannot grant ALLOW")
    if policy.on_expiry is not None and not isinstance(policy.on_expiry, TarlVerdict):
        raise ConditionTypeError("on_expiry must be DENY or ESCALATE")
    for rule in policy.rules:
        duration = rule.duration_seconds
        if duration is not None and (
            isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0
        ):
            raise ConditionTypeError("rule duration must be positive")

    valid_from = (
        _parse_policy_timestamp(policy.valid_from, "valid_from")
        if policy.valid_from is not None
        else None
    )
    effective_until = (
        _parse_policy_timestamp(policy.valid_until, "valid_until")
        if policy.valid_until is not None
        else None
    )

    if policy.if_unresolved_after is not None:
        duration = policy.if_unresolved_after
        if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
            raise ConditionTypeError("if_unresolved_after must be a positive duration")
        if valid_from is None:
            raise ConditionTypeError("if_unresolved_after requires valid_from")
        try:
            succession_at = valid_from + datetime.timedelta(seconds=duration)
        except OverflowError as exc:
            raise ConditionTypeError(
                "if_unresolved_after exceeds the datetime range"
            ) from exc
        if effective_until is None or succession_at < effective_until:
            effective_until = succession_at

    return valid_from, effective_until


def _policy_authority_expiry(
    policy: "TarlPolicy",
    rule: "TarlRule",
    evaluated_at: datetime.datetime,
) -> datetime.datetime | None:
    """Return the earliest rule or policy cutoff for a matched verdict."""
    evaluated_at = _coerce_datetime(evaluated_at)
    _valid_from, effective_until = _policy_temporal_bounds(policy)
    candidates: list[datetime.datetime] = []
    if effective_until is not None:
        candidates.append(effective_until)
    if rule.duration_seconds is not None:
        duration = rule.duration_seconds
        if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
            raise ConditionTypeError("rule duration must be positive")
        try:
            candidates.append(evaluated_at + datetime.timedelta(seconds=duration))
        except OverflowError as exc:
            raise ConditionTypeError(
                "rule duration exceeds the datetime range"
            ) from exc
    return min(candidates) if candidates else None


def _check_policy_temporal(
    policy: "TarlPolicy",
    now: "datetime.datetime | None" = None,
) -> Optional["TarlDecision"]:
    """
    Check whether a policy is within its declared effective time window.

    ``now`` lets a caller supply a **trusted** time (e.g. a verified signed-time
    source) instead of the host clock, so a spoofed system clock cannot satisfy a
    temporal window (C043). Defaults to ``datetime.now(UTC)``.

    Returns a TarlDecision when the policy is outside its window (not-yet-active
    or expired/auto-expired), using policy.on_expiry or ESCALATE as the verdict.
    Returns None when the policy is in-window and should be evaluated normally.
    """
    if now is None:
        now = datetime.datetime.now(datetime.UTC)
    else:
        try:
            now = _coerce_datetime(now)
        except ConditionTypeError as exc:
            return TarlDecision(
                verdict=TarlVerdict.DENY,
                reason=f"fail-closed: {exc}",
            )
    try:
        valid_from, effective_until = _policy_temporal_bounds(policy)
    except ConditionTypeError as exc:
        return TarlDecision(
            verdict=TarlVerdict.DENY,
            reason=f"fail-closed: invalid temporal policy metadata: {exc}",
        )
    expiry_verdict = policy.on_expiry or TarlVerdict.ESCALATE

    # Not-yet-active check
    if valid_from is not None and now < valid_from:
        return TarlDecision(
            verdict=expiry_verdict,
            reason=(
                f"Policy '{policy.name}' not yet effective "
                f"(valid_from: {policy.valid_from})"
            ),
        )

    if effective_until is not None and now >= effective_until:
        return TarlDecision(
            verdict=expiry_verdict,
            reason=(
                f"Policy '{policy.name}' expired "
                f"(effective until: {effective_until.isoformat()})"
            ),
        )

    return None


# ── Temporal builtins ────────────────────────────────────────────────────────


def _coerce_datetime(now: Any) -> datetime.datetime:
    if isinstance(now, datetime.datetime):
        parsed = now
    elif isinstance(now, str):
        try:
            parsed = datetime.datetime.fromisoformat(now.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ConditionTypeError(f"invalid trusted clock value {now!r}") from exc
    else:
        raise ConditionTypeError(f"invalid trusted clock value {now!r}")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ConditionTypeError("trusted clock value must be timezone-aware")
    return parsed.astimezone(datetime.UTC)


def _resolve_temporal(name: str, now: Any | None = None):
    current = (
        _coerce_datetime(now)
        if now is not None
        else datetime.datetime.now(datetime.UTC)
    )
    return {
        "CURRENT_HOUR": current.hour,
        "CURRENT_DAY": current.day,
        "CURRENT_WEEKDAY": current.strftime("%A").upper(),
        "CURRENT_MONTH": current.month,
        "CURRENT_YEAR": current.year,
        "CURRENT_TIMESTAMP": current.isoformat(),
    }.get(name, False)


# ── Safe built-in functions ──────────────────────────────────────────────────


def _call_safe_function(
    name: str,
    args: list,
    now: datetime.datetime | str | None = None,
):
    try:
        if name == "MATCHES":
            _require_string_args(name, args, 2)
            return bool(re.search(args[1], args[0]))
        if name == "STARTS_WITH":
            _require_string_args(name, args, 2)
            return args[0].startswith(args[1])
        if name == "ENDS_WITH":
            _require_string_args(name, args, 2)
            return args[0].endswith(args[1])
        if name == "CONTAINS":
            _require_string_args(name, args, 2)
            return args[1] in args[0]
        if name == "LEN":
            if len(args) != 1:
                raise ConditionTypeError(f"LEN expected 1 argument, got {len(args)}")
            v = args[0]
            if not isinstance(v, (str, list, dict, set)):
                raise ConditionTypeError(
                    f"LEN expected string or collection, got {type(v).__name__}"
                )
            return len(v)
        if name == "LOWER":
            _require_string_args(name, args, 1)
            return args[0].lower()
        if name == "UPPER":
            _require_string_args(name, args, 1)
            return args[0].upper()
        if name == "ELAPSED_SINCE":
            _require_string_args(name, args, 1)
            past = datetime.datetime.fromisoformat(args[0])
            current = (
                _coerce_datetime(now)
                if now is not None
                else datetime.datetime.now(tz=past.tzinfo)
            )
            return (current - past).total_seconds()
    except ConditionTypeError:
        raise
    except (IndexError, ValueError, TypeError, AttributeError, re.error) as exc:
        raise ConditionTypeError(f"{name} could not be evaluated: {exc}") from exc
    raise ConditionTypeError(f"unknown safe function {name}")


def _require_string_args(name: str, args: list, count: int) -> None:
    if len(args) != count:
        raise ConditionTypeError(
            f"{name} expected {count} argument(s), got {len(args)}"
        )
    for index, value in enumerate(args):
        if not isinstance(value, str):
            raise ConditionTypeError(
                f"{name} argument {index + 1} expected string, "
                f"got {type(value).__name__}"
            )


def _require_boolean(value: Any, operation: str) -> bool:
    if not isinstance(value, bool):
        raise ConditionTypeError(
            f"{operation} expected bool, got {type(value).__name__}"
        )
    return value


def _require_numeric(value: Any, operation: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConditionTypeError(
            f"{operation} expected number, got {type(value).__name__}"
        )
    if isinstance(value, float) and not math.isfinite(value):
        raise ConditionTypeError(f"{operation} received a non-finite number")
    return value


def _require_finite_result(value: int | float, operation: str) -> int | float:
    if isinstance(value, float) and not math.isfinite(value):
        raise ConditionTypeError(f"{operation} produced a non-finite arithmetic result")
    return value


def _strict_membership(value: Any, collection: list | set | frozenset) -> bool:
    matched = False
    for item in collection:
        try:
            left, right = _coerce_equatable(value, item)
        except ConditionTypeError as exc:
            raise ConditionTypeError(
                f"membership collection contains an incompatible "
                f"{type(item).__name__} value"
            ) from exc
        if _strict_expression_equal(left, right):
            matched = True
    return matched


def _strict_expression_equal(left: Any, right: Any) -> bool:
    """Compare coerced values without Python's nested bool/int equivalence."""
    if isinstance(left, (list, dict)):
        return canonical_context_bytes(left) == canonical_context_bytes(right)
    return bool(left == right)


# ── Expression evaluator ─────────────────────────────────────────────────────


class SafeExpr:
    """
    Sandboxed condition algebra evaluator.

    Grammar (precedence low → high):
      expr         := and_expr  (OR and_expr)*
      and_expr     := not_expr  (AND not_expr)*
      not_expr     := NOT not_expr | comparison
      comparison   := additive  [(==|!=|<|>|<=|>=) additive |
                                  [NOT] IN in_rhs]
      additive     := multiplicative  ((+|-) multiplicative)*
      multiplicative := unary  ((*|/|%) unary)*
      unary        := -unary | primary
      primary      := literal | ident_or_call | (expr) | inline_set
    """

    class ParseError(Exception):
        pass

    @classmethod
    def evaluate(
        cls,
        expr,
        context: dict | PreparedContext,
        now: datetime.datetime | None = None,
    ) -> bool:
        tokens = PolicyParser._tokenize(expr) if isinstance(expr, str) else expr
        parser = cls(tokens)
        result = parser.parse_expr()
        if parser.current().type != EOF:
            raise cls.ParseError(f"Unexpected token: {parser.current()}")
        prepared = (
            context
            if isinstance(context, PreparedContext)
            else prepare_context(context)
        )
        eval_context = dict(prepared.canonical)
        if now is not None:
            eval_context[_TRUSTED_NOW_KEY] = now
        return _require_boolean(
            cls._eval_node(result, eval_context), "condition result"
        )

    def __init__(self, tokens: list[ExprToken]):
        self.tokens = tokens
        self.pos = 0

    def current(self) -> ExprToken:
        return (
            self.tokens[self.pos]
            if self.pos < len(self.tokens)
            else ExprToken(EOF, None)
        )

    def _peek(self) -> ExprToken:
        p = self.pos + 1
        return self.tokens[p] if p < len(self.tokens) else ExprToken(EOF, None)

    def advance(self) -> ExprToken:
        tok = self.current()
        self.pos += 1
        return tok

    def expect(self, *types) -> ExprToken:
        tok = self.current()
        if tok.type not in types:
            raise self.ParseError(f"Expected {types}, got {tok.type}({tok.value!r})")
        return self.advance()

    # or
    def parse_expr(self):
        left = self.parse_and_expr()
        while self.current().type == OR:
            self.advance()
            left = ("or", left, self.parse_and_expr())
        return left

    # and
    def parse_and_expr(self):
        left = self.parse_not_expr()
        while self.current().type == AND:
            self.advance()
            left = ("and", left, self.parse_not_expr())
        return left

    # unary not  (NOT IN is handled in parse_comparison, not here)
    def parse_not_expr(self):
        if self.current().type == NOT and self._peek().type != IN:
            self.advance()
            return ("not", self.parse_not_expr())
        return self.parse_comparison()

    # ==, !=, <, >, <=, >=, IN, NOT IN
    def parse_comparison(self):
        left = self.parse_additive()
        cur = self.current()

        if cur.type == NOT and self._peek().type == IN:
            self.advance()
            self.advance()
            return ("not_in", left, self._parse_in_rhs())

        if cur.type == IN:
            self.advance()
            return ("in", left, self._parse_in_rhs())

        if cur.type in (EQEQ, NE, LT, GT, LE, GE):
            op = cur.type
            self.advance()
            return ("compare", op, left, self.parse_additive())

        return left

    def _parse_in_rhs(self):
        tok = self.current()
        if tok.type == LBRACKET:
            return self._parse_inline_set()
        if tok.type == SOURCE:
            return ("source", self.advance().value)
        if tok.type == IDENT:
            return ("ident", self.advance().value)
        raise self.ParseError(
            f"Expected set, source, or identifier after IN; got {tok}"
        )

    def _parse_inline_set(self):
        self.expect(LBRACKET)
        items = []
        while self.current().type not in (RBRACKET, EOF):
            items.append(self.parse_primary())
            if self.current().type == COMMA:
                self.advance()
        self.expect(RBRACKET)
        return ("set", items)

    # +, -
    def parse_additive(self):
        left = self.parse_multiplicative()
        while self.current().type in (PLUS, MINUS):
            op = self.advance().type
            right = self.parse_multiplicative()
            left = ("add", left, right) if op == PLUS else ("sub", left, right)
        return left

    # *, /, %
    def parse_multiplicative(self):
        left = self.parse_unary()
        while self.current().type in (STAR, SLASH, PERCENT):
            op = self.advance().type
            right = self.parse_unary()
            if op == STAR:
                left = ("mul", left, right)
            elif op == SLASH:
                left = ("div", left, right)
            else:
                left = ("mod", left, right)
        return left

    # unary minus
    def parse_unary(self):
        if self.current().type == MINUS:
            self.advance()
            return ("neg", self.parse_primary())
        return self.parse_primary()

    # literals, identifiers, calls, dot-access, quantifiers, sets
    def parse_primary(self):
        tok = self.current()

        if tok.type == LPAREN:
            self.advance()
            expr = self.parse_expr()
            self.expect(RPAREN)
            return expr

        if tok.type == LBRACKET:
            return self._parse_inline_set()

        if tok.type == INT:
            return ("int", self.advance().value)
        if tok.type == FLOAT:
            return ("float", self.advance().value)
        if tok.type == STRING:
            return ("string", self.advance().value)
        if tok.type == BOOL_TRUE:
            self.advance()
            return ("bool", True)
        if tok.type == BOOL_FALSE:
            self.advance()
            return ("bool", False)
        if tok.type == SOURCE:
            return ("source", self.advance().value)

        if tok.type == IDENT:
            name = self.advance().value

            # Function call or quantifier: NAME(...)
            if self.current().type == LPAREN:
                self.advance()  # consume (
                upper = name.upper()
                if upper in _QUANTIFIERS:
                    return self._parse_quantifier_body(upper)
                return self._parse_function_body(name)

            # Dot-access chain: a.b.c
            parts = [name]
            while self.current().type == DOT and self._peek().type == IDENT:
                self.advance()  # DOT
                parts.append(self.advance().value)  # IDENT

            if len(parts) == 1:
                return ("ident", name)
            return ("attr", parts)

        raise self.ParseError(f"Unexpected token: {tok}")

    def _parse_function_body(self, name: str):
        """Parse arg1, arg2, ...) — opening ( already consumed."""
        args = []
        while self.current().type not in (RPAREN, EOF):
            args.append(self.parse_expr())
            if self.current().type == COMMA:
                self.advance()
        self.expect(RPAREN)
        return ("call", name.upper(), args)

    def _parse_quantifier_body(self, quantifier: str):
        """Parse collection, var -> condition) — opening ( already consumed."""
        collection = self.parse_expr()
        self.expect(COMMA)
        if self.current().type != IDENT:
            raise self.ParseError(f"Expected lambda variable in {quantifier}(...)")
        var = self.advance().value
        if var.startswith("__tarl_"):
            raise self.ParseError(
                f"Reserved lambda variable in {quantifier}(...): {var}"
            )
        self.expect(ARROW)
        condition = self.parse_expr()
        self.expect(RPAREN)
        return (quantifier.lower(), collection, var, condition)

    # ── Evaluator ────────────────────────────────────────────────────────────

    @staticmethod
    def _eval_node(node, context: dict):
        if not isinstance(node, tuple):
            return bool(node)
        tag = node[0]

        # Literals
        if tag in ("int", "float", "bool", "string"):
            return node[1]

        # Simple identifier: temporal builtin or context lookup
        if tag == "ident":
            name = node[1]
            if name in _TEMPORAL_BUILTINS:
                return _resolve_temporal(name, context.get(_TRUSTED_NOW_KEY))
            return resolve_context_path(context, [name]).require_value()

        # Dot-access: missing/invalid is not the ordinary boolean value False.
        if tag == "attr":
            return resolve_context_path(context, node[1]).require_value()

        # Dynamic source (list injected by TarlRuntime as "source:<name>")
        if tag == "source":
            source_name = f"source:{node[1]}"
            return resolve_context_path(context, [source_name]).require_value()

        # Inline set: list of evaluated items
        if tag == "set":
            return [SafeExpr._eval_node(item, context) for item in node[1]]

        # Arithmetic
        ev = SafeExpr._eval_node
        if tag == "add":
            left = _require_numeric(ev(node[1], context), "addition")
            right = _require_numeric(ev(node[2], context), "addition")
            return _require_finite_result(left + right, "addition")
        if tag == "sub":
            left = _require_numeric(ev(node[1], context), "subtraction")
            right = _require_numeric(ev(node[2], context), "subtraction")
            return _require_finite_result(left - right, "subtraction")
        if tag == "mul":
            left = _require_numeric(ev(node[1], context), "multiplication")
            right = _require_numeric(ev(node[2], context), "multiplication")
            return _require_finite_result(left * right, "multiplication")
        if tag == "div":
            right = _require_numeric(ev(node[2], context), "division")
            if right == 0:
                raise ConditionTypeError("division by zero")
            left = _require_numeric(ev(node[1], context), "division")
            return _require_finite_result(left / right, "division")
        if tag == "mod":
            right = _require_numeric(ev(node[2], context), "modulo")
            if right == 0:
                raise ConditionTypeError("modulo by zero")
            left = _require_numeric(ev(node[1], context), "modulo")
            return _require_finite_result(left % right, "modulo")
        if tag == "neg":
            return _require_finite_result(
                -_require_numeric(SafeExpr._eval_node(node[1], context), "unary minus"),
                "unary minus",
            )

        # Logic
        if tag == "not":
            return not _require_boolean(SafeExpr._eval_node(node[1], context), "NOT")
        if tag == "and":
            left = _require_boolean(SafeExpr._eval_node(node[1], context), "AND")
            right = _require_boolean(SafeExpr._eval_node(node[2], context), "AND")
            return left and right
        if tag == "or":
            left = _require_boolean(SafeExpr._eval_node(node[1], context), "OR")
            right = _require_boolean(SafeExpr._eval_node(node[2], context), "OR")
            return left or right

        # Set membership
        if tag == "in":
            val = SafeExpr._eval_node(node[1], context)
            col = SafeExpr._eval_node(node[2], context)
            if not isinstance(col, (list, set, frozenset)):
                raise ConditionTypeError(
                    f"IN expected a collection, got {type(col).__name__}"
                )
            return _strict_membership(val, col)
        if tag == "not_in":
            val = SafeExpr._eval_node(node[1], context)
            col = SafeExpr._eval_node(node[2], context)
            if not isinstance(col, (list, set, frozenset)):
                raise ConditionTypeError(
                    f"NOT IN expected a collection, got {type(col).__name__}"
                )
            return not _strict_membership(val, col)

        # Comparison
        if tag == "compare":
            op = node[1]
            lv = SafeExpr._eval_node(node[2], context)
            rv = SafeExpr._eval_node(node[3], context)
            if op in (LT, GT, LE, GE):
                lv, rv = _coerce_ordered(lv, rv)
            elif op in (EQEQ, NE):
                lv, rv = _coerce_equatable(lv, rv)
            try:
                if op == EQEQ:
                    return _strict_expression_equal(lv, rv)
                if op == NE:
                    return not _strict_expression_equal(lv, rv)
                if op == LT:
                    return lv < rv
                if op == GT:
                    return lv > rv
                if op == LE:
                    return lv <= rv
                if op == GE:
                    return lv >= rv
            except TypeError as exc:
                raise ConditionTypeError(
                    f"comparison operands are incompatible: {exc}"
                ) from exc
            raise ConditionTypeError(f"unknown comparison operator {op}")

        # Safe function calls
        if tag == "call":
            args = [SafeExpr._eval_node(a, context) for a in node[2]]
            return _call_safe_function(
                node[1],
                args,
                context.get(_TRUSTED_NOW_KEY),
            )

        # Quantifiers
        if tag == "all":
            _, collection_node, var, cond = node
            if not isinstance(var, str) or var.startswith("__tarl_"):
                raise ConditionTypeError(
                    "ALL lambda variable uses a reserved internal name"
                )
            col = SafeExpr._eval_node(collection_node, context)
            if not isinstance(col, (list, set, frozenset)):
                raise ConditionTypeError(
                    f"ALL expected a collection, got {type(col).__name__}"
                )
            if not col:
                raise ConditionTypeError(
                    "ALL cannot establish a predicate over an empty collection"
                )
            results = [
                _require_boolean(
                    SafeExpr._eval_node(cond, {**context, var: item}),
                    "ALL predicate",
                )
                for item in col
            ]
            return all(results)
        if tag == "any":
            _, collection_node, var, cond = node
            if not isinstance(var, str) or var.startswith("__tarl_"):
                raise ConditionTypeError(
                    "ANY lambda variable uses a reserved internal name"
                )
            col = SafeExpr._eval_node(collection_node, context)
            if not isinstance(col, (list, set, frozenset)):
                raise ConditionTypeError(
                    f"ANY expected a collection, got {type(col).__name__}"
                )
            if not col:
                raise ConditionTypeError(
                    "ANY cannot establish a predicate over an empty collection"
                )
            results = [
                _require_boolean(
                    SafeExpr._eval_node(cond, {**context, var: item}),
                    "ANY predicate",
                )
                for item in col
            ]
            return any(results)

        raise ConditionTypeError(f"unknown expression node {tag!r}")

    @staticmethod
    def _resolve_value(node, context: dict):
        """Resolve a node to its raw value (for backwards compatibility)."""
        if isinstance(node, (bool, int, float, str)):
            return node
        if not isinstance(node, tuple):
            return None
        tag = node[0]
        if tag in ("int", "float", "string", "bool"):
            return node[1]
        if tag == "ident":
            return context.get(node[1], node[1])
        if tag == "attr":
            return SafeExpr._eval_node(node, context)
        return None


def _coerce_ordered(lv: Any, rv: Any) -> tuple[Any, Any]:
    """Accept only type-compatible ordered operands; never parse strings."""
    if isinstance(lv, bool) or isinstance(rv, bool):
        raise ConditionTypeError("bool in ordering comparison")
    if isinstance(lv, (int, float)) and isinstance(rv, (int, float)):
        return (
            _require_numeric(lv, "numeric comparison"),
            _require_numeric(rv, "numeric comparison"),
        )
    if isinstance(lv, str) and isinstance(rv, str):
        return lv, rv
    raise ConditionTypeError(
        f"cannot order {type(lv).__name__} and {type(rv).__name__}"
    )


def _coerce_equatable(lv: Any, rv: Any) -> tuple[Any, Any]:
    """Coerce compatible equality operands or reject type confusion."""
    if isinstance(lv, bool) or isinstance(rv, bool):
        if isinstance(lv, bool) and isinstance(rv, bool):
            return lv, rv
        raise ConditionTypeError(
            f"cannot compare {type(lv).__name__} and {type(rv).__name__}"
        )
    if isinstance(lv, (int, float)) and isinstance(rv, (int, float)):
        return (
            _require_numeric(lv, "numeric comparison"),
            _require_numeric(rv, "numeric comparison"),
        )
    if type(lv) is type(rv):
        return lv, rv
    raise ConditionTypeError(
        f"cannot compare {type(lv).__name__} and {type(rv).__name__}"
    )


# ── Module-level evaluate_policy ─────────────────────────────────────────────


def evaluate_policy(
    context: dict,
    policy_text: str = "",
    policy: TarlPolicy | None = None,
    now: datetime.datetime | None = None,
) -> TarlDecision:
    """
    Evaluate a policy against a context dict.
    First-match-wins: Eval(P,c) = vₖ where k=min{i|φᵢ(c)=true}, else DENY.

    Phase 5: enforces valid_from/valid_until/if_unresolved_after windows and
    computes expires_at for time-bound verdicts (duration_seconds > 0).
    """
    if policy is None:
        if not policy_text:
            return DEFAULT_DENY
        policy = PolicyParser.parse(policy_text)

    try:
        prepared = prepare_context(context)
    except ContextResolutionError as exc:
        return TarlDecision(
            verdict=TarlVerdict.DENY,
            reason=str(exc),
        )

    try:
        evaluation_now = (
            _coerce_datetime(now)
            if now is not None
            else datetime.datetime.now(datetime.UTC)
        )
    except ConditionTypeError as exc:
        return TarlDecision(
            verdict=TarlVerdict.DENY,
            reason=f"fail-closed: {exc}",
        )

    temporal = _check_policy_temporal(policy, now=evaluation_now)
    if temporal is not None:
        return temporal

    for i, rule in enumerate(policy.rules):
        try:
            result = SafeExpr.evaluate(rule.condition, prepared, now=evaluation_now)
            if result:
                authority_expiry = _policy_authority_expiry(
                    policy, rule, evaluation_now
                )
                expires_at = (
                    authority_expiry.isoformat(timespec="seconds")
                    if authority_expiry is not None
                    else None
                )
                return TarlDecision(
                    verdict=rule.verdict,
                    reason=f"Rule matched: {rule}",
                    rule_index=i,
                    matched_rule=str(rule),
                    expires_at=expires_at,
                )
        except Exception as exc:
            return TarlDecision(
                verdict=TarlVerdict.DENY,
                reason=(f"fail-closed: rule {i} could not be evaluated: {exc}"),
                rule_index=i,
                matched_rule=str(rule),
            )

    return DEFAULT_DENY
