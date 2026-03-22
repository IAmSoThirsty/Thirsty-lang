from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def linguist_root() -> Path:
    return repo_root() / "integrations" / "linguist-test"


def output_root() -> Path:
    return Path(__file__).resolve().parent / "out" / "upstream-series"


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "git",
            f"-c",
            f"safe.directory={linguist_root().as_posix()}",
            "-C",
            str(linguist_root()),
            *args,
        ],
        check=True,
        text=True,
        capture_output=True,
    )


def rev_parse(ref: str) -> str:
    return git("rev-parse", ref).stdout.strip()


def export_range(name: str, rev_range: str, directory: Path) -> list[str]:
    directory.mkdir(parents=True, exist_ok=True)
    git("format-patch", "-o", str(directory), rev_range)
    return sorted(path.name for path in directory.glob("*.patch"))


def main() -> None:
    out_dir = output_root()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    phase_1_dir = out_dir / "phase-1"
    phase_2_dir = out_dir / "phase-2"

    phase_1_range = "origin/main..main"
    phase_2_range = "main..codex/utf-recognition-submission"

    phase_1_patches = export_range("phase-1", phase_1_range, phase_1_dir)
    phase_2_patches = export_range("phase-2", phase_2_range, phase_2_dir)

    manifest = {
        "linguist_repo": str(linguist_root()),
        "phase_1": {
            "base": rev_parse("origin/main"),
            "head": rev_parse("main"),
            "range": phase_1_range,
            "patches": phase_1_patches,
        },
        "phase_2": {
            "base": rev_parse("main"),
            "head": rev_parse("codex/utf-recognition-submission"),
            "range": phase_2_range,
            "patches": phase_2_patches,
        },
    }
    (out_dir / "series_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Exported upstream patch series to: {out_dir}")


if __name__ == "__main__":
    main()
