"""
Thirsty-Lang Type System
Base types, generic types, unification, and assignability checking.
"""

from collections.abc import Callable
from dataclasses import dataclass, field


class Type:
    """Base class for all types."""

    def __str__(self):
        return type_to_string(self)


@dataclass
class IntType(Type):
    pass


@dataclass
class FloatType(Type):
    pass


@dataclass
class BoolType(Type):
    pass


@dataclass
class StringType(Type):
    pass


@dataclass
class VoidType(Type):
    pass


@dataclass
class AnyType(Type):
    pass


@dataclass
class ErrorType(Type):
    message: str = ""


# === Generic Types ===


@dataclass
class GenericType(Type):
    base_type: str  # "Quenched", "Reservoir", "Task", "Governed"
    type_args: list[Type] = field(default_factory=list)


class QuenchedType(GenericType):
    def __init__(self, type_arg: Type):
        super().__init__(base_type="Quenched", type_args=[type_arg])

    @property
    def inner_type(self) -> Type:
        return self.type_args[0] if self.type_args else AnyType()


class ReservoirType(GenericType):
    def __init__(self, type_arg: Type):
        super().__init__(base_type="Reservoir", type_args=[type_arg])

    @property
    def inner_type(self) -> Type:
        return self.type_args[0] if self.type_args else AnyType()


class TaskType(GenericType):
    def __init__(self, type_arg: Type):
        super().__init__(base_type="Task", type_args=[type_arg])


class DictType(GenericType):
    def __init__(self, key_type: Type, value_type: Type):
        super().__init__(base_type="Dict", type_args=[key_type, value_type])

    @property
    def key_type(self) -> Type:
        return self.type_args[0]

    @property
    def value_type(self) -> Type:
        return self.type_args[1]


class ResultType(GenericType):
    def __init__(self, ok_type: Type, err_type: Type):
        super().__init__(base_type="Result", type_args=[ok_type, err_type])

    @property
    def ok_type(self) -> Type:
        return self.type_args[0] if len(self.type_args) > 0 else AnyType()

    @property
    def err_type(self) -> Type:
        return self.type_args[1] if len(self.type_args) > 1 else AnyType()


class GovernedType(GenericType):
    def __init__(self, type_arg: Type):
        super().__init__(base_type="Governed", type_args=[type_arg])


# === Named Types ===


@dataclass
class EnumType(Type):
    name: str
    variants: list[str] = field(default_factory=list)
    declaration_id: object | None = field(default=None, compare=False, repr=False)


@dataclass
class StructType(Type):
    name: str
    field_types: dict[str, Type] = field(default_factory=dict)
    declaration_id: object | None = field(default=None, compare=False, repr=False)


@dataclass
class InterfaceType(Type):
    name: str
    method_sigs: dict[str, list[Type]] = field(
        default_factory=dict
    )  # name -> [param_types]
    declaration_id: object | None = field(default=None, compare=False, repr=False)


# === Type Variables ===


@dataclass
class TypeVariable(Type):
    name: str  # e.g., "T", "E"


# === Function Types ===


@dataclass
class FunctionType(Type):
    param_types: list[Type] = field(default_factory=list)
    return_type: Type = field(default_factory=VoidType)


@dataclass(eq=False)
class ConstructorType(Type):
    """A nominal constructor value, distinct from an instance of its type.

    The signature is derived on demand so forward/recursive struct placeholders
    retain their identity when their fields are populated by the checker.
    """

    instance_type: EnumType | StructType

    def __post_init__(self):
        if not isinstance(self.instance_type, (EnumType, StructType)):
            raise TypeError("constructor requires an enum or struct instance type")

    @property
    def signature(self) -> FunctionType:
        params: list[Type] = (
            list(self.instance_type.field_types.values())
            if isinstance(self.instance_type, StructType)
            else [AnyType()]
        )
        return FunctionType(params, self.instance_type)

    def __eq__(self, other):
        return isinstance(other, ConstructorType) and _same_type(
            self.instance_type, other.instance_type
        )


