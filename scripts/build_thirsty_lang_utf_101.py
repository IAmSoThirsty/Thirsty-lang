#!/usr/bin/env python3
"""Build the canonical Thirsty-Lang UTF 101 PDF from maintained Markdown sources.

The builder intentionally implements a small, deterministic Markdown subset
instead of depending on a browser or platform HTML renderer. The source list,
order, authority class, fixed document date, and output path live in
``docs/thirsty_lang_utf_101.toml``.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import os
import re
import sys
import textwrap
import tomllib
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

try:
    import reportlab
    from reportlab import rl_config
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import LETTER, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        BaseDocTemplate,
        Flowable,
        Frame,
        HRFlowable,
        ListFlowable,
        ListItem,
        LongTable,
        NextPageTemplate,
        PageBreak,
        PageTemplate,
        Paragraph,
        Preformatted,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.platypus.tableofcontents import TableOfContents
except ImportError as exc:  # pragma: no cover - exercised by user environment
    raise SystemExit(
        "PDF dependencies are missing. Run: " 'python -m pip install -e ".[docs]"'
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs" / "thirsty_lang_utf_101.toml"
GITHUB_BLOB_ROOT = "https://github.com/IAmSoThirsty/Thirsty-lang/blob/master/"

NAVY = colors.HexColor("#102A43")
DEEP_BLUE = colors.HexColor("#075985")
WATER = colors.HexColor("#0EA5E9")
CYAN = colors.HexColor("#67E8F9")
PALE_BLUE = colors.HexColor("#EEF8FF")
PALE_CYAN = colors.HexColor("#ECFEFF")
INK = colors.HexColor("#243B53")
MUTED = colors.HexColor("#627D98")
LINE = colors.HexColor("#B9E2F5")
PALE_RED = colors.HexColor("#FFF1F2")
RED = colors.HexColor("#B42318")
WHITE = colors.white


@dataclass(frozen=True)
class SourceDocument:
    path: Path
    title: str
    authority: str


@dataclass(frozen=True)
class ManualConfig:
    manifest_path: Path
    title: str
    subtitle: str
    software_version: str
    document_revision: str
    publisher: str
    license: str
    output: Path
    source_date_epoch: int
    documents: tuple[SourceDocument, ...]


def load_manifest(path: Path) -> ManualConfig:
    path = path.resolve()
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    manual = data["manual"]
    documents: list[SourceDocument] = []
    for item in data.get("document", []):
        source = (ROOT / item["path"]).resolve()
        try:
            source.relative_to(ROOT)
        except ValueError as exc:
            raise ValueError(f"manual source escapes repository: {source}") from exc
        if not source.is_file():
            raise FileNotFoundError(f"manual source not found: {source}")
        documents.append(SourceDocument(source, item["title"], item["authority"]))
    if not documents:
        raise ValueError("manual manifest contains no documents")
    output = (ROOT / manual["output"]).resolve()
    return ManualConfig(
        manifest_path=path,
        title=manual["title"],
        subtitle=manual["subtitle"],
        software_version=manual["software_version"],
        document_revision=manual["document_revision"],
        publisher=manual["publisher"],
        license=manual["license"],
        output=output,
        source_date_epoch=int(manual["source_date_epoch"]),
        documents=tuple(documents),
    )


def source_manifest(config: ManualConfig) -> tuple[str, list[tuple[str, str]]]:
    """Return aggregate digest and per-file digests in stable path order."""

    paths = {config.manifest_path, Path(__file__).resolve()}
    paths.update(document.path for document in config.documents)
    entries: list[tuple[str, str]] = []
    aggregate = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(ROOT).as_posix()):
        rel = path.relative_to(ROOT).as_posix()
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        entries.append((rel, digest))
        aggregate.update(rel.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(raw)
        aggregate.update(b"\0")
    return aggregate.hexdigest(), entries


def register_fonts() -> None:
    """Use ReportLab's bundled Bitstream Vera family for portable Unicode."""

    fonts = Path(reportlab.__file__).resolve().parent / "fonts"
    mapping = {
        "Vera": "Vera.ttf",
        "VeraBd": "VeraBd.ttf",
        "VeraIt": "VeraIt.ttf",
        "VeraBI": "VeraBI.ttf",
    }
    for name, filename in mapping.items():
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(fonts / filename)))
    pdfmetrics.registerFontFamily(
        "Vera",
        normal="Vera",
        bold="VeraBd",
        italic="VeraIt",
        boldItalic="VeraBI",
    )


