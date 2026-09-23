/**
 * AuthentiText: quick document statistics (browser + Node).
 *
 * JavaScript twin of analyzer/services/text_stats.py. Both are tested against
 * analyzer/tests/fixtures/text_stats_cases.json, so the live counts in the
 * editor match what the server saves. See the Python module for the rules.
 * These are estimates; Phase 4 segments sentences with spaCy.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;  // Node (tests)
  else root.TextStats = api;                                             // Browser
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const READING_WPM = 238;
  const WORD_RE = /[0-9]+(?:[.,][0-9]+)+|[\p{L}\p{N}]+(?:['\u2019-][\p{L}\p{N}]+)*/gu;
  const HAS_WORD_RE = /[\p{L}\p{N}]/u;
  const BLANK_LINE_RE = /\n[ \t]*\n/;
  const PARAGRAPH_SPLIT_BLANK = /\n\s*\n/;
  // Soft wrap: a line break inside a sentence, as when text is pasted from a PDF.
  // Mirrors analyzer/services/segmentation.py.
  const SENTENCE_END_RE = /[.!?\u2026:;]["'\u201d\u2019)\]]*$/;
  const LIST_MARKER_RE = /^\s*(?:[-*\u2022\u2013\u2014]|\d+[.)]|[a-z][.)]\s|#{1,6}\s)/;
  const CONTINUES_RE = /^["'\u201c\u2018(\[]*[a-z0-9]/;

  function isSoftWrap(before, after) {
    before = before.replace(/\s+$/, "");
    after = after.trim();
    if (!before || !after) return false;
    if (SENTENCE_END_RE.test(before) || LIST_MARKER_RE.test(after)) return false;
    return CONTINUES_RE.test(after);
  }
  const SENTENCE_SPLIT_RE = /(?<=[.!?\u2026])["'\u201d\u2019)\]]*\s+/u;

  function normalizeNewlines(text) {
    return text.replace(/\r\n?/g, "\n");
  }

  function splitParagraphs(text) {
    let blocks;
    if (BLANK_LINE_RE.test(text)) {
      blocks = text.split(PARAGRAPH_SPLIT_BLANK);
    } else {
      blocks = [];
      let current = "";
      text.split("\n").forEach((line, index) => {
        if (index && !isSoftWrap(current, line)) {
          blocks.push(current);
          current = line;
        } else {
          current = index ? `${current}\n${line}` : line;
        }
      });
      blocks.push(current);
    }
    return blocks.filter((block) => HAS_WORD_RE.test(block));
  }

  function splitSentences(paragraph) {
    return paragraph.split(SENTENCE_SPLIT_RE).filter((piece) => HAS_WORD_RE.test(piece));
  }

  function compute(text) {
    text = normalizeNewlines(text || "");
    const words = (text.match(WORD_RE) || []).length;
    const paragraphs = splitParagraphs(text);
    const sentences = paragraphs.reduce((sum, p) => sum + splitSentences(p).length, 0);
    return {
      characters: [...text].length, // code points, matching Python's len()
      words,
      sentences,
      paragraphs: paragraphs.length,
      reading_minutes: words ? Math.ceil(words / READING_WPM) : 0,
    };
  }

  return { compute, READING_WPM };
});
