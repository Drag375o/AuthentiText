"""
The document as a Word file with each sentence marked by its signal.

Marks never rely on colour alone: each band has its own highlight AND its own
underline style, so the file still reads correctly in greyscale, in print, or
for a reader with colour-vision deficiency. Everything is set in Times New
Roman, and headings are plain bold black rather than Word's default blue. A legend at the top explains all
three bands, and the reader can edit or remove the marks like any other Word
formatting.
"""
from __future__ import annotations

import io

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX, WD_UNDERLINE
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

BANDS = [
    {"key": "high", "ceiling": 1.01, "name": "High signal",
     "highlight": WD_COLOR_INDEX.PINK, "underline": WD_UNDERLINE.DOTTED,
     "legend": "Pink highlight, dotted underline: the sentence shows several characteristics associated with AI-generated examples."},
    {"key": "mid", "ceiling": 0.60, "name": "Medium signal",
     "highlight": WD_COLOR_INDEX.YELLOW, "underline": WD_UNDERLINE.DASH,
     "legend": "Yellow highlight, dashed underline: some characteristics were found, but fewer or weaker."},
    {"key": "low", "ceiling": 0.34, "name": "Low signal",
     "highlight": None, "underline": WD_UNDERLINE.NONE,
     "legend": "No highlight: nothing notable was measured in the sentence."},
]
ORDERED = sorted(BANDS, key=lambda b: b["ceiling"])   # low, mid, high
GREY = RGBColor(0x6B, 0x6B, 0x6B)
BLACK = RGBColor(0x00, 0x00, 0x00)
BODY_FONT = "Times New Roman"
BLACK = RGBColor(0x00, 0x00, 0x00)
FONT = "Times New Roman"


def _use_font(style_font) -> None:
    """Word needs the typeface named in the rFonts element as well as on the style."""
    style_font.name = FONT
    element = style_font.element.rPr if hasattr(style_font.element, "rPr") else None
    rpr = element if element is not None else style_font.element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    for attribute in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attribute), FONT)


def _plain_headings(document) -> None:
    """Headings in plain bold black: no Word blue, no italics."""
    for name in ("Heading 1", "Heading 2", "Heading 3", "Title"):
        try:
            style = document.styles[name]
        except KeyError:
            continue
        _use_font(style.font)
        style.font.bold = True
        style.font.italic = False
        style.font.color.rgb = BLACK


def band_for(probability: float | None) -> dict | None:
    if probability is None:
        return None
    for band in ORDERED:
        if probability < band["ceiling"]:
            return band
    return ORDERED[-1]


def _use_body_font(font) -> None:
    """Set the typeface for Latin and for the theme fallbacks Word uses."""
    font.name = BODY_FONT
    element = font.element.get_or_add_rPr().get_or_add_rFonts()
    for attribute in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        element.set(qn(attribute), BODY_FONT)


def _style_document(document) -> None:
    """Times New Roman throughout; headings bold and black rather than Word's blue."""
    normal = document.styles["Normal"]
    _use_body_font(normal.font)
    normal.font.size = Pt(11)
    normal.font.color.rgb = BLACK
    for name, size in (("Heading 1", 16), ("Heading 2", 13)):
        style = document.styles[name]
        _use_body_font(style.font)
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = BLACK
        style.element.xpath(".//w:color") and [c.set(qn("w:val"), "000000") for c in style.element.xpath(".//w:color")]


def _meta(paragraph, text: str, size: float = 9) -> None:
    run = paragraph.add_run(text)
    _use_body_font(run.font)
    run.font.size = Pt(size)
    run.font.color.rgb = GREY


def render_docx(data: dict) -> bytes:
    document = Document()
    normal = document.styles["Normal"]
    _use_font(normal.font)
    normal.font.size = Pt(11)
    _plain_headings(document)

    result = data["result"]
    heading = document.add_heading(data["document"]["title"], level=1)
    heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
    probability = result["ai_probability"]
    signal_text = "" if probability is None else f", {round(probability * 100)}% signal"
    _meta(document.add_paragraph(),
          f"Sentence heatmap from AuthentiText \u00b7 {result['label_display'] or 'not analyzed'}{signal_text}")

    if result["is_demo"]:
        notice = document.add_paragraph()
        run = notice.add_run(result["notice"] or "DEMO ANALYSIS \u2014 not a real prediction")
        _use_body_font(run.font)
        run.bold = True
        run.font.size = Pt(10.5)
        run.font.color.rgb = BLACK

    document.add_heading("How to read the marks", level=2)
    for band in reversed(ORDERED):
        bullet = document.add_paragraph(style="List Bullet")
        sample = bullet.add_run(band["name"])
        _use_body_font(sample.font)
        sample.underline = band["underline"]
        if band["highlight"]:
            sample.font.highlight_color = band["highlight"]
        rest = bullet.add_run(" \u2014 " + band["legend"].split(": ", 1)[1])
        _use_body_font(rest.font)
        rest.font.size = Pt(10.5)

    caveat = document.add_paragraph()
    _meta(caveat, "These marks are signals, not proof. They do not show who wrote the text, and every "
                  "pattern measured also appears in human writing.", size=9.5)

    document.add_heading("The document", level=2)
    paragraph = None
    current_block = None
    for sentence in data["sentences"]:
        block = (sentence.get("paragraph"), sentence["heading"])
        if paragraph is None or block != current_block:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.space_after = Pt(8)
            current_block = block
        else:
            paragraph.add_run(" ")
        run = paragraph.add_run(sentence["text"])
        _use_body_font(run.font)
        if sentence["heading"]:
            run.bold = True
            continue
        band = band_for(sentence["ai_probability"])
        if band:
            run.underline = band["underline"]
            if band["highlight"]:
                run.font.highlight_color = band["highlight"]

    document.add_page_break()
    document.add_heading("Sentence scores", level=2)
    table = document.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    for index, title in enumerate(("#", "Signal", "Sentence")):
        cell = table.rows[0].cells[index]
        run = cell.paragraphs[0].add_run(title)
        run.bold = True
        run.font.color.rgb = BLACK
    for sentence in data["sentences"]:
        cells = table.add_row().cells
        cells[0].text = str(sentence["index"] + 1)
        cells[1].text = ("heading" if sentence["heading"] else
                         "\u2014" if sentence["ai_probability"] is None else
                         f"{round(sentence['ai_probability'] * 100)}%")
        cells[2].text = sentence["text"]
        for cell in cells:
            for run in cell.paragraphs[0].runs:
                _use_body_font(run.font)
                run.font.size = Pt(10)

    _meta(document.add_paragraph(), f"Generated {data['generated_at'][:16].replace('T', ' ')} UTC by AuthentiText. "
                                    f"Detector {result['model_version']}"
                                    f"{' (demo, no measured accuracy)' if result['is_demo'] else ''}.")

    # Table styles carry their own fonts, so set every run explicitly.
    for paragraph in document.paragraphs:
        for run in paragraph.runs:
            _use_font(run.font)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        _use_font(run.font)
                        run.font.size = Pt(9.5)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
