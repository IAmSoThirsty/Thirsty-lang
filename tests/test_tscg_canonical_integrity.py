"""Canonical output must preserve the tree, including association and grouping."""

import itertools

import pytest

from utf.tscg.core import (
    CANONICALIZATION_ID,
    CombineExpr,
    SymbolExpr,
    TSCGNode,
    canonical_form,
    checksum,
    parse,
)


@pytest.mark.parametrize(
    "outer,inner", list(itertools.product(["->", "^", "||"], repeat=2))
)
@pytest.mark.parametrize("right", [False, True])
def test_canonicalization_preserves_operator_tree(outer, inner, right):
    source = (
        f"$COG {outer} ($DNT {inner} $SHD)"
        if right
        else f"($COG {inner} $DNT) {outer} $SHD"
    )
    original = parse(source)
    normalized = canonical_form(original)
    assert parse(normalized) == original
    assert canonical_form(parse(normalized)) == normalized


def test_previously_colliding_trees_stay_distinct():
    left = canonical_form(parse("($COG -> $DNT) || $SHD"))
    right = canonical_form(parse("$COG -> ($DNT || $SHD)"))
    assert left != right
    assert checksum(left) != checksum(right)
    assert CANONICALIZATION_ID == "tscg.grouping-preserving.v2"


@pytest.mark.parametrize(
    "node",
    [
        TSCGNode(),
        SymbolExpr("UNKNOWN"),
        CombineExpr(SymbolExpr("COG"), SymbolExpr("DNT"), "+"),
    ],
)
def test_invalid_nodes_cannot_be_canonicalized(node):
    with pytest.raises(ValueError):
        canonical_form(node)
