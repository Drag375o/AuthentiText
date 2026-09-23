"""
The document as a PDF with each sentence marked by its signal.

Marks never rely on colour alone. Every band has a background tint AND a
different number of underlines, so the marks still read in greyscale or in
print (ReportLab supports single and double rules, not dashes):

    Low     no mark
    Medium  single underline, grey tint
    High    double underline, red tint

Sentences are drawn as one flowing paragraph per source paragraph, using
ReportLab's inline markup, so the document keeps its original shape.
"""
from __future__ import annotations

import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

INK = colors.HexColor("#111111")
MUTED = colors.HexColor("#6B6B6B")
WARN = colors.HexColor("#8E3B46")
HIGH_TINT = colors.HexColor("#F6E4E6")
MID_TINT = colors.HexColor("#E8E8E8")

BANDS = [
    {"key": "low", "ceiling": 0.34, "name": "Low signal", "tint": None, "underline": None,
     "legend": "left plain \u2014 nothing notable was measured in the sentence."},
    {"key": "mid", "ceiling": 0.60, "name": "Medium signal", "tint": MID_TINT, "underline": ("single", MUTED),
     "legend": "grey tint, single underline \u2014 some characteristics were found, but fewer or weaker."},
    {"key": "high", "ceiling": 1.01, "name": "High signal", "tint": HIGH_TINT, "underline": ("double", WARN),
     "legend": "red tint, double underline \u2014 several characteristics associated with AI-generated examples."},
]


def band_for(probability: float | None) -> dict | None:
    if probability is None:
        return None
    for band in BANDS:
        if probability < band["ceiling"]:
            return band
    return BANDS[-1]


def _hex(colour) -> str:
    return "#" + colour.hexval()[2:]


def mark(text: str, band: dict | None) -> str:
    """Wrap sentence text in ReportLab inline markup for its band."""
    body = escape(text)
    if band is None or band["underline"] is None:
        return body
    kind, colour = band["underline"]
    marked = f'<u kind="{kind}" color="{_hex(colour)}" width="0.9" offset="-2.5">{body}</u>'
    return f'<font backColor="{_hex(band["tint"])}">{marked}</font>' if band["tint"] else marked


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName="Times-Bold", fontSize=20,
                                leading=24, textColor=INK, alignment=0, spaceAfter=2),
        "sub": ParagraphStyle("sub", parent=base["Normal"], fontName="Times-Roman", fontSize=9,
                              textColor=MUTED, spaceAfter=12),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Times-Bold", fontSize=12,
                             textColor=INK, spaceBefore=14, spaceAfter=6),
        "legend": ParagraphStyle("legend", parent=base["Normal"], fontName="Times-Roman", fontSize=9.5,
                                 leading=15, textColor=INK, leftIndent=6, spaceAfter=3),
        "body": ParagraphStyle("body", parent=base["Normal"], fontName="Times-Roman", fontSize=11,
                               leading=18, textColor=INK, spaceAfter=9, alignment=TA_JUSTIFY),
        "heading": ParagraphStyle("docheading", parent=base["Normal"], fontName="Times-Bold", fontSize=11.5,
                                  leading=16, textColor=INK, spaceBefore=6, spaceAfter=5),
        "small": ParagraphStyle("small", parent=base["Normal"], fontName="Times-Roman", fontSize=8.5,
                                leading=12, textColor=MUTED),
        "notice": ParagraphStyle("notice", parent=base["Normal"], fontName="Times-Bold", fontSize=10,
                                 leading=14, textColor=WARN, spaceAfter=8),
    }


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Times-Roman", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 12 * mm, "AuthentiText sentence heatmap \u2014 signals, not proof")
    canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def render_heatmap_pdf(data: dict) -> bytes:
    styles = _styles()
    buffer = io.BytesIO()
    document_meta, result = data["document"], data["result"]
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"AuthentiText heatmap: {document_meta['title']}",
                            author="AuthentiText", leftMargin=22 * mm, rightMargin=22 * mm,
                            topMargin=18 * mm, bottomMargin=20 * mm)
    story = []

    story.append(Paragraph(escape(document_meta["title"]), styles["title"]))
    probability = result["ai_probability"]
    signal = "" if probability is None else f", {round(probability * 100)}% signal"
    story.append(Paragraph(f"Sentence heatmap &middot; {escape(result['label_display'] or 'not analyzed')}{signal}",
                           styles["sub"]))
    if result["is_demo"]:
        story.append(Paragraph(escape(result["notice"] or "DEMO ANALYSIS \u2014 not a real prediction"), styles["notice"]))

    story.append(Paragraph("How to read the marks", styles["h2"]))
    for band in BANDS:
        sample = mark(band["name"], band)
        story.append(Paragraph(f"&bull;&nbsp; {sample}: {escape(band['legend'])}", styles["legend"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("These marks are signals, not proof. They do not show who wrote the text, and every "
                           "pattern measured also appears in human writing.", styles["small"]))

    story.append(Paragraph("The document", styles["h2"]))
    block: list[str] = []
    current = None
    for sentence in data["sentences"]:
        key = (sentence.get("paragraph"), sentence["heading"])
        if current is not None and key != current:
            story.append(Paragraph(" ".join(block), styles["heading" if current[1] else "body"]))
            block = []
        current = key
        block.append(escape(sentence["text"]) if sentence["heading"]
                     else mark(sentence["text"], band_for(sentence["ai_probability"])))
    if block:
        story.append(Paragraph(" ".join(block), styles["heading" if current and current[1] else "body"]))

    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Generated {data['generated_at'][:16].replace('T', ' ')} UTC by AuthentiText. "
                           f"Detector {escape(result['model_version'])}"
                           f"{' (demo, no measured accuracy)' if result['is_demo'] else ''}.", styles["small"]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
