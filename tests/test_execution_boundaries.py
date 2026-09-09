"""Regression tests for module, effect, and semantic execution boundaries."""

from types import SimpleNamespace

import pytest

from utf.tarl.authority import VerifiedAuthority
from utf.tarl.core import PolicyParser
from utf.tarl.runtime import TarlRuntime
from utf.thirsty_lang.ast import Expr, Stmt
from utf.thirsty_lang.checker import Checker, check_ast
from utf.thirsty_lang.interpreter import GovernanceViolation, Interpreter
from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser
from utf.thirsty_lang.typesys import AnyType, FloatType, ReservoirType


def parse(source):
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    ast = parser.parse()
    assert not lexer.errors, lexer.errors
    assert not parser.errors, parser.errors
    return ast


def governed(
    policy='when action == "import" => ALLOW\nwhen action == "write" => ALLOW',
):
    runtime = TarlRuntime(
        PolicyParser.parse(f"policy test\n{policy}\nwhen true => DENY")
    )
    interpreter = Interpreter().attach_tarl(runtime).set_authority("tester")
    interpreter.mode = "governed"
    return interpreter


@pytest.mark.parametrize(
    "body",
    [
        'print("forbidden")',
        'drink output = print\noutput("forbidden")',
        'glass apply(callback) { callback("forbidden") }\napply(print)',
        'cascade print("forbidden")',
    ],
)
def test_pure_blocks_all_output_call_shapes(body, capsys):
    with pytest.raises(RuntimeError, match="pure"):
        Interpreter().interpret(parse(f"module test: pure\n{body}"))
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    ("namespace", "call"),
    [
        ("env", 'api.get("PATH")'),
        ("time", "api.now()"),
        ("crypto", "api.random_bytes(8)"),
        ("fs", 'api.exists("anything")'),
    ],
)
def test_pure_blocks_ambient_state(namespace, call):
    with pytest.raises(RuntimeError, match="pure"):
        governed('when action == "import" => ALLOW').interpret(
            parse(f'module test: pure\nimport "thirst::{namespace}" as api\n{call}')
        )


def test_pure_allows_deterministic_library_calls():
    assert (
        governed('when action == "import" => ALLOW').interpret(
            parse(
                'module test: pure\nimport "thirst::json" as api\napi.stringify([1, 2])'
            )
        )
        == "[1, 2]"
    )


def test_pure_callback_cannot_use_foreign_core_interpreter(capsys):
    foreign = Interpreter()
    foreign.interpret(parse('glass output() { print("forbidden") }'))
    caller = Interpreter()
    caller.env.define("callback", foreign.env.get("output"))
    with pytest.raises(RuntimeError, match="pure"):
        caller.interpret(parse("module test: pure\ncallback()"))
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("body", ["callback()", "cascade callback()"])
def test_exported_pure_function_keeps_callback_effect_restriction(body, capsys):
    pure = Interpreter()
    pure.interpret(parse(f"module test: pure\nglass apply(callback) {{ {body} }}"))
    core = Interpreter()
    core.interpret(parse('glass output() { print("forbidden") }'))
    with pytest.raises(RuntimeError, match="pure"):
        pure.env.get("apply")(core.env.get("output"))
    assert capsys.readouterr().out == ""


def test_pure_import_cannot_downgrade_mode(tmp_path, capsys):
    (tmp_path / "effect.thirsty").write_text(
        'module effect: core\nprint("forbidden")', encoding="utf-8"
    )
    caller = governed('when action == "import" => ALLOW')
    caller.source_directory = tmp_path
    with pytest.raises(ImportError, match="pure"):
        caller.interpret(parse('module test: pure\nimport "effect.thirsty" as effect'))
    assert capsys.readouterr().out == ""


