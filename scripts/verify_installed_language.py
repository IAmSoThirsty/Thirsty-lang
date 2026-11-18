"""Check a wheel installation from a disposable directory using its console launcher."""

import argparse
import json
import os
import subprocess
import sys
import sysconfig
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory


def check_install(work: Path) -> None:
    example = Path(str(files("utf") / "examples/data_report/main.thirsty"))
    if not example.is_relative_to(Path(sys.prefix)) or not example.is_file():
        raise RuntimeError(f"Expected the installed data_report example, got {example}")
    scripts = Path(sysconfig.get_path("scripts"))
    cli = scripts / ("thirsty.exe" if os.name == "nt" else "thirsty")
    policy = work / "report.tarl"
    data = work / "orders.json"
    app = work / "contract.thirsty"
    environment = dict(os.environ, THIRSTY_REPORT_INPUT=data.as_posix())
    environment.pop("PYTHONPATH", None)

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [cli, *args],
            cwd=work,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=90,
        )

    def allow(grants: list[tuple[str, str]]) -> None:
        rules = [
            f"when action == {json.dumps(action)} and target == {json.dumps(target)} => ALLOW"
            for action, target in grants
        ]
        policy.write_text(
            "\n".join([*rules, "when true => DENY", ""]), encoding="utf-8"
        )

    def execute(program: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return run(
            "run", str(program), "--policy", str(policy), "--authority", "reader", *args
        )

    def expect(
        result: subprocess.CompletedProcess[str], code: int, error: str = ""
    ) -> None:
        if result.returncode != code or error.lower() not in result.stderr.lower():
            raise AssertionError(
                (code, error, result.returncode, result.stdout, result.stderr)
            )
        if code and result.stdout:
            raise AssertionError(f"Unexpected output before failure: {result.stdout!r}")

    expect(run("--help"), 0)
    grants = [
        ("import", "thirst::" + name) for name in ("collections", "json", "env", "fs")
    ]
    grants.extend(
        [("read", "thirst::env.get:THIRSTY_REPORT_INPUT"), ("write", "stdout")]
    )
    allow([*grants, ("read", "thirst::fs.read_file:" + data.as_posix())])
    data.write_bytes(example.with_name("orders.json").read_bytes())
    good = execute(example)
    expect(good, 0)
    report = json.loads(good.stdout)
    expected = {
        "orders": 4,
        "units": 8,
        "revenue_cents": 8900,
        "categories": [
            {"category": "books", "orders": 2, "units": 3, "revenue_cents": 4400},
            {"category": "hardware", "orders": 2, "units": 5, "revenue_cents": 4500},
        ],
    }
    if report != expected:
        raise AssertionError(report)
    data.write_text("{", encoding="utf-8")
    expect(execute(example), 1, "expecting")
    allow(grants)
    expect(execute(example), 2, "governance denied")

    prefix = "drink xs: Reservoir[Int] = [1]\ndrink alias: Any = xs\n"
    app.write_text(prefix + "alias[0] = 2\npour xs[0]", encoding="utf-8")
    valid = execute(app)
    expect(valid, 0)
    if valid.stdout.strip() != "2":
        raise AssertionError(valid.stdout)
    app.write_text(prefix + 'alias[0] = "bad"\npour xs[0]', encoding="utf-8")
    expect(execute(app), 1, "Int")
    app.write_text("drink x = 1\ndrink y = x + 1\npour y", encoding="utf-8")
    limited = execute(app, "--max-steps", "1")
    expect(limited, 1, "step")
    app.write_text(
        'import "thirst::tscgb" as codec\npour codec.decode(codec.encode("  wave  "))',
        encoding="utf-8",
    )
    allow([("import", "thirst::tscgb"), ("write", "stdout")])
    framed = execute(app)
    expect(framed, 0)
    if framed.stdout.rstrip("\r\n") != "  wave  ":
        raise AssertionError(framed.stdout)
    print(
        f"PASS {cli}: data_report, malformed JSON, denied read, typed alias writes, step limit, TSCG-B"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--work-dir", type=Path, help="Parent directory for disposable CLI inputs"
    )
    with TemporaryDirectory(dir=parser.parse_args().work_dir) as temp:
        check_install(Path(temp).resolve())