def make_styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    styles: dict[str, ParagraphStyle] = {}
    styles["Body"] = ParagraphStyle(
        "Body",
        parent=sample["BodyText"],
        fontName="Vera",
        fontSize=9.15,
        leading=12.25,
        textColor=INK,
        spaceAfter=6.2,
        splitLongWords=True,
        allowWidows=0,
        allowOrphans=0,
    )
    styles["Small"] = ParagraphStyle(
        "Small", parent=styles["Body"], fontSize=7.6, leading=9.6, textColor=MUTED
    )
    styles["CoverTitle"] = ParagraphStyle(
        "CoverTitle",
        fontName="VeraBd",
        fontSize=30,
        leading=35,
        textColor=WHITE,
        alignment=TA_LEFT,
        spaceAfter=10,
    )
    styles["CoverKicker"] = ParagraphStyle(
        "CoverKicker",
        fontName="VeraBd",
        fontSize=8.2,
        leading=10,
        textColor=CYAN,
        tracking=1.6,
        spaceAfter=13,
    )
    styles["CoverSubtitle"] = ParagraphStyle(
        "CoverSubtitle",
        fontName="Vera",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#DFF7FF"),
        spaceAfter=9,
    )
    styles["CoverStatement"] = ParagraphStyle(
        "CoverStatement",
        fontName="VeraBd",
        fontSize=12.5,
        leading=16,
        textColor=WHITE,
        tracking=0.5,
        spaceAfter=18,
    )
    styles["CoverMeta"] = ParagraphStyle(
        "CoverMeta",
        fontName="Vera",
        fontSize=9.4,
        leading=12.5,
        textColor=WHITE,
    )
    styles["PartKicker"] = ParagraphStyle(
        "PartKicker",
        fontName="VeraBd",
        fontSize=8.4,
        leading=10,
        textColor=WATER,
        tracking=1.2,
        spaceAfter=9,
    )
    styles["PartTitle"] = ParagraphStyle(
        "PartTitle",
        fontName="VeraBd",
        fontSize=23,
        leading=28,
        textColor=NAVY,
        spaceAfter=10,
        keepWithNext=True,
    )
    styles["H2"] = ParagraphStyle(
        "H2",
        fontName="VeraBd",
        fontSize=16,
        leading=20,
        textColor=NAVY,
        spaceBefore=15,
        spaceAfter=7,
        keepWithNext=True,
    )
    styles["H3"] = ParagraphStyle(
        "H3",
        fontName="VeraBd",
        fontSize=12.1,
        leading=15.2,
        textColor=DEEP_BLUE,
        spaceBefore=11,
        spaceAfter=5,
        keepWithNext=True,
    )
    styles["H4"] = ParagraphStyle(
        "H4",
        fontName="VeraBd",
        fontSize=9.7,
        leading=12.5,
        textColor=INK,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )
    styles["TOCTitle"] = ParagraphStyle(
        "TOCTitle",
        fontName="VeraBd",
        fontSize=25,
        leading=30,
        textColor=NAVY,
        spaceAfter=18,
    )
    styles["CodeLabel"] = ParagraphStyle(
        "CodeLabel",
        fontName="VeraBd",
        fontSize=6.8,
        leading=8,
        textColor=DEEP_BLUE,
        spaceBefore=3,
        spaceAfter=2,
    )
    styles["Code"] = ParagraphStyle(
        "Code",
        fontName="Courier",
        fontSize=6.8,
        leading=8.5,
        textColor=colors.HexColor("#E6F6FF"),
        backColor=NAVY,
        borderColor=DEEP_BLUE,
        borderWidth=0.5,
        borderPadding=7,
        leftIndent=7,
        rightIndent=0,
        spaceAfter=8,
    )
    styles["Callout"] = ParagraphStyle(
        "Callout",
        parent=styles["Body"],
        backColor=PALE_BLUE,
        borderColor=WATER,
        borderWidth=0,
        borderLeft=4,
        borderPadding=8,
        leftIndent=8,
        rightIndent=5,
        spaceBefore=5,
        spaceAfter=9,
    )
    styles["Warning"] = ParagraphStyle(
        "Warning",
        parent=styles["Callout"],
        backColor=PALE_RED,
        borderColor=RED,
    )
    styles["TableHead"] = ParagraphStyle(
        "TableHead",
        fontName="VeraBd",
        fontSize=6.9,
        leading=8.5,
        textColor=WHITE,
        alignment=TA_LEFT,
    )
    styles["TableBody"] = ParagraphStyle(
        "TableBody",
        fontName="Vera",
        fontSize=6.55,
        leading=8.25,
        textColor=INK,
    )
    styles["TableBodyWide"] = ParagraphStyle(
        "TableBodyWide",
        parent=styles["TableBody"],
        fontSize=6.15,
        leading=7.7,
    )
    styles["Source"] = ParagraphStyle(
        "Source",
        fontName="VeraIt",
        fontSize=7.5,
        leading=9.5,
        textColor=MUTED,
        spaceAfter=12,
    )
    return styles