def test_import_shares_full_live_restrictions(tmp_path, monkeypatch):
    (tmp_path / "module.thirsty").write_text(
        "module test: core\nglass value() { return 1 }", encoding="utf-8"
    )
    parent = governed()
    parent.set_verified_authority(VerifiedAuthority("operator", ("read", "write")))
    parent.set_hardened()
    parent.set_path_guard([tmp_path])
    parent.source_directory = tmp_path
    captured = []
    original = Interpreter.interpret

    def capture(child, *args, **kwargs):
        captured.append(child)
        return original(child, *args, **kwargs)

    monkeypatch.setattr(Interpreter, "interpret", capture)
    monkeypatch.setattr(parent, "_gate_capability", lambda *args, **kwargs: None)
    module = parent._import_thirsty_file("module.thirsty")
    child = captured[0]
    assert child.hardened and child.authority_authenticated
    assert child.authority_grants == ("read", "write")
    assert child._verified_authority is parent._verified_authority
    assert child.path_guard is parent.path_guard
    assert child.tarl_runtime is parent.tarl_runtime
    assert child.mode == "core"
    assert child._governance_is_required()
    assert module["value"]() == 1
    parent.set_authority(None)
    assert child.authority is None
    assert not child.authority_authenticated
    assert child.authority_grants == ()


def test_nested_imported_closure_observes_revocation(tmp_path, capsys):
    package = tmp_path / "package"
    package.mkdir()
    (package / "inner.thirsty").write_text(
        'glass output() { print("allowed") }', encoding="utf-8"
    )
    (package / "outer.thirsty").write_text(
        'import "inner.thirsty" as inner\nglass output() { inner.output() }',
        encoding="utf-8",
    )
    parent = governed()
    parent.source_directory = tmp_path
    parent.set_path_guard([tmp_path])
    imported = parent._import_thirsty_file("package/outer.thirsty")
    imported["output"]()
    assert capsys.readouterr().out == "allowed\n"
    parent.set_authority(None)
    with pytest.raises(GovernanceViolation):
        imported["output"]()
    assert capsys.readouterr().out == ""


