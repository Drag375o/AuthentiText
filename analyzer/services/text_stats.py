"""
Quick document statistics for the editor.

These are fast, rule-based ESTIMATES. They power the live counts on the Analyze
page and the counts saved with a document before the NLP pipeline runs.
Phase 4 replaces sentence and paragraph segmentation with spaCy, which
handles abbreviations ("e.g.", "Dr.") that these rules can't.

The same rules are implemented in static/js/text-stats.js. Both are tested
against analyzer/tests/fixtures/text_stats_cases.json so they can't drift apart.

Rules
- word:       letters/digits, allowing internal apostrophes or hyphens (it's, well-known);
              numbers with . or , separators count once (3.14, 1,000)
- paragraph:  if the text contains a blank line, blank lines separate paragraphs;
              otherwise each line break does. Only blocks containing a word count.
- sentence:   within each paragraph, a split after . ! ? or ... (optionally followed
              by closing quotes/brackets) and whitespace. Only pieces with a word count.
- characters: Unicode code points, with CRLF counted as one line break
- reading:    whole minutes, rounded up, at READING_WPM
"""
from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass

READING_WPM = 238  # average silent reading speed for non-fiction (Brysbaert, 2019)

# Numbers with separators (3.14, 1,000) first, then words with internal ' or -.
WORD_RE = re.compile(r"[0-9]+(?:[.,][0-9]+)+|[^\W_]+(?:['\u2019\-][^\W_]+)*")
HAS_WORD_RE = re.compile(r"[^\W_]")
BLANK_LINE_RE = re.compile(r"\n[ \t]*\n")
PARAGRAPH_SPLIT_BLANK = re.compile(r"\n\s*\n")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?\u2026])[\"'\u201d\u2019)\]]*\s+")


@dataclass(frozen=True)
class TextStats:
    characters: int
    words: int
    sentences: int
    paragraphs: int
    reading_minutes: int

    def as_dict(self) -> dict:
        return asdict(self)


def normalize_newlines(text: str) -> str:
    """Browsers submit textareas with CRLF; count them as a single line break."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def split_paragraphs(text: str) -> list[str]:
    splitter = PARAGRAPH_SPLIT_BLANK if BLANK_LINE_RE.search(text) else re.compile(r"\n")
    return [block for block in splitter.split(text) if HAS_WORD_RE.search(block)]


def split_sentences(paragraph: str) -> list[str]:
    return [piece for piece in SENTENCE_SPLIT_RE.split(paragraph) if HAS_WORD_RE.search(piece)]


def compute_text_stats(text: str) -> TextStats:
    text = normalize_newlines(text)
    words = len(WORD_RE.findall(text))
    paragraphs = split_paragraphs(text)
    sentences = sum(len(split_sentences(p)) for p in paragraphs)
    return TextStats(
        characters=len(text),
        words=words,
        sentences=sentences,
        paragraphs=len(paragraphs),
        reading_minutes=math.ceil(words / READING_WPM) if words else 0,
    )