class Heading(Paragraph):
    def __init__(
        self,
        text: str,
        style: ParagraphStyle,
        level: int,
        key: str,
    ) -> None:
        super().__init__(text, style)
        self.toc_level = level
        self.bookmark_key = key
        self.plain_text = re.sub(r"<[^>]+>", "", text)


class ArchitectureFlow(Flowable):
    """Small vector summary used on the cover and orientation pages."""

    def __init__(self, width: float, dark: bool = False) -> None:
        super().__init__()
        self.width = width
        self.height = 0.75 * inch
        self.dark = dark

    def draw(self) -> None:
        c = self.canv
        labels = ["SOURCE", "CHECK", "POLICY", "VERDICT", "PROOF", "EFFECT"]
        gap = 0.09 * inch
        box_width = (self.width - gap * (len(labels) - 1)) / len(labels)
        fill = colors.HexColor("#0C4A6E") if self.dark else PALE_BLUE
        text_color = WHITE if self.dark else NAVY
        for index, label in enumerate(labels):
            x = index * (box_width + gap)
            c.setFillColor(fill)
            c.setStrokeColor(CYAN if self.dark else LINE)
            c.roundRect(x, 0.18 * inch, box_width, 0.38 * inch, 4, fill=1, stroke=1)
            c.setFillColor(text_color)
            c.setFont("VeraBd", 6.6)
            c.drawCentredString(x + box_width / 2, 0.32 * inch, label)
            if index < len(labels) - 1:
                start = x + box_width
                c.setStrokeColor(CYAN if self.dark else WATER)
                c.line(start + 1, 0.37 * inch, start + gap - 2, 0.37 * inch)
                c.line(start + gap - 5, 0.40 * inch, start + gap - 2, 0.37 * inch)
                c.line(start + gap - 5, 0.34 * inch, start + gap - 2, 0.37 * inch)


class CodeBlock(Preformatted):
    """Splittable preformatted block with an explicit painted background."""

    def wrap(self, availWidth: float, _availHeight: float) -> tuple[float, float]:
        self.width = availWidth
        self.height = self.style.leading * len(self.lines) + 8
        return self.width, self.height

    def draw(self) -> None:
        self.canv.saveState()
        self.canv.setFillColor(NAVY)
        self.canv.setStrokeColor(DEEP_BLUE)
        self.canv.roundRect(0, 0, self.width, self.height, 3, fill=1, stroke=1)
        if self.style.textColor:
            self.canv.setFillColor(self.style.textColor)
        text_object = self.canv.beginText(
            self.style.leftIndent,
            self.height - self.style.fontSize - 4,
        )
        text_object.setFont(
            self.style.fontName,
            self.style.fontSize,
            self.style.leading,
        )
        for line in self.lines:
            text_object.textLine(line)
        self.canv.drawText(text_object)
        self.canv.restoreState()

    def split(self, availWidth: float, availHeight: float) -> list[Flowable]:
        if availHeight < self.style.leading + 8:
            return []
        lines_that_fit = int((availHeight - 8) / self.style.leading)
        if lines_that_fit >= len(self.lines):
            return [self]
        first = "\n".join(self.lines[:lines_that_fit])
        remainder = "\n".join(self.lines[lines_that_fit:])
        continuation_style = self.style
        if continuation_style.firstLineIndent != 0:
            continuation_style = deepcopy(continuation_style)
            continuation_style.firstLineIndent = 0
        return [CodeBlock(first, self.style), CodeBlock(remainder, continuation_style)]


class InvariantCanvas(canvas.Canvas):
    def __init__(self, *args, metadata: dict[str, str], **kwargs) -> None:
        kwargs["invariant"] = 1
        super().__init__(*args, **kwargs)
        self.setTitle(metadata["title"])
        self.setAuthor(metadata["author"])
        self.setSubject(metadata["subject"])
        self.setCreator("Thirsty-Lang deterministic ReportLab builder")
        self.setKeywords(metadata["keywords"])


class CanonicalDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str, config: ManualConfig, digest: str) -> None:
        self.config = config
        self.source_digest = digest
        self.current_heading = "Canonical Reference"
        portrait_frame = Frame(
            0.67 * inch,
            0.66 * inch,
            LETTER[0] - 1.34 * inch,
            LETTER[1] - 1.36 * inch,
            id="portrait-frame",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        land = landscape(LETTER)
        landscape_frame = Frame(
            0.58 * inch,
            0.62 * inch,
            land[0] - 1.16 * inch,
            land[1] - 1.30 * inch,
            id="landscape-frame",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        cover_frame = Frame(
            0.72 * inch,
            0.68 * inch,
            LETTER[0] - 1.44 * inch,
            LETTER[1] - 1.36 * inch,
            id="cover-frame",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        super().__init__(
            filename,
            pagesize=LETTER,
            pageTemplates=[
                PageTemplate("cover", [cover_frame], self._draw_cover, pagesize=LETTER),
                PageTemplate(
                    "portrait", [portrait_frame], self._draw_page, pagesize=LETTER
                ),
                PageTemplate(
                    "landscape", [landscape_frame], self._draw_page, pagesize=land
                ),
            ],
            title=f"{config.title} - v{config.software_version}",
            author=config.publisher,
            subject=f"{config.subtitle}; source-sha256={digest}",
            keywords=f"Thirsty-Lang,TARL,governance,security,{digest}",
        )

    def _draw_cover(self, canv: canvas.Canvas, _doc: BaseDocTemplate) -> None:
        width, height = LETTER
        canv.saveState()
        canv.setFillColor(NAVY)
        canv.rect(0, 0, width, height, fill=1, stroke=0)

        # Layered current lines give the flagship edition a dynamic water mark
        # while remaining deterministic, vector-only, and print-safe.
        canv.setFillColor(colors.HexColor("#0B3A5B"))
        path = canv.beginPath()
        path.moveTo(0, height * 0.78)
        path.lineTo(width, height * 0.98)
        path.lineTo(width, height)
        path.lineTo(0, height)
        path.close()
        canv.drawPath(path, fill=1, stroke=0)
        canv.setFillColor(colors.HexColor("#075985"))
        path = canv.beginPath()
        path.moveTo(width * 0.58, 0)
        path.lineTo(width, height * 0.23)
        path.lineTo(width, 0)
        path.close()
        canv.drawPath(path, fill=1, stroke=0)

        canv.setFillColor(colors.HexColor("#0C4A6E"))
        canv.circle(width * 0.94, height * 0.87, 1.55 * inch, fill=1, stroke=0)
        canv.setStrokeColor(colors.HexColor("#38BDF8"))
        canv.setLineWidth(1.2)
        for radius in (0.72, 1.00, 1.28):
            canv.circle(
                width * 0.90,
                height * 0.13,
                radius * inch,
                fill=0,
                stroke=1,
            )
        canv.setStrokeColor(CYAN)
        canv.setLineWidth(4)
        canv.line(0.72 * inch, height - 0.66 * inch, 1.50 * inch, height - 0.66 * inch)
        canv.setFillColor(colors.HexColor("#0EA5E9"))
        canv.roundRect(
            width - 1.76 * inch,
            height - 0.91 * inch,
            1.05 * inch,
            0.34 * inch,
            8,
            fill=1,
            stroke=0,
        )
        canv.setFillColor(WHITE)
        canv.setFont("VeraBd", 8.2)
        canv.drawCentredString(width - 1.235 * inch, height - 0.79 * inch, "UTF / 101")
        canv.setStrokeColor(CYAN)
        canv.setLineWidth(2)
        canv.line(0.72 * inch, 0.58 * inch, width - 0.72 * inch, 0.58 * inch)
        canv.setFillColor(colors.HexColor("#CFFAFE"))
        canv.setFont("Vera", 7.3)
        canv.drawString(
            0.72 * inch,
            0.35 * inch,
            f"{self.config.publisher}  |  {self.config.license}  |  Revision {self.config.document_revision}",
        )
        canv.restoreState()

    def _draw_page(self, canv: canvas.Canvas, doc: BaseDocTemplate) -> None:
        width, height = doc.pagesize
        canv.saveState()
        canv.setStrokeColor(LINE)
        canv.setLineWidth(0.55)
        canv.line(
            0.58 * inch, height - 0.43 * inch, width - 0.58 * inch, height - 0.43 * inch
        )
        canv.setFont("VeraBd", 6.8)
        canv.setFillColor(NAVY)
        canv.drawString(0.58 * inch, height - 0.30 * inch, "THIRSTY-LANG UTF 101")
        canv.setFont("Vera", 6.6)
        canv.setFillColor(MUTED)
        header = self.current_heading[:82]
        canv.drawRightString(width - 0.58 * inch, height - 0.30 * inch, header)
        canv.setStrokeColor(LINE)
        canv.line(0.58 * inch, 0.43 * inch, width - 0.58 * inch, 0.43 * inch)
        canv.setFont("Vera", 6.5)
        canv.drawString(
            0.58 * inch,
            0.26 * inch,
            f"v{self.config.software_version}  |  revision {self.config.document_revision}",
        )
        canv.drawCentredString(width / 2, 0.26 * inch, f"Page {doc.page}")
        canv.drawRightString(
            width - 0.58 * inch,
            0.26 * inch,
            f"source {self.source_digest[:12]}",
        )
        canv.restoreState()

    def afterFlowable(self, flowable: Flowable) -> None:
        if not isinstance(flowable, Heading):
            return
        self.current_heading = flowable.plain_text
        key = flowable.bookmark_key
        level = flowable.toc_level
        self.canv.bookmarkPage(key)
        if level <= 2:
            self.canv.addOutlineEntry(
                flowable.plain_text, key, level=level, closed=level > 0
            )
        self.notify("TOCEntry", (level, flowable.plain_text, self.page, key))


def normalize_text(value: str) -> str:
    replacements = {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u2192": "->",
        "\u2190": "<-",
        "\u21d2": "=>",
        "\u00a0": " ",
        "\ufe0f": "",
        "✅": "PASS",
        "❌": "FAIL",
        "⚠": "WARNING",
        "✔": "PASS",
        "✘": "FAIL",
        "💧": "",
        "🌊": "",
        "🔐": "",
        "🧾": "",
        "⚡": "",
        "🧱": "",
        "🛡": "",
        "🌑": "",
        "🧬": "",
        "📡": "",
        "🚦": "",
        "🧪": "",
        "⛓": "",
        "⏱": "",
        "🗺": "",
        "🗳": "",
        "🧯": "",
        "🚪": "",
        "🧰": "",
        "🔏": "",
        "🔁": "",
        "⛲": "",
        "🥛": "",
        "⏲": "",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    # Drop remaining pictographs that bundled PDF fonts cannot represent.
    value = re.sub(r"[\U0001F000-\U0001FAFF]", "", value)
    return value


def plain_markdown(value: str) -> str:
    value = normalize_text(value)
    value = re.sub(r"!\[([^]]*)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"[`*_~]", "", value)
    return value.strip()


def resolve_link(target: str, source: Path) -> str:
    target = html.unescape(target).strip()
    if target.startswith(("https://", "http://", "mailto:", "#")):
        return target
    path_part, marker, fragment = target.partition("#")
    if not path_part:
        return target
    resolved = (source.parent / path_part).resolve()
    try:
        relative = resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return target
    url = GITHUB_BLOB_ROOT + quote(relative, safe="/")
    if marker:
        url += "#" + quote(fragment, safe="-")
    return url


def inline_markup(value: str, source: Path) -> str:
    value = normalize_text(value)
    escaped = html.escape(value, quote=False)

    def image_repl(match: re.Match[str]) -> str:
        return f"[image: {match.group(1)}]"

    escaped = re.sub(r"!\[([^]]*)\]\(([^)]+)\)", image_repl, escaped)

    def link_repl(match: re.Match[str]) -> str:
        label = match.group(1)
        target = resolve_link(match.group(2), source)
        href = html.escape(target, quote=True)
        return f'<a href="{href}" color="#0369A1"><u>{label}</u></a>'

    escaped = re.sub(r"\[([^]]+)\]\(([^)]+)\)", link_repl, escaped)
    escaped = re.sub(
        r"`([^`]+)`",
        r'<font name="Courier" color="#075985">\1</font>',
        escaped,
    )
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", escaped)
    escaped = re.sub(r"~~(.+?)~~", r"<strike>\1</strike>", escaped)
    return escaped


def wrap_code(raw: str, width: int = 100) -> str:
    lines: list[str] = []
    for line in normalize_text(raw).splitlines() or [""]:
        if len(line) <= width:
            lines.append(line.rstrip())
            continue
        indent = re.match(r"\s*", line).group(0)
        wrapped = textwrap.wrap(
            line,
            width=width,
            subsequent_indent=indent + "  ",
            replace_whitespace=False,
            drop_whitespace=False,
            break_long_words=True,
            break_on_hyphens=False,
        )
        lines.extend(part.rstrip() for part in wrapped)
    return "\n".join(lines)


def split_table_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    cells: list[str] = []
    cell: list[str] = []
    code_fence = 0
    index = 0
    while index < len(line):
        char = line[index]
        if char == "\\" and index + 1 < len(line) and line[index + 1] == "|":
            cell.append("|")
            index += 2
            continue
        if char == "`":
            run = 1
            while index + run < len(line) and line[index + run] == "`":
                run += 1
            if code_fence == 0:
                code_fence = run
            elif code_fence == run:
                code_fence = 0
            cell.append("`" * run)
            index += run
            continue
        if char == "|" and code_fence == 0:
            cells.append("".join(cell).strip())
            cell.clear()
        else:
            cell.append(char)
        index += 1
    cells.append("".join(cell).strip())
    return cells


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


class MarkdownRenderer:
    def __init__(self, styles: dict[str, ParagraphStyle]) -> None:
        self.styles = styles
        self.heading_counter = 0

    def heading(self, text: str, level: int, style: str) -> Heading:
        self.heading_counter += 1
        slug = re.sub(r"[^a-z0-9]+", "-", plain_markdown(text).lower()).strip("-")
        key = f"h-{self.heading_counter:04d}-{slug[:48] or 'section'}"
        return Heading(text, self.styles[style], level, key)

    def render_document(self, document: SourceDocument, number: int) -> list[Flowable]:
        source_label = document.path.relative_to(ROOT).as_posix()
        flows: list[Flowable] = [NextPageTemplate("portrait"), PageBreak()]
        flows.append(
            Paragraph(
                f"PART {number:02d}  /  {document.authority.upper()}",
                self.styles["PartKicker"],
            )
        )
        flows.append(self.heading(html.escape(document.title), 0, "PartTitle"))
        flows.append(
            Paragraph(
                f'Maintained source: <font name="Courier">{html.escape(source_label)}</font>',
                self.styles["Source"],
            )
        )
        flows.append(ArchitectureFlow(LETTER[0] - 1.34 * inch, dark=False))
        flows.append(HRFlowable(width="100%", color=LINE, thickness=1.1, spaceAfter=13))
        text = document.path.read_text(encoding="utf-8")
        flows.extend(self.render_markdown(text, document.path, skip_first_h1=True))
        return flows

    def render_markdown(
        self,
        text: str,
        source: Path,
        *,
        skip_first_h1: bool = False,
    ) -> list[Flowable]:
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        flows: list[Flowable] = []
        paragraph: list[str] = []
        first_h1_seen = False

        def flush_paragraph() -> None:
            if not paragraph:
                return
            joined = " ".join(piece.strip() for piece in paragraph).strip()
            paragraph.clear()
            if not joined:
                return
            style = (
                self.styles["Warning"]
                if joined.lower().startswith(("warning:", "security:"))
                else self.styles["Body"]
            )
            flows.append(Paragraph(inline_markup(joined, source), style))

        index = 0
        while index < len(lines):
            line = lines[index]
            stripped = line.strip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                flush_paragraph()
                fence = stripped[:3]
                language = stripped[3:].strip() or "text"
                index += 1
                code: list[str] = []
                while index < len(lines) and not lines[index].strip().startswith(fence):
                    code.append(lines[index])
                    index += 1
                label = (
                    "DIAGRAM SOURCE - MERMAID"
                    if language.lower() == "mermaid"
                    else language.upper()
                )
                flows.append(Paragraph(html.escape(label), self.styles["CodeLabel"]))
                flows.append(CodeBlock(wrap_code("\n".join(code)), self.styles["Code"]))
                index += 1
                continue
            heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if heading_match:
                flush_paragraph()
                markdown_level = len(heading_match.group(1))
                title = heading_match.group(2).rstrip("#").strip()
                if markdown_level == 1 and not first_h1_seen:
                    first_h1_seen = True
                    if skip_first_h1:
                        index += 1
                        continue
                # Each maintained document is wrapped by a generated level-0
                # part heading, so source H2/H3 map to outline levels 1/2.
                toc_level = min(2, max(1, markdown_level - 1))
                style_name = "H2" if toc_level == 1 else "H3"
                if markdown_level >= 4:
                    style_name = "H4"
                    toc_level = 2
                flows.append(
                    self.heading(inline_markup(title, source), toc_level, style_name)
                )
                index += 1
                continue
            if (
                index + 1 < len(lines)
                and "|" in line
                and is_table_separator(lines[index + 1])
            ):
                flush_paragraph()
                raw_rows = [split_table_row(line)]
                index += 2
                while (
                    index < len(lines) and lines[index].strip() and "|" in lines[index]
                ):
                    raw_rows.append(split_table_row(lines[index]))
                    index += 1
                flows.extend(self.render_table(raw_rows, source))
                continue
            list_match = re.match(r"^\s*([-+*]|\d+[.)])\s+(.+)$", line)
            if list_match:
                flush_paragraph()
                ordered = list_match.group(1)[0].isdigit()
                items: list[ListItem] = []
                while index < len(lines):
                    match = re.match(r"^\s*([-+*]|\d+[.)])\s+(.+)$", lines[index])
                    if not match or match.group(1)[0].isdigit() != ordered:
                        break
                    item_text = match.group(2).strip()
                    continuation: list[str] = []
                    cursor = index + 1
                    while cursor < len(lines):
                        candidate = lines[cursor]
                        if not candidate.strip() or re.match(
                            r"^\s*([-+*]|\d+[.)])\s+", candidate
                        ):
                            break
                        if re.match(r"^\s{2,}\S", candidate):
                            continuation.append(candidate.strip())
                            cursor += 1
                        else:
                            break
                    if continuation:
                        item_text += " " + " ".join(continuation)
                        index = cursor
                    else:
                        index += 1
                    items.append(
                        ListItem(
                            Paragraph(
                                inline_markup(item_text, source), self.styles["Body"]
                            ),
                            leftIndent=13,
                        )
                    )
                flows.append(
                    ListFlowable(
                        items,
                        bulletType="1" if ordered else "bullet",
                        start="1" if ordered else None,
                        leftIndent=18,
                        bulletFontName="Vera",
                        bulletFontSize=7.5,
                        bulletColor=DEEP_BLUE,
                        spaceAfter=6,
                    )
                )
                continue
            if stripped.startswith(">"):
                flush_paragraph()
                quote_lines: list[str] = []
                while index < len(lines) and lines[index].strip().startswith(">"):
                    quote_lines.append(lines[index].strip()[1:].strip())
                    index += 1
                quote = " ".join(quote_lines)
                warning = any(
                    word in quote.lower() for word in ("warning", "critical", "danger")
                )
                flows.append(
                    Paragraph(
                        inline_markup(quote, source),
                        self.styles["Warning" if warning else "Callout"],
                    )
                )
                continue
            if stripped in {"---", "***", "___"}:
                flush_paragraph()
                flows.append(
                    HRFlowable(
                        width="100%",
                        color=LINE,
                        thickness=0.65,
                        spaceBefore=5,
                        spaceAfter=8,
                    )
                )
                index += 1
                continue
            if stripped.startswith("<!--"):
                flush_paragraph()
                while index < len(lines) and "-->" not in lines[index]:
                    index += 1
                index += 1
                continue
            if not stripped:
                flush_paragraph()
                index += 1
                continue
            paragraph.append(line)
            index += 1
        flush_paragraph()
        return flows

    def render_table(self, rows: list[list[str]], source: Path) -> list[Flowable]:
        column_count = max(len(row) for row in rows)
        normalized = [row + [""] * (column_count - len(row)) for row in rows]
        total_chars = max(sum(len(cell) for cell in row) for row in normalized)
        wide = column_count >= 5 or total_chars > 280
        available = (
            (landscape(LETTER)[0] - 1.16 * inch) if wide else (LETTER[0] - 1.34 * inch)
        )
        weights = []
        for col in range(column_count):
            largest = max(len(row[col]) for row in normalized)
            weights.append(max(9, min(52, largest)))
        weight_total = sum(weights)
        widths = [available * weight / weight_total for weight in weights]
        body_style = self.styles["TableBodyWide" if wide else "TableBody"]
        data: list[list[Paragraph]] = []
        for row_index, row in enumerate(normalized):
            style = self.styles["TableHead"] if row_index == 0 else body_style
            data.append([Paragraph(inline_markup(cell, source), style) for cell in row])
        table = LongTable(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
        vertical_padding = 2.5 if wide else 3.5
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4.2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4.2),
                    ("TOPPADDING", (0, 0), (-1, -1), vertical_padding),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), vertical_padding),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_BLUE]),
                ]
            )
        )
        if wide:
            return [
                NextPageTemplate("landscape"),
                PageBreak(),
                table,
                NextPageTemplate("portrait"),
                PageBreak(),
            ]
        return [table, Spacer(1, 8)]


