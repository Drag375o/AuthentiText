"""
The writing profile across a user's documents.

Deliberately not a single average. Averaging a lab report with a diary produces
a number that describes neither, and a portfolio of documents in different
genres will vary more between genres than between writers. So each dimension
reports the spread: where the documents sit, the median, and the range.

Only completed analyses count, and a dimension is reported only when at least
one document has a score for it.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

from .stylometry import PROFILE_DIMENSIONS

MIN_DOCUMENTS = 2       # below this there is no spread to report
WIDE_SPREAD = 35        # a range this wide is worth remarking on


@dataclass(frozen=True)
class Point:
    analysis_id: str
    title: str
    score: int


def _points(analyses, key: str) -> list[Point]:
    points = []
    for analysis in analyses:
        for dimension in (analysis.report or {}).get("profile", []):
            if dimension["key"] == key and dimension["score"] is not None:
                points.append(Point(str(analysis.pk), analysis.display_name, int(dimension["score"])))
    return points


def build_writing_profile(analyses: list) -> dict:
    rows = []
    for dimension in PROFILE_DIMENSIONS:
        points = _points(analyses, dimension.key)
        scores = [point.score for point in points]
        rows.append({
            "key": dimension.key,
            "label": dimension.label,
            "description": dimension.description,
            "points": points,
            "count": len(scores),
            "median": round(statistics.median(scores)) if scores else None,
            "low": min(scores) if scores else None,
            "high": max(scores) if scores else None,
            "spread": (max(scores) - min(scores)) if len(scores) > 1 else None,
        })

    widest = max((row for row in rows if row["spread"] is not None),
                 key=lambda row: row["spread"], default=None)
    steadiest = min((row for row in rows if row["spread"] is not None),
                    key=lambda row: row["spread"], default=None)
    words = [a.word_count for a in analyses if a.word_count]
    return {
        "rows": rows,
        "documents": len(analyses),
        "total_words": sum(words),
        "median_words": round(statistics.median(words)) if words else 0,
        "first": min((a.created_at for a in analyses), default=None),
        "last": max((a.created_at for a in analyses), default=None),
        "widest": widest if widest and widest["spread"] and widest["spread"] >= WIDE_SPREAD else None,
        "steadiest": steadiest,
        "enough": len(analyses) >= MIN_DOCUMENTS,
    }
