"""
Stylometry: measurable writing habits, and the 0-100 Writing Profile.

Two kinds of output:

1. Measured features
   - formality_score: the F-score of Heylighen & Dewaele (1999),
     F = ((nouns + adjectives + prepositions + articles) - (pronouns + verbs +
     adverbs + interjections) + 100) / 2, computed on part-of-speech shares.
     Around 50 is neutral; academic prose runs high, conversation low.
   - first_person_ratio, contraction_ratio: markers of personal voice.

2. Profile scores (0-100)
   Each dimension rescales one or more measured features between two anchors
   using linear interpolation. THE ANCHORS ARE REFERENCE RANGES CHOSEN FROM
   TYPICAL ENGLISH PROSE, NOT PERCENTILES FROM A CORPUS. A score of 70 means
   "high within this reference range", not "higher than 70% of writers".
   They describe the text, never the person. Each anchor pair is stated in the
   dimension's description so the mapping is inspectable.
"""
from __future__ import annotations

from dataclasses import dataclass

from .preprocessing import ProcessedDocument

FIRST_PERSON = {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours", "ourselves"}
ARTICLES = {"a", "an", "the"}


@dataclass(frozen=True)
class Dimension:
    key: str
    label: str
    feature: str
    low: float          # value mapped to 0
    high: float         # value mapped to 100
    description: str


PROFILE_DIMENSIONS: list[Dimension] = [
    Dimension("vocabulary_diversity", "Vocabulary diversity", "mattr", 0.55, 0.85,
              "From moving-average type-token ratio, rescaled between 0.55 (repetitive) and 0.85 (highly varied)."),
    Dimension("sentence_variation", "Sentence variation", "sentence_length_cv", 0.15, 0.75,
              "From sentence-length variation, rescaled between 0.15 (very even) and 0.75 (highly varied)."),
    Dimension("syntax_complexity", "Syntax complexity", "clauses_per_sentence", 1.0, 3.0,
              "From clauses per sentence, rescaled between 1 (simple sentences) and 3 (heavily subordinated)."),
    Dimension("formality", "Formality", "formality_score", 35.0, 75.0,
              "From the Heylighen & Dewaele F-score, rescaled between 35 (conversational) and 75 (formal academic)."),
    Dimension("repetition", "Repetition", "trigram_repeat_rate", 0.0, 0.15,
              "From the share of repeated three-word sequences, rescaled between 0 and 0.15."),
    Dimension("personal_voice", "Personal voice", "first_person_ratio", 0.0, 0.08,
              "From the share of first-person pronouns, rescaled between 0 and 0.08."),
    Dimension("semantic_diversity", "Semantic diversity", "semantic_diversity", 0.5, 1.0,
              "From how much sentences differ from one another, rescaled between 0.5 (circling one idea) and 1.0."),
]
BY_KEY = {d.key: d for d in PROFILE_DIMENSIONS}


def compute_stylometry(doc: ProcessedDocument, pos_ratios: dict[str, float | None]) -> dict[str, float | None]:
    """Measured stylometric features. POS ratios come from syntax.compute_syntax."""
    words = doc.words
    if not words:
        return {"formality_score": None, "first_person_ratio": None, "contraction_ratio": None}

    def ratio(name: str) -> float:
        return (pos_ratios.get(f"pos_{name}_ratio") or 0.0) * 100

    articles = sum(1 for w in words if w.norm in ARTICLES) / len(words) * 100
    formal = ratio("noun") + ratio("propn") + ratio("adj") + ratio("adp") + articles
    contextual = ratio("pron") + ratio("verb") + ratio("adv") + ratio("aux")
    return {
        "formality_score": (formal - contextual + 100) / 2,
        "first_person_ratio": sum(1 for w in words if w.norm in FIRST_PERSON) / len(words),
        "contraction_ratio": sum(1 for t in doc.tokens if t.is_clitic) / len(words),
    }


def scale(value: float | None, low: float, high: float) -> int | None:
    if value is None:
        return None
    return round(max(0.0, min(1.0, (value - low) / (high - low))) * 100)


def build_profile(features: dict[str, float | None]) -> list[dict]:
    """The Writing Profile: one 0-100 score per dimension, or None when its feature is missing."""
    return [
        {"key": d.key, "label": d.label, "score": scale(features.get(d.feature), d.low, d.high),
         "feature": d.feature, "description": d.description}
        for d in PROFILE_DIMENSIONS
    ]
