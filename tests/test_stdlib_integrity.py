"""Security regressions for stdlib effects and content-based dependency locks."""

import hashlib
import hmac
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from utf.thirsty_lang import module_system as ms
from utf.thirsty_lang.package_manager import PackageManager, create_thirsty_lock


def test_hmac_matches_standard_and_detects_tampering():
    crypto = ms.STDLIB_MODULES["thirst::crypto"]()
    key, data = "\x0b" * 20, "Hi There"
    expected = "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"
    assert crypto["hmac"](key, data) == expected
    assert (
        crypto["hmac_sha256"](key, data)
        == hmac.new(key.encode(), data.encode(), hashlib.sha256).hexdigest()
    )
    assert crypto["verify_hmac"](key, data, expected)
    assert not crypto["verify_hmac"](key, data + "!", expected)
    with pytest.raises(ValueError):
        crypto["hmac"]("", data)


def test_ed25519_known_vector_and_legacy_digest_rejection():
    crypto = ms.STDLIB_MODULES["thirst::crypto"]()
    seed = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
    public = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    expected = "ed25519:e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
    assert crypto["public_key"](seed) == public
    assert crypto["ed25519_sign"]("", seed) == expected
    assert crypto["ed25519_verify"]("", expected, public)
    assert not crypto["verify"]("changed", expected, public)
    assert not crypto["verify"]("", hashlib.sha256(seed.encode()).hexdigest(), public)
    assert not crypto["verify"]("", "ed25519:not-hex", public)
    assert not crypto["verify"]("", expected, "bad-key")
    with pytest.raises(ValueError):
        crypto["sign"]("data", "")
    with pytest.raises(TypeError):
        crypto["sign"]("data")


def test_crypto_randomness_uses_system_entropy(monkeypatch):
    import secrets

    calls = []
    monkeypatch.setattr(
        secrets, "token_bytes", lambda size: calls.append(size) or b"x" * size
    )
    assert ms.STDLIB_MODULES["thirst::crypto"]()["random_bytes"](3) == "787878"
    assert calls == [3]


@pytest.mark.parametrize("size", [-1, True, 1.5, 1048577])
def test_randomness_rejects_invalid_or_excessive_lengths(size):
    with pytest.raises(ValueError):
        ms.STDLIB_MODULES["thirst::crypto"]()["random_bytes"](size)


@pytest.fixture
def database():
    module = ms.STDLIB_MODULES["thirst::sqlite"]()
    handle = module["connect"](":memory:")
    module["execute"](handle, "CREATE TABLE items(value TEXT)")
    module["execute"](handle, "INSERT INTO items VALUES (?)", ["original"])
    yield module, handle
    module["close"](handle)


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO items VALUES ('forbidden')",
        "DELETE FROM items",
        "UPDATE items SET value='forbidden'",
        "CREATE TABLE forbidden(value)",
        "DROP TABLE items",
        "PRAGMA user_version=7",
        "PRAGMA journal_mode=WAL",
        "ATTACH DATABASE ':memory:' AS other",
        "BEGIN IMMEDIATE",
        "SELECT load_extension('missing')",
        "WITH x(v) AS (SELECT 'forbidden') INSERT INTO items SELECT v FROM x",
    ],
)
def test_query_cannot_mutate_or_change_connection_authority(database, sql):
    module, handle = database
    with pytest.raises(sqlite3.DatabaseError):
        module["query"](handle, sql)
    assert module["query"](handle, "SELECT value FROM items") == [{"value": "original"}]
    # Denial must restore ordinary authorized writes.
    module["execute"](handle, "INSERT INTO items VALUES (?)", ["allowed"])
    assert module["query"](handle, "SELECT count(*) AS n FROM items") == [{"n": 2}]


def test_query_rechecks_previously_prepared_write_and_parameters(database):
    module, handle = database
    sql = "INSERT INTO items VALUES (?)"
    module["execute"](handle, sql, ["first"])
    with pytest.raises(sqlite3.DatabaseError):
        module["query"](handle, sql, ["second"])
    malicious = "x'); DROP TABLE items; --"
    module["execute"](handle, sql, [malicious])
    assert module["query"](
        handle, "SELECT value FROM items WHERE value = :v", {"v": malicious}
    ) == [{"value": malicious}]


