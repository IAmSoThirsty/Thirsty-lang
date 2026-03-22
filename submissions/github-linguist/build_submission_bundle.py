from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


BUNDLE_DOCS = (
    "README.md",
    "PR_STRATEGY.md",
    "PULL_REQUEST_DRAFT.md",
    "SEARCH_QUERIES.md",
    "SAMPLE_INDEX.md",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def submission_root() -> Path:
    return Path(__file__).resolve().parent


def registry_path() -> Path:
    return repo_root() / "integrations" / "thirsty-lang-engine" / "utf_language_registry.json"


def load_registry() -> dict:
    return json.loads(registry_path().read_text(encoding="utf-8"))


def phase_languages(phase: str, registry: dict) -> list[dict]:
    if phase == "phase-1":
        return [language for language in registry["languages"] if language["name"] == "Thirsty-Lang"]
    return registry["languages"]


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_sample_dirs(languages: list[dict], destination: Path) -> None:
    source_root = repo_root() / "integrations" / "linguist-test" / "samples"
    for language in languages:
        sample_dir = source_root / language["sample_dir"]
        target_dir = destination / language["sample_dir"]
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(sample_dir, target_dir)


def write_manifest(bundle_dir: Path, phase: str, languages: list[dict]) -> None:
    manifest = {
        "phase": phase,
        "language_count": len(languages),
        "languages": [
            {
                "name": language["name"],
                "aliases": language["aliases"],
                "extensions": language["extensions"],
            }
            for language in languages
        ],
        "files": {
            "languages_yml": "linguist/lib/linguist/languages.yml",
            "grammar": "linguist/vendor/grammars/thirsty.tmLanguage.json",
            "samples": "linguist/samples",
        },
    }
    (bundle_dir / "bundle_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def build_bundle(phase: str, output_dir: Path) -> Path:
    registry = load_registry()
    languages = phase_languages(phase, registry)

    bundle_dir = output_dir / phase
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)

    for document in BUNDLE_DOCS:
        copy_file(submission_root() / document, bundle_dir / document)

    copy_file(
        repo_root() / "integrations" / "linguist-test" / "lib" / "linguist" / "languages.yml",
        bundle_dir / "linguist" / "lib" / "linguist" / "languages.yml",
    )
    copy_file(
        repo_root() / "integrations" / "linguist-test" / "vendor" / "grammars" / "thirsty.tmLanguage.json",
        bundle_dir / "linguist" / "vendor" / "grammars" / "thirsty.tmLanguage.json",
    )
    copy_sample_dirs(languages, bundle_dir / "linguist" / "samples")
    write_manifest(bundle_dir, phase, languages)

    return bundle_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a GitHub Linguist submission bundle for the UTF language family."
    )
    parser.add_argument(
        "--phase",
        choices=("phase-1", "phase-2"),
        default="phase-1",
        help="phase-1 builds the safer umbrella-language bundle, phase-2 builds the full UTF family bundle",
    )
    parser.add_argument(
        "--output-dir",
        default=str(submission_root() / "out"),
        help="destination directory for the generated submission bundle",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    bundle_dir = build_bundle(args.phase, output_dir)
    print(f"Built {args.phase} submission bundle at: {bundle_dir}")


if __name__ == "__main__":
    main()