@dataclass(eq=False)
class FunctionUnionType(Type):
    """One selected callable with a known set of possible signatures.

    This is not overload dispatch: callers must satisfy every alternative.
    Keeping alternatives preserves arity, nominal identity, and known input
    restrictions that would be erased by a gradual Any common type.
    """

    alternatives: tuple[FunctionType | ConstructorType, ...]

    def __post_init__(self):
        if not self.alternatives or not all(
            isinstance(item, (FunctionType, ConstructorType))
            for item in self.alternatives
        ):
            raise ValueError("function alternatives must contain known signatures")
        unique: list[FunctionType | ConstructorType] = []
        for item in self.alternatives:
            if not any(_same_type(item, existing) for existing in unique):
                unique.append(item)
        self.alternatives = tuple(unique)

    def __eq__(self, other):
        return (
            isinstance(other, FunctionUnionType)
            and len(self.alternatives) == len(other.alternatives)
            and all(
                any(_same_type(left, right) for right in other.alternatives)
                for left in self.alternatives
            )
        )


# === Type String Map ===

TYPE_NAME_MAP: "dict[str, type[Type]]" = {
    "Int": IntType,
    "Float": FloatType,
    "Bool": BoolType,
    "String": StringType,
    "Void": VoidType,
    "Any": AnyType,
    "Error": ErrorType,
}


_GENERIC_ARITIES = {
    "quenched": 1,
    "reservoir": 1,
    "task": 1,
    "dict": 2,
    "result": 2,
    "governed": 1,
}


def _generic_type(base: str, arguments: list[Type]) -> GenericType:
    """Construct a known wrapper, preserving omitted-argument Any defaults."""
    base_lower = base.lower()
    arity = _GENERIC_ARITIES.get(base_lower)
    if arity is None:
        return GenericType(base_type=base, type_args=arguments)
    if len(arguments) > arity:
        raise ValueError(f"{base} accepts at most {arity} type argument(s)")
    args = arguments + [AnyType() for _ in range(arity - len(arguments))]
    if base_lower == "quenched":
        return QuenchedType(args[0])
    if base_lower == "reservoir":
        return ReservoirType(args[0])
    if base_lower == "task":
        return TaskType(args[0])
    if base_lower == "dict":
        return DictType(args[0], args[1])
    if base_lower == "result":
        return ResultType(args[0], args[1])
    return GovernedType(args[0])


def _type_arguments(name: str, opening: int) -> list[str]:
    """Read one balanced argument list; no ignored suffixes or empty slots."""
    arguments = []
    depth = 1
    start = opening + 1
    for offset in range(start, len(name)):
        char = name[offset]
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                if offset != len(name) - 1:
                    raise ValueError("unexpected text after generic type arguments")
                argument = name[start:offset].strip()
                if argument:
                    arguments.append(argument)
                elif arguments:
                    raise ValueError("empty generic type argument")
                return arguments
        elif char == "," and depth == 1:
            argument = name[start:offset].strip()
            if not argument:
                raise ValueError("empty generic type argument")
            arguments.append(argument)
            start = offset + 1
    raise ValueError("unclosed generic type arguments")


def type_from_name(
    name: str, resolver: Callable[[str], Type | None] | None = None
) -> Type:
    """Resolve a type expression, including nominal names inside generics.

    The optional resolver receives each trimmed leaf name before built-in
    lookup. Return a Type to preserve that exact object, or None to use the
    existing built-in/unknown-name fallback. This lets callers retain lexical
    nominal bindings and supply primitive aliases without a global registry.
    Resolver exceptions propagate. Unknown leaf names remain Any; unknown
    generic constructors remain GenericType. Known wrappers retain omitted
    Any arguments (for example, Result[Int] means Result[Int, Any]). Malformed
    bracket/comma syntax and excess known-wrapper arguments raise ValueError.
    """
    name = name.strip()
    opening = name.find("[")
    if opening >= 0:
        base = name[:opening].strip()
        if not base or "]" in base or "," in base:
            raise ValueError("invalid generic type constructor")
        arguments = _type_arguments(name, opening)
        return _generic_type(
            base, [type_from_name(argument, resolver) for argument in arguments]
        )
    if "]" in name or "," in name:
        raise ValueError("unexpected bracket or comma in type name")
    if resolver is not None:
        resolved = resolver(name)
        if resolved is not None:
            if not isinstance(resolved, Type):
                raise TypeError("type name resolver must return a Type or None")
            return resolved
    cls = TYPE_NAME_MAP.get(name)
    return cls() if cls else AnyType()