def test_sqlite_write_does_not_allow_attachment_escape(database):
    module, handle = database
    with pytest.raises(sqlite3.DatabaseError):
        module["execute"](handle, "ATTACH DATABASE ':memory:' AS outside")


def test_sqlite_query_rejects_unknown_function_effects(monkeypatch):
    original = sqlite3.connect
    effects = []

    def connect(*args, **kwargs):
        conn = original(*args, **kwargs)
        conn.create_function("effect", 0, lambda: effects.append(True) or 1)
        return conn

    monkeypatch.setattr(sqlite3, "connect", connect)
    module = ms.STDLIB_MODULES["thirst::sqlite"]()
    handle = module["connect"](":memory:")
    try:
        with pytest.raises(sqlite3.DatabaseError):
            module["query"](handle, "SELECT effect()")
        assert effects == []
    finally:
        module["close"](handle)


def test_sqlite_concurrent_calls_keep_authorizers_isolated(database):
    module, handle = database

    def read_or_write(index):
        if index % 2:
            module["execute"](handle, "INSERT INTO items VALUES (?)", [str(index)])
        else:
            with pytest.raises(sqlite3.DatabaseError):
                module["query"](handle, "INSERT INTO items VALUES ('bad')")

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(read_or_write, range(40)))
    assert module["query"](handle, "SELECT count(*) AS n FROM items") == [{"n": 21}]


def test_connection_handles_do_not_collide():
    module = ms.STDLIB_MODULES["thirst::sqlite"]()
    first, second = module["connect"](":memory:"), module["connect"](":memory:")
    try:
        assert first != second
        module["execute"](first, "CREATE TABLE only_first(x)")
        with pytest.raises(sqlite3.OperationalError):
            module["query"](second, "SELECT * FROM only_first")
    finally:
        module["close"](first)
        module["close"](second)


@pytest.mark.parametrize(
    "source",
    [
        "root:\n  nested: value",
        "- item",
        "x: [not JSON]",
        "x: &anchor value",
        "x: *anchor",
        "x: 2026-09-06",
        "x: 01",
        "x: first # silently ignored",
        "x: first\nx: second",
        '{"x": 1, "x": 2}',
        '{"x": NaN}',
        "x: 'unclosed",
        "x: .nan",
        "ignored line",
        "x: 1e9999",
    ],
)
def test_yaml_rejects_unsupported_and_ambiguous_input(source):
    with pytest.raises(ValueError):
        ms.STDLIB_MODULES["thirst::yaml"]()["parse"](source)


def test_yaml_json_subset_preserves_types_and_nested_values():
    module = ms.STDLIB_MODULES["thirst::yaml"]()
    value = {
        "quoted:key": [True, None, {"unicode": "\u03a9", "line": "a\nb"}],
        "int": 3,
    }
    assert module["parse"](module["dump"](value)) == value
    assert module["parse"]("s: 'it''s fine'\nb: true\nn: null\nf: 1.25") == {
        "s": "it's fine",
        "b": True,
        "n": None,
        "f": 1.25,
    }
    with pytest.raises(TypeError):
        module["dump"]({1: "not a string key"})
    with pytest.raises(ValueError):
        module["dump"]({"bad": float("inf")})


def test_toml_nested_tables_quoted_keys_and_escaping_roundtrip():
    module = ms.STDLIB_MODULES["thirst::toml"]()
    value = {
        "top": 'a\nb"c',
        "a.b": {"child": {"flag": True}},
        "array": [{"dotted.key": 1}],
        "after": 4,
    }
    assert module["parse"](module["dump"](value)) == value
    assert PackageManager()._parse_toml(module["dump"](value)) == value
    with pytest.raises(TypeError):
        module["dump"]({"no_null_in_toml": None})
    with pytest.raises(ValueError):
        PackageManager()._parse_toml("x = 1\nx = 2")


