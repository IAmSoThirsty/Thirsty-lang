"""Default governance and definition/caller restrictions cannot be downgraded."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from utf.tarl.authority import VerifiedAuthority
from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
from utf.tarl.spec import TarlVerdict
from utf.thirsty_lang import interpreter as interpreter_module
from utf.thirsty_lang.ast import ModuleHeader
from utf.thirsty_lang.interpreter import GovernanceViolation, Interpreter
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
def make_interpreter():
    interpreters = []
    runtimes = []

    def make(*, policy=None, runtime=None, **options):
        interpreter = Interpreter(**options)
        interpreters.append(interpreter)
        if policy is not None:
            runtime = TarlRuntime(PolicyParser.parse(policy))
            runtimes.append(runtime)
        if runtime is not None:
            interpreter.attach_tarl(runtime).set_authority("test-operator")
        return interpreter

    yield make
    for interpreter in interpreters:
        interpreter.executor.shutdown(wait=True)
    for runtime in runtimes:
        runtime.shutdown()


@pytest.fixture
def effects(monkeypatch):
    output = Mock(name="stdout")
    input_ = Mock(name="stdin", return_value="input-value")
    monkeypatch.setattr("builtins.print", output)
    monkeypatch.setattr("builtins.input", input_)
    return output, input_


def assert_denial(error):
    assert error.value.proof is not None
    assert error.value.proof.verdict is TarlVerdict.DENY


_EFFECT_ROUTES = [
    pytest.param('print("forbidden")', id="print"),
    pytest.param('pour "forbidden"', id="pour-statement"),
    pytest.param('drink output = print\noutput("forbidden")', id="print-alias"),
    pytest.param('pour_alias("forbidden")', id="pour-alias"),
    pytest.param('drink mut value = ""\nsip value', id="sip"),
    pytest.param(
        'glass output(value) { print(value) }\noutput("forbidden")',
        id="regular-function",
    ),
    pytest.param(
        'drink output = glass(value) { print(value) }\noutput("forbidden")',
        id="lambda",
    ),
    pytest.param(
        "glass apply(callback, value) { return callback(value) }\n"
        'apply(print, "forbidden")',
        id="callback",
    ),
    pytest.param('cascade print("forbidden")', id="cascade"),
    pytest.param('"forbidden" | print', id="pipe"),
    pytest.param('"forbidden" -> print', id="pipeline"),
]


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("header", ["", "module test: core\n", "module test: strict\n"])
@pytest.mark.parametrize("source", _EFFECT_ROUTES)
def test_default_governance_denies_all_effect_routes_before_sink(
    optimization, header, source, make_interpreter, effects
):
    interpreter = make_interpreter(opt_level=optimization)
    interpreter.env.define("pour_alias", interpreter.env.get("pour"))
    with pytest.raises(GovernanceViolation) as error:
        interpreter.interpret(parse(header + source))
    assert_denial(error)
    effects[0].assert_not_called()
    effects[1].assert_not_called()


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("source", _EFFECT_ROUTES)
def test_pure_effect_semantics_still_refuse_before_sink(
    optimization, source, make_interpreter, effects
):
    interpreter = make_interpreter(opt_level=optimization, policy="when true => ALLOW")
    interpreter.env.define("pour_alias", interpreter.env.get("pour"))
    with pytest.raises(RuntimeError, match="pure"):
        interpreter.interpret(parse("module test: pure\n" + source))
    effects[0].assert_not_called()
    effects[1].assert_not_called()


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("mode", [None, "core", "strict", "pure", "governed"])
def test_secure_default_keeps_deterministic_arithmetic_available(
    optimization, mode, make_interpreter
):
    interpreter = make_interpreter(opt_level=optimization)
    assert interpreter.interpret(parse("drink value = 6\nvalue * 7"), mode=mode) == 42


@pytest.mark.parametrize("invalid", ["", "CORE", "core ", "unsafe", True, 0, [], {}])
@pytest.mark.parametrize("location", ["request", "header"])
def test_invalid_execution_mode_is_rejected_before_effects(
    invalid, location, make_interpreter, effects
):
    interpreter = make_interpreter()
    program = parse('print("forbidden")')
    options = {}
    if location == "request":
        options["mode"] = invalid
    else:
        program.header = ModuleHeader("test", invalid, (1, 1, 1, 10))
    with pytest.raises(ValueError, match="mode"):
        interpreter.interpret(program, **options)
    effects[0].assert_not_called()
    assert interpreter.interpret(parse("40 + 2")) == 42


@pytest.mark.parametrize("invalid", [None, 0, 1, "true", [], {}])
def test_host_opt_out_requires_an_actual_boolean(invalid):
    with pytest.raises(TypeError, match="Bool|bool"):
        Interpreter(allow_ungoverned=invalid)


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("header", ["", "module test: core\n", "module test: strict\n"])
def test_explicit_host_opt_out_allows_core_compatibility(
    optimization, header, make_interpreter, effects
):
    interpreter = make_interpreter(opt_level=optimization, allow_ungoverned=True)
    interpreter.interpret(parse(header + 'print("permitted")'))
    effects[0].assert_called_once_with("permitted")


@pytest.mark.parametrize(
    ("header", "options"),
    [
        ("module test: governed\n", {}),
        ("", {"mode": "governed"}),
        ("module test: core\n", {"mode": "governed"}),
        ("module test: governed\n", {"mode": "core", "force_mode": True}),
    ],
)
def test_governed_request_or_declaration_strengthens_host_opt_out(
    header, options, make_interpreter, effects
):
    interpreter = make_interpreter(allow_ungoverned=True)
    with pytest.raises(GovernanceViolation) as error:
        interpreter.interpret(parse(header + 'print("forbidden")'), **options)
    assert_denial(error)
    effects[0].assert_not_called()


@pytest.mark.parametrize("posture", ["hardened", "required-audit"])
@pytest.mark.parametrize("mode", ["core", "strict"])
def test_hardened_or_required_audit_cannot_be_disabled_by_host_core_opt_out(
    posture, mode, make_interpreter, effects
):
    interpreter = make_interpreter(allow_ungoverned=True, policy="when true => ALLOW")
    if posture == "hardened":
        interpreter.set_hardened()
    else:
        interpreter.tarl_runtime.set_require_audit()
    with pytest.raises(GovernanceViolation) as error:
        interpreter.interpret(parse(f'module test: {mode}\nprint("forbidden")'))
    assert_denial(error)
    effects[0].assert_not_called()


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("mode", ["core", "strict", "pure", "governed"])
def test_default_stdlib_import_denies_before_module_resolution(
    optimization, mode, make_interpreter, monkeypatch
):
    resolver = Mock(side_effect=AssertionError("module resolution must not occur"))
    monkeypatch.setattr(interpreter_module, "resolve_import", resolver)
    interpreter = make_interpreter(opt_level=optimization)
    with pytest.raises(GovernanceViolation) as error:
        interpreter.interpret(
            parse(f'module test: {mode}\nimport "thirst::json" as api')
        )
    assert_denial(error)
    resolver.assert_not_called()
    assert not interpreter.env.has("api")


def test_default_file_import_denies_before_source_read(make_interpreter, monkeypatch):
    read = Mock(side_effect=AssertionError("source read must not occur"))
    monkeypatch.setattr(Path, "read_text", read)
    interpreter = make_interpreter()
    with pytest.raises(GovernanceViolation) as error:
        interpreter.interpret(parse('import "unread.thirsty" as api'))
    assert_denial(error)
    read.assert_not_called()
    assert not interpreter.env.has("api")


def test_pure_deterministic_import_requires_and_honors_import_policy(make_interpreter):
    interpreter = make_interpreter(
        policy='when action == "import" => ALLOW\nwhen true => DENY'
    )
    assert (
        interpreter.interpret(
            parse(
                'module test: pure\nimport "thirst::json" as api\napi.stringify([1, 2])'
            )
        )
        == "[1, 2]"
    )


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize(
    ("module", "member", "arguments"),
    [
        ("fs", "write_file", '"unused-path", "forbidden"'),
        ("process", "run", '"unused-command"'),
        ("http", "get", '"https://unused.invalid"'),
        ("env", "set", '"UNUSED_VARIABLE", "forbidden"'),
    ],
)
def test_import_permission_never_grants_sensitive_stdlib_effect(
    optimization, module, member, arguments, make_interpreter, monkeypatch
):
    sink = Mock(side_effect=AssertionError("sensitive operation must not occur"))
    exports = STDLIB_MODULES[f"thirst::{module}"]()
    exports[member] = sink
    monkeypatch.setattr(interpreter_module, "resolve_import", lambda _: exports)
    interpreter = make_interpreter(
        opt_level=optimization,
        policy='when action == "import" => ALLOW\nwhen true => DENY',
    )
    with pytest.raises(GovernanceViolation) as error:
        interpreter.interpret(
            parse(f'import "thirst::{module}" as api\napi.{member}({arguments})')
        )
    assert_denial(error)
    sink.assert_not_called()


_DEFINITIONS = [
    pytest.param("glass output(value) { print(value) }\noutput", id="regular"),
    pytest.param("drink output = glass(value) { print(value) }\noutput", id="lambda"),
    pytest.param("print", id="builtin"),
    pytest.param(
        "glass factory() { return glass(value) { print(value) } }\nfactory()",
        id="escaped-callback",
    ),
    pytest.param("glass output(value) { cascade print(value) }\noutput", id="cascade"),
]


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("definition", _DEFINITIONS)
@pytest.mark.parametrize("mode", ["governed", "pure"])
def test_definition_restrictions_survive_interpreter_reuse_and_callback_escape(
    optimization, definition, mode, make_interpreter, effects
):
    interpreter = make_interpreter(opt_level=optimization, allow_ungoverned=True)
    output = interpreter.interpret(parse(f"module original: {mode}\n{definition}"))
    assert callable(output)
    assert interpreter.interpret(parse("module later: core\n40 + 2")) == 42
    original_environment = interpreter.env
    if mode == "governed":
        with pytest.raises(GovernanceViolation) as error:
            output("forbidden")
        assert_denial(error)
    else:
        with pytest.raises(RuntimeError, match="pure"):
            output("forbidden")
    effects[0].assert_not_called()
    assert interpreter.env is original_environment
    assert not interpreter.env.has("value")
    # A failed restricted callback must restore the caller's scope and posture.
    interpreter.interpret(parse('module later: core\nprint("permitted")'))
    effects[0].assert_called_once_with("permitted")


_CALLS = [
    pytest.param('callback("forbidden")', id="direct"),
    pytest.param('cascade callback("forbidden")', id="cascade"),
    pytest.param('"forbidden" | callback', id="pipe"),
]


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("definition", _DEFINITIONS[:4])
@pytest.mark.parametrize("call", _CALLS)
def test_secure_caller_denial_constrains_foreign_explicitly_unsafe_callables(
    optimization, definition, call, make_interpreter, effects
):
    owner = make_interpreter(opt_level=optimization, allow_ungoverned=True)
    callback = owner.interpret(parse(definition))
    caller = make_interpreter(opt_level=optimization, policy="when true => DENY")
    caller.env.define("callback", callback)
    original_environment = owner.env
    with pytest.raises(GovernanceViolation) as error:
        caller.interpret(parse(call))
    assert_denial(error)
    effects[0].assert_not_called()
    assert owner.env is original_environment
    assert not owner.env.has("value")
    # Caller restrictions leave no context residue on a later explicit host call.
    owner.interpret(parse('print("permitted")'))
    effects[0].assert_called_once_with("permitted")


class _AuditLog:
    def __init__(self):
        self.proofs = []

    def store(self, proof, expires_at=None):
        self.proofs.append(proof)
        return len(self.proofs)


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("definition", _DEFINITIONS[:3:2])
@pytest.mark.parametrize(
    ("owner_verdict", "caller_verdict"),
    [("ALLOW", "ALLOW"), ("ALLOW", "DENY"), ("DENY", "ALLOW"), ("DENY", "DENY")],
)
def test_separate_declaring_and_calling_policies_must_both_allow_effects(
    optimization, definition, owner_verdict, caller_verdict, make_interpreter, effects
):
    owner = make_interpreter(
        opt_level=optimization, policy=f"when true => {owner_verdict}"
    )
    caller = make_interpreter(
        opt_level=optimization, policy=f"when true => {caller_verdict}"
    )
    owner_log, caller_log = _AuditLog(), _AuditLog()
    owner.tarl_runtime.set_archive(owner_log)
    caller.tarl_runtime.set_archive(caller_log)
    callback = owner.interpret(parse(definition))
    caller.env.define("callback", callback)
    if owner_verdict == caller_verdict == "ALLOW":
        caller.interpret(parse('callback("permitted")'))
        effects[0].assert_called_once_with("permitted")
        assert len(owner_log.proofs) == len(caller_log.proofs) == 1
        assert owner_log.proofs[0].verdict is TarlVerdict.ALLOW
        assert caller_log.proofs[0].verdict is TarlVerdict.ALLOW
    else:
        with pytest.raises(GovernanceViolation) as error:
            caller.interpret(parse('callback("forbidden")'))
        assert_denial(error)
        effects[0].assert_not_called()
        assert any(
            proof.verdict is TarlVerdict.DENY
            for proof in [*owner_log.proofs, *caller_log.proofs]
        )
        assert len(owner_log.proofs) <= 1
        assert len(caller_log.proofs) <= 1


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("definition", _DEFINITIONS[:3:2])
@pytest.mark.parametrize(
    "call", ['callback("permitted")', 'cascade callback("permitted")']
)
def test_shared_runtime_does_not_duplicate_audit_for_one_effect(
    optimization, definition, call, make_interpreter, effects
):
    owner = make_interpreter(opt_level=optimization, policy="when true => ALLOW")
    audit = _AuditLog()
    owner.tarl_runtime.set_archive(audit).set_require_audit()
    caller = make_interpreter(opt_level=optimization, runtime=owner.tarl_runtime)
    caller.env.define("callback", owner.interpret(parse(definition)))
    caller.interpret(parse(call))
    effects[0].assert_called_once_with("permitted")
    assert len(audit.proofs) == 1
    assert audit.proofs[0].verdict is TarlVerdict.ALLOW


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("definition", _DEFINITIONS[:3:2])
def test_pure_caller_context_reaches_foreign_unsafe_cascade_and_is_restored(
    optimization, definition, make_interpreter, effects
):
    owner = make_interpreter(opt_level=optimization, allow_ungoverned=True)
    caller = make_interpreter(opt_level=optimization, policy="when true => ALLOW")
    caller.env.define("callback", owner.interpret(parse(definition)))
    with pytest.raises(RuntimeError, match="pure"):
        caller.interpret(parse('module test: pure\ncascade callback("forbidden")'))
    effects[0].assert_not_called()
    owner.interpret(parse('print("permitted")'))
    effects[0].assert_called_once_with("permitted")


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("mode", ["governed", "pure"])
@pytest.mark.parametrize(
    ("module", "member", "arguments"),
    [
        ("fs", "write_file", ("unused-path", "forbidden")),
        ("process", "run", ("unused-command",)),
        ("time", "now", ()),
    ],
)
def test_imported_capability_keeps_defining_restrictions_after_reuse(
    optimization, mode, module, member, arguments, make_interpreter, monkeypatch
):
    sink = Mock(side_effect=AssertionError("sensitive operation must not occur"))
    exports = STDLIB_MODULES[f"thirst::{module}"]()
    exports[member] = sink
    monkeypatch.setattr(interpreter_module, "resolve_import", lambda _: exports)
    owner = make_interpreter(
        opt_level=optimization,
        allow_ungoverned=True,
        policy='when action == "import" => ALLOW\nwhen true => DENY',
    )
    callback = owner.interpret(
        parse(
            f'module original: {mode}\nimport "thirst::{module}" as api\napi.{member}'
        )
    )
    assert callable(callback)
    owner.interpret(parse("module later: core\n42"))
    if mode == "governed":
        with pytest.raises(GovernanceViolation) as error:
            callback(*arguments)
        assert_denial(error)
    else:
        with pytest.raises(RuntimeError, match="pure"):
            callback(*arguments)
    sink.assert_not_called()


@pytest.mark.parametrize(
    ("owner_authority", "caller_authority"),
    [("allowed", "denied"), ("denied", "allowed")],
)
def test_shared_runtime_keeps_distinct_authority_checks(
    owner_authority, caller_authority, make_interpreter, effects
):
    owner = make_interpreter(
        policy='when authority == "allowed" => ALLOW\nwhen true => DENY'
    ).set_authority(owner_authority)
    caller = make_interpreter(runtime=owner.tarl_runtime).set_authority(
        caller_authority
    )
    caller.env.define(
        "callback",
        owner.interpret(parse("glass output(value) { print(value) }\noutput")),
    )
    with pytest.raises(GovernanceViolation) as error:
        caller.interpret(parse('callback("forbidden")'))
    assert_denial(error)
    effects[0].assert_not_called()


def test_shared_runtime_keeps_both_path_confinement_checks(
    make_interpreter, monkeypatch, tmp_path
):
    sink = Mock(side_effect=AssertionError("file write must not occur"))
    exports = STDLIB_MODULES["thirst::fs"]()
    exports["write_file"] = sink
    monkeypatch.setattr(interpreter_module, "resolve_import", lambda _: exports)
    owner = make_interpreter(policy="when true => ALLOW").set_path_guard([tmp_path])
    caller = make_interpreter(runtime=owner.tarl_runtime).set_path_guard(
        [tmp_path / "caller-only"]
    )
    callback = owner.interpret(parse('import "thirst::fs" as api\napi.write_file'))
    caller.env.define("callback", callback)
    target = (tmp_path / "outside-caller.txt").as_posix()
    with pytest.raises(GovernanceViolation) as error:
        caller.interpret(parse(f'callback("{target}", "forbidden")'))
    assert_denial(error)
    sink.assert_not_called()
    assert not (tmp_path / "outside-caller.txt").exists()


@pytest.mark.parametrize(
    "call", ['callback("forbidden")', 'cascade callback("forbidden")']
)
def test_later_policy_cannot_revoke_earlier_authority_and_release_an_effect(
    call, make_interpreter, effects
):
    owner = make_interpreter(policy="when true => ALLOW")
    caller = make_interpreter(policy="when true => ALLOW")
    authorized = []

    class RevokingLog:
        def __init__(self, current):
            self.current = current

        def store(self, proof, expires_at=None):
            authorized.append(self.current)
            if len(authorized) == 2:
                authorized[0].set_authority(None)
            return len(authorized)

    owner.tarl_runtime.set_archive(RevokingLog(owner))
    caller.tarl_runtime.set_archive(RevokingLog(caller))
    caller.env.define(
        "callback",
        owner.interpret(parse("glass output(value) { print(value) }\noutput")),
    )
    with pytest.raises(GovernanceViolation) as error:
        caller.interpret(parse(call))
    assert_denial(error)
    assert "binding changed" in error.value.reason
    assert len(authorized) == 2
    effects[0].assert_not_called()


@pytest.mark.parametrize("optimization", range(4))
@pytest.mark.parametrize("call", ["callback()", "cascade callback()"])
@pytest.mark.parametrize("caller_policy", [None, "when true => DENY"])
def test_foreign_governed_function_cannot_bypass_callers_denied_action(
    optimization, call, caller_policy, make_interpreter
):
    owner = make_interpreter(opt_level=optimization, policy="when true => ALLOW")
    caller = make_interpreter(opt_level=optimization, policy=caller_policy)
    callback = owner.interpret(
        parse(
            "drink mut released = 0\n"
            "glass secret() requires true { released = released + 1\nreturn 42 }\nsecret"
        )
    )
    caller.env.define("callback", callback)
    with pytest.raises(GovernanceViolation) as error:
        caller.interpret(parse(call))
    assert_denial(error)
    assert owner.env.get("released") == 0


@pytest.mark.parametrize("shared_runtime", [False, True])
@pytest.mark.parametrize("call", ["callback()", "cascade callback()"])
def test_final_credential_callback_cannot_revoke_an_already_checked_binding(
    shared_runtime, call, make_interpreter, effects
):
    owner = make_interpreter(policy="when true => ALLOW")
    caller = (
        make_interpreter(runtime=owner.tarl_runtime)
        if shared_runtime
        else make_interpreter(policy="when true => ALLOW")
    )
    revoked = []

    def revalidate(_now):
        # Revoke only once both local authorization gates have returned ALLOW.
        # This exercises the compound gate's final credential-validation phase.
        if owner._last_proof is not None and caller._last_proof is not None:
            revoked.append(True)
            caller.set_authority(None)
        return None

    credential = VerifiedAuthority("same", ("write",), _revalidate=revalidate)
    owner.set_verified_authority(credential)
    caller.set_verified_authority(credential)
    caller.env.define(
        "callback",
        owner.interpret(parse('glass output() { print("forbidden") }\noutput')),
    )
    with pytest.raises(GovernanceViolation) as error:
        caller.interpret(parse(call))
    assert_denial(error)
    assert revoked
    assert "binding changed" in error.value.reason
    effects[0].assert_not_called()
