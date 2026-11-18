"""Documentation artifact contract for the canonical Thirsty-Lang UTF 101 PDF."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytest.importorskip(
    "reportlab", reason="install the docs extra to build the canonical PDF"
)
pytest.importorskip(
    "pypdf", reason="install the docs extra to verify the canonical PDF"
)
sys.path.insert(0, str(ROOT / "scripts"))

from build_thirsty_lang_utf_101 import (  # noqa: E402
    CanonicalDocTemplate,
    MarkdownRenderer,
    load_manifest,
    make_styles,
    register_fonts,
    source_manifest,
    split_table_row,
    toc_story,
)
from verify_thirsty_lang_utf_101 import validate_pdf  # noqa: E402

MANIFEST = ROOT / "docs" / "thirsty_lang_utf_101.toml"
PDF = ROOT / "output" / "pdf" / "Thirsty-Lang-UTF-101.pdf"


def _pdf_text_fragments(page):
    fragments = []

    def visit(text, cm, tm, _font, _size):
        if text.strip():
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            fragments.append((text.strip(), x, y))

    page.extract_text(visitor_text=visit)
    return fragments


def _running_header(page):
    height = float(page.mediabox.height)
    return [text for text, _x, y in _pdf_text_fragments(page) if y > height - 36]


def test_pdf_table_parser_preserves_pipe_operators_in_code_spans():
    row = "| 2 | low pipe `|`, `|>` and escaped \\| | left |"
    assert split_table_row(row) == [
        "2",
        "low pipe `|`, `|>` and escaped |",
        "left",
    ]


@pytest.mark.parametrize("line_count", [2, 35])
def test_code_language_label_stays_with_first_code_segment(line_count, tmp_path: Path):
    from pypdf import PdfReader
    from reportlab.platypus import BaseDocTemplate, Flowable, Frame, PageTemplate

    class LeadingContent(Flowable):
        def wrap(self, available_width, available_height):
            # Leave 14 points: the language label fits, but its first code
            # segment cannot also fit unless both move to the following page.
            return available_width, 86

        def draw(self):
            self.canv.drawString(0, 0, "Leading content")

    register_fonts()
    renderer = MarkdownRenderer(make_styles())
    lines = [f"line-{number:03d}" for number in range(line_count)]
    source = "```thirsty\n" + "\n".join(lines) + "\n```"
    output = tmp_path / "code-label-boundary.pdf"
    frame = Frame(
        50,
        50,
        300,
        100,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    document = BaseDocTemplate(
        str(output),
        pagesize=(400, 200),
        pageTemplates=[PageTemplate("boundary", [frame])],
    )
    document.build([LeadingContent(), *renderer.render_markdown(source, MANIFEST)])
    texts = [page.extract_text() for page in PdfReader(output).pages]
    label_pages = [index for index, text in enumerate(texts) if "THIRSTY" in text]
    first_code_page = next(
        index for index, text in enumerate(texts) if lines[0] in text
    )
    assert label_pages == [first_code_page]
    assert "Leading content" in texts[0]
    assert first_code_page == 1
    rendered_lines = [
        line.strip()
        for text in texts
        for line in text.splitlines()
        if line.strip().startswith("line-")
    ]
    assert rendered_lines == lines
    code_pages = [index for index, text in enumerate(texts) if "line-" in text]
    if line_count == 2:
        assert len(code_pages) == 1
    else:
        assert len(code_pages) > 1


def test_pdf_toc_rebuild_does_not_reuse_final_section_header(tmp_path: Path):
    from pypdf import PdfReader
    from reportlab.platypus import NextPageTemplate, PageBreak, Paragraph

    config = load_manifest(MANIFEST)
    register_fonts()
    styles = make_styles()
    renderer = MarkdownRenderer(styles)
    output = tmp_path / "running-headers.pdf"
    document = CanonicalDocTemplate(str(output), config, "0" * 64)
    document.multiBuild(
        [
            Paragraph("Cover", styles["Body"]),
            NextPageTemplate("portrait"),
            PageBreak(),
            *toc_story(styles),
            PageBreak(),
            renderer.heading("First Section", 0, "PartTitle"),
            Paragraph("First section content.", styles["Body"]),
            PageBreak(),
            renderer.heading("Document Provenance", 0, "PartTitle"),
        ]
    )

    pages = PdfReader(output).pages
    assert len(pages) == 4
    assert "Contents" in pages[1].extract_text()
    assert _running_header(pages[1]) == ["THIRSTY-LANG UTF 101", "Canonical Reference"]
    assert _running_header(pages[2]) == [
        "THIRSTY-LANG UTF 101",
        "First Section",
    ]
    assert _running_header(pages[3]) == [
        "THIRSTY-LANG UTF 101",
        "Document Provenance",
    ]


def test_running_header_uses_first_heading_then_carries_last_to_continuation(
    tmp_path: Path,
):
    from pypdf import PdfReader
    from reportlab.platypus import NextPageTemplate, PageBreak, Paragraph

    register_fonts()
    styles = make_styles()
    renderer = MarkdownRenderer(styles)
    output = tmp_path / "section-headers.pdf"
    document = CanonicalDocTemplate(str(output), load_manifest(MANIFEST), "0" * 64)
    document.build(
        [
            Paragraph("Cover", styles["Body"]),
            NextPageTemplate("portrait"),
            PageBreak(),
            renderer.heading("First Section", 0, "PartTitle"),
            Paragraph("First section content.", styles["Body"]),
            renderer.heading("Later Subsection", 1, "H2"),
            Paragraph("Later subsection content.", styles["Body"]),
            PageBreak(),
            Paragraph("Later subsection continuation.", styles["Body"]),
        ]
    )
    pages = PdfReader(output).pages
    assert len(pages) == 3
    assert _running_header(pages[1]) == ["THIRSTY-LANG UTF 101", "First Section"]
    assert _running_header(pages[2]) == ["THIRSTY-LANG UTF 101", "Later Subsection"]


def test_page_furniture_uses_active_portrait_and_landscape_dimensions(tmp_path: Path):
    from pypdf import PdfReader
    from reportlab.lib.units import inch
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.platypus import NextPageTemplate, PageBreak, Paragraph

    register_fonts()
    styles = make_styles()
    output = tmp_path / "page-dimensions.pdf"
    document = CanonicalDocTemplate(str(output), load_manifest(MANIFEST), "0" * 64)
    document.build(
        [
            Paragraph("Cover", styles["Body"]),
            NextPageTemplate("portrait"),
            PageBreak(),
            Paragraph("Portrait content", styles["Body"]),
            NextPageTemplate("landscape"),
            PageBreak(),
            Paragraph("Landscape content", styles["Body"]),
        ]
    )
    pages = PdfReader(output).pages
    assert len(pages) == 3
    assert pages[1].mediabox.width < pages[1].mediabox.height
    assert pages[2].mediabox.width > pages[2].mediabox.height
    for number, page in enumerate(pages[1:], 2):
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        fragments = _pdf_text_fragments(page)
        assert _running_header(page) == ["THIRSTY-LANG UTF 101", "Canonical Reference"]
        assert all(0 <= x < width and 0 <= y < height for _text, x, y in fragments)
        text, x, y = next(item for item in fragments if item[0] == f"Page {number}")
        assert x + stringWidth(text, "Vera", 6.5) / 2 == pytest.approx(
            width / 2, abs=0.01
        )
        assert y == pytest.approx(0.26 * inch)
        text, x, _y = next(item for item in fragments if item[0].startswith("source "))
        assert x + stringWidth(text, "Vera", 6.5) == pytest.approx(
            width - 0.58 * inch, abs=0.01
        )
        operations = page.get_contents().operations
        footer_lines = [
            (tuple(operands), tuple(operations[index + 1][0]))
            for index, (operands, operator) in enumerate(operations[:-1])
            if operator == b"m"
            and operations[index + 1][1] == b"l"
            and abs(float(operands[1]) - 0.43 * inch) < 0.01
        ]
        assert len(footer_lines) == 1
        assert footer_lines[0][0] == pytest.approx((0.58 * inch, 0.43 * inch))
        assert footer_lines[0][1] == pytest.approx((width - 0.58 * inch, 0.43 * inch))


@pytest.mark.parametrize("row_count", [1, 90])
def test_wide_table_keeps_immediate_heading_chain_and_outline_on_its_page(
    row_count, tmp_path: Path
):
    from pypdf import PdfReader
    from reportlab.platypus import NextPageTemplate, PageBreak, Paragraph

    register_fonts()
    styles = make_styles()
    renderer = MarkdownRenderer(styles)
    table_source = (
        "## Milestones\n\n### Dependencies\n\n"
        "| Marker | Work | Evidence | State | Scope |\n"
        "|---|---|---|---|---|\n"
        + "\n".join(
            f"| row-{number:03d} | Work | Evidence | Open | Local |"
            for number in range(row_count)
        )
    )
    output = tmp_path / "table-headings.pdf"
    document = CanonicalDocTemplate(str(output), load_manifest(MANIFEST), "0" * 64)
    document.multiBuild(
        [
            Paragraph("Cover", styles["Body"]),
            NextPageTemplate("portrait"),
            PageBreak(),
            renderer.heading("Chapter", 0, "PartTitle"),
            Paragraph("Portrait introduction.", styles["Body"]),
            *renderer.render_markdown(table_source, MANIFEST),
            Paragraph("Portrait continuation.", styles["Body"]),
        ]
    )
    reader = PdfReader(output)
    pages = reader.pages
    table_pages = [
        index for index, page in enumerate(pages) if "row-" in page.extract_text()
    ]
    assert table_pages[0] == 2
    assert "Milestones" not in pages[1].extract_text()
    assert "Dependencies" not in pages[1].extract_text()
    first_table = pages[table_pages[0]]
    assert "Milestones" in first_table.extract_text()
    assert "Dependencies" in first_table.extract_text()
    assert _running_header(first_table) == ["THIRSTY-LANG UTF 101", "Milestones"]
    for index in table_pages:
        assert pages[index].mediabox.width > pages[index].mediabox.height
        assert "Marker" in pages[index].extract_text()
    for index in table_pages[1:]:
        assert _running_header(pages[index]) == ["THIRSTY-LANG UTF 101", "Dependencies"]
    assert pages[-1].mediabox.width < pages[-1].mediabox.height
    assert "Portrait continuation." in pages[-1].extract_text()
    chapter, descendants = reader.outline
    assert chapter.title == "Chapter"
    milestones, subsection = descendants
    assert reader.get_destination_page_number(milestones) == table_pages[0]
    assert reader.get_destination_page_number(subsection[0]) == table_pages[0]


@pytest.mark.parametrize("row_count", [1, 90])
@pytest.mark.parametrize("second_heading", [False, True])
def test_adjacent_wide_tables_do_not_insert_a_blank_portrait_page(
    row_count, second_heading, tmp_path: Path
):
    from pypdf import PdfReader
    from reportlab.platypus import NextPageTemplate, PageBreak, Paragraph

    register_fonts()
    styles = make_styles()
    renderer = MarkdownRenderer(styles)
    columns = "| Marker | Work | Evidence | State | Scope |\n|---|---|---|---|---|\n"
    first = columns + "\n".join(
        f"| first-{number:03d} | Work | Evidence | Open | Local |"
        for number in range(row_count)
    )
    second = columns + "| second-000 | Work | Evidence | Open | Local |"
    between = "\n\n## Second table\n\n### Detail\n\n" if second_heading else "\n\n"
    source = "## First table\n\n" + first + between + second
    output = tmp_path / "adjacent-tables.pdf"
    document = CanonicalDocTemplate(str(output), load_manifest(MANIFEST), "0" * 64)
    document.multiBuild(
        [
            Paragraph("Cover", styles["Body"]),
            NextPageTemplate("portrait"),
            PageBreak(),
            renderer.heading("Chapter", 0, "PartTitle"),
            Paragraph("Portrait introduction.", styles["Body"]),
            *renderer.render_markdown(source, MANIFEST),
            Paragraph("Portrait continuation.", styles["Body"]),
        ]
    )
    pages = PdfReader(output).pages
    first_pages = [
        index for index, page in enumerate(pages) if "first-" in page.extract_text()
    ]
    second_page = next(
        index for index, page in enumerate(pages) if "second-000" in page.extract_text()
    )
    assert first_pages[0] == 2
    assert second_page == first_pages[-1] + 1
    for index in [*first_pages, second_page]:
        assert pages[index].mediabox.width > pages[index].mediabox.height
        assert "Marker" in pages[index].extract_text()
    assert _running_header(pages[second_page]) == [
        "THIRSTY-LANG UTF 101",
        "Second table" if second_heading else "First table",
    ]
    if second_heading:
        assert "Detail" in pages[second_page].extract_text()
    assert second_page == len(pages) - 2
    assert pages[-1].mediabox.width < pages[-1].mediabox.height
    assert "Portrait continuation." in pages[-1].extract_text()


def test_manifest_is_complete_and_repository_confined():
    config = load_manifest(MANIFEST)
    assert config.software_version == "0.9.0"
    assert len(config.documents) >= 14
    paths = {
        document.path.relative_to(ROOT).as_posix() for document in config.documents
    }
    assert config.title == "Thirsty-Lang UTF 101 (Universal Thirsty Family)"
    assert (
        config.subtitle
        == "The Canonical End-to-End Reference - unreleased M3.1-M3.5 and M4.1"
    )
    assert "docs/THIRSTY_LANG_UTF_101.md" in paths
    assert "docs/LANGUAGE_SPEC.md" in paths
    assert "docs/EXECUTION_CONTROL.md" in paths
    assert "docs/GRAMMAR.md" in paths
    assert "docs/THREAT_MODEL.md" in paths
    assert "docs/STATUS.md" in paths
    assert "docs/PRODUCTION_DEPLOYMENT.md" in paths
    digest, entries = source_manifest(config)
    assert len(digest) == 64
    assert all(len(file_digest) == 64 for _path, file_digest in entries)


def test_source_manifest_normalizes_only_crlf(tmp_path, monkeypatch):
    import build_thirsty_lang_utf_101 as builder

    config = load_manifest(MANIFEST)
    sources = {
        "builder.py": b"# builder\n# EOF",
        "composition.toml": b'[manual]\ntitle = "Test"\n',
        "manuscript.md": "Café  \nstandalone\rCR\t".encode(),
    }
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    monkeypatch.setattr(builder, "__file__", str(tmp_path / "builder.py"))
    config = replace(
        config,
        manifest_path=tmp_path / "composition.toml",
        documents=(replace(config.documents[0], path=tmp_path / "manuscript.md"),),
    )
    expected_entries = []
    aggregate = hashlib.sha256()
    for name, content in sorted(sources.items()):
        expected_entries.append((name, hashlib.sha256(content).hexdigest()))
        aggregate.update(name.encode("utf-8") + b"\0" + content + b"\0")
    expected = aggregate.hexdigest(), expected_entries
    for newline in (b"\n", b"\r\n"):
        for name, content in sources.items():
            (tmp_path / name).write_bytes(content.replace(b"\n", newline))
        assert source_manifest(config) == expected

    # A trailing newline changes the manuscript even when the rest uses CRLF.
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_bytes(manuscript.read_bytes() + b"\n")
    digest, entries = source_manifest(config)
    assert digest != expected[0]
    assert dict(entries)["manuscript.md"] != dict(expected_entries)["manuscript.md"]


def test_canonical_pdf_matches_current_sources():
    assert PDF.is_file(), "build the canonical PDF before running its contract test"
    result = validate_pdf(PDF, MANIFEST)
    assert result["errors"] == []
    assert result["pages"] >= 45
    assert result["outline_entries"] >= 25


def test_embedded_docs_report_the_package_version(tmp_path: Path):
    output = tmp_path / "embedded-docs"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "utf.thirsty_lang.cli",
            "docs",
            "--output-dir",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    generated = (output / "index.html").read_text(encoding="utf-8")
    assert "v0.9.0" in generated
    assert "v1.0.0" not in generated
    assert "tarl-lsp" in generated
    assert "Documentation:" in completed.stdout
