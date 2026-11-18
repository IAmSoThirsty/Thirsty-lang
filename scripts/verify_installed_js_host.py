"""Exercise the policy-bound Node host through the console launcher of an installed wheel."""

import argparse
import json
import os
import shutil
import subprocess
import sysconfig
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory

CHECKOUT = Path(__file__).resolve().parents[1]
FIXTURES = CHECKOUT / "docs/operations/fixtures/portable-collections"
READER_POLICY = (
    'when action == "write" and target == "stdout" and authority == "reader" => ALLOW\n'
    "when true => DENY\n"
)


def installed_launcher() -> Path:
    package = Path(str(files("utf"))).resolve()
    libraries = [
        Path(sysconfig.get_path(key)).resolve() for key in ("purelib", "platlib")
    ]
    if not any(package.is_relative_to(library) for library in libraries):
        raise RuntimeError(f"Expected an installed utf package, found {package}")
    name = "thirsty.exe" if os.name == "nt" else "thirsty"
    cli = Path(sysconfig.get_path("scripts")) / name
    if not cli.is_file():
        raise FileNotFoundError(f"Installed console launcher is missing: {cli}")
    return cli


def verify(work: Path) -> None:
    cli = installed_launcher()
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    policy = work / "reader.tarl"
    policy.write_text(READER_POLICY, encoding="utf-8")

    def check(
        *args: str,
        code: int = 0,
        stdout: str | None = None,
        errors: tuple[str, ...] = (),
    ) -> None:
        result = subprocess.run(
            [cli, *args],
            cwd=work,
            env=environment,
            text=True,
            capture_output=True,
            encoding="utf-8",
            timeout=90,
        )
        expected_stdout = "" if code else stdout
        if (
            result.returncode != code
            or (expected_stdout is not None and result.stdout != expected_stdout)
            or any(error.lower() not in result.stderr.lower() for error in errors)
        ):
            raise AssertionError(
                f"{cli.name} {' '.join(args)}\n"
                f"Expected exit {code}, stdout {expected_stdout!r}, stderr containing {errors!r}.\n"
                f"Got exit {result.returncode}, stdout {result.stdout!r}, stderr {result.stderr!r}."
            )

    def build(source: Path, bound_policy: Path = policy) -> Path:
        check("build", source.name, "--target", "js", "--policy", bound_policy.name)
        artifact = source.with_suffix(".js")
        manifest = json.loads(
            source.with_suffix(".manifest.json").read_text(encoding="utf-8")
        )
        if not artifact.is_file() or manifest["build"]["governance_loss"] is not False:
            raise AssertionError(
                f"Missing governed JavaScript artifact for {source.name}"
            )
        return artifact

    def launch(
        artifact: Path,
        authority: str = "reader",
        selected: Path = policy,
        *,
        code: int = 0,
        stdout: str | None = None,
        errors: tuple[str, ...] = (),
    ) -> None:
        check(
            "run-js",
            artifact.name,
            "--policy",
            selected.name,
            "--authority",
            authority,
            code=code,
            stdout=stdout,
            errors=errors,
        )

    for kind in ("valid", "invalid", "dynamic"):
        fixture = FIXTURES / f"list-alias-{kind}.thirsty"
        shutil.copyfile(fixture, work / fixture.name)

    valid = build(work / "list-alias-valid.thirsty")
    launch(valid, stdout="2\n")
    invalid = work / "list-alias-invalid.thirsty"
    check(
        "build",
        invalid.name,
        "--target",
        "js",
        "--policy",
        policy.name,
        code=1,
        errors=("E021", "4:1"),
    )
    if any(
        invalid.with_suffix(suffix).exists() for suffix in (".js", ".manifest.json")
    ):
        raise AssertionError("The statically invalid fixture emitted a build artifact")
    dynamic = build(work / "list-alias-dynamic.thirsty")
    launch(dynamic, code=1, errors=("4:1", "requires Int"))

    effect = work / "effect.thirsty"
    effect.write_text(
        'module effect: governed\npour "guest output"\n', encoding="utf-8"
    )
    check("build", effect.name, "--target", "js", code=1, errors=("--policy",))
    artifact = build(effect)
    launch(artifact, stdout="guest output\n")
    launch(artifact, "visitor", code=2, errors=("denied",))
    check(
        "run-js", artifact.name, "--authority", "reader", code=2, errors=("--policy",)
    )
    check(
        "run-js",
        artifact.name,
        "--policy",
        policy.name,
        code=2,
        errors=("--authority",),
    )

    other = work / "other.tarl"
    other.write_text("when true => ALLOW\n", encoding="utf-8")
    launch(artifact, selected=other, code=1, errors=("does not match",))
    with artifact.open("ab") as stream:
        stream.write(b"\n// changed after compilation\n")
    launch(artifact, code=1, errors=("does not match",))

    print(
        f"PASS {cli}: three portable fixtures, permitted and denied stdout, "
        "missing bindings, mismatched policy and changed artifact"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--work-dir", type=Path, help="Existing scratch directory outside the checkout"
    )
    args = parser.parse_args()
    with TemporaryDirectory(dir=args.work_dir) as directory:
        work = Path(directory).resolve()
        if work.is_relative_to(CHECKOUT):
            raise ValueError(f"Select a scratch directory outside {CHECKOUT}")
        verify(work)
