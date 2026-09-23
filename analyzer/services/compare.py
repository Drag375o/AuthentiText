"""
Comparing two analyses.

Sentences are aligned with difflib rather than lines, because the pipeline has
already segmented them properly: a "changed sentence" is then a unit a reader
recognises. Within a changed pair, a word-level diff shows exactly what moved.

Every number is reported as a pair plus its difference. Differences between two
documents of different length, genre or topic say more about those things than
about how they were written, so the interface repeats that caveat.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from .features import BY_NAME
from .stylometry import PROFILE_DIMENSIONS

WORD_RE = re.compile(r"\w+(?:['\u2019-]\w+)*|\s+|[^\w\s]")
BARE_WORD_RE = re.compile(r"[^\W\d_]+|\d+")
# Similarity is measured over words, not characters. Two unrelated English
# sentences share plenty of letters (0.31 for "The cat sat on the mat" against
# "Feline occupancy of floor coverings remains widespread"), which made every
# pair look vaguely related. Over words the same pair scores 0.00.
SIMILAR_ENOUGH = 0.60      # below this, a changed pair reads as a rewrite rather than an edit
UNRELATED = 0.20           # below this the two sentences have nothing to do with each other,
                           # so they are reported as a removal and an addition, not as an edit
COMPARED_FEATURES = [
    "word_count", "sentence_count", "paragraph_count",
    "sentence_length_mean", "sentence_length_cv", "sentence_length_burstiness",
    "mattr", "mtld", "type_token_ratio", "lexical_density", "rare_word_ratio",
    "trigram_repeat_rate", "repeated_phrase_coverage",
    "parse_depth_mean", "clauses_per_sentence", "passive_sentence_ratio",
    "formality_score", "first_person_ratio", "contraction_ratio",
    "transitions_per_100", "hedges_per_100", "formulaic_phrases_per_100",
    "semantic_diversity", "local_coherence",
]


@dataclass(frozen=True)
class Side:
    analysis: object
    values: dict[str, float]
    sentences: list[str]
    vocabulary: set[str]


def _words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def sentence_similarity(before: str, after: str) -> float:
    """How much wording two sentences share, 0-1, compared word by word."""
    return SequenceMatcher(None, BARE_WORD_RE.findall(before.lower()),
                           BARE_WORD_RE.findall(after.lower())).ratio()


def _side(analysis) -> Side:
    sentences = [s.text for s in analysis.sentences.all()]
    vocabulary = {word.lower() for sentence in sentences for word in re.findall(r"[^\W\d_]+", sentence)}
    return Side(analysis, {f.feature_name: f.feature_value for f in analysis.features.all()},
                sentences, vocabulary)


def word_diff(before: str, after: str) -> tuple[list[dict], list[dict]]:
    """Two runs of {text, change} where change is "same", "removed" or "added"."""
    matcher = SequenceMatcher(None, _words(before), _words(after), autojunk=False)
    left, right = [], []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        old, new = "".join(_words(before)[i1:i2]), "".join(_words(after)[j1:j2])
        if tag == "equal":
            left.append({"text": old, "change": "same"})
            right.append({"text": new, "change": "same"})
            continue
        if old:
            left.append({"text": old, "change": "removed"})
        if new:
            right.append({"text": new, "change": "added"})
    return left, right


def align_sentences(a: Side, b: Side) -> list[dict]:
    """
    Rows of {kind, a, b, ...} where kind is unchanged, changed, added or removed.
    Matching is on normalised text, so a change in spacing alone is not a change.
    """
    normalise = lambda text: " ".join(text.lower().split())
    left = [normalise(text) for text in a.sentences]
    right = [normalise(text) for text in b.sentences]
    rows: list[dict] = []

    for tag, i1, i2, j1, j2 in SequenceMatcher(None, left, right, autojunk=False).get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                rows.append({"kind": "unchanged", "a": a.sentences[i1 + offset], "b": b.sentences[j1 + offset],
                             "a_index": i1 + offset, "b_index": j1 + offset})
            continue
        if tag == "replace":
            # Pair them up in order; a pair that barely resembles its partner is
            # reported as a rewrite rather than an edit.
            for offset in range(max(i2 - i1, j2 - j1)):
                before = a.sentences[i1 + offset] if i1 + offset < i2 else None
                after = b.sentences[j1 + offset] if j1 + offset < j2 else None
                if before is None:
                    rows.append({"kind": "added", "a": None, "b": after, "b_index": j1 + offset})
                elif after is None:
                    rows.append({"kind": "removed", "a": before, "b": None, "a_index": i1 + offset})
                else:
                    ratio = sentence_similarity(before, after)
                    if ratio < UNRELATED:
                        rows.append({"kind": "removed", "a": before, "b": None, "a_index": i1 + offset})
                        rows.append({"kind": "added", "a": None, "b": after, "b_index": j1 + offset})
                        continue
                    left_run, right_run = word_diff(before, after)
                    rows.append({"kind": "changed", "a": before, "b": after,
                                 "a_index": i1 + offset, "b_index": j1 + offset,
                                 "a_runs": left_run, "b_runs": right_run,
                                 "similarity": round(ratio, 3), "rewritten": ratio < SIMILAR_ENOUGH})
            continue
        for offset in range(i1, i2):
            rows.append({"kind": "removed", "a": a.sentences[offset], "b": None, "a_index": offset})
        for offset in range(j1, j2):
            rows.append({"kind": "added", "a": None, "b": b.sentences[offset], "b_index": offset})
    return rows


def feature_rows(a: Side, b: Side) -> list[dict]:
    rows = []
    for name in COMPARED_FEATURES:
        spec = BY_NAME.get(name)
        if spec is None:
            continue
        first, second = a.values.get(name), b.values.get(name)
        delta = None if first is None or second is None else second - first
        rows.append({"spec": spec, "a": first, "b": second, "delta": delta,
                     "direction": "" if delta is None or abs(delta) < 1e-9 else ("up" if delta > 0 else "down")})
    return rows


def profile_rows(a: Side, b: Side) -> list[dict]:
    a_scores = {p["key"]: p for p in (a.analysis.report or {}).get("profile", [])}
    b_scores = {p["key"]: p for p in (b.analysis.report or {}).get("profile", [])}
    rows = []
    for dimension in PROFILE_DIMENSIONS:
        first = (a_scores.get(dimension.key) or {}).get("score")
        second = (b_scores.get(dimension.key) or {}).get("score")
        rows.append({"label": dimension.label, "description": dimension.description,
                     "a": first, "b": second,
                     "delta": None if first is None or second is None else second - first})
    return rows


def detection_rows(a: Side, b: Side) -> dict:
    def side(analysis):
        detection = (analysis.report or {}).get("detection", {})
        return {"label": analysis.get_result_label_display() if analysis.result_label else "",
                "probability": analysis.ai_probability, "confidence": analysis.confidence,
                "is_demo": analysis.is_demo, "families": detection.get("families", [])}

    first, second = side(a.analysis), side(b.analysis)
    families = []
    for one, two in zip(first["families"], second["families"]):
        families.append({"label": one["label"], "a": one["score"], "b": two["score"],
                         "delta": None if one["score"] is None or two["score"] is None else two["score"] - one["score"]})
    delta = (None if first["probability"] is None or second["probability"] is None
             else second["probability"] - first["probability"])
    return {"a": first, "b": second, "families": families, "probability_delta": delta}


def build_comparison(analysis_a, analysis_b) -> dict:
    a, b = _side(analysis_a), _side(analysis_b)
    rows = align_sentences(a, b)
    counts = {kind: sum(1 for row in rows if row["kind"] == kind)
              for kind in ("unchanged", "changed", "added", "removed")}
    return {
        "a": analysis_a,
        "b": analysis_b,
        "rows": rows,
        "counts": counts,
        "rewritten": sum(1 for row in rows if row.get("rewritten")),
        "features": feature_rows(a, b),
        "profile": profile_rows(a, b),
        "detection": detection_rows(a, b),
        "vocabulary": {
            "added": sorted(b.vocabulary - a.vocabulary)[:40],
            "removed": sorted(a.vocabulary - b.vocabulary)[:40],
            "added_count": len(b.vocabulary - a.vocabulary),
            "removed_count": len(a.vocabulary - b.vocabulary),
            "shared": len(a.vocabulary & b.vocabulary),
        },
    }
