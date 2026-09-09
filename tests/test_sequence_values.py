"""Native sequence semantics and explicit host-coercion boundaries."""

from enum import Enum
from itertools import product

import pytest

from utf.thirsty_lang.sequences import get_index, get_slice, set_index


def containers(size):
    yield list(range(size))
    yield tuple(range(size))
    yield bytes(range(size))
    yield "a\u03a9\U0001f600e\u0301\x00"[:size]


def test_index_corpus_matches_native_sequences():
    for size in range(7):
        for sequence in containers(size):
            for index in range(-10, 11):
                if -len(sequence) <= index < len(sequence):
                    actual = get_index(sequence, index)
                    expected = sequence[index]
                    assert actual == expected
                    assert type(actual) is type(expected)
                else:
                    with pytest.raises(IndexError, match="index out of bounds"):
                        get_index(sequence, index)


def test_slice_corpus_matches_native_values_and_types():
    bounds = (None, -20, -6, -2, -1, 0, 1, 2, 6, 20)
    steps = (None, -9, -2, -1, 1, 2, 9)
    for size in range(7):
        for sequence in containers(size):
            for start, stop, step in product(bounds, bounds, steps):
                actual = get_slice(sequence, start, stop, step)
                assert type(actual) is type(sequence)
                assert actual == sequence[slice(start, stop, step)]


def test_large_integers_clip_slices_and_fail_indices_without_formatting():
    huge = 10**10000
    for sequence in containers(6):
        for index in (huge, -huge):
            with pytest.raises(IndexError):
                get_index(sequence, index)
        for start, stop, step in product(
            (None, -huge, huge), (None, -huge, huge), (None, -huge, huge)
        ):
            assert (
                get_slice(sequence, start, stop, step)
                == sequence[slice(start, stop, step)]
            )
    values = [1]
    with pytest.raises(IndexError):
        set_index(values, huge, 2)
    assert values == [1]


def test_list_assignment_corpus_validates_before_mutation():
    replacement = object()
    for size in range(7):
        for index in range(-10, 11):
            actual = list(range(size))
            expected = actual.copy()
            if -size <= index < size:
                expected[index] = replacement
                assert set_index(actual, index, replacement) is None
                assert actual == expected
            else:
                with pytest.raises(IndexError):
                    set_index(actual, index, replacement)
                assert actual == expected


@pytest.mark.parametrize("invalid", [True, False, 1.0, "1", None, [], {}, slice(1)])
def test_non_integer_sequence_indices_are_rejected(invalid):
    for sequence in containers(3):
        with pytest.raises(TypeError, match="index must be an Int"):
            get_index(sequence, invalid)
    values = [1, 2]
    with pytest.raises(TypeError, match="index must be an Int"):
        set_index(values, invalid, 9)
    assert values == [1, 2]


@pytest.mark.parametrize("invalid", [True, False, 1.0, "1", [], {}, slice(1)])
@pytest.mark.parametrize("position", [0, 1, 2])
def test_invalid_slice_bounds_are_rejected(invalid, position):
    bounds = [None, None, None]
    bounds[position] = invalid
    for sequence in containers(3):
        with pytest.raises(TypeError, match="slice .* must be an Int or none"):
            get_slice(sequence, *bounds)


def test_zero_stride_is_invalid_even_for_empty_sequences():
    for size in (0, 3):
        for sequence in containers(size):
            with pytest.raises(ValueError, match="slice step cannot be zero"):
                get_slice(sequence, step=0)


def test_slice_shallow_aliasing_and_immutable_assignment():
    child = [1]
    original = [child, [2]]
    sliced = get_slice(original)
    assert sliced is not original
    assert sliced[0] is child
    child.append(3)
    assert original[0] == sliced[0] == [1, 3]
    set_index(sliced, 1, "replacement")
    assert original == [[1, 3], [2]]
    for sequence in ("abc", (1, 2), b"ab"):
        with pytest.raises(TypeError, match="cannot index-assign"):
            set_index(sequence, 0, "replacement")


def test_string_indices_are_codepoints_and_bytes_indices_are_integers():
    assert get_index("\U0001f600e\u0301", 0) == "\U0001f600"
    assert get_slice("\U0001f600e\u0301", 1) == "e\u0301"
    assert get_index("e\u0301", -1) == "\u0301"
    assert get_index(b"\x00\xff", -1) == 255
    assert get_slice(b"\x00\xff", step=-1) == b"\xff\x00"