# === Type Unification & Assignability ===

WIDENING_RULES: dict[type, list[type]] = {
    IntType: [FloatType],
    FloatType: [],
    BoolType: [],
    StringType: [],
}


def _same_nominal_declaration(
    left: EnumType | StructType | InterfaceType,
    right: EnumType | StructType | InterfaceType,
) -> bool:
    """Use supplied declaration identity without traversing recursive fields.

    Two legacy manually constructed descriptors retain their structural/name
    comparison. An identified declaration does not match an unidentified one.
    Dataclass equality remains available for structural descriptor comparison;
    assignability and unification use this nominal declaration contract.
    """
    if left.declaration_id is not None or right.declaration_id is not None:
        return left.declaration_id is right.declaration_id
    return left == right


def _same_type(left: Type, right: Type) -> bool:
    """Exact descriptor equivalence, never gradual mutual assignability."""
    if left is right:
        return True
    if type(left) is not type(right):
        return False
    if isinstance(left, (EnumType, StructType, InterfaceType)) and isinstance(
        right, (EnumType, StructType, InterfaceType)
    ):
        return _same_nominal_declaration(left, right)
    if isinstance(left, GenericType) and isinstance(right, GenericType):
        return (
            left.base_type == right.base_type
            and len(left.type_args) == len(right.type_args)
            and all(
                _same_type(a, b)
                for a, b in zip(left.type_args, right.type_args, strict=True)
            )
        )
    if isinstance(left, FunctionType) and isinstance(right, FunctionType):
        return (
            len(left.param_types) == len(right.param_types)
            and all(
                _same_type(a, b)
                for a, b in zip(left.param_types, right.param_types, strict=True)
            )
            and _same_type(left.return_type, right.return_type)
        )
    return left == right


def unify(t1: Type, t2: Type) -> Type:
    """Find the most specific common supertype of t1 and t2."""
    if isinstance(t1, AnyType) or isinstance(t2, AnyType):
        return AnyType()
    if isinstance(
        t1, (FunctionType, ConstructorType, FunctionUnionType)
    ) and isinstance(t2, (FunctionType, ConstructorType, FunctionUnionType)):
        left = t1.alternatives if isinstance(t1, FunctionUnionType) else (t1,)
        right = t2.alternatives if isinstance(t2, FunctionUnionType) else (t2,)
        joined = FunctionUnionType((*left, *right))
        return joined.alternatives[0] if len(joined.alternatives) == 1 else joined
    if type(t1) is type(t2):
        if isinstance(t1, (EnumType, StructType, InterfaceType)) and isinstance(
            t2, (EnumType, StructType, InterfaceType)
        ):
            return t1 if _same_nominal_declaration(t1, t2) else AnyType()
        if isinstance(t1, GenericType) and isinstance(t2, GenericType):
            if t1.base_type != t2.base_type or len(t1.type_args) != len(t2.type_args):
                return AnyType()
            args = [
                unify(left, right)
                for left, right in zip(t1.type_args, t2.type_args, strict=True)
            ]
            if type(t1) is GenericType:
                return GenericType(t1.base_type, args)
            return _generic_type(t1.base_type, args)
        if isinstance(t1, TypeVariable) and isinstance(t2, TypeVariable):
            return t1 if t1.name == t2.name else AnyType()
        return t1
    # Widening
    if isinstance(t1, IntType) and isinstance(t2, FloatType):
        return FloatType()
    if isinstance(t1, FloatType) and isinstance(t2, IntType):
        return FloatType()
    # Fall through to Any
    return AnyType()


