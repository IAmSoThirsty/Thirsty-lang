"""Verify one-use shield output through both launchers of an installed wheel."""

import argparse
import hashlib
import json
import os
import subprocess
import sysconfig
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory

from utf.tarl import keystore
from utf.tarl.authority import AuthorityIssuer

SITE = (2, 1)
POLICY = (
    'when authority_authenticated == true and action == "write" and target == "stdout" => ALLOW\n'
    "when true => DENY\n"
)


def verify(work: Path) -> None:
    package = Path(str(files("utf"))).resolve()
    libraries = (Path(sysconfig.get_path(k)).resolve() for k in ("purelib", "platlib"))
    if not any(package.is_relative_to(p) for p in libraries):
        raise RuntimeError(f"Expected an installed utf package, got {package}")
    cli = Path(sysconfig.get_path("scripts")) / (
        "thirsty.exe" if os.name == "nt" else "thirsty"
    )
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    policy = work / "stdout.tarl"
    policy.write_text(POLICY, encoding="utf-8")

    issuer_key = keystore.generate("shield-test-issuer", keystore.ROLE_AUTHORITY_ISSUER)
    key_file = work / "issuer.pub.json"
    issuer_key.public_only().write(str(key_file))
    issuer = AuthorityIssuer(issuer_key.key_id, issuer_key.private_bytes())

    def check(args, code, stdout=None):
        proc = subprocess.run(
            [cli, *args], cwd=work, env=env, capture_output=True, timeout=90
        )
        if proc.returncode != code or (stdout is not None and proc.stdout != stdout):
            raise AssertionError(
                f"{args!r} expected exit {code}, stdout {stdout!r}; "
                f"got exit {proc.returncode}, stdout {proc.stdout!r}, stderr {proc.stderr!r}"
            )

    cases = (
        ("once", ['pour "ready"'], "matching", 0, b"ready\n"),
        (
            "local",
            ["drink count: Int = 3", "drink doubled = count + count", 'pour "ready"'],
            "matching",
            0,
            b"ready\n",
        ),
        ("spent", ['pour "ready"', 'pour "ready"'], "matching", 2, b"ready\n"),
        ("surrender", ["surrender()", 'pour "ready"'], "matching", 2, b""),
        ("surrender-only", ["surrender()"], "matching", 0, b""),
        ("missing-grant", ['pour "ready"'], "empty", 2, b""),
        ("unsigned", ['pour "ready"'], "unsigned", 2, b""),
    )
    for name, body, credential, code, output in cases:
        path = work / f"{name}.thirsty"
        source = (
            "module status: governed\nshield {\n    " + "\n    ".join(body) + "\n}\n"
        )
        path.write_bytes(source.encode("utf-8"))
        # Construct the issuer's grant from the specified wire format, independently of the compiler.
        source_digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        record_digest = hashlib.sha256(b"ready\n").hexdigest()
        expected = (
            [
                f"shield:v1:write:stdout:{source_digest}:{SITE[0]}:{SITE[1]}:{record_digest}"
            ]
            if 'pour "ready"' in body
            else []
        )
        bindings = ["--policy", str(policy)]
        if credential == "unsigned":
            bindings.extend(["--authority", "status-worker"])
        else:
            grants = [] if credential == "empty" else expected
            token = issuer.issue("status-worker", grants, ttl_seconds=1800)
            token_file = work / f"{name}.claim.json"
            token_file.write_text(token.to_json(), encoding="utf-8")
            bindings.extend(
                [
                    "--authority-token",
                    str(token_file),
                    "--authority-key-file",
                    str(key_file),
                ]
            )
        check(["build", path.name, "--target", "js", "--policy", str(policy)], 0)
        manifest = json.loads(
            path.with_suffix(".manifest.json").read_text(encoding="utf-8")
        )["build"]
        effects = [{"action": "write", "target": "stdout"}] if expected else []
        if (
            manifest["shield"]["grants"] != expected
            or manifest["shield"]["site"] != list(SITE)
            or manifest["shield"]["max_publications_per_run"] != 1
            or manifest["supported_effects"] != effects
        ):
            raise AssertionError(f"Wrong shield manifest for {name}: {manifest!r}")
        check(["run", path.name, *bindings], code, output)
        check(["run-js", path.with_suffix(".js").name, *bindings], code, output)
        print(f"PASS {name}: both installed hosts returned {code} and {output!r}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--work-dir", type=Path, help="Existing scratch directory outside the checkout"
    )
    args = parser.parse_args()
    with TemporaryDirectory(dir=args.work_dir) as directory:
        work = Path(directory).resolve()
        if work.is_relative_to(Path(__file__).resolve().parents[1]):
            raise ValueError("Select a scratch directory outside the checkout")
        verify(work)
