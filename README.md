# AuthentiText

*Analyze the signals behind your writing.*

AuthentiText is an NLP-powered writing analysis platform that combines linguistic analysis, stylometry, statistical text features, semantic similarity, and machine learning to provide explainable document-level and sentence-level writing analysis.

> **Status: Phase 7 in progress.** The full path now runs: upload or paste, NLP pipeline, detector, explainable results with a sentence heatmap. The shipped detector is a clearly labelled **demo** with no measured accuracy; a training command is included so a real classifier can replace it. Reports download as PDF, Word and PDF heatmaps, JSON and CSV, and two documents can be compared side by side. Next: the writing profile page and the remaining documentation. The NLP pipeline comes next; routes for unbuilt features show an honest "not built yet" page. All analysis on the landing page is a hand-written illustration and is labelled that way.

## Setup

**Windows PowerShell** (run each line separately; PowerShell 5.1 doesn't support `&&`):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
npm install
npm run build:css
python manage.py migrate
python manage.py runserver
```

To use the Django admin at `/admin/`, create an account for yourself with `python manage.py createsuperuser`.

If activation is blocked, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.
A virtual environment stores absolute paths, so never move `.venv`; delete and recreate it instead.

**macOS / Linux:**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
npm install && npm run build:css
python manage.py migrate
python manage.py runserver
```

While editing templates, run `npm run watch:css` in a second terminal.

## Hero

The hero has no photo. Behind the headline and the sample card is a faint field of text drawn on a `<canvas>` (`static/js/hero-field.js`). The pointer acts as a reading lens: nearby words darken and some take on the signal underlines. When the pointer is idle, or on touch screens, the lens drifts by itself.

- **Tuning:** the `CONFIG` object at the top of `hero-field.js` sets lens size, strength, drift timing and how quiet the field is behind the headline.
- **Colours:** set by the `--field-*` variables in `static/src/input.css`, which read from `tailwind.config.js`.
- **Performance:** the resting field is drawn once to an offscreen canvas; each frame only redraws words under the lens. The loop pauses when the hero is off-screen or the tab is hidden.
- **Accessibility:** the canvas is `aria-hidden` and ignores pointer events. With reduced motion turned on, it shows a still frame and the card appears without rising.

## Tests

```bash
python manage.py test     # Python: models, views, permissions, text statistics
npm run test:js           # JavaScript: the editor's counting rules
```

The editor counts words, sentences and paragraphs in the browser (`static/js/text-stats.js`) and on the server (`analyzer/services/text_stats.py`). Both run against the same cases in `analyzer/tests/fixtures/text_stats_cases.json`, so the live counts always match what's saved. Add a case there whenever you change a counting rule.

## Design system

| Role | Font | Used for |
| --- | --- | --- |
| Wordmark and handwriting | Cedarville Cursive | Brand name, quotes, reviewer margin notes |
| Headings | Montserrat (200 / 800) | Thin-and-heavy headline contrast |
| Body | Times New Roman | Paragraphs and document text |
| Labels | Julius Sans One | Navigation, buttons, metadata |

Tokens live in `tailwind.config.js`. Components (`.bento`, `.bento-card`, `.span-2x1`, `.sig-high`, …) live in `static/src/input.css`.
Signal strength is always shown three ways: underline style (dotted, dashed, solid), background tint, and screen-reader text.

## Accounts and data

- **Authentication** uses Django's built-in system: hashed passwords, password validators, and safe `?next=` redirects. Logout is POST-only with a CSRF token.
- **Account pages** (`templates/auth/`) share a split layout: a photo panel on the left and the form on the right. The photo is `static/images/hero.webp`, at least 1200 x 1600 px in portrait (1600 x 2000 recommended), under about 400 KB. Keep the lower third fairly dark; the heading sits there. Without the file, the panel shows solid black. On phones the panel is hidden.
- **Keep me logged in:** unticked, the session ends when the browser closes; ticked, it lasts two weeks.
- **Password reset** works for accounts with an email address. In development, reset emails are printed in the terminal running `runserver`. Set the `EMAIL_*` variables in `.env` to send real mail. Unknown addresses get the same response, so the form can't be used to discover accounts.
- **Models** (`analyzer/models.py`): `Analysis` stores the untouched original text plus results; `SentenceAnalysis` stores per-sentence results with character offsets into that text; `Feature` stores one named value per analysis.
- **Probabilities** are nullable and constrained to 0–1 in the database. "Insufficient evidence" is stored as no probability, never as a guessed number.
- **Isolation:** views look analyses up only through `Analysis.objects.for_user(request.user)`. Another user's analysis returns 404, so its existence isn't revealed. Primary keys are UUIDs, so URLs can't be guessed by counting.

## Analyze page

`/analyze/` (signed in) is the editor. It shows live words, sentences, paragraphs, characters and reading time (238 words per minute), plus a gauge toward `ANALYSIS_MIN_WORDS` (150 by default). Below that, results will be reported as "Insufficient evidence". Texts over `ANALYSIS_MAX_CHARS` (100,000) are rejected on both the browser and the server. The original text is saved exactly as written, including leading and trailing spaces. Ctrl+Enter saves, and the page warns before you leave with unsaved text.

The counts are rule-based estimates. Phase 4 replaces sentence segmentation with spaCy.

## File upload

The **Upload a file** tab on `/analyze/` accepts TXT, PDF and DOCX by drag-and-drop or file picker, up to `MAX_UPLOAD_SIZE_MB` (5 MB). The extracted text opens in the editor for review before saving. The uploaded file itself is never stored, only its text.

- **Validation** (`analyzer/services/uploads.py`) uses the file's own bytes, not its name or the browser's claimed type. A PDF must start with `%PDF-`; a DOCX must be a zip that declares itself a Word document. Filenames are reduced to their last path component and stripped of control characters. DOCX archives are checked for zip bombs and macros before opening.
- **Extraction** (`analyzer/services/parser.py`): PDFs keep their paragraphs (lines within a block are joined, and hyphenated words rejoined). DOCX body paragraphs are kept; tables, headers and footers are skipped and reported. TXT is read as UTF-8, UTF-16 with a byte-order mark, or Windows-1252.
- **Clear refusals** for password-protected PDFs, scans with no selectable text (OCR isn't supported), `.doc` and macro-enabled files, and files over the page or length limits.
- **Honest progress:** the bar shows real bytes sent, then "Extracting text…" while the server works.
- **Signed upload token:** the server signs the filename and binds it to your account, so the saved document's "uploaded file" label and filename can't be forged. Tokens expire after 6 hours.
- **Works without JavaScript:** the upload form submits normally and returns the pre-filled editor.

PyMuPDF is licensed under AGPL-3.0, which suits an open-source portfolio project. For closed-source use, swap in `pypdf` inside `extract_pdf`.

## Analysis pipeline

Analyzing a document runs it through spaCy (`en_core_web_sm`) and computes document statistics and lexical features. The results are saved as `SentenceAnalysis` and `Feature` rows and shown on the document page, with a sentence-rhythm chart and an explanation for every measure. See [docs/NLP_PIPELINE.md](docs/NLP_PIPELINE.md) for the design, [docs/FEATURES.md](docs/FEATURES.md) for every feature, and [docs/LIMITATIONS.md](docs/LIMITATIONS.md) for known limits.

```bash
python manage.py analyze_pending       # analyze documents saved before the pipeline existed
python manage.py feature_docs --write   # regenerate the feature table
```

## Detection

The result on every document is produced by a detector behind one interface (`analyzer/services/detector.py`). Probability, confidence and uncertainty are reported separately, and texts under 150 words return "Insufficient evidence" with no number at all.

**The shipped detector is a demo.** It combines ten hand-chosen signals deterministically and is labelled `DEMO ANALYSIS — not a real prediction` on every result. It has no measured accuracy because it was never trained on labelled data.

To train a real one:

```bash
python manage.py train_detector data/labelled.jsonl   # {"text": ..., "label": "human"|"ai"} per line
```

It trains on features from the application's own pipeline, measures itself on held-out data, and saves those metrics with the model. Drop the bundle in `ml/models/` and AuthentiText uses it automatically. See [docs/DETECTION.md](docs/DETECTION.md).

## Comparing documents

`/compare/` puts two of your analyzed documents side by side: the sentence diff (removed wording struck through on the left, added wording underlined on the right), every measured feature with its change, the writing profile, the signal families, and the vocabulary that appears in only one of them.

Sentences are aligned with `difflib`, and similarity is measured **over words, not characters**: two unrelated English sentences share plenty of letters (0.31 for "The cat sat on the mat" against "Feline occupancy of floor coverings remains widespread") but no words, so a character-level measure made every pair look vaguely related. A pair sharing under 20% of its wording is reported as a removal plus an addition rather than an edit.

## Reports

Every analyzed document has a **Download** section after its original text:

| Format | What it is |
|---|---|
| **PDF** | the full report: plain-language summary, result, signal breakdown, writing profile, every measured feature, the sentence table and the limitations |
| **PDF heatmap** | your document with each sentence marked, opening with a three-point key: red tint and a double underline for high signal, grey tint and a single underline for medium, nothing for low |
| **Word (.docx)** | the same marked document, editable: Times New Roman throughout, headings bold and black, and the marks are ordinary Word formatting a reader can change or remove |
| **JSON** | the whole analysis, for your own tools |
| **CSV** | one row per feature, signal, profile score and sentence (UTF-8 with a BOM, so Excel reads it correctly) |

The page also shows the same summary in plain language, as labelled points (the document, the result, what stands out, the strongest signals, and what the result is not), justified across the full width. Rendering is in `analyzer/services/reports/`; ReportLab is used for PDF because it installs with pip on Windows without system libraries.

## Semantic embeddings

Sentence similarity, coherence and redundancy run through a swappable embedder (`analyzer/services/embeddings.py`).

- **Default (no setup):** scikit-learn TF-IDF, which compares the words sentences share. Deterministic and instant, but blind to paraphrase.
- **Optional, better:** install sentence-transformers and AuthentiText uses it automatically. The first run downloads a model of a few hundred MB.

  ```bash
  pip install "sentence-transformers>=3.0"
  ```

Set `EMBEDDING_BACKEND` in `.env` to `tfidf` to force the default, or `sentence-transformers` to fail loudly if the model is missing. The document page always names the backend that produced the numbers.

## Pattern library

Discourse markers and formulaic phrases come from `analyzer/resources/patterns.json`. Add or edit entries there; each needs a `pattern`, `category`, `description` and `strength` (`low`, `medium` or `high`, meaning how generic the phrase is). Use `"position": "start"` for words that only count at the start of a sentence, and `"pos"` to restrict a one-word pattern to a part of speech. The file is validated when loaded. After editing, restart the server and run `python manage.py analyze_pending --all` to re-analyze saved documents.

## Managing documents

- **Rename:** on a document's page, click **Rename** next to the title. Enter saves, Esc cancels, and the page updates without reloading (`static/js/rename.js`). An empty name falls back to the first words of the text. Without JavaScript, the same form submits normally.
- **Delete:** asks through the shared confirmation dialog (`templates/components/confirm_dialog.html`, `static/js/confirm-dialog.js`). It's a native `<dialog>`: focus stays inside, Esc and clicking outside cancel, and **Cancel** is focused first so an accidental Enter never deletes. While deleting, the button shows a spinner and the dialog can't be dismissed.
- **Reusing the dialog:** add `data-confirm="Message"` (plus optional `data-confirm-title`, `data-confirm-label`, `data-confirm-busy`) to any form, or call `await window.ConfirmDialog.ask({...})` from JavaScript. The editor's **Clear** uses it too.
- **Motion:** buttons press in slightly on click, and the dialog fades and rises in. All motion is removed when the system's reduced-motion setting is on.

## Project layout

```
config/            settings (env-driven, PostgreSQL-ready), urls
core/              landing, about, placeholder routes, context processor
accounts/          register, login, logout, styled forms
analyzer/          models, editor, dashboard, analysis page, delete, admin,
                   services/ (nlp, segmentation, preprocessing, document_stats, lexical,
                   syntax, discourse, statistics_features, semantics, embeddings, stylometry,
                   features, pipeline, uploads, parser, text_stats),
                   resources/patterns.json, management commands
docs/              NLP_PIPELINE.md, DETECTION.md, FEATURES.md (generated), LIMITATIONS.md
ml/                training/ (train_baseline.py), models/ (bundles, not committed)
templates/         base, partials/, components/, landing/, auth/, analyzer/
static/src/        Tailwind source
static/css/        compiled CSS (built by npm run build:css)
static/js/         app.js (site), hero-field.js (hero), heatmap.js (sentence viewer),
                   text-stats.js + analyzer.js (editor), upload.js, confirm-dialog.js, rename.js,
                   charts.js (Chart.js visualisations)
tests/js/          Node tests for the browser code
```

## Roadmap

1. Foundation, design system, landing page (done)
2. Authentication and user-scoped models (done)
3. Document ingestion: editor and validated TXT/PDF/DOCX uploads (done)
4. NLP pipeline, linguistic layer: preprocessing, document statistics, lexical, syntactic and discourse features, pattern library (done)
5. NLP pipeline, statistical and semantic layer: entropy, burstiness, sentence embeddings, stylometric profile (done)
6. Detector interface, demo mode, trained baseline, explainability, results dashboard, sentence heatmap (done)
8. Compare, writing profile, reports, dashboard
9. Remaining documentation in `docs/`

## Limitations

A result describes characteristics a text shares with training examples. It does not prove authorship, AI use, plagiarism, misconduct or intent.
