"""
A plain-language summary of an analysis.

Deterministic sentences built from the stored numbers. The wording follows the
project's rules: the result describes measurable characteristics, never
authorship, and a demo result says so in its first sentence.
"""
from __future__ import annotations

from .features import BY_NAME

DEMO_LINE = ("This result comes from the demo detector, which combines hand-chosen signals and has no "
             "measured accuracy. Read it as an illustration, not as evidence about this document.")
CLOSING_LINE = ("A result describes measurable characteristics of the text. It does not prove authorship, "
                "AI use, plagiarism or misconduct.")

LABEL_SENTENCES = {
    "likely_human": "The combined signal is low: the text looks more like the human-written examples than the AI-generated ones.",
    "possibly_ai_assisted": "The combined signal sits in the middle, which is consistent with AI assistance, heavy editing, or simply a formal writing style.",
    "likely_ai_associated": "The combined signal is high: the text shares several characteristics with AI-generated examples.",
    "uncertain": "The signals disagree too much to place this text in any band.",
    "insufficient_evidence": "There is not enough text here to measure reliably, so no estimate is given.",
}


def _percent(value: float | None) -> str:
    return "\u2014" if value is None else f"{round(value * 100)}%"


def _describe(name: str, values: dict, high: float, low: float, high_text: str, low_text: str) -> str | None:
    value = values.get(name)
    if value is None:
        return None
    if value >= high:
        return high_text
    if value <= low:
        return low_text
    return None


def build_summary(analysis, values: dict[str, float], report: dict) -> dict:
    """
    Returns the summary as labelled points for the page, plus the same text as
    plain paragraphs for the PDF:

        {"headline": str,
         "points": [{"label": str, "text": str}, ...],
         "paragraphs": [str, ...]}
    """
    detection = report.get("detection", {})
    label_display = analysis.get_result_label_display() if analysis.result_label else "Not analyzed"

    first = [f"\u201c{analysis.display_name}\u201d is {int(values.get('word_count', 0)):,} words long, "
             f"in {int(values.get('sentence_count', 0)):,} sentences across {int(values.get('paragraph_count', 0)):,} paragraphs."]
    reading = values.get("reading_minutes")
    if reading:
        first.append(f"It takes about {int(reading)} minute{'s' if reading != 1 else ''} to read.")

    result = [f"Result: {label_display}."]
    if detection.get("probability") is not None:
        result.append(f"The AI-associated signal is {_percent(detection['probability'])}, "
                      f"with {_percent(detection.get('confidence'))} confidence and "
                      f"{_percent(detection.get('uncertainty'))} uncertainty.")
    result.append(LABEL_SENTENCES.get(analysis.result_label, ""))
    if analysis.is_demo:
        result.append(DEMO_LINE)

    observations = [
        _describe("sentence_length_cv", values, 0.55, 0.25,
                  "Sentence lengths vary widely, which gives the writing a noticeable rhythm.",
                  "Sentence lengths are unusually even."),
        _describe("mattr", values, 0.80, 0.65,
                  "Vocabulary is varied for a text of this length.",
                  "Vocabulary repeats more than is typical."),
        _describe("semantic_diversity", values, 0.85, 0.65,
                  "The sentences range widely in meaning rather than circling one idea.",
                  "The sentences stay close to one another in meaning, covering little ground."),
        _describe("formulaic_phrases_per_100", values, 1.0, 0.1,
                  "Stock academic phrases appear often.",
                  "Few stock phrases from the pattern library appear."),
        _describe("passive_sentence_ratio", values, 0.4, 0.05,
                  "Much of the text is in the passive voice.",
                  "The writing is mostly in the active voice."),
        _describe("first_person_ratio", values, 0.03, 0.002,
                  "The writer is present in the text through first-person language.",
                  "The text avoids first-person language."),
    ]
    observations = [line for line in observations if line]
    if not observations:
        observations = ["No single measurement stood out from the usual range for English prose."]

    strongest = [s for s in detection.get("signals", []) if (s.get("score") or 0) >= 0.5]
    strongest.sort(key=lambda s: -s["score"])
    signal_lines = [f"{s['label']}: {s['text']}" for s in strongest[:3]]

    points = [
        {"label": "The document", "text": " ".join(first)},
        {"label": "The result", "text": " ".join(part for part in result if part)},
        {"label": "What stands out", "text": " ".join(observations)},
    ]
    if signal_lines:
        points.append({"label": "Strongest signals", "text": " ".join(signal_lines)})
    points.append({"label": "What this is not", "text": CLOSING_LINE})
    paragraphs = [point["text"] for point in points]

    probability = detection.get("probability")
    headline = label_display if probability is None else f"{label_display}, {_percent(probability)} signal"
    return {"headline": headline, "points": points, "paragraphs": paragraphs}
