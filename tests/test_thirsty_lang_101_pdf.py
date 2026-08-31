"""Documentation artifact contract for the canonical Thirsty-Lang 101 PDF."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytest.importorskip("reportlab", reason="install the docs extra to build the canonical PDF")
pytest.importorskip("pypdf", reason="install the docs extra to verify the canonical PDF")
sys.path.insert(0, str(ROOT / "scripts"))

from build_thirsty_lang_101 import (  # noqa: E402
    load_manifest,
    source_manifest,
    split_table_row,
)
from verify_thirsty_lang_101 import validate_pdf  # noqa: E402

MANIFEST = ROOT / "docs" / "thirsty_lang_101.toml"
PDF = ROOT / "output" / "pdf" / "Thirsty-Lang-101.pdf"


def test_pdf_table_parser_preserves_pipe_operators_in_code_spans():
    row = "| 2 | low pipe `|`, `|>` and escaped \\| | left |"
    assert split_table_row(row) == [
        "2",
        "low pipe `|`, `|>` and escaped |",
        "left",
    ]


def test_manifest_is_complete_and_repository_confined():
    config = load_manifest(MANIFEST)
    assert config.software_version == "0.8.6"
    assert len(config.documents) >= 14
    paths = {document.path.relative_to(ROOT).as_posix() for document in config.documents}
    assert "docs/THIRSTY_LANG_101.md" in paths
    assert "docs/LANGUAGE_SPEC.md" in paths
    assert "docs/GRAMMAR.md" in paths
    assert "docs/THREAT_MODEL.md" in paths
    assert "docs/STATUS.md" in paths
    assert "docs/PRODUCTION_DEPLOYMENT.md" in paths
    digest, entries = source_manifest(config)
    assert len(digest) == 64
    assert all(len(file_digest) == 64 for _path, file_digest in entries)


def test_canonical_pdf_matches_current_sources():
    assert PDF.is_file(), "build the canonical PDF before running its contract test"
    result = validate_pdf(PDF, MANIFEST)
    assert result["errors"] == []
    assert result["pages"] >= 45
    assert result["outline_entries"] >= 25


def test_embedded_docs_report_the_package_version(tmp_path: Path):
    output = tmp_path / "embedded-docs"
    completed = subprocess.run(
        [sys.executable, "-m", "utf.thirsty_lang.cli", "docs", "--output-dir", str(output)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    generated = (output / "index.html").read_text(encoding="utf-8")
    assert "v0.8.6" in generated
    assert "v1.0.0" not in generated
    assert "tarl-lsp" in generated
    assert "Documentation:" in completed.stdout
