"""
Discourse markers, formulaic phrases, and sentence openings.

Patterns come from a configurable JSON library (analyzer/resources/patterns.json,
or settings.PATTERN_LIBRARY_PATH). Each pattern is tokenised with spaCy's
tokenizer and matched against sentence tokens by normalised form, so case,
curly apostrophes and punctuation between words don't matter. Longer patterns
win over shorter ones that overlap them.

These are descriptive signals. Transitions and hedges are normal in good
writing; a match is a reason to look, never evidence of AI use.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from django.conf import settings

from .nlp import get_nlp
from .preprocessing import ProcessedDocument, normalize_form

STRENGTHS = ("low", "medium", "high")
POSITIONS = ("any", "start")
RATE_FEATURES = {
    "transition": "transitions_per_100", "contrast": "contrast_markers_per_100", "cause_effect": "cause_effect_markers_per_100",
    "conclusion": "conclusion_markers_per_100", "emphasis": "emphasis_markers_per_100", "hedging": "hedges_per_100",
    "academic_formula": "formulaic_phrases_per_100",
}
OPENING_WORDS = 2


class PatternLibraryError(ValueError):
    pass


@dataclass(frozen=True)
class Pattern:
    text: str
    category: str
    description: str
    strength: str
    position: str
    pos: str | None
    tokens: tuple[str, ...]


def library_path() -> Path:
    return Path(getattr(settings, "PATTERN_LIBRARY_PATH", "") or Path(__file__).resolve().parent.parent / "resources" / "patterns.json")


def validate_library(data: dict) -> None:
    categories = data.get("categories")
    if not isinstance(categories, dict) or not categories:
        raise PatternLibraryError("The library needs a 'categories' object.")
    seen = set()
    for i, p in enumerate(data.get("patterns", [])):
        where = f"pattern #{i} ({p.get('pattern')!r})"
        for key in ("pattern", "category", "description", "strength"):
            if not isinstance(p.get(key), str) or not p[key].strip():
                raise PatternLibraryError(f"{where} is missing '{key}'.")
        if p["category"] not in categories:
            raise PatternLibraryError(f"{where} has unknown category '{p['category']}'.")
        if p["strength"] not in STRENGTHS:
            raise PatternLibraryError(f"{where} has strength '{p['strength']}'; use one of {STRENGTHS}.")
        if p.get("position", "any") not in POSITIONS:
            raise PatternLibraryError(f"{where} has position '{p['position']}'; use one of {POSITIONS}.")
        key = p["pattern"].strip().lower()
        if key in seen:
            raise PatternLibraryError(f"{where} is a duplicate.")
        seen.add(key)


@lru_cache(maxsize=1)
def load_library() -> tuple[dict[str, str], tuple[Pattern, ...]]:
    data = json.loads(library_path().read_text(encoding="utf-8"))
    validate_library(data)
    tokenizer = get_nlp().tokenizer
    patterns = []
    for p in data["patterns"]:
        tokens = tuple(normalize_form(t.norm_ or t.text) for t in tokenizer(p["pattern"]) if not t.is_punct or t.text == "-")
        tokens = tuple(t for t in tokens if t != "-")
        patterns.append(Pattern(p["pattern"], p["category"], p["description"], p["strength"],
                                p.get("position", "any"), p.get("pos"), tokens))
    patterns.sort(key=lambda p: -len(p.tokens))           # longest first
    return data["categories"], tuple(patterns)


def find_patterns(doc: ProcessedDocument) -> list[dict]:
    """Every non-overlapping match: pattern, category, sentence index, and span in the original."""
    _, patterns = load_library()
    matches = []
    for sentence in doc.sentences:
        tokens = [t for t in sentence.tokens if not t.is_punct]
        norms = [t.norm for t in tokens]
        used = [False] * len(tokens)
        for pattern in patterns:
            n = len(pattern.tokens)
            limit = 1 if pattern.position == "start" else len(tokens) - n + 1
            for i in range(max(0, limit)):
                if tuple(norms[i:i + n]) != pattern.tokens or any(used[i:i + n]):
                    continue
                if pattern.pos and tokens[i].pos != pattern.pos:
                    continue
                used[i:i + n] = [True] * n
                matches.append({"pattern": pattern.text, "category": pattern.category, "strength": pattern.strength,
                                "description": pattern.description, "sentence": sentence.index,
                                "start": tokens[i].start, "end": tokens[i + n - 1].end, "initial": i == 0})
    return sorted(matches, key=lambda m: m["start"])


def opening_features(doc: ProcessedDocument) -> tuple[dict[str, float | None], list[dict]]:
    sentences = [s for s in doc.sentences if len(s.words) >= OPENING_WORDS]
    if len(sentences) < 3:
        return {"repeated_opening_ratio": None, "opening_pattern_diversity": None}, []
    openings = defaultdict(list)
    for s in sentences:
        openings[" ".join(w.norm for w in s.words[:OPENING_WORDS])].append(s.index)
    repeated = {k: v for k, v in openings.items() if len(v) > 1}
    pos_patterns = {tuple(w.pos for w in s.words[:3]) for s in sentences}
    features = {
        "repeated_opening_ratio": sum(len(v) for v in repeated.values()) / len(sentences),
        "opening_pattern_diversity": len(pos_patterns) / len(sentences),
    }
    groups = sorted(({"opening": k, "count": len(v), "sentences": v} for k, v in repeated.items()),
                    key=lambda g: (-g["count"], g["opening"]))
    return features, groups[:10]


def compute_discourse(doc: ProcessedDocument) -> tuple[dict[str, float | None], dict]:
    categories, _ = load_library()
    matches = find_patterns(doc)
    words = len(doc.words)
    counts = Counter(m["category"] for m in matches)
    features: dict[str, float | None] = {
        name: (counts[category] * 100 / words if words else None) for category, name in RATE_FEATURES.items()
    }
    initial_markers = {m["sentence"] for m in matches if m["initial"] and m["category"] != "academic_formula"}
    features["marker_initial_ratio"] = (len(initial_markers) / len(doc.sentences)) if doc.sentences else None
    opening, groups = opening_features(doc)
    features.update(opening)

    by_pattern: dict[str, dict] = {}
    for m in matches:
        entry = by_pattern.setdefault(m["pattern"], {k: m[k] for k in ("pattern", "category", "strength", "description")} | {"spans": []})
        entry["spans"].append([m["start"], m["end"], m["sentence"]])
    summary = sorted(by_pattern.values(), key=lambda e: (-STRENGTHS.index(e["strength"]), -len(e["spans"]), e["pattern"]))
    details = {"patterns": summary, "pattern_categories": categories, "repeated_openings": groups,
               "category_counts": dict(counts)}
    return features, details
