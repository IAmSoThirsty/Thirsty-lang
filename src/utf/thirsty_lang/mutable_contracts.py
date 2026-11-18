"""Run-local writable contracts for exact native lists and dictionaries.

Bindings retain object identity. A validation transaction publishes nested
constraints only after the entire input and the requested write succeed.
"""

from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from threading import RLock
from typing import Any, cast
from weakref import WeakSet

from utf.thirsty_lang.typesys import (
    AnyType,
    BoolType,
    DictType,
    EnumType,
    ErrorType,
    FloatType,
    GenericType,
    IntType,
    QuenchedType,
    ReservoirType,
    StringType,
    StructType,
    Type,
    VoidType,
    is_assignable,
)

_CONTAINER = (ReservoirType, DictType, QuenchedType)
_GRAPH_LOCK = RLock()
_ACTIVE: ContextVar["MutableContracts | None"] = ContextVar(
    "mutable_contracts", default=None
)
_MAX_DEPTH = 64
_MAX_VISITS = 100_000
_MAX_RETAINED = 65_536


def _refine(old: Type, new: Type) -> Type:
    """Meet gradual arguments while preserving concrete writable invariance."""
    if isinstance(old, AnyType):
        return new
    if isinstance(new, AnyType):
        return old
    if isinstance(old, ReservoirType) and isinstance(new, ReservoirType):
        return ReservoirType(_refine(old.inner_type, new.inner_type))
    if isinstance(old, QuenchedType) and isinstance(new, QuenchedType):
        return QuenchedType(_refine(old.inner_type, new.inner_type))
    if isinstance(old, DictType) and isinstance(new, DictType):
        return DictType(
            _refine(old.key_type, new.key_type), _refine(old.value_type, new.value_type)
        )
    if is_assignable(old, new) and is_assignable(new, old):
        return old
    raise TypeError(f"incompatible writable contracts {old} and {new}")


def _matches(value: Any, expected: Type) -> bool:
    if isinstance(expected, IntType):
        return type(value) is int
    if isinstance(expected, FloatType):
        return type(value) in (int, float)
    if isinstance(expected, BoolType):
        return type(value) is bool
    if isinstance(expected, StringType):
        return type(value) is str
    if isinstance(expected, VoidType):
        return value is None
    if isinstance(expected, ErrorType):
        return isinstance(value, Exception)
    if isinstance(expected, EnumType):
        return type(value) is expected.declaration_id
    if isinstance(expected, StructType):
        from utf.thirsty_lang.interpreter import StructInstance

        return (
            isinstance(value, StructInstance)
            and value.declaration is expected.declaration_id
        )
    if isinstance(expected, GenericType):
        raise TypeError(f"no guest runtime representation for {expected}")
    return False


class _ContractGraph:
    def __init__(self) -> None:
        self.entries: dict[int, tuple[Any, Type]] = {}
        self.owners: WeakSet[MutableContracts] = WeakSet()