def cover_story(
    config: ManualConfig,
    styles: dict[str, ParagraphStyle],
    digest: str,
) -> list[Flowable]:
    width = LETTER[0] - 1.44 * inch
    meta = [
        [
            Paragraph("SOFTWARE", styles["CoverMeta"]),
            Paragraph("DOCUMENT", styles["CoverMeta"]),
            Paragraph("SOURCE SET", styles["CoverMeta"]),
        ],
        [
            Paragraph(f"v{config.software_version}", styles["CoverMeta"]),
            Paragraph(config.document_revision, styles["CoverMeta"]),
            Paragraph(digest[:16], styles["CoverMeta"]),
        ],
    ]
    table = Table(meta, colWidths=[width / 3] * 3)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0C4A6E")),
                ("BOX", (0, 0), (-1, -1), 0.65, CYAN),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#38BDF8")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return [
        Spacer(1, 0.57 * inch),
        Paragraph(
            "UNIVERSAL THIRSTY FAMILY  /  CANONICAL FIELD MANUAL",
            styles["CoverKicker"],
        ),
        Paragraph(config.title, styles["CoverTitle"]),
        Paragraph(config.subtitle, styles["CoverSubtitle"]),
        Paragraph(
            "ONE FAMILY. SIX TIERS. ONE GOVERNED CURRENT.",
            styles["CoverStatement"],
        ),
        ArchitectureFlow(width, dark=True),
        Spacer(1, 0.27 * inch),
        table,
        Spacer(1, 0.35 * inch),
        Paragraph(
            "Language and runtime contract  |  policy and proof specification  |  "
            "security acceptance  |  deployment  |  release evidence  |  source traceability",
            styles["CoverMeta"],
        ),
        Spacer(1, 0.20 * inch),
        Paragraph(
            "Canonical principle: missing is not false; invalid is not false; "
            "unresolved is not evidence.",
            styles["CoverMeta"],
        ),
        NextPageTemplate("portrait"),
        PageBreak(),
    ]