def test_import_path_guard_prevents_source_access(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.thirsty"
    outside.write_text('print("forbidden")', encoding="utf-8")
    parent = governed()
    parent.source_directory = allowed
    parent.set_path_guard([allowed])
    reads = []
    parent.set_locked(SimpleNamespace(read_source=lambda path: reads.append(path)))
    with pytest.raises(GovernanceViolation):
        parent._import_thirsty_file("../outside.thirsty")
    assert reads == []


@pytest.mark.parametrize("source", ["drink value = 1 @", "glass f( {"])
def test_import_lexical_and_parse_errors_are_fatal(tmp_path, source):
    (tmp_path / "bad.thirsty").write_text(source, encoding="utf-8")
    parent = governed('when action == "import" => ALLOW')
    parent.source_directory = tmp_path
    with pytest.raises(ImportError, match="Failed to import"):
        parent.interpret(parse('import "bad.thirsty" as bad'))


def test_cyclic_import_reports_error(tmp_path):
    (tmp_path / "a.thirsty").write_text('import "b.thirsty" as b', encoding="utf-8")
    (tmp_path / "b.thirsty").write_text('import "a.thirsty" as a', encoding="utf-8")
    parent = governed('when action == "import" => ALLOW')
    parent.source_directory = tmp_path
    with pytest.raises(ImportError, match="Cyclic file import"):
        parent._import_thirsty_file("a.thirsty")


def test_locked_context_propagates_and_supplies_executed_bytes(tmp_path):
    (tmp_path / "a.thirsty").write_text("invalid on disk", encoding="utf-8")
    reads = []
    namespaces = []

    def read_source(path):
        reads.append(path)
        return 'import "thirst::json" as json\ndrink value = 42'

    parent = governed('when action == "import" => ALLOW').set_locked(
        SimpleNamespace(read_source=read_source, verify_stdlib=namespaces.append)
    )
    parent.source_directory = tmp_path
    module = parent._import_thirsty_file("a.thirsty")
    assert module["value"] == 42
    assert reads == [(tmp_path / "a.thirsty").resolve()]
    assert namespaces == ["thirst::json"]


@pytest.mark.parametrize(
    "source",
    [
        "drink values = [1, missing_identifier]",
        "glass f(x) { return x }\nf(1, missing_identifier)",
        "drink value = flood missing_identifier",
        "drink value = drip missing_identifier",
        "drink value = condense missing_identifier",
        "drink value = evaporate missing_identifier",
        "drink value = new Missing(missing_identifier)",
        "unknown_target = missing_identifier",
    ],
)
def test_checker_visits_previously_hidden_subexpressions(source):
    errors = check_ast(parse(source))
    assert any(
        error.code == "E011" and "missing_identifier" in error.message
        for error in errors
    )


def test_array_inference_visits_all_elements_and_widens():
    checker = Checker()
    checker.check_all(parse('drink mixed = [1, "two"]\ndrink numeric = [1, 2.5]'))
    mixed = checker.scope.lookup("mixed")["type"]
    numeric = checker.scope.lookup("numeric")["type"]
    assert isinstance(mixed, ReservoirType) and isinstance(mixed.inner_type, AnyType)
    assert isinstance(numeric.inner_type, FloatType)


@pytest.mark.parametrize(
    "source",
    [
        "shield { drink value = 1 }",
        "detect { drink value = 1 }",
        "defend protection(rules) { action }",
        "sanitize(1)",
        "armor(1)",
        "interface Shape { area() -> Int }",
    ],
)
def test_unimplemented_protections_never_succeed_silently(source):
    ast = parse(source)
    assert any(error.code == "E901" for error in check_ast(ast))
    with pytest.raises(NotImplementedError):
        Interpreter().interpret(ast)


def test_unknown_ast_nodes_fail_explicitly():
    interpreter = Interpreter()
    with pytest.raises(NotImplementedError, match="unsupported statement"):
        interpreter._execute(Stmt(span=(1, 1, 1, 1)))
    with pytest.raises(NotImplementedError, match="unsupported expression"):
        interpreter._evaluate(Expr(span=(1, 1, 1, 1)))


def test_debug_governance_denial_cannot_be_swallowed(capsys):
    interpreter = Interpreter(debug_mode=True)
    source = 'module test: governed\nspillage { print("forbidden") } error { drink swallowed = true }'
    with pytest.raises(GovernanceViolation):
        interpreter.interpret(parse(source))
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("optimization", [0, 1, 2, 3])
def test_return_call_occurs_once_and_unwinds(optimization):
    source = "drink mut calls = 0\nglass once() { calls = calls + 1\nreturn calls }\nglass caller() { return once()\ncalls = 100 }\ncaller()\ncalls"
    assert Interpreter(opt_level=optimization).interpret(parse(source)) == 1


def test_constructor_failure_restores_environment():
    interpreter = Interpreter()
    original = interpreter.env
    interpreter.interpret(
        parse("fountain Broken { glass init() { missing_identifier } }")
    )
    with pytest.raises(NameError):
        interpreter.interpret(parse("new Broken()"))
    assert interpreter.env is original


@pytest.mark.parametrize(
    "source", ["false and missing_identifier", "true or missing_identifier"]
)
def test_boolean_operators_short_circuit(source):
    assert isinstance(Interpreter().interpret(parse(source)), bool)


def test_core_header_cannot_disable_hardened_requirements(capsys):
    with pytest.raises(
        GovernanceViolation, match=r"authenticated \(signed\) authority"
    ):
        Interpreter().set_hardened().interpret(
            parse('module test: core\nprint("forbidden")')
        )
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("restriction", ["hardened", "required-audit"])
def test_new_restrictions_reach_existing_core_closures(restriction, capsys):
    interpreter = Interpreter(allow_ungoverned=True)
    interpreter.interpret(parse('glass output() { print("forbidden") }'))
    if restriction == "hardened":
        interpreter.set_hardened()
    else:
        interpreter.attach_tarl(
            TarlRuntime(PolicyParser.parse("when true => ALLOW")).set_require_audit()
        )
    with pytest.raises(GovernanceViolation):
        interpreter.env.get("output")()
    assert capsys.readouterr().out == ""


def test_required_audit_cannot_be_silently_attached_to_core(capsys):
    interpreter = Interpreter().attach_tarl(
        TarlRuntime(PolicyParser.parse("when true => ALLOW")).set_require_audit()
    )
    with pytest.raises(GovernanceViolation):
        interpreter.interpret(parse('print("forbidden")'))
    assert capsys.readouterr().out == ""


def test_nominal_enums_and_typed_structs_execute():
    source = "enum Color { Red, Blue }\nstruct Point { x: Int\n color: Color }\ndrink point = new Point(2, Color.Red)\npoint.x = 3\npoint.x == 3 and point.color == Color.Red"
    ast = parse(source)
    assert check_ast(ast) == []
    assert Interpreter().interpret(ast) is True


@pytest.mark.parametrize(
    "expression", ['new Point("wrong")', "new Point()", "new Point(1, 2)"]
)
def test_struct_constructor_rejects_wrong_types_and_arity(expression):
    ast = parse(f"struct Point {{ x: Int }}\n{expression}")
    assert check_ast(ast)
    with pytest.raises(TypeError):
        Interpreter().interpret(ast)


def test_struct_assignment_rejects_wrong_type():
    with pytest.raises(TypeError, match="requires Int"):
        Interpreter().interpret(
            parse(
                'struct Point { x: Int }\ndrink point = new Point(1)\npoint.x = "wrong"'
            )
        )


def test_enum_variants_keep_nominal_identity():
    assert (
        Interpreter().interpret(
            parse("enum A { Value }\nenum B { Value }\nA.Value == B.Value")
        )
        is False
    )


def test_uncaught_throw_remains_failure():
    from utf.thirsty_lang.interpreter import SpillageException

    with pytest.raises(SpillageException, match="validation failed"):
        Interpreter().interpret(parse('throw "validation failed"'))


@pytest.mark.parametrize("change", ["expire", "revoke", "broken-clock"])
def test_imported_governed_function_observes_credential_lifetime(tmp_path, change):
    import datetime as dt

    from utf.tarl.authority import AuthorityIssuer, AuthorityVerifier

    now = dt.datetime(2026, 9, 6, tzinfo=dt.UTC)
    issuer = AuthorityIssuer("issuer", bytes(range(32)))
    verifier = AuthorityVerifier().add_ed25519_key("issuer", issuer.public_key_bytes())
    claim = issuer.issue("operator", ["import", "function"], ttl_seconds=60, now=now)
    verified = verifier.verify(claim, now=now)
    assert verified.valid
    parent = governed(
        'when action == "import" => ALLOW\nwhen action == "value" => ALLOW'
    )
    parent.set_verified_authority(verified.authority)
    parent.tarl_runtime.set_clock(lambda: now)
    parent.source_directory = tmp_path
    (tmp_path / "library.thirsty").write_text(
        "glass value() requires true { return 1 }", encoding="utf-8"
    )
    library = parent._import_thirsty_file("library.thirsty")
    assert library["value"]() == 1
    if change == "expire":
        now += dt.timedelta(seconds=60)
    elif change == "revoke":
        verifier.revoke_key("issuer")
    else:
        parent.tarl_runtime.set_clock(lambda: "not a clock")
    with pytest.raises(GovernanceViolation):
        library["value"]()


@pytest.mark.parametrize("route", ["broker", "function"])
@pytest.mark.parametrize("denial_sink_fails", [False, True])
def test_authority_revoked_during_audit_cannot_reach_effect(route, denial_sink_fails):
    import datetime as dt

    from utf.tarl.authority import AuthorityIssuer, AuthorityVerifier
    from utf.tarl.broker import CapabilityBroker
    from utf.tarl.spec import TarlVerdict

    now = dt.datetime(2026, 9, 6, tzinfo=dt.UTC)
    issuer = AuthorityIssuer("issuer", bytes(range(32)))
    verifier = AuthorityVerifier().add_ed25519_key("issuer", issuer.public_key_bytes())
    credential = verifier.verify(
        issuer.issue("operator", ["write"], now=now), now=now
    ).authority
    runtime = TarlRuntime(PolicyParser.parse("when true => ALLOW")).set_clock(
        lambda: now
    )
    records = []

    class RevokingArchive:
        def store(self, proof, **kwargs):
            if proof.verdict == TarlVerdict.DENY and denial_sink_fails:
                raise OSError("denial sink unavailable")
            records.append(proof.verdict)
            verifier.revoke_key("issuer")

    runtime.set_archive(RevokingArchive()).set_require_audit()
    if route == "broker":
        decision = CapabilityBroker(runtime, credential).request("write", "stdout")
        assert not decision.allowed
        assert "issuer" in decision.reason
    else:
        interpreter = (
            Interpreter().attach_tarl(runtime).set_verified_authority(credential)
        )
        source = "module test: governed\ndrink mut effects = 0\nglass action() requires true { effects = effects + 1 }\naction()"
        with pytest.raises(GovernanceViolation, match="issuer"):
            interpreter.interpret(parse(source))
        assert interpreter.env.get("effects") == 0
    assert records == (
        [TarlVerdict.ALLOW]
        if denial_sink_fails
        else [TarlVerdict.ALLOW, TarlVerdict.DENY]
    )


@pytest.mark.parametrize("route", ["broker", "function", "capability"])
@pytest.mark.parametrize(
    "replacement", ["clear", "expire-clear", "different", "restore"]
)
def test_inflight_authority_rebinding_rejects_old_allow(route, replacement, capsys):
    import datetime as dt

    from utf.tarl.broker import CapabilityBroker

    now = dt.datetime(2026, 9, 6, tzinfo=dt.UTC)
    original = VerifiedAuthority(
        "original", ("write",), expires_at=(now + dt.timedelta(seconds=60)).isoformat()
    )
    runtime = TarlRuntime(
        PolicyParser.parse('when authority == "original" => ALLOW\nwhen true => DENY')
    ).set_clock(lambda: now)
    if route == "broker":
        owner = CapabilityBroker(runtime, original)
    else:
        owner = Interpreter().attach_tarl(runtime).set_verified_authority(original)
    evaluate = runtime.evaluate_with_proof

    def rebind_after_evaluation(*args, **kwargs):
        nonlocal now
        result = evaluate(*args, **kwargs)
        # This is deliberately after successful policy/proof evaluation.
        if replacement in {"clear", "expire-clear"}:
            if replacement == "expire-clear":
                now += dt.timedelta(seconds=60)
            owner.set_authority(None)
        elif replacement == "different":
            owner.set_authority(VerifiedAuthority("replacement"))
        else:
            owner.set_authority(None)
            owner.set_authority(original)
        return result

    runtime.evaluate_with_proof = rebind_after_evaluation
    if route == "broker":
        decision = owner.request("write", "stdout")
        assert not decision.allowed
        assert "binding changed" in decision.reason
    else:
        source = (
            "module test: governed\ndrink mut effects = 0\nglass action() requires true { effects = effects + 1 }\naction()"
            if route == "function"
            else 'module test: governed\nprint("forbidden")'
        )
        denial = (
            "binding changed|expired"
            if replacement == "expire-clear"
            else "binding changed"
        )
        with pytest.raises(GovernanceViolation, match=denial):
            owner.interpret(parse(source))
        if route == "function":
            assert owner.env.get("effects") == 0
    assert capsys.readouterr().out == ""