def is_assignable(source: Type, target: Type) -> bool:
    """Check if a value of source type can be assigned to a target type variable."""
    if isinstance(target, AnyType):
        return True
    if isinstance(source, AnyType):
        return True
    if isinstance(source, FunctionUnionType):
        return all(is_assignable(item, target) for item in source.alternatives)
    if isinstance(target, FunctionUnionType):
        return any(is_assignable(source, item) for item in target.alternatives)
    if isinstance(source, ConstructorType):
        if isinstance(target, ConstructorType):
            return _same_type(source.instance_type, target.instance_type)
        if isinstance(target, FunctionType):
            return is_assignable(source.signature, target)
        return False
    if isinstance(target, ConstructorType):
        # A function may match a constructor's call signature without exposing
        # its nominal identity or (for enums) its variant members.
        return False
    if type(source) is type(target):
        if isinstance(source, (EnumType, StructType, InterfaceType)) and isinstance(
            target, (EnumType, StructType, InterfaceType)
        ):
            return _same_nominal_declaration(source, target)
        if isinstance(source, GenericType) and isinstance(target, GenericType):
            return (
                source.base_type == target.base_type
                and len(source.type_args) == len(target.type_args)
                and all(
                    is_assignable(left, right)
                    for left, right in zip(
                        source.type_args, target.type_args, strict=True
                    )
                )
            )
        if isinstance(source, FunctionType) and isinstance(target, FunctionType):
            if len(source.param_types) != len(target.param_types):
                return False
            for sp, tp in zip(source.param_types, target.param_types, strict=True):
                if not is_assignable(tp, sp):
                    return False
            return is_assignable(source.return_type, target.return_type)
        if isinstance(source, TypeVariable) and isinstance(target, TypeVariable):
            return source.name == target.name
        return True  # same type
    # Int -> Float widening
    if isinstance(source, IntType) and isinstance(target, FloatType):
        return True
    # Different type constructors are not assignable. (Same-named enums/structs
    # are already accepted above by the same-class check.)
    return False


def type_to_string(t: Type) -> str:
    """Convert a Type object to its string representation."""
    if isinstance(t, IntType):
        return "Int"
    elif isinstance(t, FloatType):
        return "Float"
    elif isinstance(t, BoolType):
        return "Bool"
    elif isinstance(t, StringType):
        return "String"
    elif isinstance(t, VoidType):
        return "Void"
    elif isinstance(t, AnyType):
        return "Any"
    elif isinstance(t, ErrorType):
        return "Error"
    elif isinstance(t, QuenchedType):
        return f"Quenched[{type_to_string(t.inner_type)}]"
    elif isinstance(t, ReservoirType):
        return f"Reservoir[{type_to_string(t.inner_type)}]"
    elif isinstance(t, TaskType):
        inner = type_to_string(t.type_args[0]) if t.type_args else "Any"
        return f"Task[{inner}]"
    elif isinstance(t, ResultType):
        ok = type_to_string(t.ok_type)
        err = type_to_string(t.err_type)
        return f"Result[{ok}, {err}]"
    elif isinstance(t, GovernedType):
        inner = type_to_string(t.type_args[0]) if t.type_args else "Any"
        return f"Governed[{inner}]"
    elif isinstance(t, EnumType):
        return t.name
    elif isinstance(t, StructType):
        return t.name
    elif isinstance(t, InterfaceType):
        return t.name
    elif isinstance(t, TypeVariable):
        return t.name
    elif isinstance(t, FunctionType):
        params = ", ".join(type_to_string(p) for p in t.param_types)
        ret = type_to_string(t.return_type)
        return f"({params}) -> {ret}"
    elif isinstance(t, ConstructorType):
        return f"Constructor[{type_to_string(t.instance_type)}]"
    elif isinstance(t, FunctionUnionType):
        variants = sorted(type_to_string(item) for item in t.alternatives)
        return "CallableChoice[" + " | ".join(variants) + "]"
    elif isinstance(t, GenericType):
        args = ", ".join(type_to_string(a) for a in t.type_args)
        return f"{t.base_type}[{args}]"
    else:
        return str(t)