def toc_story(styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            "TOC0",
            fontName="VeraBd",
            fontSize=9.1,
            leading=12,
            textColor=NAVY,
            leftIndent=0,
            firstLineIndent=0,
            spaceBefore=5,
        ),
        ParagraphStyle(
            "TOC1",
            fontName="Vera",
            fontSize=7.8,
            leading=10.4,
            textColor=INK,
            leftIndent=13,
            firstLineIndent=0,
        ),
        ParagraphStyle(
            "TOC2",
            fontName="Vera",
            fontSize=7.1,
            leading=9.2,
            textColor=MUTED,
            leftIndent=26,
            firstLineIndent=0,
        ),
    ]
    return [
        Paragraph("Contents", styles["TOCTitle"]),
        Paragraph(
            "The PDF outline and this table of contents are generated from the maintained source headings.",
            styles["Callout"],
        ),
        toc,
        NextPageTemplate("portrait"),
    ]


def colophon_story(
    renderer: MarkdownRenderer,
    config: ManualConfig,
    digest: str,
    entries: list[tuple[str, str]],
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    flows: list[Flowable] = [NextPageTemplate("portrait"), PageBreak()]
    flows.append(
        Paragraph("COLOPHON  /  REPRODUCIBLE SOURCE MANIFEST", styles["PartKicker"])
    )
    flows.append(renderer.heading("Document Provenance", 0, "PartTitle"))
    flows.append(
        Paragraph(
            f'Aggregate source SHA-256: <font name="Courier">{digest}</font>. '
            "The aggregate hashes each repository-relative path, a NUL separator, "
            "its exact bytes, and a final NUL in sorted path order. It includes the "
            "composition manifest and PDF builder, but not the generated PDF, avoiding "
            "a self-referential checksum.",
            styles["Body"],
        )
    )
    flows.append(
        Paragraph(
            f"Built deterministically for Thirsty-Lang {config.software_version}; "
            f"document revision {config.document_revision}; fixed source epoch "
            f"{config.source_date_epoch}. Final PDF metadata carries the same digest.",
            styles["Body"],
        )
    )
    rows = [["Source", "SHA-256"]] + [[path, sha] for path, sha in entries]
    flows.extend(renderer.render_table(rows, config.manifest_path))
    flows.extend(
        [
            Paragraph("Authority and limits", styles["H2"]),
            Paragraph(
                "This edition unifies maintained project documentation. Active source "
                "and deterministic tests decide implemented behavior when prose and code "
                "conflict. The Bootstrap Competence Register remains the authority for its "
                "own independent acceptance states; PDF generation does not promote a "
                "failed competence.",
                styles["Callout"],
            ),
            Paragraph(
                f"Copyright 2026 {config.publisher}. Distributed under {config.license}.",
                styles["Small"],
            ),
        ]
    )
    return flows


def build_pdf(config: ManualConfig, output: Path | None = None) -> tuple[Path, str]:
    output = (output or config.output).resolve()
    try:
        output.relative_to(ROOT)
    except ValueError:
        # Explicit validator/determinism temp outputs are allowed outside ROOT.
        pass
    output.parent.mkdir(parents=True, exist_ok=True)
    os.environ["SOURCE_DATE_EPOCH"] = str(config.source_date_epoch)
    rl_config.invariant = 1
    register_fonts()
    styles = make_styles()
    digest, entries = source_manifest(config)
    renderer = MarkdownRenderer(styles)
    story: list[Flowable] = []
    story.extend(cover_story(config, styles, digest))
    story.extend(toc_story(styles))
    for number, document in enumerate(config.documents, start=1):
        story.extend(renderer.render_document(document, number))
    story.extend(colophon_story(renderer, config, digest, entries, styles))
    doc = CanonicalDocTemplate(str(output), config, digest)
    metadata = {
        "title": f"{config.title} - v{config.software_version}",
        "author": config.publisher,
        "subject": f"{config.subtitle}; source-sha256={digest}",
        "keywords": f"Thirsty-Lang,TARL,governance,security,{digest}",
    }

    def canvas_maker(*args, **kwargs):
        return InvariantCanvas(*args, metadata=metadata, **kwargs)

    doc.multiBuild(story, canvasmaker=canvas_maker)
    return output, digest


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="composition manifest (default: docs/thirsty_lang_utf_101.toml)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="override final PDF path",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    config = load_manifest(manifest)
    output = args.output
    if output is not None and not output.is_absolute():
        output = ROOT / output
    final_path, digest = build_pdf(config, output)
    pdf_digest = hashlib.sha256(final_path.read_bytes()).hexdigest()
    print(f"PDF: {final_path}")
    print(f"Source SHA-256: {digest}")
    print(f"PDF SHA-256: {pdf_digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
