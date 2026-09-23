"""
Signal definitions for the demo detector.

Each signal takes ONE measured feature and maps it to a 0-1 contribution
through two documented anchors, in a documented direction. Nothing here is
learned from data: these are hand-chosen heuristics, which is exactly why the
detector that uses them is labelled a demo.

Honest notes baked into the descriptions:
- Every one of these patterns appears in human writing too.
- Several are sensitive to genre rather than authorship (formality, personal
  voice), so they carry less weight.
- Testing on a human/AI paraphrase pair showed sentence-length regularity
  separating nothing once headings were excluded, while semantic diversity
  separated the pair clearly. The weights below reflect that.
"""
from __future__ import annotations

from dataclasses import dataclass

FAMILIES = {
    "linguistic": "Linguistic",
    "stylometric": "Stylometric",
    "statistical": "Statistical",
    "semantic": "Semantic",
    "structural": "Structural",
}


@dataclass(frozen=True)
class Signal:
    key: str
    family: str
    label: str
    feature: str
    low: float          # feature value mapped to a 0 contribution
    high: float         # feature value mapped to a 1 contribution
    weight: float       # relative influence on the combined score
    high_text: str      # shown when the contribution is high
    low_text: str       # shown when the contribution is low
    caveat: str


SIGNALS: list[Signal] = [
    Signal("formulaic_phrases", "linguistic", "Formulaic phrasing", "formulaic_phrases_per_100",
           0.0, 3.0, 1.0,
           "Stock phrases from the pattern library appear often.",
           "Few stock phrases from the pattern library.",
           "Textbooks, student essays and business writing use these phrases constantly."),
    Signal("marker_openings", "linguistic", "Marker-led sentences", "marker_initial_ratio",
           0.05, 0.45, 0.7,
           "Many sentences open with a discourse marker such as \u201cHowever\u201d or \u201cFurthermore\u201d.",
           "Sentences rarely open with a discourse marker.",
           "Marker-led sentences are taught as good structure in academic writing."),
    Signal("semantic_spread", "semantic", "Semantic spread", "semantic_diversity",
           0.95, 0.60, 1.4,
           "Sentences stay close to one another in meaning, covering little ground.",
           "Sentences range widely in meaning.",
           "A tightly focused paragraph on one narrow topic also scores this way."),
    Signal("local_coherence", "semantic", "Neighbour similarity", "local_coherence",
           0.10, 0.45, 1.0,
           "Consecutive sentences restate each other closely.",
           "Consecutive sentences move the text forward.",
           "Careful, well-linked prose can also score high here."),
    Signal("opening_variety", "structural", "Sentence openings", "opening_pattern_diversity",
           0.95, 0.45, 0.8,
           "Sentences begin in a small number of grammatical shapes.",
           "Sentences begin in varied ways.",
           "Short texts have few openings to vary, so this is unreliable below a page."),
    Signal("repeated_openings", "structural", "Repeated openings", "repeated_opening_ratio",
           0.0, 0.4, 0.6,
           "Several sentences begin with the same two words.",
           "Sentence openings rarely repeat.",
           "Lists and parallel constructions repeat openings deliberately."),
    Signal("length_regularity", "statistical", "Sentence-length regularity", "sentence_length_cv",
           0.55, 0.15, 0.5,
           "Sentence lengths are unusually even.",
           "Sentence lengths vary.",
           "Edited prose is often regular. In testing this signal separated a human/AI pair by almost nothing, so it carries little weight."),
    Signal("vocabulary_flatness", "statistical", "Vocabulary spread", "normalized_entropy",
           0.99, 0.90, 0.5,
           "A small set of words carries much of the text.",
           "Vocabulary is spread evenly.",
           "Technical writing repeats its key terms by necessity."),
    Signal("personal_voice", "stylometric", "Personal voice", "first_person_ratio",
           0.04, 0.0, 0.4,
           "Almost no first-person voice.",
           "The writer is present in the text.",
           "Reports, documentation and academic prose avoid the first person by convention, so this says more about genre than authorship."),
    Signal("contractions", "stylometric", "Contractions", "contraction_ratio",
           0.02, 0.0, 0.3,
           "No contractions such as \u201ccan't\u201d or \u201cit's\u201d.",
           "Contractions appear, as in ordinary speech.",
           "Formal registers drop contractions as a rule, so this reflects register more than authorship."),
]

BY_KEY = {s.key: s for s in SIGNALS}


def contribution(signal: Signal, value: float | None) -> float | None:
    """Scale a feature value to 0-1 between the signal's anchors. Works in either direction."""
    if value is None:
        return None
    span = signal.high - signal.low
    if span == 0:
        return None
    return max(0.0, min(1.0, (value - signal.low) / span))
