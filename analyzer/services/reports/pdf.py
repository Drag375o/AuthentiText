"""
PDF report (ReportLab).

ReportLab is used rather than an HTML-to-PDF converter because it is pure
Python: it installs with pip on Windows without system libraries, which matters
for a project people are meant to be able to run.

Every style uses Times (Times-Roman and Times-Bold), the PDF built-in faces, so
the file needs no embedded fonts and reads the same everywhere.
"""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from xml.sax.saxutils import escape

INK = colors.HexColor("#111111")
MUTED = colors.HexColor("#6B6B6B")
RULE = colors.HexColor("#DDDDDD")
FOG = colors.HexColor("#F4F4F4")
WARN = colors.HexColor("#8E3B46")
MAX_SENTENCES = 60


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName="Times-Bold", fontSize=22,
                                leading=26, textColor=INK, alignment=TA_LEFT, spaceAfter=2),
        "sub": ParagraphStyle("sub", parent=base["Normal"], fontName="Times-Roman", fontSize=9,
                              textColor=MUTED, spaceAfter=14),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Times-Bold", fontSize=13,
                             textColor=INK, spaceBefore=16, spaceAfter=6),
        "body": ParagraphStyle("body", parent=base["Normal"], fontName="Times-Roman", fontSize=10.5,
                               leading=15.5, textColor=INK, spaceAfter=7, alignment=TA_JUSTIFY),
        "body_tight": ParagraphStyle("body_tight", parent=base["Normal"], fontName="Times-Roman", fontSize=10,
                                     leading=14.5, textColor=INK, alignment=TA_JUSTIFY),
        "small": ParagraphStyle("small", parent=base["Normal"], fontName="Times-Roman", fontSize=8.5,
                                leading=12, textColor=MUTED),
        "cell": ParagraphStyle("cell", parent=base["Normal"], fontName="Times-Roman", fontSize=8.5,
                               leading=11, textColor=INK),
        "notice": ParagraphStyle("notice", parent=base["Normal"], fontName="Times-Bold", fontSize=10,
                                 leading=14, textColor=WARN, spaceAfter=10),
    }


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Times-Roman", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 12 * mm, "AuthentiText \u2014 signals, not proof")
    canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def _percent(value) -> str:
    return "\u2014" if value is None else f"{round(value * 100)}%"


def _table(rows, widths, styles, header: bool = True) -> Table:
    if not header:
        rows = rows[1:]
    table = Table(rows, colWidths=widths, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold" if header else "Times-Roman"),
        ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("BACKGROUND", (0, 0), (-1, 0), FOG if header else colors.white),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def render_pdf(data: dict) -> bytes:
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"AuthentiText report: {data['document']['title']}",
                            author="AuthentiText", leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=20 * mm)
    story = []
    document, result = data["document"], data["result"]

    story.append(Paragraph(escape(document["title"]), styles["title"]))
    story.append(Paragraph(
        f"Writing analysis report &middot; {document['source']}"
        f"{' &middot; ' + escape(document['filename']) if document['filename'] else ''}"
        f" &middot; analyzed {escape((document['analyzed_at'] or '')[:16].replace('T', ' '))}", styles["sub"]))

    if result["is_demo"]:
        story.append(Paragraph(escape(result["notice"] or "DEMO ANALYSIS \u2014 not a real prediction"), styles["notice"]))

    story.append(Paragraph("Summary", styles["h2"]))
    summary_rows = [[Paragraph(f"<b>{escape(point['label'])}</b>", styles["cell"]),
                     Paragraph(escape(point["text"]), styles["body_tight"])]
                    for point in data["summary"].get("points", [])]
    if summary_rows:
        story.append(_table([["", ""]] + summary_rows, [32 * mm, 134 * mm], styles, header=False))
    else:
        for paragraph in data["summary"]["paragraphs"]:
            story.append(Paragraph(escape(paragraph), styles["body"]))

    story.append(Paragraph("Result", styles["h2"]))
    story.append(_table([
        ["Measure", "Value"],
        ["Label", result["label_display"] or "\u2014"],
        ["AI-associated signal", _percent(result["ai_probability"])],
        ["Confidence", _percent(result["confidence"])],
        ["Uncertainty", _percent(result["uncertainty"])],
        ["Detector", f"{result['model_version']}{' (demo)' if result['is_demo'] else ''}"],
        ["Pipeline", result["pipeline_version"]],
        ["Embeddings", result["embedding_backend"] or "\u2014"],
    ], [70 * mm, 95 * mm], styles))
    for reason in result["reasons"]:
        story.append(Paragraph(f"\u2022 {escape(reason)}", styles["small"]))

    if data["signals"]:
        story.append(Paragraph("Signal breakdown", styles["h2"]))
        rows = [["Signal", "Family", "Score", "What was found"]]
        rows += [[Paragraph(escape(s["label"]), styles["cell"]), Paragraph(escape(s["family"]), styles["cell"]),
                  _percent(s["score"]), Paragraph(escape(s["finding"]), styles["small"])] for s in data["signals"]]
        story.append(_table(rows, [32 * mm, 22 * mm, 14 * mm, 97 * mm], styles))

    if data["profile"]:
        story.append(Paragraph("Writing profile", styles["h2"]))
        story.append(Paragraph("Scores from 0 to 100 against fixed reference ranges, not percentiles. "
                               "They describe the writing, not the writer.", styles["small"]))
        story.append(Spacer(1, 4))
        rows = [["Dimension", "Score", "How it is measured"]]
        rows += [[Paragraph(escape(d["label"]), styles["cell"]), "\u2014" if d["score"] is None else str(d["score"]),
                  Paragraph(escape(d["description"]), styles["small"])] for d in data["profile"]]
        story.append(_table(rows, [36 * mm, 14 * mm, 115 * mm], styles))

    story.append(PageBreak())
    story.append(Paragraph("Measured features", styles["h2"]))
    rows = [["Feature", "Category", "Value"]]
    for feature in data["features"]:
        value = feature["value"]
        shown = ("\u2014" if value is None else
                 f"{round(value * 100)}%" if feature["unit"] == "ratio" else
                 f"{value:,.0f}" if feature["unit"] == "count" else f"{value:.2f}")
        rows.append([Paragraph(escape(feature["label"]), styles["cell"]), feature["category"].title(), shown])
    story.append(_table(rows, [85 * mm, 40 * mm, 40 * mm], styles))

    sentences = data["sentences"]
    if sentences:
        story.append(Paragraph("Sentence analysis", styles["h2"]))
        shown = sentences[:MAX_SENTENCES]
        rows = [["#", "Sentence", "Words", "Signal"]]
        for sentence in shown:
            rows.append([str(sentence["index"] + 1),
                         Paragraph(escape(sentence["text"][:300]), styles["small"]),
                         str(sentence["words"] or ""),
                         "heading" if sentence["heading"] else _percent(sentence["ai_probability"])])
        story.append(_table(rows, [10 * mm, 112 * mm, 17 * mm, 26 * mm], styles))
        if len(sentences) > MAX_SENTENCES:
            story.append(Paragraph(f"Showing the first {MAX_SENTENCES} of {len(sentences)} sentences. "
                                   f"The JSON and CSV exports contain them all.", styles["small"]))

    story.append(Paragraph("Limitations", styles["h2"]))
    for line in data["limitations"]:
        story.append(Paragraph(f"\u2022 {escape(line)}", styles["body"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Generated {data['generated_at'][:16].replace('T', ' ')} UTC by AuthentiText. "
                           f"Document fingerprint (SHA-256): {document['text_sha256'][:16]}\u2026", styles["small"]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
