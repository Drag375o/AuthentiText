"""Shared shape for every export, so PDF, JSON and CSV can never disagree."""
from __future__ import annotations

from datetime import datetime, timezone

from ..features import BY_NAME
from ..summary import build_summary

LIMITATIONS = [
    "A result describes measurable characteristics of the text. It does not prove authorship, AI use, plagiarism, academic misconduct or intent.",
    "Every pattern measured here also appears in human writing.",
    "Formality, personal voice and contraction use reflect genre and register more than authorship.",
    "Results are unreliable for short texts, and for text that has been rewritten or paraphrased.",
]


def build_report(analysis) -> dict:
    values = {f.feature_name: f.feature_value for f in analysis.features.all()}
    report = analysis.report or {}
    detection = report.get("detection", {})
    summary = build_summary(analysis, values, report)

    return {
        "document": {
            "title": analysis.display_name,
            "source": analysis.get_source_type_display(),
            "filename": analysis.filename,
            "language": analysis.language,
            "created_at": analysis.created_at.isoformat(),
            "analyzed_at": analysis.processed_at.isoformat() if analysis.processed_at else None,
            "text_sha256": analysis.text_hash,
        },
        "result": {
            "label": analysis.result_label,
            "label_display": analysis.get_result_label_display() if analysis.result_label else "",
            "ai_probability": analysis.ai_probability,
            "confidence": analysis.confidence,
            "uncertainty": analysis.uncertainty,
            "is_demo": analysis.is_demo,
            "notice": detection.get("notice", ""),
            "reasons": [r for r in detection.get("reasons", []) if r],
            "model_version": analysis.model_version,
            "pipeline_version": analysis.pipeline_version,
            "embedding_backend": report.get("embedding_label", ""),
        },
        "summary": summary,
        "signals": [
            {"key": s["key"], "label": s["label"], "family": s["family_label"], "score": s["score"],
             "feature": s["feature"], "value": s["value"], "finding": s["text"], "caveat": s["caveat"]}
            for s in detection.get("signals", [])
        ],
        "families": detection.get("families", []),
        "features": [
            {"name": name, "label": BY_NAME[name].label, "category": BY_NAME[name].category,
             "unit": BY_NAME[name].unit, "value": values.get(name),
             "description": BY_NAME[name].description}
            for name in sorted(values)
            if name in BY_NAME
        ],
        "profile": report.get("profile", []),
        "sentences": [
            {"index": s.sentence_index, "text": s.text, "ai_probability": s.ai_probability,
             "words": (s.signals or {}).get("words"), "heading": bool((s.signals or {}).get("heading")),
             "paragraph": (s.signals or {}).get("paragraph", 0),
             "markers": (s.signals or {}).get("markers", [])}
            for s in analysis.sentences.all()
        ],
        "patterns": report.get("patterns", []),
        "limitations": LIMITATIONS,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "AuthentiText",
    }
