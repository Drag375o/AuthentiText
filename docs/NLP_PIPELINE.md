# NLP pipeline

Version `0.4.0` (`analyzer/services/pipeline.py`). Runs synchronously when a document is analyzed.

```
original text (stored untouched)
  → paragraph segmentation            segmentation.py
  → spaCy on each paragraph           preprocessing.py, nlp.py
      tokens, lemmas, POS tags, dependency parse, sentences
  → English check                     preprocessing.detect_language
  → document statistics               document_stats.py
  → lexical features                  lexical.py
  → SentenceAnalysis + Feature rows + report     pipeline.save_results
```

## Design decisions

**The original is never modified.** Every token and sentence keeps absolute character offsets, so `original_text[start:end]` is always the text exactly as written. Normalised forms (lower case, Unicode NFC, straight apostrophes) exist only in the processed representation.

**Paragraphs first.** Paragraphs are split by rule (blank lines, or line breaks if there are none), then spaCy processes each one with `nlp.pipe`. A sentence can never run across a paragraph break, so a heading without a full stop doesn't merge into the next paragraph.

**One model load per process.** `get_nlp()` is cached. The first analysis pays about half a second to load `en_core_web_sm`; after that a 450-word essay takes around 40 ms. The named-entity recogniser is excluded because nothing uses it.

**A custom sentence-boundary rule.** The parser keeps "at 5 p.m. It rained" as one sentence. A small component (`abbreviation_boundaries`) runs before the parser and starts a new sentence when a known sentence-final abbreviation (a.m., p.m., etc., Inc. …) is followed by a capitalised pronoun, article or common opener. Titles such as "Dr." aren't in the list, and a lower-case continuation ("5 p.m. the next day") is left alone.

**Words.** A word token isn't punctuation or whitespace and contains a letter or digit. Clitics that spaCy splits off ("n't", "'s", "'re" …) aren't counted separately, so "can't" is one word, matching the editor's counts. Vocabulary uses spaCy's normalised form, so "ca" (from "can't") counts as "can".

**Feature registry.** Every stored feature is declared in `features.py` with a label, unit and plain-English explanation. The pipeline refuses to produce an unregistered feature, the document page reads the explanations from it, and `docs/FEATURES.md` is generated from it.

## Failure handling

`analyze_document()` catches any exception, logs the traceback, and marks the analysis `failed`. The user's text is kept, and the page offers **Analyze again**. Technical details never reach the page.

## Re-running

Documents saved before a pipeline change can be updated in bulk:

```bash
python manage.py analyze_pending          # pending, failed, or older pipeline version
python manage.py analyze_pending --all    # everything
```
