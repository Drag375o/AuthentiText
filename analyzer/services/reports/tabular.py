"""JSON and CSV exports. Same data as the PDF, for people who want the numbers."""
from __future__ import annotations

import csv
import io
import json


def render_json(data: dict) -> bytes:
    return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")


def render_csv(data: dict) -> bytes:
    """
    One long table: every feature, signal, profile score and sentence as a row.
    A single file keeps a spreadsheet import simple; filter on `section`.
    """
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["section", "name", "value", "unit_or_detail", "notes"])

    document, result = data["document"], data["result"]
    writer.writerow(["document", "title", document["title"], "", ""])
    writer.writerow(["document", "analyzed_at", document["analyzed_at"] or "", "", ""])
    for key in ("label_display", "ai_probability", "confidence", "uncertainty", "model_version",
                "pipeline_version", "embedding_backend"):
        writer.writerow(["result", key, "" if result[key] is None else result[key], "",
                         result["notice"] if key == "label_display" and result["is_demo"] else ""])

    for feature in data["features"]:
        writer.writerow(["feature", feature["name"], "" if feature["value"] is None else feature["value"],
                         feature["unit"], feature["label"]])
    for signal in data["signals"]:
        writer.writerow(["signal", signal["key"], "" if signal["score"] is None else signal["score"],
                         signal["family"], signal["finding"]])
    for dimension in data["profile"]:
        writer.writerow(["profile", dimension["key"], "" if dimension["score"] is None else dimension["score"],
                         "0-100", dimension["label"]])
    for sentence in data["sentences"]:
        writer.writerow(["sentence", sentence["index"] + 1,
                         "" if sentence["ai_probability"] is None else sentence["ai_probability"],
                         "heading" if sentence["heading"] else f"{sentence['words']} words",
                         sentence["text"]])
    for line in data["limitations"]:
        writer.writerow(["limitation", "", "", "", line])
    return buffer.getvalue().encode("utf-8-sig")   # BOM so Excel reads UTF-8 correctly
