"""Checks shared-list mutation and host admission for the Node compiler."""

import shutil
import subprocess

import pytest

from utf.thirsty_lang import cli, js_host


def test_failed_write_preserves_alias_and_writable_type(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for executable JS validation")
    # Inspect the exact mutation primitives used by compiled programs after a failure.
    probe = r"""
const assert = require('node:assert/strict');
const xs = [1n];
const alias = __bindList(xs, 'Int', '2:1');
assert.equal(alias, xs);
assert.throws(() => __set('no', alias, 0n, '4:1'), /4:1: typed value requires Int/);
assert.deepEqual(xs, [1n]);
assert.throws(() => __bindList(alias, 'Float', '5:1'), /incompatible writable contracts/);
__bindList(alias, 'Any', '5:1');
assert.throws(() => __set(false, alias, 0n, '6:1'), /requires Int/);
__set(2n, alias, -1n, '7:1');
assert.equal(__get(xs, 0n, '8:1'), 2n);
assert.throws(() => __set(9n, xs, 1n, '9:1'), /bounds/);
assert.throws(() => __get(xs, true, '9:1'), /Int/);
assert.equal(__get('a🌊b', 1n, '10:1'), '🌊');
"""
    result = subprocess.run(
        [node, "--input-type=commonjs", "-"],
        input=js_host._NODE_HOST + probe,
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=tmp_path,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr


def test_bound_bytes_use_snapshot_of_source_and_policy(tmp_path):
    path = tmp_path / "app.thirsty"
    text = "drink main = 7\n"
    path.write_text(text, encoding="utf-8")
    tree, _ = cli._checked_build_source(path)
    compiled = cli._compile_governed_js(tree, text, "when true => DENY")
    assert compiled != cli._compile_governed_js(tree, text + "\n", "when true => DENY")
    assert compiled != cli._compile_governed_js(tree, text, "when true => ALLOW")
    assert "console.log(" not in compiled
    assert "__broker('write'," in compiled


def test_foreign_js_and_blank_authority_refused_before_launch(tmp_path):
    artifact = tmp_path / "app.js"
    artifact.write_text("/* foreign */", encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        js_host.launch_verified(artifact, "expected code", "reader")
    with pytest.raises(ValueError, match="authority"):
        js_host.launch_verified(artifact, "/* foreign */", " ")


@pytest.mark.parametrize(
    "typ", ["Dict[String, Int]", "Reservoir[Reservoir[Int]]", "Task[Int]"]
)
def test_unmodeled_collection_annotations_do_not_disappear(typ):
    with pytest.raises(ValueError, match="does not support annotation"):
        js_host.list_contract(typ)


def test_pure_output_and_unmediated_import_are_refused(tmp_path):
    path = tmp_path / "program.thirsty"
    for source in ('module guard: pure\npour "no"', 'import "thirst::fs" as fs'):
        path.write_text(source, encoding="utf-8")
        with pytest.raises((ValueError, SystemExit)):
            tree, text = cli._checked_build_source(path)
            cli._compile_governed_js(tree, text, "when true => ALLOW")
