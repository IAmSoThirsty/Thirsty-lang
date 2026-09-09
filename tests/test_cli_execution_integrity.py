"""Run restrictions cannot disappear at CLI dispatch or storage failures."""

import sys

import pytest

from utf.tarl.archive import TarlAuditArchive
from utf.thirsty_lang import cli
from utf.thirsty_lang.package_manager import PackageManager


def invoke(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["thirsty", *map(str, args)])
    cli.main()


def program(tmp_path, mode="governed"):
    source = tmp_path / "main.thirsty"
    source.write_text(f'module main: {mode}\npour "executed"\n', encoding="utf-8")
    policy = tmp_path / "policy.tarl"
    policy.write_text("when true => ALLOW\n", encoding="utf-8")
    return source, policy


def test_required_audit_persists_before_effect(monkeypatch, tmp_path, capsys):
    source, policy = program(tmp_path)
    db = tmp_path / "proofs.db"
    invoke(
        monkeypatch,
        "run",
        source,
        "--policy",
        policy,
        "--require-audit",
        "--audit-db",
        db,
    )
    assert "executed" in capsys.readouterr().out
    with TarlAuditArchive(str(db)) as archive:
        assert archive.verify_chain().valid
        assert len(archive.query()) == 1


def test_required_audit_storage_failure_prevents_effect(monkeypatch, tmp_path, capsys):
    source, policy = program(tmp_path)

    def unavailable(*_args, **_kwargs):
        raise OSError("disk unavailable")

    monkeypatch.setattr(TarlAuditArchive, "store", unavailable)
    with pytest.raises(SystemExit) as exc:
        invoke(
            monkeypatch,
            "run",
            source,
            "--policy",
            policy,
            "--require-audit",
            "--audit-db",
            tmp_path / "proofs.db",
        )
    assert exc.value.code == 2
    assert "executed" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "options", [[], ["--require-audit"], ["--audit-db", "unused.db"]]
)
def test_missing_policy_or_archive_is_not_silently_accepted(
    monkeypatch, tmp_path, options
):
    source, policy = program(tmp_path)
    arguments = ["--require-audit"] if not options else options
    if options == ["--require-audit"]:
        arguments += ["--policy", str(policy)]
    with pytest.raises(SystemExit) as exc:
        invoke(monkeypatch, "run", source, *arguments)
    assert exc.value.code == 1


def test_required_audit_preserves_core_semantics_with_governance(
    monkeypatch, tmp_path, capsys
):
    source, policy = program(tmp_path, "core")
    db = tmp_path / "proofs.db"
    invoke(
        monkeypatch,
        "run",
        source,
        "--policy",
        policy,
        "--require-audit",
        "--audit-db",
        db,
    )
    assert "executed" in capsys.readouterr().out
    with TarlAuditArchive(str(db)) as archive:
        assert archive.verify_chain().valid
        assert len(archive.query()) == 1


@pytest.mark.parametrize(
    "option,value",
    [
        ("--policy", "policy.tarl"),
        ("--authority", "admin"),
        ("--audit-db", "proofs.db"),
        ("--thirst-level", "governed"),
    ],
)
def test_gods_delegation_cannot_drop_restrictions(monkeypatch, tmp_path, option, value):
    source = tmp_path / "main.thirstofgods"
    source.write_text("not executed", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        invoke(monkeypatch, "run", source, option, value)
    assert exc.value.code == 1


def test_locked_entrypoint_tampering_is_rejected(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    source, _ = program(tmp_path, "core")
    manager = PackageManager(str(tmp_path))
    manager.generate_lock()
    assert manager.write_lock()
    source.write_text('pour "tampered"\n', encoding="utf-8")
    with pytest.raises(SystemExit):
        invoke(monkeypatch, "run", source, "--locked")
    assert "tampered" not in capsys.readouterr().out


def test_audit_mismatch_and_lock_write_failure_have_failure_exit(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        invoke(monkeypatch, "audit")
    monkeypatch.setattr(PackageManager, "write_lock", lambda _self: False)
    with pytest.raises(SystemExit):
        invoke(monkeypatch, "lock")


def test_missing_run_source_is_explicit(monkeypatch, capsys):
    with pytest.raises(SystemExit):
        invoke(monkeypatch, "run")
    assert "source file" in capsys.readouterr().err
