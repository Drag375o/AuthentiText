# NLP pipeline

Version `0.6.0` (`analyzer/services/pipeline.py`). Runs synchronously when a document is analyzed.

```
original text (stored untouched)
  → paragraph segmentation            segmentation.py
  → spaCy on each paragraph           preprocessing.py, nlp.py
      tokens, lemmas, POS tags, dependency parse, sentences
  → English check                     preprocessing.detect_language
  → document statistics               document_stats.py
  → lexical features                  lexical.py
  → syntactic features                syntax.py
      POS distribution, parse depth, dependency distance, clauses, passive voice
  → discourse and patterns            discourse.py + resources/patterns.json
      markers by category, formulaic phrases, sentence openings
  → statistical features              statistics_features.py
      entropy, burstiness, n-gram repetition, Zipf slope, distinctive terms
  → semantic features                 semantics.py + embeddings.py
      sentence similarity, coherence, redundancy, diversity
  → stylometric features + profile    stylometry.py
  → SentenceAnalysis + Feature rows + report     pipeline.save_results
```

## Design decisions

**The original is never modified.** Every token and sentence keeps absolute character offsets, so `original_text[start:end]` is always the text exactly as written. Normalised forms (lower case, Unicode NFC, straight apostrophes) exist only in the processed representation.

**Paragraphs first.** Paragraphs are split by rule (blank lines, or line breaks if there are none), then spaCy processes each one with `nlp.pipe`. A single line break is ignored when it is a soft wrap, that is when the line before it does not end in sentence-ending punctuation and the line after starts in lower case: text pasted from a PDF would otherwise be cut into fragments like "We", which distorts every rhythm measure. The same rule is mirrored in the editor's live counts (`text_stats.py` and `static/js/text-stats.js`). A sentence can never run across a paragraph break, so a heading without a full stop doesn't merge into the next paragraph.

**One model load per process.** `get_nlp()` is cached. The first analysis pays about half a second to load `en_core_web_sm`; after that a 450-word essay takes around 40 ms. The named-entity recogniser is excluded because nothing uses it.

**A custom sentence-boundary rule.** The parser keeps "at 5 p.m. It rained" as one sentence. A small component (`abbreviation_boundaries`) runs before the parser and starts a new sentence when a known sentence-final abbreviation (a.m., p.m., etc., Inc. …) is followed by a capitalised pronoun, article or common opener. Titles such as "Dr." aren't in the list, and a lower-case continuation ("5 p.m. the next day") is left alone.

**Headings are not sentences.** A paragraph that is a single short line (12 words or fewer) with no sentence-ending punctuation is marked as a heading. Headings stay in the text, the word counts and the sentence list, but are excluded from every sentence-length measure (mean, median, spread, variation, burstiness). This matters more than it sounds: in testing, one "3.3 Data Split" heading shifted burstiness by 0.16, which was larger than the difference between the two documents being compared.

**Words.** A word token isn't punctuation or whitespace and contains a letter or digit. Clitics that spaCy splits off ("n't", "'s", "'re" …) aren't counted separately, so "can't" is one word, matching the editor's counts. Vocabulary uses spaCy's normalised form, so "ca" (from "can't") counts as "can".

**Feature registry.** Every stored feature is declared in `features.py` with a label, unit and plain-English explanation. The pipeline refuses to produce an unregistered feature, the document page reads the explanations from it, and `docs/FEATURES.md` is generated from it.

**Syntax from the parse.** Clauses are counted from dependency labels: the main clause plus `advcl`, `ccomp`, `csubj`, `csubjpass`, `acl`, `relcl`, `xcomp`, and verbs coordinated with another verb. Passive voice is a `nsubjpass`, `auxpass` or `csubjpass` label. Mean dependency distance follows Liu (2008). Tokens keep spaCy's own position numbers, so whitespace tokens inside a paragraph can't shift head references.

**The pattern library** (`analyzer/resources/patterns.json`) is data, not code. Each entry has a `pattern`, `category`, `description` and `strength` (how generic or formulaic the phrase is, *not* how "AI-like"), plus optional `position: "start"` (sentence-initial only, for words like "so" and "but") and `pos` (for example "may" only as a verb, not the month). Patterns are tokenised with spaCy's tokenizer and matched by normalised form, longest first, without overlaps. The library is validated when loaded, with a clear message for mistakes. Point `PATTERN_LIBRARY_PATH` at your own file to use a different library.

**Embeddings are an adapter.** `embeddings.get_embedder()` returns a `BaseEmbedder`; `semantics.py` only ever calls `encode()`. Two implementations ship:

| | TF-IDF (default) | sentence-transformers (optional) |
|---|---|---|
| Install | none, uses scikit-learn | `pip install "sentence-transformers>=3.0"`, plus a model download |
| Measures | shared wording | meaning, including paraphrase |
| Near-duplicate threshold | 0.5 cosine | 0.85 cosine |

`EMBEDDING_BACKEND` chooses: `auto` (default: the transformer if it loads, otherwise TF-IDF), `tfidf`, or `sentence-transformers` (fails loudly if unavailable). Every analysis records which backend produced it, and the document page names it, so a result never implies more semantic understanding than was used.

Latent semantic analysis (TruncatedSVD over the TF-IDF matrix) was implemented and then removed. Fitted on the few dozen sentences of a single document it is unstable: in testing it reported two unrelated sentences as 99% similar. Plain TF-IDF is less clever and much more trustworthy at this scale.

**The Writing Profile is a rescaling, not a ranking.** Each of the seven dimensions maps one measured feature between two fixed anchors (`stylometry.PROFILE_DIMENSIONS`). The anchors are reference ranges for ordinary English prose, chosen by hand; they are *not* percentiles from a corpus, and the interface says so. Formality uses the F-score of Heylighen & Dewaele (1999), computed from part-of-speech shares.

**No perplexity.** Token predictability by perplexity needs a language model, which this project does not ship. Entropy over the word distribution is a weaker but honest substitute, and the gap is recorded in `docs/LIMITATIONS.md` rather than filled with a fabricated number.

## Failure handling

`analyze_document()` catches any exception, logs the traceback, and marks the analysis `failed`. The user's text is kept, and the page offers **Analyze again**. Technical details never reach the page.

## Re-running

Documents saved before a pipeline change can be updated in bulk:

```bash
python manage.py analyze_pending          # pending, failed, or older pipeline version
python manage.py analyze_pending --all    # everything
```
