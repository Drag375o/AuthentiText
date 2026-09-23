# Setup

## Requirements

- Python 3.11 or newer
- Node.js 18 or newer (only to build the CSS)
- About 500 MB of disk space, mostly for the spaCy model

## Install

**Windows (PowerShell).** Run each line separately; PowerShell 5.1 does not support `&&`.

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

**macOS / Linux**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
npm install && npm run build:css
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000 and create an account.

`requirements.txt` installs the spaCy English model directly from its release URL, so no separate `spacy download` step is needed.

## While developing

```bash
npm run watch:css        # rebuild CSS as you edit templates
python manage.py test    # Python tests
npm run test:js          # JavaScript tests
```

Add `DJANGO_SECRET_KEY` to `.env` before doing anything public. The default is a development placeholder.

## Optional: better semantics

Sentence similarity uses TF-IDF by default, which compares shared wording. Installing sentence-transformers switches it to meaning-based embeddings automatically:

```bash
pip install "sentence-transformers>=3.0"
```

The first analysis afterwards downloads a model of a few hundred MB. The document page always names the backend in use. Set `EMBEDDING_BACKEND=tfidf` in `.env` to force the default back.

## Settings worth knowing

All are environment variables, read in `config/settings.py`.

| Variable | Default | Meaning |
|---|---|---|
| `DJANGO_SECRET_KEY` | development placeholder | set this for anything public |
| `DJANGO_DEBUG` | `true` | turn off in production |
| `DATABASE_ENGINE` | SQLite | set to `postgresql` with the `DB_*` variables |
| `ANALYSIS_MIN_WORDS` | 150 | below this, results are "insufficient evidence" |
| `ANALYSIS_MAX_CHARS` | 100000 | longest text accepted |
| `MAX_UPLOAD_SIZE_MB` | 5 | upload limit |
| `EMBEDDING_BACKEND` | `auto` | `auto`, `tfidf`, `sentence-transformers` |
| `DETECTOR_BACKEND` | `auto` | `auto`, `trained`, `demo` |
| `PATTERN_LIBRARY_PATH` | bundled file | point at your own pattern library |

## Management commands

```bash
python manage.py analyze_pending          # analyze documents saved before a pipeline change
python manage.py analyze_pending --all    # re-analyze everything
python manage.py train_detector data.jsonl  # train a real classifier
python manage.py feature_docs --write     # regenerate docs/FEATURES.md
python manage.py createsuperuser          # access /admin/
```

## Troubleshooting

**The page loads without styling.** Run `npm run build:css`; `static/css/styles.css` is generated, not committed.

**`spacy` cannot find the model.** Reinstall requirements inside the activated virtual environment.

**A virtual environment stops working after you move the project.** Virtual environments store absolute paths. Delete `.venv` and create it again.

**Windows PowerShell blocks activation.** Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.
