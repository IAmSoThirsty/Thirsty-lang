"""
Thirsty-Lang CLI — Command-line interface with all subcommands.
"""

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

from utf.thirsty_lang import __version__
from utf.thirsty_lang.ast import (
    ArrayLiteral,
    AssignStmt,
    BinaryOp,
    BlockStmt,
    BoolLiteral,
    CallExpr,
    ExprStmt,
    FloatLiteral,
    FunctionDecl,
    Identifier,
    IntLiteral,
    NoneLiteral,
    ReturnStmt,
    StringLiteral,
    UnaryOp,
    VariableDecl,
)
from utf.thirsty_lang.execution import resolve_execution_mode
from utf.thirsty_lang.token import TokenType


def main():
    """Main entry point for the Thirsty-Lang CLI."""
    from utf.console import enable_utf8

    enable_utf8()
    parser = argparse.ArgumentParser(
        prog="thirsty",
        description="Thirsty-Lang: A governance-first programming language",
        epilog="For more information, see https://thirsty-lang.dev",
    )
    parser.add_argument(
        "--version", action="version", version=f"Thirsty-Lang {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # run
    run_parser = subparsers.add_parser("run", help="Run a .thirsty file")
    run_parser.add_argument("file", nargs="?", help="Path to .thirsty file")
    run_parser.add_argument(
        "--trace", action="store_true", help="Enable execution tracing"
    )
    run_parser.add_argument(
        "--release",
        action="store_true",
        help="Suppress verbose error output, show user-friendly messages",
    )
    run_parser.add_argument(
        "--opt",
        type=int,
        choices=[0, 1, 2, 3],
        default=0,
        help="Optimization level (0-3)",
    )
    run_parser.add_argument(
        "--thirst-level",
        choices=["core", "governed"],
        default=None,
        help="Requested semantics; governance is required by default",
    )
    run_parser.add_argument(
        "--unsafe-core",
        action="store_true",
        help="Explicitly permit ungoverned compatibility execution; cannot be combined with security controls",
    )
    run_parser.add_argument(
        "--authority",
        type=str,
        help="Authority tag injected into the governance context for governed mode",
    )
    run_parser.add_argument(
        "--policy",
        type=str,
        help="Path to a .tarl policy file to route governed calls through",
    )
    run_parser.add_argument(
        "--context-schema",
        type=str,
        metavar="FILE",
        help=(
            "Explicit context schema JSON for governed policy authority; "
            "otherwise a complete schema is derived from the policy"
        ),
    )
    run_parser.add_argument("--demo", action="store_true", help="Run demo program")
    run_parser.add_argument(
        "--locked",
        action="store_true",
        help="Require lockfile verification before executing",
    )
    run_parser.add_argument(
        "--hardened",
        action="store_true",
        help="Hardened posture: require an authenticated (signed) authority and Ed25519-signed proofs at every governed gate",
    )
    run_parser.add_argument(
        "--audit-db",
        metavar="FILE",
        help="Persist decision proofs in a local SQLite archive",
    )
    run_parser.add_argument(
        "--require-audit",
        action="store_true",
        help="Require --policy and --audit-db; deny effects when evidence cannot be persisted",
    )
    run_parser.add_argument(
        "--authority-token",
        type=str,
        metavar="FILE",
        help="Path to a signed authority claim (JSON) authenticating the authority",
    )
    run_parser.add_argument(
        "--authority-key",
        type=str,
        action="append",
        metavar="ID:HEX",
        help="Trusted issuer Ed25519 public key for verifying the authority token (deprecated: hex on argv is exposed; prefer --authority-key-file)",
    )
    run_parser.add_argument(
        "--authority-key-file",
        type=str,
        action="append",
        metavar="FILE",
        help="Trusted issuer Ed25519 public key file from 'tarl keygen' (repeatable)",
    )
    run_parser.add_argument(
        "--sign-proofs",
        type=str,
        metavar="ID:HEX",
        help="Ed25519 private seed (hex) the runtime uses to sign decision proofs (deprecated: hex on argv is exposed; prefer --sign-proofs-file)",
    )
    run_parser.add_argument(
        "--sign-proofs-file",
        type=str,
        metavar="FILE",
        help="Ed25519 proof-signer private key file from 'tarl keygen'",
    )

    # repl
    repl_parser = subparsers.add_parser("repl", help="Start interactive REPL")
    repl_parser.add_argument(
        "--trace", action="store_true", help="Show stack traces on errors"
    )
    repl_parser.add_argument(
        "--opt",
        type=int,
        choices=[0, 1, 2, 3],
        default=0,
        help="Optimization level (0-3)",
    )
    repl_parser.add_argument(
        "--thirst-level",
        choices=["core", "governed"],
        default=None,
        help="Requested semantics; governance is required by default",
    )
    repl_parser.add_argument(
        "--unsafe-core",
        action="store_true",
        help="Explicitly permit ungoverned compatibility execution",
    )

    # fmt
    fmt_parser = subparsers.add_parser("fmt", help="Format .thirsty files")
    fmt_parser.add_argument("files", nargs="+", help="Files to format")
    fmt_parser.add_argument(
        "--check", action="store_true", help="Check formatting without modifying"
    )

    # new
    new_parser = subparsers.add_parser(
        "new", help="Scaffold a new Thirsty-Lang project"
    )
    new_parser.add_argument("name", help="Project name")
    new_parser.add_argument(
        "--mode",
        choices=["core", "governed"],
        default="governed",
        help="Default governance mode",
    )

    # build
    build_parser = subparsers.add_parser("build", help="Build a .thirsty project")
    build_parser.add_argument(
        "--target",
        choices=[
            "llvm-ir",
            "llvm-obj",
            "llvm-exe",
            "llvm-asm",
            "llvm-jit",
            "js",
            "wasm-pyodide",
        ],
        default="js",
        help="Build target",
    )
    build_parser.add_argument(
        "--emit-manifest", action="store_true", help="Emit governance manifest"
    )
    build_parser.add_argument(
        "--allow-governance-loss",
        action="store_true",
        help="Acknowledge unavailable host governance in the build target; always emits a disclosure manifest",
    )
    build_parser.add_argument(
        "--policy",
        type=str,
        help="Path to a .tarl policy file to bind into the emitted manifest",
    )
    build_parser.add_argument(
        "--context-schema",
        type=str,
        metavar="FILE",
        help="Path to an explicit context schema JSON file for the emitted manifest",
    )
    build_parser.add_argument("file", nargs="?", help="Entry point .thirsty file")

    # prove
    prove_parser = subparsers.add_parser(
        "prove", help="Emit static proof-obligation report without executing effects"
    )
    prove_parser.add_argument("file", help="Path to .thirsty file")
    prove_parser.add_argument(
        "--policy", required=True, type=str, help="Path to the .tarl policy file"
    )
    prove_parser.add_argument(
        "--context-schema",
        type=str,
        metavar="FILE",
        help="Path to an explicit context schema JSON file",
    )
    prove_parser.add_argument(
        "--emit-manifest",
        action="store_true",
        help="Write <program>.proof-obligations.json as well as stdout",
    )

    # explain-denial
    explain_parser = subparsers.add_parser(
        "explain-denial",
        help="Explain missing policy/context/authority/proof conditions",
    )
    explain_parser.add_argument("file", help="Path to .thirsty file")
    explain_parser.add_argument(
        "--policy", type=str, help="Path to a .tarl policy file"
    )
    explain_parser.add_argument(
        "--context-schema",
        type=str,
        metavar="FILE",
        help="Path to an explicit context schema JSON file",
    )

    # govern
    govern_parser = subparsers.add_parser("govern", help="Governance operations")
    govern_parser.add_argument("file", nargs="?", help="Path to .thirsty file")
    govern_parser.add_argument(
        "--report", action="store_true", help="Generate governance report"
    )
    govern_parser.add_argument(
        "--auto-tarl", action="store_true", help="Auto-generate T.A.R.L. policy"
    )
    govern_parser.add_argument(
        "--enforce", action="store_true", help="Exit 1 if any function gets DENY"
    )

    # add
    add_parser = subparsers.add_parser("add", help="Add a dependency")
    add_parser.add_argument(
        "package", help="Package name with optional version (e.g., pkg@1.0)"
    )

    # audit
    audit_parser = subparsers.add_parser(
        "audit", help="Audit dependencies for integrity"
    )
    audit_parser.add_argument(
        "--fix", action="store_true", help="Attempt to fix issues"
    )

    # lock
    lock_parser = subparsers.add_parser("lock", help="Generate lockfile")
    lock_parser.add_argument(
        "--update", action="store_true", help="Update existing lockfile"
    )

    # doctor
    doctor_parser = subparsers.add_parser("doctor", help="Project health check")
    doctor_parser.add_argument(
        "--fix", action="store_true", help="Attempt to fix issues"
    )

    # lsp
    lsp_parser = subparsers.add_parser("lsp", help="Start LSP server")
    lsp_parser.add_argument("--stdio", action="store_true", help="Use stdio mode")
    lsp_parser.add_argument("--port", type=int, default=9898, help="TCP port")

    # docs
    docs_parser = subparsers.add_parser("docs", help="Generate documentation")
    docs_parser.add_argument("--output-dir", default="./docs", help="Output directory")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    try:
        if args.command == "run":
            cmd_run(args)
        elif args.command == "repl":
            cmd_repl(args)
        elif args.command == "fmt":
            cmd_fmt(args)
        elif args.command == "new":
            cmd_new(args)
        elif args.command == "build":
            cmd_build(args)
        elif args.command == "prove":
            cmd_prove(args)
        elif args.command == "explain-denial":
            cmd_explain_denial(args)
        elif args.command == "govern":
            cmd_govern(args)
        elif args.command == "add":
            cmd_add(args)
        elif args.command == "audit":
            cmd_audit(args)
        elif args.command == "lock":
            cmd_lock(args)
        elif args.command == "doctor":
            cmd_doctor(args)
        elif args.command == "lsp":
            cmd_lsp(args)
        elif args.command == "docs":
            cmd_docs(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if os.environ.get("THIRSTY_DEBUG"):
            traceback.print_exc()
        sys.exit(1)


def _lex_parse_check(
    file_path: str, mode: str | None = None, effect_warnings: bool = False
):
    """Helper: lex, parse, and type-check a file. Returns (ast, errors, checker)."""
    from utf.thirsty_lang.checker import check_ast
    from utf.thirsty_lang.lexer import Lexer
    from utf.thirsty_lang.parser import Parser

    with open(file_path, encoding="utf-8") as f:
        source = f.read()

    lexer = Lexer(source)
    tokens = lexer.lex()

    parser = Parser(tokens)
    ast = parser.parse()

    # Check for lexer/parser errors
    errors = list(lexer.errors)
    errors.extend(parser.errors)
    errors.extend(check_ast(ast, effect_warnings=effect_warnings, mode=mode))

    return ast, errors, source


def cmd_run(args):
    """Execute a .thirsty file."""
    from utf.thirsty_lang.checker import check_ast
    from utf.thirsty_lang.diagnostics import DiagnosticBundle
    from utf.thirsty_lang.interpreter import GovernanceViolation, Interpreter
    from utf.thirsty_lang.lexer import Lexer
    from utf.thirsty_lang.module_system import LockedImports
    from utf.thirsty_lang.parser import Parser

    unsafe_core = getattr(args, "unsafe_core", False)
    security_options = (
        "locked",
        "policy",
        "context_schema",
        "authority",
        "authority_token",
        "authority_key",
        "authority_key_file",
        "sign_proofs",
        "sign_proofs_file",
        "hardened",
        "audit_db",
        "require_audit",
    )
    if unsafe_core and (
        any(
            value is not None and value is not False
            for value in (getattr(args, name, None) for name in security_options)
        )
        or args.thirst_level == "governed"
    ):
        print(
            "Error: --unsafe-core cannot be combined with governance or security controls",
            file=sys.stderr,
        )
        sys.exit(1)
    if unsafe_core:
        print(
            "Warning: --unsafe-core permits ungoverned compatibility execution",
            file=sys.stderr,
        )

    locked_imports = None
    if getattr(args, "locked", False):
        if args.demo:
            print("Error: --locked requires a project source file", file=sys.stderr)
            sys.exit(1)
        try:
            locked_imports = LockedImports(os.getcwd())
        except (OSError, ValueError, ImportError) as exc:
            print(f"Error: lockfile validation failed: {exc}", file=sys.stderr)
            sys.exit(1)

    if args.demo:
        source = """module hello: governed

glass greet(name: String) {
    return "hello, " + name + "!"
}

drink main = "thirsty world"
drink result = greet(main)
result
"""
        file_path = "<demo>"
    else:
        file_path = args.file
        if not file_path:
            print("Error: run requires a source file or --demo", file=sys.stderr)
            sys.exit(1)
        if file_path.endswith(".thirstofgods"):
            restrictions = (
                "policy",
                "context_schema",
                "authority",
                "authority_token",
                "authority_key",
                "authority_key_file",
                "sign_proofs",
                "sign_proofs_file",
                "hardened",
                "audit_db",
                "require_audit",
            )
            if (
                locked_imports is not None
                or any(
                    value is not None and value is not False
                    for value in (getattr(args, name, None) for name in restrictions)
                )
                or args.thirst_level is not None
                or unsafe_core
            ):
                print(
                    "Error: restricted runs of .thirstofgods must use the Thirsty-Lang entry point after explicit conversion",
                    file=sys.stderr,
                )
                sys.exit(1)
            from utf.thirst_of_gods.cli import run as gods_run

            gods_run(file_path)
            return
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        try:
            if locked_imports is not None:
                source = locked_imports.read_source(file_path)
            else:
                with open(file_path, encoding="utf-8") as f:
                    source = f.read()
        except (OSError, UnicodeError, ValueError, ImportError) as exc:
            print(f"Error: cannot load source: {exc}", file=sys.stderr)
            sys.exit(1)

    lexer = Lexer(source)
    tokens = lexer.lex()

    parser = Parser(tokens)
    ast = parser.parse()

    # Check errors
    errors = []
    errors.extend(lexer.errors)
    errors.extend(parser.errors)
    errors.extend(check_ast(ast, mode=args.thirst_level, allow_ungoverned=unsafe_core))

    if errors:
        bundle = DiagnosticBundle(errors)
        print(bundle.format_all(), file=sys.stderr)
        sys.exit(1)

    interpreter = Interpreter(
        opt_level=args.opt, debug_mode=args.trace, allow_ungoverned=unsafe_core
    )
    if not args.demo:
        interpreter.source_directory = Path(file_path).resolve().parent
    if locked_imports is not None:
        interpreter.set_locked(locked_imports)
        print("Lockfile verified. Content integrity checks enabled.")

    # Governance wiring: bind the authority tag into the governance context,
    # and route governed calls through a TARL policy engine when --policy
    # supplies a .tarl file.
    authority = getattr(args, "authority", None)
    if authority:
        interpreter.set_authority(authority)
    policy_path = getattr(args, "policy", None)
    runtime = None
    if policy_path:
        if not os.path.isfile(policy_path):
            print(f"Error: policy file not found: {policy_path}", file=sys.stderr)
            sys.exit(1)
        from utf.tarl.core import PolicyParser
        from utf.tarl.runtime import TarlRuntime

        with open(policy_path, encoding="utf-8") as pf:
            policy = PolicyParser.parse(pf.read())
        runtime = TarlRuntime(policy)
        schema_path = getattr(args, "context_schema", None)
        if schema_path:
            if not os.path.isfile(schema_path):
                print(
                    f"Error: context schema file not found: {schema_path}",
                    file=sys.stderr,
                )
                sys.exit(1)
            from utf.tarl.schema import ContextSchema
            from utf.thirsty_lang.proof_obligations import (
                load_explicit_context_schema,
            )

            try:
                described_schema = load_explicit_context_schema(schema_path)
                runtime.set_context_schema(
                    ContextSchema.from_dict(described_schema.to_dict())
                )
            except (OSError, ValueError) as exc:
                print(f"Error: invalid context schema: {exc}", file=sys.stderr)
                sys.exit(1)
        interpreter.attach_tarl(runtime)
        # A policy with no authority tag still needs a context to evaluate.
        if authority is None:
            interpreter.set_authority("")
    elif getattr(args, "context_schema", None):
        print("Error: --context-schema requires --policy", file=sys.stderr)
        sys.exit(1)

    # Authenticated authority provenance: verify a signed claim against trusted
    # issuer keys and bind the authenticated identity (overriding any bare tag).
    token_path = getattr(args, "authority_token", None)
    if token_path:
        from utf.tarl.authority import AuthorityClaim, AuthorityVerifier

        if not os.path.isfile(token_path):
            print(f"Error: authority token not found: {token_path}", file=sys.stderr)
            sys.exit(1)
        verifier = AuthorityVerifier()
        for spec in getattr(args, "authority_key", None) or []:
            kid, _, hexkey = spec.partition(":")
            try:
                verifier.add_ed25519_key(kid, bytes.fromhex(hexkey))
            except ValueError as e:
                print(f"Error: invalid --authority-key {spec!r}: {e}", file=sys.stderr)
                sys.exit(1)
        for key_path in getattr(args, "authority_key_file", None) or []:
            from utf.tarl import keystore

            try:
                kf = keystore.load(key_path)
                if kf.role != keystore.ROLE_AUTHORITY_ISSUER:
                    raise ValueError("expected an authority-issuer key")
                verifier.add_ed25519_key(kf.key_id, kf.public_bytes())
            except (OSError, ValueError) as e:
                print(
                    f"Error: invalid --authority-key-file {key_path!r}: {e}",
                    file=sys.stderr,
                )
                sys.exit(1)
        with open(token_path, encoding="utf-8") as tf:
            claim = AuthorityClaim.from_json(tf.read())
        auth_result = verifier.verify(claim)
        if not auth_result.valid:
            print(
                f"Error: authority token rejected: {auth_result.reason}",
                file=sys.stderr,
            )
            sys.exit(1)
        interpreter.set_verified_authority(auth_result.authority)

    # Proof signing: give the runtime an Ed25519 key so decision proofs are
    # non-repudiable (required by hardened mode).
    sign_spec = getattr(args, "sign_proofs", None)
    sign_file = getattr(args, "sign_proofs_file", None)
    if sign_file and runtime is not None:
        from utf.tarl import keystore

        try:
            kf = keystore.load(sign_file)
            if kf.role != keystore.ROLE_PROOF_SIGNER:
                raise ValueError("expected a proof-signer key")
            runtime.set_ed25519_signing_key(kf.key_id, kf.private_bytes())
        except (OSError, ValueError) as e:
            print(
                f"Error: invalid --sign-proofs-file {sign_file!r}: {e}", file=sys.stderr
            )
            sys.exit(1)
    elif sign_spec and runtime is not None:
        kid, _, hexseed = sign_spec.partition(":")
        try:
            runtime.set_ed25519_signing_key(kid, bytes.fromhex(hexseed))
        except ValueError as e:
            print(f"Error: invalid --sign-proofs key: {e}", file=sys.stderr)
            sys.exit(1)

    if getattr(args, "hardened", False):
        interpreter.set_hardened(True)

    audit_path = getattr(args, "audit_db", None)
    require_audit = getattr(args, "require_audit", False)
    if (audit_path or require_audit or sign_file or sign_spec) and runtime is None:
        print(
            "Error: audit and proof-signing options require --policy", file=sys.stderr
        )
        sys.exit(1)
    if require_audit and not audit_path:
        print("Error: --require-audit requires --audit-db", file=sys.stderr)
        sys.exit(1)
    _, governance_required = resolve_execution_mode(
        ast.header.mode if ast.header else None,
        args.thirst_level,
        allow_ungoverned=unsafe_core,
    )
    if require_audit and not governance_required:
        print("Error: --require-audit requires a governed module", file=sys.stderr)
        sys.exit(1)
    archive = None
    if audit_path and runtime is not None:
        from utf.tarl.archive import TarlAuditArchive

        try:
            archive = TarlAuditArchive(audit_path)
        except Exception as exc:
            print(f"Error: audit archive unavailable: {exc}", file=sys.stderr)
            sys.exit(1)
        runtime.set_archive(archive).set_require_audit(require_audit)

    try:
        result = interpreter.interpret(ast, mode=args.thirst_level)
        if result is not None:
            print(result)
    except GovernanceViolation as e:
        print(f"governance denied: {e.name}: {e.reason}", file=sys.stderr)
        if e.proof is not None:
            print(
                f"  proof: verdict={e.proof.verdict} " f"policy={e.proof.policy_hash}",
                file=sys.stderr,
            )
        sys.exit(2)
    except Exception as e:
        if args.release:
            print(f"Error: {e}", file=sys.stderr)
        else:
            print(f"Runtime Error: {e}", file=sys.stderr)
        if args.trace:
            traceback.print_exc()
        sys.exit(1)
    finally:
        if archive is not None:
            archive.close()


def cmd_repl(args):
    """Start an interactive REPL."""
    from utf.thirsty_lang.checker import check_ast
    from utf.thirsty_lang.interpreter import Environment, Interpreter
    from utf.thirsty_lang.lexer import Lexer
    from utf.thirsty_lang.parser import Parser

    debug_enabled = args.trace or os.environ.get("THIRSTY_DEBUG") == "1"

    unsafe_core = getattr(args, "unsafe_core", False)
    if unsafe_core and args.thirst_level == "governed":
        print(
            "Error: --unsafe-core cannot be combined with governed execution",
            file=sys.stderr,
        )
        sys.exit(1)
    mode, governance_required = resolve_execution_mode(
        mode=args.thirst_level, allow_ungoverned=unsafe_core
    )
    if unsafe_core:
        print(
            "Warning: --unsafe-core permits ungoverned compatibility execution",
            file=sys.stderr,
        )
    print(
        f"Thirsty-Lang REPL (mode: {mode}, governance: {'required' if governance_required else 'disabled'}, opt={args.opt})"
    )
    print("Type 'exit' to quit, 'help' for commands, '.clear' to reset state.")
    print()

    interpreter = Interpreter(
        opt_level=args.opt, debug_mode=debug_enabled, allow_ungoverned=unsafe_core
    )
    source_buffer = ""
    pending = False

    while True:
        try:
            if not pending:
                line = input(">>> ")
            else:
                line = input("... ")

            if line.lower() in ("exit", "quit"):
                break
            if line.lower() == "help":
                print("Commands: exit, help, .clear")
                print("Thirsty-Lang expressions and statements")
                continue
            if line.strip() == ".clear":
                interpreter.env = Environment()
                interpreter._register_builtins()
                source_buffer = ""
                pending = False
                print("State cleared.")
                continue
            if line.strip() == "" and not pending:
                continue

            source_buffer += line + "\n"

            # Try to lex/parse the accumulated input
            lexer = Lexer(source_buffer)
            tokens = lexer.lex()
            parser = Parser(tokens)
            try:
                ast = parser.parse()
            except Exception:
                pending = True
                continue

            errors = []
            errors.extend(lexer.errors)
            errors.extend(parser.errors)
            errors.extend(
                check_ast(ast, mode=args.thirst_level, allow_ungoverned=unsafe_core)
            )

            if errors:
                needs_more = False
                for e in errors:
                    msg = (
                        str(e.message).lower()
                        if hasattr(e, "message")
                        else str(e).lower()
                    )
                    if "unexpected end" in msg or "eof" in msg or "expect" in msg:
                        if not pending:
                            needs_more = True
                        break
                if needs_more:
                    pending = True
                    continue
                for e in errors:
                    print(f"  {e.code}: {e.message}")
                source_buffer = ""
                pending = False
                continue

            pending = False
            try:
                result = interpreter.interpret(ast, mode=args.thirst_level)
                if result is not None:
                    print(result)
            except Exception as e:
                print(f"Error: {e}")
                if debug_enabled:
                    import traceback

                    traceback.print_exc()
                source_buffer = ""

        except (EOFError, KeyboardInterrupt):
            print()
            break
        except Exception as e:
            print(f"Error: {e}")
            if debug_enabled:
                import traceback

                traceback.print_exc()
            source_buffer = ""
            pending = False


def cmd_fmt(args):
    """Format .thirsty files."""
    from utf.thirsty_lang.formatter import format
    from utf.thirsty_lang.lexer import Lexer
    from utf.thirsty_lang.parser import Parser

    for file_path in args.files:
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            continue

        with open(file_path, encoding="utf-8") as f:
            source = f.read()

        lexer = Lexer(source)
        tokens = lexer.lex()
        parser = Parser(tokens)
        ast = parser.parse()

        if lexer.errors or parser.errors or ast.parse_failed:
            from utf.thirsty_lang.diagnostics import DiagnosticBundle

            print(
                DiagnosticBundle([*lexer.errors, *parser.errors]).format_all(),
                file=sys.stderr,
            )
            print(
                f"Error: refusing to format malformed source: {file_path}",
                file=sys.stderr,
            )
            sys.exit(1)

        formatted = format(ast)

        if args.check:
            if source.strip() != formatted.strip():
                print(f"{file_path}: would reformat")
                sys.exit(1)
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(formatted)
            print(f"Formatted: {file_path}")


def cmd_new(args):
    """Scaffold a new Thirsty-Lang project."""
    from utf.thirsty_lang.package_manager import (
        create_thirsty_lock,
        create_thirsty_toml,
    )

    project_dir = os.path.join(os.getcwd(), args.name)
    if os.path.exists(project_dir):
        print(f"Error: Directory already exists: {project_dir}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(project_dir)
    os.makedirs(os.path.join(project_dir, "src"))
    os.makedirs(os.path.join(project_dir, "tests"))

    # Create main.thirsty
    main_path = os.path.join(project_dir, "src", "main.thirsty")
    with open(main_path, "w", encoding="utf-8") as f:
        f.write(f"""module {args.name}: {args.mode}

glass greet(name: String) {{
    return "hello, " + name + "!"
}}

drink main = greet("thirsty world")
main
""")

    # Create thirsty.toml
    create_thirsty_toml(project_dir, args.name, mode=args.mode)

    # Create thirsty.lock
    create_thirsty_lock(project_dir)

    print(f"Created Thirsty-Lang project: {args.name}")
    print(f"  cd {project_dir}")
    print("  thirsty run src/main.thirsty")


def cmd_build(args):
    """Build a .thirsty project."""
    from utf.thirsty_lang.lexer import Lexer
    from utf.thirsty_lang.parser import Parser

    if not args.file:
        # Try to find main.thirsty
        main_path = os.path.join(os.getcwd(), "src", "main.thirsty")
        if os.path.exists(main_path):
            args.file = main_path
        else:
            print(
                "Error: No file specified and no src/main.thirsty found",
                file=sys.stderr,
            )
            sys.exit(1)

    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    with open(args.file, encoding="utf-8") as f:
        source = f.read()

    lexer = Lexer(source)
    tokens = lexer.lex()

    parser = Parser(tokens)
    ast = parser.parse()

    from utf.thirsty_lang.checker import check_ast
    from utf.thirsty_lang.diagnostics import DiagnosticBundle

    diagnostics = [*lexer.errors, *parser.errors, *check_ast(ast)]
    if diagnostics or getattr(ast, "parse_failed", False):
        print(DiagnosticBundle(diagnostics).format_all(), file=sys.stderr)
        sys.exit(1)

    _validate_build_mode(ast)

    target = args.target
    base = os.path.splitext(args.file)[0]

    governance_loss = _authorize_build_governance_loss(
        target, getattr(args, "allow_governance_loss", False)
    )

    # Reject unsupported source before disclosure, then persist the required
    # disclosure before producing an executable artifact or invoking a toolchain.
    compiled_code = ""
    if target.startswith("llvm-"):
        compiled_code = _transpile_to_llvm_ir(ast)
    elif target == "js":
        compiled_code = _transpile_to_js(ast)
    elif target != "wasm-pyodide":
        raise ValueError(f"Unsupported build target: {target}")
    _emit_manifest(
        ast,
        args.file,
        source=source,
        target=target,
        governance_loss=governance_loss,
        policy_path=getattr(args, "policy", None),
        context_schema_path=getattr(args, "context_schema", None),
    )

    if target.startswith("llvm-"):
        output_path = _build_llvm(ast, base, target, ir=compiled_code)
        print(f"Built: {output_path}")

    elif target == "js":
        # Simple JavaScript transpilation
        output_path = base + ".js"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(compiled_code)
        print(f"Built: {output_path}")

    elif target == "wasm-pyodide":
        output_path = _build_pyodide(source, base, allow_ungoverned=governance_loss)
        print(f"Built: {output_path}")


def _authorize_build_governance_loss(target: str, allowed: bool) -> bool:
    """Public builders require host consent before emitting ungoverned targets."""
    if not allowed:
        print(
            f"Error: refusing to build to '{target}': governance is required by default; "
            "this target cannot preserve host policy/authority enforcement. "
            "Use --allow-governance-loss to acknowledge the loss and emit a disclosure manifest.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(
        f"Warning: governance loss acknowledged for '{target}'; host policy/authority "
        "configuration is unavailable. Pyodide retains explicit governed declarations "
        "and denies their effects without policy.",
        file=sys.stderr,
    )
    return True


def _validate_build_mode(ast) -> None:
    """Preserve strict initialization before any backend artifact is emitted."""
    import dataclasses

    if not ast.header or ast.header.mode != "strict":
        return
    pending = [ast]
    visited = 0
    while pending:
        visited += 1
        if visited > 5000:
            raise ValueError("Strict build AST analysis budget exceeded")
        node = pending.pop()
        if isinstance(node, VariableDecl) and node.init_expr is None:
            raise ValueError("Strict build requires every variable to be initialized")
        if dataclasses.is_dataclass(node):
            pending.extend(
                getattr(node, field.name)
                for field in dataclasses.fields(node)
                if field.name != "span"
            )
        elif isinstance(node, (list, tuple)):
            if len(node) > 5000:
                raise ValueError("Strict build AST analysis budget exceeded")
            pending.extend(node)


def _transpile_to_js(ast) -> str:
    """Internal subset renderer; public builders must authorize governance loss."""

    if getattr(ast, "parse_failed", False):
        raise ValueError("Cannot compile a malformed program")
    _validate_build_mode(ast)
    lines = ["// Generated by Thirsty-Lang compiler", _JS_PRIMITIVES, ""]

    # Only directly declared functions have a supported callable ABI here.
    import dataclasses

    from utf.thirsty_lang.ast import ModuleHeader, Program

    modeled_nodes = {
        Program,
        ModuleHeader,
        IntLiteral,
        FloatLiteral,
        StringLiteral,
        BoolLiteral,
        NoneLiteral,
        Identifier,
        ArrayLiteral,
        BinaryOp,
        UnaryOp,
        CallExpr,
        ExprStmt,
        ReturnStmt,
        VariableDecl,
        AssignStmt,
        FunctionDecl,
        BlockStmt,
    }
    functions = {s.name for s in ast.stmts if type(s) is FunctionDecl}

    visited = 0

    def validate_calls(node, depth=0):
        nonlocal visited
        visited += 1
        if visited > 5000 or depth > 64:
            raise ValueError("JS AST analysis budget exceeded")
        if dataclasses.is_dataclass(node) and type(node) not in modeled_nodes:
            raise ValueError(f"JS target does not support {type(node).__name__}")
        if isinstance(node, CallExpr) and (
            not isinstance(node.callee, Identifier) or node.callee.name not in functions
        ):
            raise ValueError("JS target only supports calls to declared functions")
        if dataclasses.is_dataclass(node):
            for field in dataclasses.fields(node):
                if field.name != "span":
                    validate_calls(getattr(node, field.name), depth + 1)
        elif isinstance(node, (list, tuple)):
            for item in node:
                validate_calls(item, depth + 1)

    validate_calls(ast)

    def validate_scope(statements, names=()):
        seen = set(names)
        for stmt in statements:
            if isinstance(stmt, (VariableDecl, FunctionDecl)):
                if stmt.name in seen:
                    raise ValueError("JS target rejects duplicate bindings in a scope")
                seen.add(stmt.name)
            if type(stmt) is FunctionDecl:
                body = (
                    stmt.body.statements
                    if isinstance(stmt.body, BlockStmt)
                    else [stmt.body]
                )
                validate_scope(body, (p[0] for p in stmt.params))

    validate_scope(ast.stmts)

    # Track main expression
    main_expr = None
    for stmt in ast.stmts:
        if hasattr(stmt, "name") and getattr(stmt, "name", None) == "main":
            if hasattr(stmt, "init_expr") and stmt.init_expr:
                main_expr = stmt.init_expr
            break

    # Generate main execution
    for stmt in ast.stmts:
        if type(stmt) is FunctionDecl:
            # Source-order initialization matches interpreter closure binding;
            # JS function declarations would incorrectly hoist availability.
            params = ", ".join(_js_name(p[0]) for p in stmt.params)
            if len(stmt.params) != len({p[0] for p in stmt.params}):
                raise ValueError("JS target rejects duplicate parameter names")
            lines.append(f"const {_js_name(stmt.name)} = function({params}) {{")
            lines.append(
                f"  if (arguments.length !== {len(stmt.params)}) throw new Error('Argument count mismatch');"
            )
            _js_stmt_body(stmt.body, lines, indent=1)
            lines.append("  return null;")
            lines.append("};")
            lines.append("")
        else:
            if isinstance(stmt, ReturnStmt):
                raise ValueError("JS target rejects top-level return")
            _js_stmt(stmt, lines, indent=0)
            lines.append("")

    if main_expr:
        lines.append(f"console.log(__display({_js_name('main')}));")

    return "\n".join(lines)


_JS_PRIMITIVES = """'use strict';
function __display(v) {
  if (v === null) return 'None';
  if (v === true) return 'True';
  if (v === false) return 'False';
  if (Object.is(v, -0)) return '-0.0';
  if (typeof v === 'number' && Number.isInteger(v)) return String(v) + '.0';
  if (Array.isArray(v)) return '[' + v.map(x => typeof x === 'string' ? JSON.stringify(x) : __display(x)).join(', ') + ']';
  return String(v);
}
function __equal(a, b) {
  if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((v, i) => __equal(v, b[i]));
  const numeric = x => ['number', 'bigint', 'boolean'].includes(typeof x);
  return numeric(a) && numeric(b) ? a == b : a === b;
}
function __intDivide(a, b) {
  if (b === 0n) throw new Error('Division by zero');
  const negative = (a < 0n) !== (b < 0n);
  a = a < 0n ? -a : a; b = b < 0n ? -b : b;
  if (a === 0n) return negative ? -0 : 0;
  let exponent = a.toString(2).length - b.toString(2).length;
  if (exponent >= 0 ? a < (b << BigInt(exponent)) : (a << BigInt(-exponent)) < b) exponent--;
  if (exponent > 1023) throw new Error('Integer division overflow');
  if (exponent < -1075) return negative ? -0 : 0;
  const shift = exponent < -1022 ? 1074 : 52 - exponent;
  const numerator = shift >= 0 ? a << BigInt(shift) : a;
  const denominator = shift >= 0 ? b : b << BigInt(-shift);
  let quotient = numerator / denominator;
  const remainder = numerator % denominator;
  if (2n * remainder > denominator || (2n * remainder === denominator && quotient % 2n === 1n)) quotient++;
  const result = Number(quotient) * (2 ** (-shift));
  if (!Number.isFinite(result)) throw new Error('Integer division overflow');
  return negative ? -result : result;
}
function __truth(v) {
  if (typeof v === 'number') return v !== 0;
  return Array.isArray(v) || typeof v === 'string' ? v.length !== 0 : Boolean(v);
}
function __neg(v) {
  if (typeof v === 'boolean') throw new TypeError('Unary minus does not accept Bool');
  if (!['number', 'bigint'].includes(typeof v)) throw new Error('Numeric operand required');
  return -v;
}
function __binary(op, a, b) {
  const boolA = typeof a === 'boolean', boolB = typeof b === 'boolean';
  if (op === '==' || op === '!=') {
    if (boolA !== boolB) throw new TypeError('Scalar equality cannot mix Bool with another type');
    return op === '==' ? __equal(a, b) : !__equal(a, b);
  }
  if (boolA || boolB) throw new TypeError('Arithmetic and ordering do not accept Bool');
  if (op === '+' && typeof a === 'string' && typeof b === 'string') return a + b;
  if (op === '+' && Array.isArray(a) && Array.isArray(b)) return a.concat(b);
  if (op === '*' && (typeof a === 'string' || Array.isArray(a))) {
    if (typeof b !== 'bigint') throw new Error('Sequence repeat count must be Int');
    const count = Number(b);
    if (count <= 0) return typeof a === 'string' ? '' : [];
    if (!Number.isSafeInteger(count) || count * a.length > 1000000) throw new Error('JS sequence resource limit exceeded');
    if (typeof a === 'string') return a.repeat(count);
    return Array.from({length: count}, () => a).flat();
  }
  if (op === '*' && (typeof b === 'string' || Array.isArray(b))) return __binary(op, b, a);
  if (['<','<=','>','>='].includes(op) && typeof a === 'string' && typeof b === 'string') {
    const aa = Array.from(a, ch => ch.codePointAt(0)), bb = Array.from(b, ch => ch.codePointAt(0));
    let comparison = 0, i = 0;
    while (i < aa.length && i < bb.length && aa[i] === bb[i]) i++;
    comparison = i < aa.length && i < bb.length ? Math.sign(aa[i] - bb[i]) : Math.sign(aa.length - bb.length);
    return op === '<' ? comparison < 0 : op === '<=' ? comparison <= 0 : op === '>' ? comparison > 0 : comparison >= 0;
  }
  if (['<','<=','>','>='].includes(op) && Array.isArray(a) && Array.isArray(b)) {
    let i = 0;
    while (i < a.length && i < b.length && __equal(a[i], b[i])) i++;
    if (i < a.length && i < b.length) {
      // Native container comparison retains its existing element semantics.
      const aa = typeof a[i] === 'boolean' ? BigInt(a[i]) : a[i];
      const bb = typeof b[i] === 'boolean' ? BigInt(b[i]) : b[i];
      return __binary(op, aa, bb);
    }
    return __binary(op, BigInt(a.length), BigInt(b.length));
  }
  if (Array.isArray(a) || Array.isArray(b)) throw new Error('Array operators unsupported by JS target');
  const numeric = x => ['number', 'bigint'].includes(typeof x);
  if (!numeric(a) || !numeric(b)) throw new Error('Numeric operands required by JS target');
  if (op === '/' && typeof a === 'bigint' && typeof b === 'bigint') return __intDivide(a, b);
  if (op === '<') return a < b;
  if (op === '<=') return a <= b;
  if (op === '>') return a > b;
  if (op === '>=') return a >= b;
  if (typeof a !== typeof b || op === '/') {
    if ((typeof a === 'bigint' && !Number.isFinite(Number(a))) ||
        (typeof b === 'bigint' && !Number.isFinite(Number(b)))) throw new Error('Integer conversion overflow');
    a = Number(a); b = Number(b);
  }
  if ((op === '/' || op === '%') && (b === 0 || b === 0n)) throw new Error('Division by zero');
  if (op === '+') return a + b;
  if (op === '-') return a - b;
  if (op === '*') return a * b;
  if (op === '/') return a / b;
  if (op === '%') {
    let r = a % b;
    if (r === 0) return b < 0 ? -0 : 0;
    return r !== 0n && ((r < 0) !== (b < 0)) ? r + b : r;
  }
  throw new Error('Unsupported operator');
}
"""


def _js_name(name: str) -> str:
    # Source identifiers cannot collide with JS keywords or target helpers.
    return "thirst_" + name.encode("utf-8").hex()


def _js_expression(expr) -> str:
    """Convert a Thirsty-Lang expression to JS."""

    if isinstance(expr, IntLiteral):
        return f"{expr.value}n"
    elif isinstance(expr, FloatLiteral):
        return json.dumps(expr.value)
    elif isinstance(expr, StringLiteral):
        return json.dumps(expr.value)
    elif isinstance(expr, BoolLiteral):
        return "true" if expr.value else "false"
    elif isinstance(expr, NoneLiteral):
        return "null"
    elif isinstance(expr, Identifier):
        if expr.name == "__error__":
            raise ValueError("JS target rejects the reserved error identifier")
        return _js_name(expr.name)
    elif isinstance(expr, ArrayLiteral):
        return "[" + ", ".join(_js_expression(e) for e in expr.elements) + "]"
    elif isinstance(expr, BinaryOp):
        op_map = {
            TokenType.PLUS: "+",
            TokenType.MINUS: "-",
            TokenType.STAR: "*",
            TokenType.SLASH: "/",
            TokenType.PERCENT: "%",
            TokenType.EQEQ: "==",
            TokenType.NE: "!=",
            TokenType.LT: "<",
            TokenType.GT: ">",
            TokenType.LE: "<=",
            TokenType.GE: ">=",
            TokenType.AND: "&&",
            TokenType.OR: "||",
        }
        if expr.op not in op_map:
            raise ValueError(f"JS target does not support operator {expr.op.name}")
        left, right = _js_expression(expr.left), _js_expression(expr.right)
        if expr.op in {TokenType.AND, TokenType.OR}:
            choice = (
                f"__truth(v) ? {right} : v"
                if expr.op is TokenType.AND
                else f"__truth(v) ? v : {right}"
            )
            return f"((v) => {choice})({left})"
        return f"__binary({json.dumps(op_map[expr.op])}, {left}, {right})"
    elif isinstance(expr, UnaryOp):
        if expr.op == TokenType.MINUS:
            return f"__neg({_js_expression(expr.operand)})"
        if expr.op == TokenType.NOT:
            return f"(!__truth({_js_expression(expr.operand)}))"
        raise ValueError(f"JS target does not support unary operator {expr.op.name}")
    elif isinstance(expr, CallExpr):
        callee = _js_expression(expr.callee)
        args = ", ".join(_js_expression(a) for a in expr.args)
        return f"{callee}({args})"
    raise ValueError(f"JS target does not support expression {type(expr).__name__}")


def _js_stmt(stmt, lines, indent=0):
    """Convert a Thirsty-Lang statement to JS."""
    prefix = "  " * indent

    if isinstance(stmt, ExprStmt):
        lines.append(f"{prefix}{_js_expression(stmt.expr)};")
    elif isinstance(stmt, ReturnStmt):
        val = _js_expression(stmt.value) if stmt.value else "null"
        lines.append(f"{prefix}return {val};")
    elif isinstance(stmt, VariableDecl):
        value = _js_expression(stmt.init_expr) if stmt.init_expr is not None else "null"
        kind = "let" if stmt.is_mut else "const"
        lines.append(f"{prefix}{kind} {_js_name(stmt.name)} = {value};")
    elif isinstance(stmt, AssignStmt) and isinstance(stmt.target, Identifier):
        lines.append(
            f"{prefix}{_js_name(stmt.target.name)} = {_js_expression(stmt.value)};"
        )
    else:
        raise ValueError(f"JS target does not support statement {type(stmt).__name__}")


def _js_stmt_body(stmt, lines, indent=0):
    """Convert a block statement body to JS."""
    if isinstance(stmt, BlockStmt):
        for s in stmt.statements:
            _js_stmt(s, lines, indent=indent)
    else:
        _js_stmt(stmt, lines, indent=indent)


class _LLVMExpr:
    """Evaluate the closed signed-i32 scalar subset before emitting any IR.

    The target exposes only an entrypoint result, not callable language exports.
    Calls are confined to validated local function ASTs, with operation/depth
    budgets. Every evaluated intermediate must fit i32; no host code executes.
    """

    def __init__(self):
        self.body = []
        self.steps = 10000
        self.depth = 0
        self.functions = {}
        self.globals = {}

    def _tick(self):
        self.steps -= 1
        if self.steps < 0:
            raise ValueError("LLVM compile-time operation budget exceeded")

    @staticmethod
    def _checked(value):
        if type(value) not in (int, bool) or not -(1 << 31) <= value < (1 << 31):
            raise ValueError("LLVM closed-scalar target requires signed-i32 values")
        return value

    def emit(self, expr, env) -> str:
        return str(int(self.evaluate(expr, env)))

    def evaluate(self, expr, env):
        self._tick()
        if isinstance(expr, (IntLiteral, BoolLiteral)):
            return self._checked(expr.value)
        if isinstance(expr, Identifier):
            if expr.name == "__error__" or expr.name not in env:
                raise ValueError(f"LLVM target has unresolved identifier {expr.name!r}")
            return self._checked(env[expr.name])
        if isinstance(expr, UnaryOp):
            if (
                expr.op == TokenType.MINUS
                and isinstance(expr.operand, IntLiteral)
                and type(expr.operand.value) is int
            ):
                return self._checked(-expr.operand.value)
            value = self.evaluate(expr.operand, env)
            if expr.op == TokenType.MINUS:
                if type(value) is bool:
                    raise ValueError("LLVM unary minus does not accept Bool")
                return self._checked(-value)
            if expr.op == TokenType.NOT:
                return not value
            raise ValueError("LLVM target does not support this unary operator")
        if isinstance(expr, BinaryOp):
            left = self.evaluate(expr.left, env)
            if expr.op == TokenType.AND:
                return self.evaluate(expr.right, env) if left else left
            if expr.op == TokenType.OR:
                return left if left else self.evaluate(expr.right, env)
            right = self.evaluate(expr.right, env)
            if expr.op in {TokenType.EQEQ, TokenType.NE}:
                if (type(left) is bool) != (type(right) is bool):
                    raise ValueError(
                        "LLVM scalar equality cannot mix Bool with another type"
                    )
            elif type(left) is bool or type(right) is bool:
                raise ValueError("LLVM arithmetic and ordering do not accept Bool")
            operations = {
                TokenType.PLUS: lambda: left + right,
                TokenType.MINUS: lambda: left - right,
                TokenType.STAR: lambda: left * right,
                TokenType.PERCENT: lambda: left % right,
                TokenType.EQEQ: lambda: left == right,
                TokenType.NE: lambda: left != right,
                TokenType.LT: lambda: left < right,
                TokenType.LE: lambda: left <= right,
                TokenType.GT: lambda: left > right,
                TokenType.GE: lambda: left >= right,
            }
            if expr.op not in operations:
                raise ValueError(
                    "LLVM closed-scalar target does not support division or this operator"
                )
            try:
                return self._checked(operations[expr.op]())
            except ArithmeticError as exc:
                raise ValueError(f"LLVM constant arithmetic failed: {exc}") from exc
        if isinstance(expr, CallExpr) and isinstance(expr.callee, Identifier):
            name = expr.callee.name
            if name in env or name not in self.functions:
                raise ValueError(f"LLVM target cannot call {name!r}")
            declaration = self.functions[name]
            if len(expr.args) != len(declaration.params):
                raise ValueError("LLVM function argument count mismatch")
            values = [self.evaluate(arg, env) for arg in expr.args]
            local = dict(self.globals)
            local.update(
                zip((param[0] for param in declaration.params), values, strict=True)
            )
            self.depth += 1
            try:
                if self.depth > 32:
                    raise ValueError("LLVM compile-time call depth exceeded")
                value, returned = self.statements(
                    declaration.body.statements, local, in_function=True
                )
                if not returned:
                    raise ValueError("LLVM functions require an explicit scalar return")
                return value
            finally:
                self.depth -= 1
        raise ValueError(
            f"LLVM target does not support expression {type(expr).__name__}"
        )

    def statements(self, statements, env, *, in_function=False):
        mutable = set()
        for stmt in statements:
            self._tick()
            if isinstance(stmt, VariableDecl):
                if stmt.init_expr is None:
                    raise ValueError("LLVM target requires initialized variables")
                env[stmt.name] = self.evaluate(stmt.init_expr, env)
                if stmt.is_mut:
                    mutable.add(stmt.name)
                else:
                    mutable.discard(stmt.name)
            elif isinstance(stmt, AssignStmt) and isinstance(stmt.target, Identifier):
                if stmt.target.name not in mutable:
                    raise ValueError("LLVM assignment must target a mutable local")
                env[stmt.target.name] = self.evaluate(stmt.value, env)
            elif isinstance(stmt, ExprStmt):
                self.evaluate(stmt.expr, env)
            elif (
                isinstance(stmt, ReturnStmt) and in_function and stmt.value is not None
            ):
                return self.evaluate(stmt.value, env), True
            elif type(stmt) is FunctionDecl and not in_function:
                if stmt.name in env:
                    del env[stmt.name]
                self.functions[stmt.name] = stmt
            else:
                raise ValueError(
                    f"LLVM target does not support statement {type(stmt).__name__}"
                )
        return 0, False


def _transpile_to_llvm_ir(ast) -> str:
    """Emit a verified constant entrypoint for a closed signed-i32 program.

    This deliberately limited backend does not compile unrestricted integers,
    dynamic inputs, effects, exported functions, division, or control flow.
    The main binding becomes the process return value (subject to OS exit-code
    conventions); a program without that binding returns zero.
    """
    import dataclasses

    if getattr(ast, "parse_failed", False):
        raise ValueError("Cannot compile a malformed program")
    _validate_build_mode(ast)
    allowed = {
        IntLiteral,
        BoolLiteral,
        Identifier,
        UnaryOp,
        BinaryOp,
        CallExpr,
        VariableDecl,
        AssignStmt,
        ExprStmt,
        ReturnStmt,
        FunctionDecl,
        BlockStmt,
    }
    pending = [(stmt, 0) for stmt in ast.stmts]
    count = 0
    while pending:
        node, depth = pending.pop()
        count += 1
        if count > 1000 or depth > 64:
            raise ValueError("LLVM AST analysis budget exceeded")
        if dataclasses.is_dataclass(node):
            if type(node) not in allowed:
                raise ValueError(f"LLVM target does not support {type(node).__name__}")
            if isinstance(node, BinaryOp) and node.op == TokenType.SLASH:
                raise ValueError("LLVM target does not support division")
            if isinstance(node, IntLiteral) and node.value.bit_length() > 32:
                raise ValueError("LLVM target requires signed-i32 values")
            if isinstance(node, FunctionDecl):
                names = [p[0] for p in node.params]
                if len(names) != len(set(names)):
                    raise ValueError("LLVM target rejects duplicate parameter names")
            for field in dataclasses.fields(node):
                if field.name != "span":
                    pending.append((getattr(node, field.name), depth + 1))
        elif isinstance(node, (list, tuple)):
            if len(node) > 1000:
                raise ValueError("LLVM AST analysis budget exceeded")
            pending.extend((item, depth + 1) for item in node)
    evaluator = _LLVMExpr()
    evaluator.statements(ast.stmts, evaluator.globals)
    result = evaluator.globals.get("main", 0)
    if type(result) is not int:
        raise ValueError("LLVM entry result must be an Int")
    return "\n".join(
        [
            "; Generated by Thirsty-Lang: closed-scalar-i32/v1",
            "; All supported computation was evaluated within compile-time budgets.",
            "define i32 @main() {",
            "entry:",
            f"  ret i32 {result}",
            "}",
            "",
        ]
    )


def _build_llvm(ast, base: str, target: str, *, ir: str | None = None) -> str:
    """Write textual IR, then drive the toolchain for non-IR targets.

    ``llvm-ir`` is fully self-contained. ``llvm-asm``/``llvm-obj``/``llvm-exe``/
    ``llvm-jit`` shell out to ``llc``/``clang``/``lli``; a missing tool raises a
    clear error (the ``.ll`` is still written).
    """
    import shutil
    import subprocess

    if ir is None:
        ir = _transpile_to_llvm_ir(ast)
    ir_path = base + ".ll"
    with open(ir_path, "w", encoding="utf-8") as f:
        f.write(ir)
    if target == "llvm-ir":
        return ir_path

    exe_suffix = ".exe" if os.name == "nt" else ""
    plan = {
        "llvm-asm": ("llc", [ir_path, "-o", base + ".s"], base + ".s"),
        "llvm-obj": ("llc", ["-filetype=obj", ir_path, "-o", base + ".o"], base + ".o"),
        "llvm-exe": ("clang", [ir_path, "-o", base + exe_suffix], base + exe_suffix),
        "llvm-jit": ("lli", [ir_path], ir_path),
    }
    tool, tool_args, out_path = plan[target]
    resolved = shutil.which(tool)
    if resolved is None:
        raise RuntimeError(
            f"LLVM toolchain '{tool}' not found on PATH (required for {target}). "
            f"Textual IR was written to {ir_path}."
        )
    subprocess.run([resolved, *tool_args], check=True)
    return out_path


_PYODIDE_BOOTSTRAP = """
import hashlib
from importlib.metadata import distribution
from pathlib import Path

installed = distribution("thirsty-lang")
if installed.version != EXPECTED_VERSION:
    raise RuntimeError("Thirsty-Lang version mismatch; execution refused")
root = Path(installed.locate_file("utf")).resolve()
digest = hashlib.sha256()
for path in sorted(root.rglob("*.py")):
    relative = path.relative_to(root).as_posix().encode("utf-8")
    content = path.read_bytes()
    digest.update(len(relative).to_bytes(8, "big"))
    digest.update(relative)
    digest.update(len(content).to_bytes(8, "big"))
    digest.update(content)
if "sha256-" + digest.hexdigest() != EXPECTED_SOURCE_INTEGRITY:
    raise RuntimeError("Thirsty-Lang source fingerprint mismatch; execution refused")

from utf.thirsty_lang.lexer import Lexer
from utf.thirsty_lang.parser import Parser
from utf.thirsty_lang.checker import check_ast
from utf.thirsty_lang.interpreter import Interpreter
lexer = Lexer(SRC)
parser = Parser(lexer.lex())
ast = parser.parse()
diagnostics = [*lexer.errors, *parser.errors, *check_ast(ast)]
if any(item.severity == "error" for item in diagnostics) or ast.parse_failed:
    raise RuntimeError("Thirsty-Lang source validation failed; execution refused")
Interpreter(allow_ungoverned=ALLOW_UNGOVERNED).interpret(ast)
"""

_PYODIDE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Thirsty-Lang (Pyodide)</title>
</head>
<body>
<pre id="out">Loading verified runtime…</pre>
<script src="https://cdn.jsdelivr.net/pyodide/v0.26.2/full/pyodide.js"></script>
<script type="module">
const SOURCE = {source_json};
const EXPECTED_VERSION = {version_json};
const EXPECTED_SOURCE_INTEGRITY = {integrity_json};
const ALLOW_UNGOVERNED = {allow_ungoverned_json};
const BOOTSTRAP = {bootstrap_json};
async function main() {{
  const out = document.getElementById("out");
  try {{
    const pyodide = await loadPyodide();
    await pyodide.loadPackage("micropip");
    const micropip = pyodide.pyimport("micropip");
    await micropip.install("thirsty-lang==" + EXPECTED_VERSION);
    pyodide.globals.set("SRC", SOURCE);
    pyodide.globals.set("EXPECTED_VERSION", EXPECTED_VERSION);
    pyodide.globals.set("EXPECTED_SOURCE_INTEGRITY", EXPECTED_SOURCE_INTEGRITY);
    pyodide.globals.set("ALLOW_UNGOVERNED", ALLOW_UNGOVERNED);
    out.textContent = "";
    pyodide.setStdout({{batched: text => {{ out.textContent += text + "\\n"; }} }});
    await pyodide.runPythonAsync(BOOTSTRAP);
    out.textContent += "Done.";
  }} catch (error) {{
    out.textContent += "Execution failed: " + String(error);
    throw error;
  }}
}}
main();
</script>
</body>
</html>
"""


def _html_json(value) -> str:
    """JSON embedded in a script element must not contain an HTML end tag."""
    return (
        json.dumps(value, ensure_ascii=True)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def _build_pyodide(source: str, base: str, *, allow_ungoverned: bool = False) -> str:
    """Emit a browser launcher pinned to this package version and source tree.

    The downloaded wheel must reproduce the source-only fingerprint before
    language code is imported/executed. Host Python ABI data is deliberately
    excluded: browser execution uses the separately pinned Pyodide runtime.
    """
    from utf.thirsty_lang.lexer import Lexer
    from utf.thirsty_lang.package_manager import runtime_source_integrity
    from utf.thirsty_lang.parser import Parser

    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    ast = parser.parse()
    if lexer.errors or parser.errors or ast.parse_failed:
        raise ValueError("Cannot build malformed source for Pyodide")
    _validate_build_mode(ast)

    html = _PYODIDE_TEMPLATE.format(
        source_json=_html_json(source),
        version_json=_html_json(__version__),
        integrity_json=_html_json(runtime_source_integrity()),
        allow_ungoverned_json=_html_json(allow_ungoverned),
        bootstrap_json=_html_json(_PYODIDE_BOOTSTRAP),
    )
    out_path = base + ".pyodide.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


def _read_optional_policy(policy_path: str | None) -> str | None:
    if policy_path is None:
        return None
    if not os.path.isfile(policy_path):
        raise FileNotFoundError(f"policy file not found: {policy_path}")
    with open(policy_path, encoding="utf-8") as f:
        return f.read()


def _emit_manifest(
    ast,
    file_path,
    source: str,
    target=None,
    governance_loss=False,
    policy_path: str | None = None,
    context_schema_path: str | None = None,
):
    """Emit governance manifest."""
    from utf.thirsty_lang.proof_obligations import extract_proof_obligations

    policy_text = _read_optional_policy(policy_path)
    manifest = extract_proof_obligations(
        ast,
        source,
        file_path,
        policy_text=policy_text,
        policy_path=policy_path,
        explicit_schema_path=context_schema_path,
        target=target,
        governance_loss=governance_loss,
    )
    # Backward-compatible policy envelope retained for existing consumers.
    manifest["governance_policy"] = {
        "tarl": {
            "path": policy_path,
            "hash": manifest["policy_dependencies"]["hash"],
        },
        "shadow_thirst": manifest["shadow_convergence_result"],
    }
    manifest_path = os.path.splitext(file_path)[0] + ".manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest: {manifest_path}")


def _proof_report(args, require_policy: bool) -> tuple[dict, list]:
    from utf.thirsty_lang.checker import check_ast
    from utf.thirsty_lang.lexer import Lexer
    from utf.thirsty_lang.parser import Parser
    from utf.thirsty_lang.proof_obligations import extract_proof_obligations

    if not os.path.isfile(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    policy_path = getattr(args, "policy", None)
    if require_policy and not policy_path:
        print("Error: --policy is required", file=sys.stderr)
        sys.exit(1)
    policy_text = _read_optional_policy(policy_path)
    with open(args.file, encoding="utf-8") as f:
        source = f.read()
    lexer = Lexer(source)
    parser = Parser(lexer.lex())
    ast = parser.parse()
    diagnostics = []
    diagnostics.extend(lexer.errors)
    diagnostics.extend(parser.errors)
    diagnostics.extend(check_ast(ast, effect_warnings=True))
    report = extract_proof_obligations(
        ast,
        source,
        args.file,
        policy_text=policy_text,
        policy_path=policy_path,
        explicit_schema_path=getattr(args, "context_schema", None),
        diagnostics=diagnostics,
    )
    return report, diagnostics


def cmd_prove(args):
    """Emit a proof-obligation report without executing side effects."""
    report, diagnostics = _proof_report(args, require_policy=True)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.emit_manifest:
        manifest_path = os.path.splitext(args.file)[0] + ".proof-obligations.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)
    has_errors = any(d.severity == "error" for d in diagnostics)
    schema = report.get("context_schema") or {}
    schema_failed = schema.get("status") not in {"complete", "explicit"}
    if has_errors or schema_failed:
        sys.exit(1)


def cmd_explain_denial(args):
    """Explain missing policy/context/authority/proof conditions."""
    from utf.thirsty_lang.proof_obligations import denial_explanation

    report, _diagnostics = _proof_report(args, require_policy=False)
    explanation = denial_explanation(report)
    print(json.dumps(explanation, indent=2, sort_keys=True))


def cmd_govern(args):
    """Governance operations."""

    if not args.file:
        # Scan for .thirsty files
        import glob

        files = glob.glob("**/*.thirsty", recursive=True)
        if not files:
            print("No .thirsty files found.", file=sys.stderr)
            sys.exit(1)
        args.file = files[0]

    ast, errors, source = _lex_parse_check(args.file)

    if args.report:
        print(f"Governance Report for: {args.file}")
        mode, governance_required = resolve_execution_mode(
            ast.header.mode if ast.header else None
        )
        print(f"  Mode: {mode}")
        print(f"  Governance: {'required' if governance_required else 'disabled'}")
        print(
            f"  Functions: {sum(1 for s in ast.stmts if hasattr(s, 'name') and hasattr(s, 'params'))}"
        )
        print(f"  Errors: {len(errors)}")
        for e in errors:
            print(f"    [{e.code}] {e.message}")

    if args.auto_tarl:
        # Auto-generate T.A.R.L. policy
        tarl_policy = "# Auto-generated T.A.R.L. Policy\n"
        for stmt in ast.stmts:
            if hasattr(stmt, "name") and getattr(stmt, "name", None):
                tarl_policy += f'\nwhen action == "{stmt.name}" => ALLOW\n'
        tarl_policy += "\nwhen true => DENY  # Default deny\n"

        # Evaluate policy against each function via TarlRuntime
        from utf.tarl.core import PolicyParser, evaluate_policy
        from utf.tarl.runtime import TarlRuntime

        policy = PolicyParser.parse(tarl_policy, name="auto-tarl")
        TarlRuntime(policy=policy)
        verdicts = []

        for stmt in ast.stmts:
            if hasattr(stmt, "name") and hasattr(stmt, "params"):
                context = {
                    "action": stmt.name,
                    "params": len(getattr(stmt, "params", [])),
                    "body_len": (
                        len(stmt.body.stmts) if hasattr(stmt.body, "stmts") else 0
                    ),
                }
                decision = evaluate_policy(context, policy_text=tarl_policy)
                verdicts.append(
                    (
                        stmt.name,
                        (
                            decision.verdict.value
                            if hasattr(decision, "verdict")
                            else str(decision)
                        ),
                    )
                )
                print(
                    f"  [{decision.verdict.value if hasattr(decision, 'verdict') else decision}] {stmt.name}"
                )

        # Write policy file
        tarl_path = os.path.splitext(args.file)[0] + ".tarl"
        with open(tarl_path, "w", encoding="utf-8") as f:
            f.write(tarl_policy)
        print(f"T.A.R.L. policy: {tarl_path}")

        if args.enforce:
            denied = [name for name, v in verdicts if v == "DENY"]
            if denied:
                print(
                    f"Enforce failed: {len(denied)} function(s) denied: {' '.join(denied)}",
                    file=sys.stderr,
                )
                sys.exit(1)


def cmd_add(args):
    """Add a dependency."""
    from utf.thirsty_lang.package_manager import PackageManager

    pm = PackageManager()
    pm.parse_manifest()

    if "@" in args.package:
        name, version = args.package.split("@", 1)
    else:
        name = args.package
        version = "*"

    pm.add_dependency(name, version)
    pm.generate_lock()
    pm.write_lock()
    print(f"Added: {name}@{version}")


def cmd_audit(args):
    """Audit dependencies."""
    from utf.thirsty_lang.package_manager import PackageManager

    pm = PackageManager()
    issues = pm.audit_dependencies()

    if not issues:
        print("No dependency issues found.")
        return

    for issue in issues:
        print(f"  [{issue['type']}] {issue['message']}")

    if args.fix:
        pm.generate_lock()
        if not pm.write_lock():
            raise OSError("Could not write the regenerated lockfile")
        print("Lockfile regenerated.")
    else:
        sys.exit(1)


def cmd_lock(args):
    """Generate or update lockfile."""
    from utf.thirsty_lang.package_manager import PackageManager

    pm = PackageManager()
    pm.parse_manifest()
    pm.generate_lock()
    if not pm.write_lock():
        raise OSError("Could not write thirsty.lock")
    print("Lockfile generated: thirsty.lock")


def cmd_doctor(args):
    """Project health check."""
    checks_passed = 0
    checks_failed = 0

    print("Thirsty-Lang Doctor — Project Health Check")
    print()

    # Check thirsty.toml
    if os.path.exists("thirsty.toml"):
        print("✓ thirsty.toml found")
        checks_passed += 1
    else:
        print("✗ thirsty.toml missing")
        checks_failed += 1

    # Check thirsty.lock
    if os.path.exists("thirsty.lock"):
        print("✓ thirsty.lock found")
        checks_passed += 1
    else:
        print("✗ thirsty.lock missing")
        checks_failed += 1

    # Check source dir
    if os.path.isdir("src"):
        thirsty_files = []
        for root, _dirs, files in os.walk("src"):
            for f in files:
                if f.endswith(".thirsty"):
                    thirsty_files.append(os.path.join(root, f))
        if thirsty_files:
            print(f"✓ {len(thirsty_files)} .thirsty source files found")
            checks_passed += 1
        else:
            print("✗ No .thirsty files in src/")
            checks_failed += 1
    else:
        print("✗ src/ directory missing")
        checks_failed += 1

    # Check Python environment
    print(
        f"✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    checks_passed += 1

    # Summary
    print()
    print(f"Passed: {checks_passed}, Failed: {checks_failed}")

    if args.fix and checks_failed > 0:
        from utf.thirsty_lang.package_manager import (
            create_thirsty_lock,
            create_thirsty_toml,
        )

        if not os.path.exists("thirsty.toml"):
            create_thirsty_toml(".", "my-project")
            print("Created thirsty.toml")
        if not os.path.exists("thirsty.lock"):
            create_thirsty_lock(".")
            print("Created thirsty.lock")
        if not os.path.isdir("src"):
            os.makedirs("src")
            print("Created src/ directory")

    if checks_failed > 0:
        sys.exit(1)


def cmd_lsp(args):
    """Start the TARL language server (JSON-RPC over stdio or a TCP socket)."""
    from utf.tarl.lsp import TarlLanguageServer

    if args.stdio:
        TarlLanguageServer().run()
    else:
        _serve_lsp_socket(args.port)


def _serve_lsp_socket(port, host="127.0.0.1"):
    """Serve one LSP session over a TCP socket using the JSON-RPC server."""
    import socket

    from utf.tarl.lsp import TarlLanguageServer

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((host, port))
        server.listen(1)
        print(f"LSP server listening on {host}:{port}")
        conn, addr = server.accept()
        print(f"Connection from {addr}")
        try:
            rstream = conn.makefile("rb")
            wstream = conn.makefile("wb")
            TarlLanguageServer(stdin=rstream, stdout=wstream).run()
        finally:
            conn.close()
    finally:
        server.close()


def cmd_docs(args):
    """Generate documentation."""

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    # Generate simple HTML docs
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Thirsty-Lang Documentation</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #0a0e27; color: #e0e0e0; }
        h1, h2, h3 { color: #00d4aa; }
        code { background: #1a1f3a; padding: 2px 6px; border-radius: 3px; color: #ff79c6; }
        pre { background: #1a1f3a; padding: 16px; border-radius: 8px; overflow-x: auto; border: 1px solid #2a2f5a; }
        .keyword { color: #ff79c6; }
        .string { color: #f1fa8c; }
        .comment { color: #6272a4; }
        .type { color: #8be9fd; }
        nav { position: fixed; left: 20px; top: 20px; width: 200px; }
        nav a { display: block; color: #00d4aa; text-decoration: none; padding: 4px 0; }
        nav a:hover { color: #ff79c6; }
        @media (max-width: 1200px) { nav { position: static; width: 100%; } }
    </style>
</head>
<body>
    <h1>🌊 Thirsty-Lang Documentation</h1>
     <p>Version __VERSION__: a governance-first language family with
     proof-carrying T.A.R.L. policy decisions.</p>
     <p><a href="https://github.com/IAmSoThirsty/Thirsty-lang/blob/master/docs/THIRSTY_LANG_UTF_101.md">Canonical Thirsty-Lang UTF 101 manual</a></p>

    <h2>Quick Start</h2>
    <pre><code><span class="keyword">module</span> hello: governed

<span class="keyword">glass</span> <span class="type">greet</span>(name: String) {
    <span class="keyword">return</span> <span class="string">"hello, "</span> + name + <span class="string">"!"</span>
}

<span class="keyword">drink</span> main = greet(<span class="string">"thirsty world"</span>)
main</code></pre>

    <h2>Keywords</h2>
    <p>Core: drink, pour, sip, thirsty, hydrated, thirst, quench, refill, glass, reservoir, well, of, flood, drip, evaporate, condense, fountain, return, mut, empty</p>
    <p>Security: shield, sanitize, armor, morph, detect, defend</p>
     <p>Structured flow: cascade, spillage, cleanup, throw</p>
     <p>T.A.R.L. policy files: policy, when, ALLOW, DENY, ESCALATE</p>
    <p>Shadow Thirst: mutation, validated_canonical, shadow, invariant, canonical, promote, reject</p>

    <h2>Types</h2>
     <p>Int, Float, Bool, String, Void, Any, Error, Quenched, Reservoir, Task, Result, Governed</p>

    <h2>CLI</h2>
    <p><code>thirsty run file.thirsty</code> — Execute a program</p>
    <p><code>thirsty repl</code> — Interactive REPL</p>
     <p><code>thirsty fmt file.thirsty</code> — Format source</p>
     <p><code>thirsty new project</code> — Scaffold project</p>
     <p>Installed companion commands: <code>tarl</code>, <code>tarl-lsp</code>,
     <code>thirst-of-gods</code>, <code>shadow-thirst</code>, <code>tscg</code>,
     and <code>tscg-b</code>.</p>

    <footer>
         <p>Thirsty-Lang v__VERSION__ — The Universal Thirsty Family</p>
    </footer>
</body>
 </html>""".replace("__VERSION__", __version__)

    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Documentation: {index_path}")


if __name__ == "__main__":
    main()
