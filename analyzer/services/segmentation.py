"""
Paragraph segmentation with exact character offsets into the original text.

Same rule as the editor's quick counts (text_stats.py): if the text contains a
blank line, blank lines separate paragraphs; otherwise each line break does.
Spans are trimmed of surrounding whitespace, so original[start:end] is the
paragraph exactly as written. Blocks without a letter or digit are dropped.
"""
from __future__ import annotations

import re

BLANK_LINE_RE = re.compile(r"\r?\n[ \t]*\r?\n")
BLANK_SEPARATOR_RE = re.compile(r"(?:\r?\n[ \t]*){2,}")
LINE_SEPARATOR_RE = re.compile(r"\r?\n|\r")
HAS_WORD_RE = re.compile(r"[^\W_]")


def paragraph_spans(text: str) -> list[tuple[int, int]]:
    separator = BLANK_SEPARATOR_RE if BLANK_LINE_RE.search(text) else LINE_SEPARATOR_RE
    spans, start = [], 0
    for match in separator.finditer(text):
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
