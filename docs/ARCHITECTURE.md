# Architecture

AuthentiText is a single Django project. Nothing runs in the background, nothing queues, and every analysis happens inside the request that asked for it. That is a deliberate choice for a portfolio project: a reader can follow one request from the browser to the database without tracing a message broker.

```
browser ── Django view ── service layer ── spaCy / scikit-learn / wordfreq
                │
                └── SQLite (PostgreSQL-ready)
```

## Apps

| App | Responsibility |
|---|---|
| `config` | settings (environment-driven), root URLs |
| `core` | landing page, about page, shared context |
| `accounts` | registration, login, logout, password reset |
| `analyzer` | models, the editor, uploads, the NLP pipeline, results, comparison, profile, reports |

## The service layer

Views stay thin. Everything that thinks lives in `analyzer/services/`, as plain functions and dataclasses with no Django imports beyond settings. That is what makes the pipeline testable without a database, and what would let it move behind a task queue later without rewriting it.

| Module | What it does |
|---|---|
| `nlp.py` | loads spaCy once per process, adds the abbreviation-boundary rule |
| `segmentation.py` | paragraph spans with exact offsets, soft-wrap and heading detection |
| `preprocessing.py` | tokens, lemmas, POS, dependencies, language check |
| `document_stats.py` | sizes, sentence-length distribution, punctuation |
| `lexical.py` | vocabulary diversity, word frequency, repeated phrases |
| `syntax.py` | POS distribution, parse depth, clauses, passive voice |
| `discourse.py` | discourse markers and the pattern library |
| `statistics_features.py` | entropy, burstiness, n-grams, distinctive terms |
| `semantics.py` + `embeddings.py` | sentence similarity behind a swappable embedder |
| `stylometry.py` | the F-score and the 0-100 writing profile |
| `features.py` | the feature registry: one place naming and explaining every feature |
| `detector.py` + `signals.py` | the detector interface, the demo scorer, the trained model |
| `pipeline.py` | runs the stages in order and saves the result |
| `compare.py`, `profile.py`, `summary.py`, `reports/` | comparison, profile aggregation, plain-language summary, exports |
| `parser.py`, `uploads.py` | text extraction and upload validation |

## Data model

Three tables, all owned by a user.

```
User ──< Analysis ──< SentenceAnalysis
                 └──< Feature
```

`Analysis` holds the original text verbatim plus the result and a JSON `report` for structured output (profile, patterns, similar pairs, detection). `SentenceAnalysis` holds each sentence with character offsets into the original, its own score and its signals. `Feature` holds one named numeric value per analysis.

Primary keys are UUIDs, so an analysis URL cannot be guessed by counting. Probabilities are constrained to 0–1 by database check constraints, and are nullable: "insufficient evidence" is stored as no number rather than a guess.

## Four decisions worth knowing

**One registry for every feature.** `features.py` declares each feature's label, unit, explanation and the reason it may be unmeasurable. The pipeline refuses to emit a feature that isn't registered, the interface reads its explanations from there, and `docs/FEATURES.md` is generated from it. Explanations cannot drift away from the numbers they describe.

**The detector is an interface, not a function.** `BaseDetector` takes measured features and returns a `DetectionResult`. The shipped `DemoDetector` is hand-chosen heuristics and says so everywhere it appears; `TrainedDetector` loads a scikit-learn bundle and reports the metrics measured at training time. Swapping one for the other changes no other code.

**Embeddings are an adapter too.** `semantics.py` only calls `encode()`. Without `sentence-transformers` installed it gets TF-IDF, and the interface names whichever backend produced the numbers.

**The original text is never modified.** Every token and sentence carries absolute character offsets, so `original_text[start:end]` is always exactly what the person wrote. Normalisation exists only in the processed representation.

## Request lifecycle: analyzing a document

1. `analyzer.views.analyze` validates the form (or `extract` validates an upload and pulls its text).
2. `pipeline.run_pipeline` runs preprocessing → statistics → lexical → syntax → discourse → statistical → semantic → stylometric → detector.
3. `pipeline.save_results` writes `Analysis`, `SentenceAnalysis` and `Feature` rows in one transaction.
4. The browser is redirected to the results page, which reads those rows back.

A 450-word document takes roughly 40 ms after warm-up; the first analysis in a process pays about half a second to load spaCy.

## Where this would change at scale

Analysis is synchronous. For long documents or many users, `analyze_document` is the natural boundary to move behind Celery: it already takes an `Analysis` and returns a boolean. Nothing else would need to change. `DATABASE_ENGINE=postgresql` switches the database without code changes.
