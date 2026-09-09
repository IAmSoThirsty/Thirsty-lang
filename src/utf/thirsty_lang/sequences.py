"""Native guest indexing and slicing without sequence coercion callbacks.

Only exact list, str, tuple, bytes, and (for indexing) dict containers are
accepted. Sequence indices and slice bounds require exact integers, excluding
booleans and objects implementing ``__index__``. Strings are indexed by Unicode
code point; no grapheme segmentation or text normalization occurs.

Dictionary operations retain native hashable-key semantics, including enum and
tuple keys, boolean/numeric key equality, and KeyError for missing entries.
Dictionary keys can invoke ``__hash__`` or ``__eq__``: those key objects remain
an embedding trust boundary. The no-coercion guarantee concerns sequence
containers, sequence indices, and slice bounds, not arbitrary dictionary keys.

List slicing makes a shallow copy: the outer list is independent and element
references remain shared. Tuples, strings, and bytes remain their original
immutable container type; a full slice may reuse the original object.
"""

from typing import TypeAlias, cast

SequenceValue: TypeAlias = list[object] | str | tuple[object, ...] | bytes

__all__ = ["get_index", "set_index", "get_slice"]


def _sequence(obj: object) -> SequenceValue:
    kind = type(obj)
    # Identity checks also avoid invoking a custom metaclass's equality/hash
    # when an embedding passes an unsupported host object.
    if kind is list or kind is str or kind is tuple or kind is bytes:
        return cast(SequenceValue, obj)
    raise TypeError("cannot index: expected a native list, string, tuple, or bytes")


def _index(index: object, size: int) -> int:
    if type(index) is not int:
        raise TypeError("sequence index must be an Int (booleans are not indices)")
    position = cast(int, index)
    if position < 0:
        position += size
    if position < 0 or position >= size:
        # Do not stringify the index: formatting extremely large integers can
        # itself fail, replacing the required IndexError with another error.
        raise IndexError(f"index out of bounds: size is {size}")
    return position


def _bound(value: object, name: str) -> int | None:
    if value is None:
        return None
    if type(value) is not int:
        raise TypeError(
            f"slice {name} must be an Int or none (booleans are not bounds)"
        )
    return cast(int, value)


def get_index(obj: object, index: object) -> object:
    """Read one native sequence element or dictionary entry.

    Negative sequence indices count from the end; out-of-range indices raise
    IndexError. Missing dictionary keys raise KeyError without conversion.
    """
    if type(obj) is dict:
        return cast(dict[object, object], obj)[index]
    sequence = _sequence(obj)
    return sequence[_index(index, len(sequence))]


def set_index(obj: object, index: object, value: object) -> None:
    """Replace a list element or insert/replace a dictionary entry in place.

    List assignment never grows the list and validates before mutation.
    Strings, tuples, and bytes do not support indexed assignment.
    """
    if type(obj) is dict:
        cast(dict[object, object], obj)[index] = value
        return
    if type(obj) is list:
        sequence = cast(list[object], obj)
        sequence[_index(index, len(sequence))] = value
        return
    raise TypeError(
        "cannot index-assign: only native lists and dictionaries are mutable"
    )


def get_slice(
    obj: object,
    start: object = None,
    stop: object = None,
    step: object = None,
) -> SequenceValue:
    """Slice a native sequence, retaining its type and clipping outlying bounds.

    Bounds are none or exact integers; negative steps reverse traversal and
    zero steps raise ValueError. Large integers are handled by native slicing
    without converting arbitrary host objects or allocating from bound sizes.
    """
    sequence = _sequence(obj)
    first = _bound(start, "start")
    last = _bound(stop, "stop")
    stride = _bound(step, "step")
    if stride == 0:
        raise ValueError("slice step cannot be zero")
    return sequence[slice(first, last, stride)]
