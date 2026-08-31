#!/usr/bin/env python3
"""Validate the canonical Thirsty-Lang 101 PDF and its source binding."""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections.abc import Iterable
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "PDF validation dependency is missing. Run: "
        'python -m pip install -e ".[docs]"'
    ) from exc

from build_thirsty_lang_101 import (
    DEFAULT_MANIFEST,
    ROOT,
    build_pdf,
    load_manifest,
    source_manifest,
)

REQUIRED_TEXT = (
    "Thirsty-Lang 101",
    "Authoritative context contract",
    "tarl.context.nested-json.v1",
    "REPRESENTATION_CONFLICT",
    "Missing is not false",
    "CR-CONTEXT-RESOLUTION-INTEGRITY",
    "Production Deployment",
    "Offensive Threat Model C001-C073",
    "TSCG-B",
    "Release Authentication and Provenance",
    "Document Provenance",
)

FORBIDDEN_TEXT = (
    "Thirsty-Lang v1.0.0",
    "__VERSION__",
    "unresolved include directive",
)


def flatten_outline(items) -> list:
    flattened: list = []
    for item in items:
        if isinstance(item, list):
            flattened.extend(flatten_outline(item))
        else:
            flattened.append(item)
    return flattened


def collect_fonts(reader: PdfReader) -> set[str]:
    fonts: set[str] = set()
    for page in reader.pages:
        resources = page.get("/Resources")
        if resources is None:
            continue
        resources = resources.get_object()
        font_dict = resources.get("/Font")
        if font_dict is None:
            continue
        for value in font_dict.get_object().values():
            font = value.get_object()
            base = font.get("/BaseFont")
            if base:
                fonts.add(str(base))
    return fonts


def validate_pdf(pdf_path: Path, manifest_path: Path = DEFAULT_MANIFEST) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    config = load_manifest(manifest_path)
    expected_source_digest, _entries = source_manifest(config)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    reader = PdfReader(str(pdf_path))
    if reader.is_encrypted:
        errors.append("PDF is encrypted")
    metadata = reader.metadata or {}
    title = str(metadata.get("/Title", ""))
    subject = str(metadata.get("/Subject", ""))
    keywords = str(metadata.get("/Keywords", ""))
    if config.title not in title or config.software_version not in title:
        errors.append(f"unexpected title metadata: {title!r}")
    if expected_source_digest not in subject + keywords:
        errors.append("metadata does not bind the current source digest")
    if len(reader.pages) < 45:
        errors.append(f"manual is unexpectedly short: {len(reader.pages)} pages")

    extracted: list[str] = []
    low_text_pages: list[int] = []
    portrait = 0
    landscape = 0
    invalid_size: list[int] = []
    for number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        extracted.append(text)
        compact = "".join(text.split())
        # A normal content or part-divider page contains substantially more
        # than the running header/footer alone.
        if len(compact) < 60:
            low_text_pages.append(number)
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        pair = sorted((round(width, 1), round(height, 1)))
        if abs(pair[0] - 612.0) > 1 or abs(pair[1] - 792.0) > 1:
            invalid_size.append(number)
        elif width < height:
            portrait += 1
        else:
            landscape += 1
    full_text = "\n".join(extracted)
    if low_text_pages:
        errors.append(f"blank or nearly blank pages: {low_text_pages}")
    if invalid_size:
        errors.append(f"non-Letter page sizes: {invalid_size}")
    if portrait == 0:
        errors.append("manual has no portrait pages")
    if landscape == 0:
        warnings.append("manual has no landscape reference pages")
    if len(full_text) < 100_000:
        errors.append(f"extracted text is unexpectedly short: {len(full_text)} characters")
    for phrase in REQUIRED_TEXT:
        if phrase.lower() not in full_text.lower():
            errors.append(f"required content missing: {phrase!r}")
    for phrase in FORBIDDEN_TEXT:
        if phrase.lower() in full_text.lower():
            errors.append(f"forbidden stale content present: {phrase!r}")
    if "\ufffd" in full_text:
        errors.append("replacement glyph U+FFFD appears in extracted text")
    try:
        outline = flatten_outline(reader.outline)
    except Exception as exc:  # pragma: no cover - corrupt outlines are unusual
        outline = []
        errors.append(f"cannot read PDF outline: {exc}")
    if len(outline) < 25:
        errors.append(f"PDF outline is unexpectedly small: {len(outline)} entries")
    fonts = collect_fonts(reader)
    if not any("Vera" in font for font in fonts):
        errors.append(f"embedded Vera document fonts not found: {sorted(fonts)}")
    if not fonts:
        errors.append("PDF exposes no font resources")
    return {
        "path": str(pdf_path.resolve()),
        "pages": len(reader.pages),
        "portrait_pages": portrait,
        "landscape_pages": landscape,
        "outline_entries": len(outline),
        "text_characters": len(full_text),
        "fonts": sorted(fonts),
        "source_sha256": expected_source_digest,
        "pdf_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        "warnings": warnings,
        "errors": errors,
    }


