# AuthentiText

*Analyze the signals behind your writing.*

AuthentiText is an NLP-powered writing analysis platform that combines linguistic analysis, stylometry, statistical text features, semantic similarity, and machine learning to provide explainable document-level and sentence-level writing analysis.

> **Status: Phase 4 of the build.** Done so far: the Django foundation, design system, landing page, accounts, the editor and file upload, and the first stages of the NLP pipeline: spaCy preprocessing, document statistics and lexical features. The NLP pipeline comes next; routes for unbuilt features show an honest "not built yet" page. All analysis on the landing page is a hand-written illustration and is labelled that way.

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
                   features, pipeline, uploads, parser, text_stats), management commands
docs/              NLP_PIPELINE.md, FEATURES.md (generated), LIMITATIONS.md
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
4. NLP pipeline: preprocessing, document statistics, lexical features (done); syntactic, statistical, semantic and stylometric next
5. Detector interface with a clearly labelled demo mode, then a trained baseline
6. Explainability, results dashboard, sentence heatmap
7. Compare, writing profile, reports, dashboard
8. Documentation in `docs/`

## Limitations

A result describes characteristics a text shares with training examples. It does not prove authorship, AI use, plagiarism, misconduct or intent.
