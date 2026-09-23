"""
Paragraph segmentation with exact character offsets into the original text.

Rules
- If the text contains a blank line, blank lines separate paragraphs.
- Otherwise each line break does, EXCEPT where the break is a soft wrap.

Soft wraps matter because text copied out of a PDF or an email arrives with a
newline every 70-odd characters, in the middle of sentences. Splitting there
would invent sentences like "We" and distort every rhythm measure. A break is
treated as a soft wrap when the line before it does not end in sentence-ending
punctuation and the line after it starts in lower case (or with a digit that
isn't a list marker).

The text itself is never modified: a paragraph span may contain newlines, and
original[start:end] is still exactly what the person wrote.
"""
from __future__ import annotations

import re

BLANK_LINE_RE = re.compile(r"\r?\n[ \t]*\r?\n")
BLANK_SEPARATOR_RE = re.compile(r"(?:\r?\n[ \t]*){2,}")
LINE_SEPARATOR_RE = re.compile(r"\r?\n|\r")
HAS_WORD_RE = re.compile(r"[^\W_]")

# A line that ends a sentence: terminal punctuation, optionally inside quotes or brackets.
SENTENCE_END_RE = re.compile(r"[.!?\u2026:;][\"'\u201d\u2019)\]]*$")
# A line that starts a new block: a bullet, a numbered item, or a Markdown heading.
LIST_MARKER_RE = re.compile(r"^\s*(?:[-*\u2022\u2013\u2014]|\d+[.)]|[a-z][.)]\s|#{1,6}\s)")
CONTINUES_RE = re.compile(r"^[\"'\u201c\u2018(\[]*[a-z0-9]")


def is_soft_wrap(before: str, after: str) -> bool:
    """True when a single line break splits one sentence across two lines."""
    before, after = before.rstrip(), after.strip()
    if not before or not after:
        return False
    if SENTENCE_END_RE.search(before) or LIST_MARKER_RE.match(after):
        return False
    return bool(CONTINUES_RE.match(after))


# A heading: one short line, no sentence-ending punctuation. Counting it as a
# sentence distorts every rhythm measure, because it is far shorter than prose.
HEADING_MAX_WORDS = 12


def looks_like_heading(block: str, total_paragraphs: int) -> bool:
    if total_paragraphs < 2 or "\n" in block.strip():
        return False
    stripped = block.strip()
    if SENTENCE_END_RE.search(stripped):
        return False
    return len(stripped.split()) <= HEADING_MAX_WORDS


def paragraph_spans(text: str) -> list[tuple[int, int]]:
    if BLANK_LINE_RE.search(text):
        separator = BLANK_SEPARATOR_RE
        spans, start = [], 0
        for match in separator.finditer(text):
            spans.append((start, match.start()))
            start = match.end()
        spans.append((start, len(text)))
    else:
        spans = []
        start = 0
        for match in LINE_SEPARATOR_RE.finditer(text):
            if is_soft_wrap(text[start:match.start()], text[match.end():]):
                continue                      # keep both lines in the same paragraph
            spans.append((start, match.start()))
            start = match.end()
        spans.append((start, len(text)))

    trimmed = []
    for s, e in spans:
        block = text[s:e]
        if not HAS_WORD_RE.search(block):
            continue
        lead = len(block) - len(block.lstrip())
        trail = len(block) - len(block.rstrip())
        trimmed.append((s + lead, e - trail))
    return trimmed