def test_dictionary_native_keys_missing_keys_and_assignment():
    class Key(Enum):
        SAMPLE = "sample"

    values = {1: "integer", "1": "string", ("tuple", 2): "tuple", Key.SAMPLE: "enum"}
    assert get_index(values, True) == "integer"
    assert get_index(values, 1.0) == "integer"
    assert get_index(values, "1") == "string"
    assert get_index(values, ("tuple", 2)) == "tuple"
    assert get_index(values, Key.SAMPLE) == "enum"
    assert set_index(values, None, "none-key") is None
    assert get_index(values, None) == "none-key"
    set_index(values, "1", "changed")
    assert values[1] == "integer" and values["1"] == "changed"
    with pytest.raises(KeyError):
        get_index(values, "missing")
    for invalid in ([], {}):
        with pytest.raises(TypeError, match="unhashable"):
            get_index(values, invalid)
        with pytest.raises(TypeError, match="unhashable"):
            set_index(values, invalid, 1)
    with pytest.raises(TypeError, match="cannot index"):
        get_slice(values)


def test_host_index_and_container_hooks_are_not_invoked():
    effects = []

    class Host:
        def __index__(self):
            effects.append("index")
            return 0

        def __getitem__(self, index):
            effects.append("getitem")
            return "host"

        def __setitem__(self, index, value):
            effects.append("setitem")

        def __len__(self):
            effects.append("len")
            return 1

        def __repr__(self):
            effects.append("repr")
            return "host"

    host = Host()
    for operation in (
        lambda: get_index(host, 0),
        lambda: set_index(host, 0, 1),
        lambda: get_slice(host),
        lambda: get_index([1], host),
        lambda: set_index([1], host, 2),
        lambda: get_slice([1], host),
        lambda: get_slice([1], None, host),
        lambda: get_slice([1], None, None, host),
    ):
        with pytest.raises(TypeError):
            operation()
    assert effects == []


def test_container_and_integer_subclasses_are_rejected_without_dispatch():
    effects = []

    class HostList(list):
        def __getitem__(self, index):
            effects.append("getitem")
            return 7

        def __setitem__(self, index, value):
            effects.append("setitem")

    class HostDict(dict):
        def __getitem__(self, key):
            effects.append("dict getitem")
            return 7

    class HostInt(int):
        def __index__(self):
            effects.append("index")
            return 0

        def __lt__(self, other):
            effects.append("compare")
            return False

    for container in (HostList([1]), HostDict(a=1)):
        with pytest.raises(TypeError):
            get_index(container, 0)
        with pytest.raises(TypeError):
            set_index(container, 0, 2)
        with pytest.raises(TypeError):
            get_slice(container)
    for operation in (
        lambda: get_index([1], HostInt(0)),
        lambda: set_index([1], HostInt(0), 2),
        lambda: get_slice([1], HostInt(0)),
    ):
        with pytest.raises(TypeError):
            operation()
    assert effects == []


def test_host_metaclass_cannot_spoof_the_exact_container_allowlist():
    effects = []

    class HostType(type):
        def __eq__(self, other):
            effects.append("type equality")
            return True

        def __hash__(self):
            effects.append("type hash")
            return 0

        def __getattribute__(self, name):
            if name == "__name__":
                effects.append("type name")
            return super().__getattribute__(name)

    class Host(metaclass=HostType):
        pass

    host = Host()
    for operation in (
        lambda: get_index(host, 0),
        lambda: set_index(host, 0, 1),
        lambda: get_slice(host),
        lambda: get_index([1], host),
        lambda: get_slice([1], host),
    ):
        with pytest.raises(TypeError):
            operation()
    assert effects == []


def test_dictionary_host_key_callbacks_remain_an_explicit_embedding_boundary():
    calls = []

    class HostKey:
        def __hash__(self):
            calls.append("hash")
            return 123

        def __eq__(self, other):
            calls.append("equal")
            return type(other) is HostKey

    key = HostKey()
    values = {}
    set_index(values, key, "value")
    assert get_index(values, HostKey()) == "value"
    assert calls == ["hash", "hash", "equal"]