def lock_project(tmp_path):
    (tmp_path / "main.thirsty").write_text(
        'import "child.thirsty" as child; drink result = child.value;', encoding="utf-8"
    )
    (tmp_path / "child.thirsty").write_text("drink value = 42;", encoding="utf-8")
    create_thirsty_lock(str(tmp_path))
    return ms.LockedImports(str(tmp_path))


def test_lock_binds_bytes_and_checks_each_read(tmp_path):
    context = lock_project(tmp_path)
    assert context.read_source("child.thirsty") == "drink value = 42;"
    (tmp_path / "child.thirsty").write_text("drink value = 99;", encoding="utf-8")
    with pytest.raises(ImportError, match="changed"):
        context.read_source("child.thirsty")
    with pytest.raises(ImportError, match="integrity"):
        ms.LockedImports(str(tmp_path))


def test_lock_rejects_unknown_and_external_source(tmp_path):
    context = lock_project(tmp_path)
    (tmp_path / "new.thirsty").write_text("drink injected = 1;", encoding="utf-8")
    with pytest.raises(ImportError, match="not in"):
        context.read_source("new.thirsty")
    with pytest.raises(ImportError, match="escapes"):
        context.read_source("../other.thirsty")


def test_locked_resolver_enforces_transitive_integrity_without_cache(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    lock_project(tmp_path)
    ms.ModuleCache.clear()
    assert ms.resolve_import("main.thirsty", locked=True)["result"] == 42
    (tmp_path / "child.thirsty").write_text("drink value = 99;", encoding="utf-8")
    with pytest.raises(ImportError, match="integrity"):
        ms.resolve_import("main.thirsty", locked=True)
    ms.ModuleCache.clear()


def test_dependency_free_lock_and_bundled_stdlib(tmp_path):
    create_thirsty_lock(str(tmp_path))
    context = ms.LockedImports(str(tmp_path))
    context.verify_stdlib("thirst::json")
    assert context.lock["dependencies"] == {}
    with pytest.raises(ImportError, match="Module not found"):
        context.verify_stdlib("thirst::missing")


def test_lock_binds_manifest_and_runtime(tmp_path, monkeypatch):
    import utf.thirsty_lang.package_manager as packages

    manifest = tmp_path / "thirsty.toml"
    manifest.write_text('[package]\nname = "original"\n', encoding="utf-8")
    context = lock_project(tmp_path)
    manifest.write_text('[package]\nname = "changed"\n', encoding="utf-8")
    with pytest.raises(ImportError, match="manifest"):
        ms.LockedImports(str(tmp_path))
    monkeypatch.setattr(packages, "runtime_integrity", lambda: "sha256-other")
    with pytest.raises(ImportError, match="runtime changed"):
        context.verify_stdlib("thirst::json")


def test_legacy_duplicate_and_malformed_locks_fail_closed(tmp_path):
    path = tmp_path / "thirsty.lock"
    for content in (
        '{"lockfile_version":1,"dependencies":{}}',
        '{"lockfile_version":2,"lockfile_version":2}',
        "[]",
        "no json",
    ):
        path.write_text(content, encoding="utf-8")
        with pytest.raises(ImportError):
            ms.LockedImports(str(tmp_path))


def test_local_dependency_content_and_unresolved_add_are_checked(tmp_path):
    source = tmp_path / "lib.thirsty"
    source.write_text("drink value = 1;", encoding="utf-8")
    manager = PackageManager(str(tmp_path))
    manager.generate_lock({"local": {"path": "lib.thirsty", "version": "1"}})
    assert manager.verify_integrity() == []
    source.write_text("drink value = 2;", encoding="utf-8")
    assert {item["name"] for item in manager.verify_integrity()} == {
        "lib.thirsty",
        "local",
    }
    with pytest.raises(ValueError, match="Unresolved dependency"):
        manager.add_dependency("unavailable-registry-package", "1")
    assert not (tmp_path / "thirsty.toml").exists()
    assert manager.manifest == {}


def test_lock_source_hashes_are_not_label_digests(tmp_path):
    source = tmp_path / "dep.thirsty"
    source.write_bytes(b"drink value = 1;")
    manager = PackageManager(str(tmp_path))
    lock = manager.generate_lock({"dep": "dep.thirsty"})
    expected = "sha256-" + hashlib.sha256(source.read_bytes()).hexdigest()
    assert lock["dependencies"]["dep"]["integrity"] == expected
    assert lock["sources"]["dep.thirsty"] == expected
    assert json.loads(json.dumps(lock)) == lock


@pytest.mark.parametrize("value", [None, True, False, 1, -3, 1.25, "scalar", [1.25]])
def test_yaml_dump_accepts_only_roundtrippable_scalar_values(value):
    module = ms.STDLIB_MODULES["thirst::yaml"]()
    assert module["parse"](module["dump"](value)) == value


def test_yaml_json_nested_nonfinite_value_is_rejected():
    with pytest.raises(ValueError, match="Non-finite"):
        ms.STDLIB_MODULES["thirst::yaml"]()["parse"]('{"nested": [1e9999]}')


def test_hmac_verifier_rejects_non_ascii_mac():
    assert not ms.STDLIB_MODULES["thirst::crypto"]()["verify_hmac"](
        "key", "data", "\u03a9"
    )


def test_explicit_local_dependency_is_not_reinterpreted_as_stdlib(tmp_path):
    source = tmp_path / "crypto.thirsty"
    source.write_text("drink local = 1;", encoding="utf-8")
    manager = PackageManager(str(tmp_path))
    lock = manager.generate_lock({"crypto": {"path": "crypto.thirsty", "version": "1"}})
    assert lock["dependencies"]["crypto"]["resolved"] == "crypto.thirsty"
    assert manager.verify_integrity() == []
    with pytest.raises(ValueError, match="unsupported specification"):
        manager.generate_lock(
            {"crypto": {"path": "crypto.thirsty", "unexpected": True}}
        )


def test_explicit_hidden_dependency_can_be_locked(tmp_path):
    hidden = tmp_path / ".local"
    hidden.mkdir()
    (hidden / "dep.thirsty").write_text("drink local = 1;", encoding="utf-8")
    manager = PackageManager(str(tmp_path))
    manager.generate_lock({"local": ".local/dep.thirsty"})
    assert manager.verify_integrity() == []
    assert manager.write_lock()
    assert (
        ms.LockedImports(str(tmp_path)).read_source(".local/dep.thirsty")
        == "drink local = 1;"
    )


def test_source_fingerprint_is_independent_of_python_version(monkeypatch):
    import utf.thirsty_lang.package_manager as packages

    source = packages.runtime_source_integrity()
    runtime = packages.runtime_integrity()
    monkeypatch.setattr(packages.platform, "python_version", lambda: "0.0.0-test")
    assert packages.runtime_source_integrity() == source
    assert packages.runtime_integrity() != runtime


def test_ambient_effect_metadata_is_centralized():
    assert ms.SENSITIVE_STDLIB_CAPABILITIES["thirst::time"] == {
        "now": "read",
        "epoch_ms": "read",
        "sleep": "execute",
    }
    assert ms.SENSITIVE_STDLIB_CAPABILITIES["thirst::crypto"] == {
        "random_bytes": "read",
        "uuid4": "read",
    }


def test_guest_assertions_remain_enforced_with_python_optimization():
    import subprocess
    import sys

    script = """
from utf.thirsty_lang.module_system import STDLIB_MODULES
checks = STDLIB_MODULES['thirst::test']()
for name, args in [('assert_eq', (1, 2)), ('assert_ne', (1, 1)), ('assert_true', (False,)), ('assert_raises', (lambda: None,))]:
    try:
        checks[name](*args)
    except AssertionError:
        continue
    raise SystemExit('assertion silently disabled: ' + name)
"""
    result = subprocess.run(
        [sys.executable, "-B", "-O", "-c", script],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
