"""Imports inside foreign closures honor every active live import lock.

These tests cover the newly imported source and namespaces. They do not claim
that the host-supplied original foreign closure has a verified source identity.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
from utf.thirsty_lang import interpreter as interpreter_module
from utf.thirsty_lang import lexer as lexer_module
from utf.thirsty_lang.interpreter import Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.module_system import STDLIB_MODULES
from utf.thirsty_lang.parser import Parser


def parse(source):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    program = parser.parse()
    assert not lexer.errors, lexer.errors
    assert not parser.errors, parser.errors
    return program


@pytest.fixture
def make_pair(tmp_path):
    runtimes = []
    interpreters = []

    def make(optimization=0):
        runtime = TarlRuntime(
            PolicyParser.parse('when action == "import" => ALLOW\nwhen true => DENY')
        )
        runtimes.append(runtime)
        owner = (
            Interpreter(opt_level=optimization)
            .attach_tarl(runtime)
            .set_authority("operator")
        )
        caller = (
            Interpreter(opt_level=optimization)
            .attach_tarl(runtime)
            .set_authority("operator")
        )
        owner.source_directory = tmp_path
        # Relative imports must still resolve from the declaring module's directory.
        caller.source_directory = tmp_path / "different-caller-directory"
        interpreters.extend((owner, caller))
        return owner, caller

    yield make
    for interpreter in interpreters:
        interpreter.executor.shutdown(wait=True)
    for runtime in runtimes:
        runtime.shutdown()


class RecordingLock:
    """A deterministic implementation of the read/verify lock interface."""

    def __init__(self, name, sources=None, *, reject=None):
        self.name = name
        self.sources = sources or {"target.thirsty": "drink value = 42"}
        self.reject = reject
        self.reads = []
        self.namespaces = []

    def read_source(self, path):
        candidate = Path(path)
        self.reads.append(candidate)
        if self.reject == "file":
            raise ImportError(f"{self.name} lock rejected file")
        if candidate.name not in self.sources:
            raise ImportError(f"{self.name} lock has no source for {candidate.name}")
        return self.sources[candidate.name]

    def verify_stdlib(self, namespace):
        self.namespaces.append(namespace)
        if self.reject == "stdlib":
            raise ImportError(f"{self.name} lock rejected stdlib")


def bind_loader(owner, caller, kind):
    body = (
        'import "target.thirsty" as api\nreturn api.value'
        if kind == "file"
        else 'import "thirst::json" as api\nreturn api.stringify([42])'
    )
    callback = owner.interpret(parse(f"glass load() {{ {body} }}\nload"))
    caller.env.define("callback", callback)


def install_locks(owner, caller, mode):
    owner_lock = RecordingLock("owner")
    caller_lock = RecordingLock("caller")
    if mode in {"owner", "both", "shared"}:
        owner.set_locked(owner_lock)
    if mode == "shared":
        caller.set_locked(owner_lock)
    elif mode in {"caller", "both"}:
        caller.set_locked(caller_lock)
    return owner_lock, caller_lock


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("call", ["callback()", "cascade callback()"])
@pytest.mark.parametrize("kind", ["file", "stdlib"])
@pytest.mark.parametrize("locks", ["owner", "caller", "both", "shared"])
def test_foreign_import_consults_each_distinct_active_lock_once(
    optimization, call, kind, locks, make_pair, tmp_path, monkeypatch
):
    target = tmp_path / "target.thirsty"
    target.write_text("invalid source must not be reread", encoding="utf-8")
    owner, caller = make_pair(optimization)
    bind_loader(owner, caller, kind)
    owner_lock, caller_lock = install_locks(owner, caller, locks)
    unread_source = Mock(side_effect=AssertionError("fresh source read is forbidden"))
    monkeypatch.setattr(Path, "read_text", unread_source)
    resolver = Mock(return_value=STDLIB_MODULES["thirst::json"]())
    monkeypatch.setattr(interpreter_module, "resolve_import", resolver)
    assert caller.interpret(parse(call)) == (42 if kind == "file" else "[42]")
    expected = [target.resolve()] if kind == "file" else ["thirst::json"]
    owner_calls = owner_lock.reads if kind == "file" else owner_lock.namespaces
    caller_calls = caller_lock.reads if kind == "file" else caller_lock.namespaces
    assert owner_calls == (expected if locks in {"owner", "both", "shared"} else [])
    assert caller_calls == (expected if locks in {"caller", "both"} else [])
    unread_source.assert_not_called()
    if kind == "stdlib":
        resolver.assert_called_once_with("thirst::json")
    else:
        resolver.assert_not_called()


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("call", ["callback()", "cascade callback()"])
@pytest.mark.parametrize("kind", ["file", "stdlib"])
@pytest.mark.parametrize("rejecting_owner", ["owner", "caller"])
def test_either_foreign_import_lock_can_reject_before_resolution_or_execution(
    optimization, call, kind, rejecting_owner, make_pair, tmp_path, monkeypatch
):
    (tmp_path / "target.thirsty").write_text("drink value = 99", encoding="utf-8")
    owner, caller = make_pair(optimization)
    bind_loader(owner, caller, kind)
    owner_lock = RecordingLock(
        "owner", reject=kind if rejecting_owner == "owner" else None
    )
    caller_lock = RecordingLock(
        "caller", reject=kind if rejecting_owner == "caller" else None
    )
    owner.set_locked(owner_lock)
    caller.set_locked(caller_lock)
    program = parse(call)
    resolver = Mock(side_effect=AssertionError("denied import must not resolve"))
    source_lexer = Mock(side_effect=AssertionError("denied source must not be parsed"))
    monkeypatch.setattr(interpreter_module, "resolve_import", resolver)
    monkeypatch.setattr(lexer_module, "Lexer", source_lexer)
    old_owner_environment = owner.env
    old_caller_environment = caller.env
    with pytest.raises(ImportError, match=f"{rejecting_owner} lock rejected"):
        caller.interpret(program)
    assert owner.env is old_owner_environment
    assert caller.env is old_caller_environment
    assert not owner.env.has("api")
    assert not caller.env.has("api")
    rejected = owner_lock if rejecting_owner == "owner" else caller_lock
    assert rejected.reads if kind == "file" else rejected.namespaces
    resolver.assert_not_called()
    source_lexer.assert_not_called()


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("call", ["callback()", "cascade callback()"])
@pytest.mark.parametrize("different", ["drink value = 43\n", "drink value = 42\r\n"])
def test_active_locks_must_agree_on_exact_returned_source_before_parsing(
    optimization, call, different, make_pair, tmp_path, monkeypatch
):
    target = tmp_path / "target.thirsty"
    target.write_text("drink value = 99", encoding="utf-8")
    owner, caller = make_pair(optimization)
    bind_loader(owner, caller, "file")
    owner_lock = RecordingLock("owner", {target.name: "drink value = 42\n"})
    caller_lock = RecordingLock("caller", {target.name: different})
    owner.set_locked(owner_lock)
    caller.set_locked(caller_lock)
    program = parse(call)
    source_lexer = Mock(side_effect=AssertionError("disagreeing source must not parse"))
    monkeypatch.setattr(lexer_module, "Lexer", source_lexer)
    with pytest.raises(ImportError, match="locks disagree about source bytes"):
        caller.interpret(program)
    assert owner_lock.reads == caller_lock.reads == [target.resolve()]
    source_lexer.assert_not_called()


@pytest.mark.parametrize("call", ["callback()", "cascade callback()"])
@pytest.mark.parametrize("replaced_owner", ["owner", "caller"])
def test_foreign_closure_observes_live_lock_replacement_on_every_import(
    call, replaced_owner, make_pair, tmp_path
):
    target = tmp_path / "target.thirsty"
    target.write_text("drink value = 99", encoding="utf-8")
    owner, caller = make_pair()
    bind_loader(owner, caller, "file")
    original_owner, original_caller = install_locks(owner, caller, "both")
    assert caller.interpret(parse(call)) == 42
    replacement = RecordingLock("replacement", reject="file")
    (owner if replaced_owner == "owner" else caller).set_locked(replacement)
    with pytest.raises(ImportError, match="replacement lock rejected file"):
        caller.interpret(parse(call))
    assert replacement.reads == [target.resolve()]
    assert original_owner.reads
    assert original_caller.reads


@pytest.mark.parametrize("call", ["callback()", "cascade callback()"])
def test_nested_imports_consult_both_locks_and_use_their_returned_source(
    call, make_pair, tmp_path, monkeypatch
):
    sources = {
        "target.thirsty": 'import "leaf.thirsty" as leaf\ndrink value = leaf.value',
        "leaf.thirsty": 'import "thirst::json" as json\ndrink value = json.stringify([42])',
    }
    for name in sources:
        (tmp_path / name).write_text("invalid on disk", encoding="utf-8")
    owner, caller = make_pair()
    bind_loader(owner, caller, "file")
    owner_lock = RecordingLock("owner", sources)
    caller_lock = RecordingLock("caller", sources)
    owner.set_locked(owner_lock)
    caller.set_locked(caller_lock)
    fresh_read = Mock(side_effect=AssertionError("verified source must not be reread"))
    monkeypatch.setattr(Path, "read_text", fresh_read)
    assert caller.interpret(parse(call)) == "[42]"
    paths = [(tmp_path / name).resolve() for name in sources]
    assert owner_lock.reads == caller_lock.reads == paths
    assert owner_lock.namespaces == caller_lock.namespaces == ["thirst::json"]
    fresh_read.assert_not_called()


@pytest.mark.parametrize("rejecting_owner", ["owner", "caller"])
def test_returned_imported_callback_retains_both_live_lock_constraints(
    rejecting_owner, make_pair, tmp_path
):
    sources = {
        "target.thirsty": 'glass load_leaf() { import "leaf.thirsty" as leaf\nreturn leaf.value }',
        "leaf.thirsty": "drink value = 42",
    }
    for name in sources:
        (tmp_path / name).write_text("invalid on disk", encoding="utf-8")
    owner, caller = make_pair()
    callback = owner.interpret(
        parse(
            'glass load() { import "target.thirsty" as api\nreturn api.load_leaf }\nload'
        )
    )
    caller.env.define("callback", callback)
    owner_lock = RecordingLock("owner", sources)
    caller_lock = RecordingLock("caller", sources)
    owner.set_locked(owner_lock)
    caller.set_locked(caller_lock)
    imported_callback = caller.interpret(parse("callback()"))
    assert callable(imported_callback)
    replacement = RecordingLock("replacement", reject="file")
    (owner if rejecting_owner == "owner" else caller).set_locked(replacement)
    with pytest.raises(ImportError, match="replacement lock rejected file"):
        imported_callback()
    assert replacement.reads == [(tmp_path / "leaf.thirsty").resolve()]
