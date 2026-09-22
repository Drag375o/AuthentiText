"""Document statistics: sizes, sentence-length distribution, punctuation habits."""
from __future__ import annotations

import math
import statistics

from .preprocessing import ProcessedDocument
from .text_stats import READING_WPM

PUNCTUATION = {
    "commas_per_100": {","},
    "semicolons_per_100": {";"},
    "colons_per_100": {":"},
    "dashes_per_100": {"\u2014", "\u2013", "--", "-"},
    "questions_per_100": {"?"},
    "exclamations_per_100": {"!"},
    "parentheses_per_100": {"("},
    "quotes_per_100": {'"', "\u201c", "\u201d", "\u2018", "\u2019", "``", "''"},
    "ellipses_per_100": {"...", "\u2026"},
}


def sentence_lengths(doc: ProcessedDocument) -> list[int]:
    return [len(s.words) for s in doc.sentences]


def _is_spaced_hyphen(doc: ProcessedDocument, token) -> bool:
    """A lone "-" between spaces works as a dash; inside a word it's just a hyphen."""
    text = doc.original_text
    before = text[token.start - 1] if token.start > 0 else " "
    after = text[token.end] if token.end < len(text) else " "
    return before.isspace() and after.isspace()


def punctuation_rates(doc: ProcessedDocument, words: int) -> dict[str, float]:
    counts = {name: 0 for name in PUNCTUATION}
    for token in doc.tokens:
        if not token.is_punct and token.text not in ("...", "\u2026"):
            continue
        for name, marks in PUNCTUATION.items():
            if token.text in marks:
                if token.text == "-" and not _is_spaced_hyphen(doc, token):
                    continue
                counts[name] += 1
    return {name: (count * 100 / words if words else 0.0) for name, count in counts.items()}


def compute_document_stats(doc: ProcessedDocument) -> dict[str, float | None]:
    words = doc.words
    word_count = len(words)
    lengths = sentence_lengths(doc)
    letters = [sum(ch.isalpha() for ch in w.text) for w in words if w.is_alpha]
    paragraph_words = [0] * len(doc.paragraphs)
    for sentence in doc.sentences:
        paragraph_words[sentence.paragraph] += len(sentence.words)

    mean = statistics.fmean(lengths) if lengths else None
    std = statistics.pstdev(lengths) if len(lengths) > 1 else (0.0 if lengths else None)
    stats: dict[str, float | None] = {
        "word_count": word_count,
        "unique_word_count": len({w.norm for w in words}),
        "sentence_count": len(doc.sentences),
        "paragraph_count": len(doc.paragraphs),
        "character_count": len(doc.original_text),
        "reading_minutes": math.ceil(word_count / READING_WPM) if word_count else 0,
        "sentence_length_mean": mean,
        "sentence_length_median": statistics.median(lengths) if lengths else None,
        "sentence_length_std": std,
        "sentence_length_min": min(lengths) if lengths else None,
        "sentence_length_max": max(lengths) if lengths else None,
        "sentence_length_cv": (std / mean) if mean else None,
        "paragraph_length_mean": statistics.fmean(paragraph_words) if paragraph_words else None,
        "avg_word_length": statistics.fmean(letters) if letters else None,
    }
    stats.update(punctuation_rates(doc, word_count))
    return stats
