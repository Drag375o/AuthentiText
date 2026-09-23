"""
Dashboard activity and the "needs attention" list.

Both answer questions the other pages do not: what have I been doing lately,
and what is waiting for me. Everything here comes from data the application
already stores, so nothing new has to be recorded.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

WEEKS = 8


@dataclass(frozen=True)
class Week:
    start: object            # date of the Monday
    documents: int
    words: int
    height: int              # 0-100, for the bar chart
    is_current: bool


def weekly_activity(analyses, weeks: int = WEEKS) -> dict:
    """Documents analyzed per week, most recent week last."""
    today = timezone.localdate()
    this_monday = today - timedelta(days=today.weekday())
    starts = [this_monday - timedelta(weeks=offset) for offset in range(weeks - 1, -1, -1)]
    buckets = {start: {"documents": 0, "words": 0} for start in starts}

    for analysis in analyses:
        when = timezone.localtime(analysis.processed_at or analysis.created_at).date()
        monday = when - timedelta(days=when.weekday())
        if monday in buckets:
            buckets[monday]["documents"] += 1
            buckets[monday]["words"] += analysis.word_count or 0

    busiest = max((bucket["documents"] for bucket in buckets.values()), default=0)
    return {
        "weeks": [Week(start=start, documents=bucket["documents"], words=bucket["words"],
                       height=round(bucket["documents"] * 100 / busiest) if busiest else 0,
                       is_current=start == this_monday)
                  for start, bucket in buckets.items()],
        "documents": sum(bucket["documents"] for bucket in buckets.values()),
        "words": sum(bucket["words"] for bucket in buckets.values()),
        "any": busiest > 0,
        "first_start": starts[0],
    }


def attention_items(analyses, current_pipeline: str) -> list[dict]:
    """
    What is waiting: documents never analyzed, documents that failed, and
    documents analyzed by an older pipeline whose numbers would now differ.
    Each item names one document so there is something to click.
    """
    from analyzer.models import Analysis

    def describe(queryset, tone: str, singular: str, plural: str, action: str) -> dict | None:
        rows = list(queryset[:1])
        count = queryset.count()
        if not count:
            return None
        first = rows[0]
        return {"tone": tone, "count": count, "analysis": first, "action": action,
                "text": singular if count == 1 else plural.format(count=count - 1)}

    pending = analyses.filter(status=Analysis.Status.PENDING)
    failed = analyses.filter(status=Analysis.Status.FAILED)
    outdated = analyses.filter(status=Analysis.Status.COMPLETE).exclude(pipeline_version=current_pipeline)

    items = [
        describe(pending, "warn", "was never analyzed.",
                 "and {count} other document(s) were never analyzed.", "Analyze now"),
        describe(failed, "high", "failed to analyze.",
                 "and {count} other document(s) failed to analyze.", "Try again"),
        describe(outdated, "ok", "was analyzed by an older version of the pipeline.",
                 "and {count} other document(s) were analyzed by an older pipeline.", "Re-run it"),
    ]
    return [item for item in items if item]
