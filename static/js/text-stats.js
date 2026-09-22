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
  const SENTENCE_SPLIT_RE = /(?<=[.!?\u2026])["'\u201d\u2019)\]]*\s+/u;

  function normalizeNewlines(text) {
    return text.replace(/\r\n?/g, "\n");
  }

  function splitParagraphs(text) {
    const splitter = BLANK_LINE_RE.test(text) ? PARAGRAPH_SPLIT_BLANK : /\n/;
    return text.split(splitter).filter((block) => HAS_WORD_RE.test(block));
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