def check_determinism(manifest_path: Path, expected_pdf: Path) -> str:
    config = load_manifest(manifest_path)
    temp_dir = ROOT / "tmp" / "pdfs"
    temp_dir.mkdir(parents=True, exist_ok=True)
    probe = temp_dir / "thirsty-lang-101-determinism-probe.pdf"
    try:
        build_pdf(config, probe)
        first = probe.read_bytes()
        first_digest = hashlib.sha256(first).hexdigest()
        build_pdf(config, probe)
        second = probe.read_bytes()
        second_digest = hashlib.sha256(second).hexdigest()
        if first != second:
            raise ValueError(
                "deterministic rebuild mismatch: "
                f"{first_digest} != {second_digest}"
            )
        expected_digest = hashlib.sha256(expected_pdf.read_bytes()).hexdigest()
        if first_digest != expected_digest:
            raise ValueError(
                "final artifact differs from deterministic rebuild: "
                f"{expected_digest} != {first_digest}"
            )
        return first_digest
    finally:
        if probe.exists():
            probe.unlink()
        if temp_dir.exists() and not any(temp_dir.iterdir()):
            temp_dir.rmdir()
        tmp_root = temp_dir.parent
        if tmp_root.exists() and not any(tmp_root.iterdir()):
            tmp_root.rmdir()


def render_pages(pdf_path: Path, render_dir: Path, dpi: int = 120) -> int:
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PyMuPDF is required for --render-dir") from exc
    render_dir = render_dir.resolve()
    allowed_root = (ROOT / "tmp" / "pdfs").resolve()
    try:
        render_dir.relative_to(allowed_root)
    except ValueError as exc:
        raise ValueError(
            f"render directory must be inside {allowed_root}"
        ) from exc
    render_dir.mkdir(parents=True, exist_ok=True)
    for previous in render_dir.glob("page-*.png"):
        if previous.is_file():
            previous.unlink()
    scale = dpi / 72.0
    matrix = fitz.Matrix(scale, scale)
    document = fitz.open(pdf_path)
    try:
        for index, page in enumerate(document):
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            pixmap.save(render_dir / f"page-{index + 1:04d}.png")
        return len(document)
    finally:
        document.close()


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, nargs="?", default=Path("output/pdf/Thirsty-Lang-101.pdf"))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--check-determinism", action="store_true")
    parser.add_argument("--render-dir", type=Path)
    parser.add_argument("--render-dpi", type=int, default=120)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    pdf_path = args.pdf if args.pdf.is_absolute() else ROOT / args.pdf
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    result = validate_pdf(pdf_path.resolve(), manifest.resolve())
    print(f"PDF: {result['path']}")
    print(
        "Pages: "
        f"{result['pages']} ({result['portrait_pages']} portrait, "
        f"{result['landscape_pages']} landscape)"
    )
    print(f"Outline entries: {result['outline_entries']}")
    print(f"Extracted text: {result['text_characters']} characters")
    print(f"Source SHA-256: {result['source_sha256']}")
    print(f"PDF SHA-256: {result['pdf_sha256']}")
    if args.check_determinism and not result["errors"]:
        digest = check_determinism(manifest.resolve(), pdf_path.resolve())
        print(f"Deterministic rebuild: PASS ({digest})")
    if args.render_dir and not result["errors"]:
        render_dir = args.render_dir if args.render_dir.is_absolute() else ROOT / args.render_dir
        count = render_pages(pdf_path.resolve(), render_dir.resolve(), args.render_dpi)
        print(f"Rendered pages: {count} -> {render_dir.resolve()}")
    for warning in result["warnings"]:
        print(f"WARNING: {warning}")
    for error in result["errors"]:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