class MutableContracts:
    """One identity table per interpreter/import graph, cleared on close."""

    def __init__(self) -> None:
        self._graph = _ContractGraph()
        self._graph.owners.add(self)

    def clear(self) -> None:
        with _GRAPH_LOCK:
            graph = self._graph
            graph.owners.discard(self)
            if not graph.owners:
                graph.entries.clear()
            self._graph = _ContractGraph()
            self._graph.owners.add(self)

    def _connect(self, caller: "MutableContracts") -> None:
        """A cross-interpreter guest call joins the live object/closure graph."""
        with _GRAPH_LOCK:
            source, target = self._graph, caller._graph
            if source is target:
                return
            if len(source.entries) > len(target.entries):
                source, target = target, source
            changes: dict[int, tuple[Any, Type]] = {}
            added = 0
            for key, (value, constraint) in source.entries.items():
                existing = target.entries.get(key)
                if existing is None:
                    added += 1
                else:
                    constraint = _refine(existing[1], constraint)
                changes[key] = (value, constraint)
            if len(target.entries) + added > _MAX_RETAINED:
                raise TypeError("mutable contract identity limit exceeded")
            target.entries.update(changes)
            for owner in tuple(source.owners):
                owner._graph = target
                target.owners.add(owner)
            source.owners.clear()
            source.entries.clear()

    @contextmanager
    def active(self) -> Iterator[None]:
        caller = _ACTIVE.get()
        if caller is not None and caller is not self:
            self._connect(caller)
        token = _ACTIVE.set(self)
        try:
            yield
        finally:
            _ACTIVE.reset(token)

    def bind(
        self,
        bindings: Iterable[tuple[Any, Type]],
        write: Callable[[], None] | None = None,
        *,
        labels: list[str] | None = None,
    ) -> None:
        with _GRAPH_LOCK:
            self._bind(bindings, write, labels)

    def _bind(
        self,
        bindings: Iterable[tuple[Any, Type]],
        write: Callable[[], None] | None,
        labels: list[str] | None,
    ) -> None:
        entries = self._graph.entries
        pending: dict[int, tuple[Any, Type]] = {}
        visits = 0
        new_entries = 0

        def visit(value: Any, expected: Type, depth: int = 0) -> None:
            nonlocal visits, new_entries
            if depth > _MAX_DEPTH:
                raise TypeError("mutable contract nesting limit exceeded")
            visits += 1
            if visits > _MAX_VISITS:
                raise TypeError("mutable contract validation limit exceeded")
            if isinstance(expected, AnyType):
                return
            if not isinstance(expected, _CONTAINER):
                if not _matches(value, expected):
                    raise TypeError(f"typed value requires {expected}")
                return
            if type(value) is not (
                list if isinstance(expected, ReservoirType) else dict
            ):
                raise TypeError(f"typed value requires {expected}")
            key = id(value)
            seen = pending.get(key)
            existing = seen or entries.get(key)
            if existing:
                expected = _refine(existing[1], expected)
                # Nominal types compare by declaration in _refine. At this
                # point differing concrete nominal leaves have already failed.
                if seen and seen[1] == expected:
                    return
            else:
                new_entries += 1
                if len(entries) + new_entries > _MAX_RETAINED:
                    raise TypeError("mutable contract identity limit exceeded")
            pending[key] = (value, expected)
            if isinstance(expected, ReservoirType):
                if not isinstance(expected.inner_type, AnyType):
                    for member in value:
                        visit(member, expected.inner_type, depth + 1)
            elif isinstance(expected, QuenchedType):
                wrapper = cast(dict[Any, Any], value)
                if (
                    len(wrapper) != 2
                    or "value" not in wrapper
                    or type(wrapper.get("type")) is not str
                ):
                    raise TypeError(
                        f"typed value requires {expected} with type and value fields"
                    )
                payload = wrapper["value"]
                if payload is not None:
                    visit(payload, expected.inner_type, depth + 1)
            elif isinstance(expected, DictType):
                for member_key, member_value in cast(dict[Any, Any], value).items():
                    visit(member_key, expected.key_type, depth + 1)
                    visit(member_value, expected.value_type, depth + 1)

        for index, (value, expected) in enumerate(bindings):
            try:
                visit(value, expected)
            except TypeError as error:
                if labels is not None:
                    raise TypeError(
                        f"field '{labels[index]}' requires {expected}: {error}"
                    ) from error
                raise
        if write is not None:
            write()
        entries.update(pending)

    def write(
        self, target: Any, key: Any, value: Any, mutation: Callable[[], None]
    ) -> None:
        with _GRAPH_LOCK:
            self._write(target, key, value, mutation)

    def _write(
        self, target: Any, key: Any, value: Any, mutation: Callable[[], None]
    ) -> None:
        entry = self._graph.entries.get(id(target))
        if entry is None:
            mutation()
            return
        contract = entry[1]
        if isinstance(contract, DictType):
            self.bind(
                ((key, contract.key_type), (value, contract.value_type)), mutation
            )
        elif isinstance(contract, ReservoirType):
            self.bind(((value, contract.inner_type),), mutation)
        elif isinstance(contract, QuenchedType):
            if type(key) is not str or key not in ("type", "value"):
                raise TypeError("Quenched requires exactly type and value fields")
            if key == "value" and value is None:
                mutation()
                return
            expected = StringType() if key == "type" else contract.inner_type
            self.bind(((value, expected),), mutation)

    def remove(self, target: Any, mutation: Callable[[], Any]) -> Any:
        with _GRAPH_LOCK:
            entry = self._graph.entries.get(id(target))
            if entry is not None and isinstance(entry[1], QuenchedType):
                raise TypeError("cannot remove required Quenched fields")
            return mutation()


def checked_removal(target: Any, mutation: Callable[[], Any]) -> Any:
    registry = _ACTIVE.get()
    return mutation() if registry is None else registry.remove(target, mutation)


def checked_write(
    target: Any, key: Any, value: Any, mutation: Callable[[], None]
) -> None:
    registry = _ACTIVE.get()
    if registry is None:
        mutation()
    else:
        registry.write(target, key, value, mutation)


def checked_setitem(target: Any, key: Any, value: Any) -> None:
    def assign():
        target[key] = value

    checked_write(target, key, value, assign)
