# Routes

AuthentiText is a server-rendered Django application, so most routes return HTML. Two endpoints answer JSON when asked, for the parts of the interface that update without a page reload. There is no public API and no token authentication: every route below is scoped to the signed-in user's own documents.

## Pages

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | landing page |
| GET | `/about/` | what the project is |
| GET | `/accounts/login/`, `/accounts/register/` | sign in, sign up |
| POST | `/accounts/logout/` | sign out (POST only, CSRF-protected) |
| GET, POST | `/accounts/password-reset/…` | the four reset steps |
| GET | `/dashboard/` | overview of your documents |
| GET, POST | `/analyze/` | the editor; POST saves and analyzes |
| GET | `/analysis/<uuid>/` | full results |
| GET | `/compare/?a=<uuid>&b=<uuid>` | two documents side by side |
| GET | `/profile/` | your writing profile across documents |

## Actions

| Method | Path | Notes |
|---|---|---|
| POST | `/analyze/extract/` | validate an upload and extract its text |
| POST | `/analysis/<uuid>/run/` | run or re-run the pipeline |
| POST | `/analysis/<uuid>/rename/` | rename a document |
| POST | `/analysis/<uuid>/delete/` | delete a document and its results |
| GET | `/analysis/<uuid>/report.pdf` | full report |
| GET | `/analysis/<uuid>/report.heatmap.pdf` | the document with sentences marked |
| GET | `/analysis/<uuid>/report.docx` | the same heatmap, editable |
| GET | `/analysis/<uuid>/report.json` | the whole analysis as JSON |
| GET | `/analysis/<uuid>/report.csv` | one row per feature, signal and sentence |

## The two JSON endpoints

Both are ordinary Django views that check `Accept: application/json` and otherwise fall back to a redirect or a rendered page, so the interface still works with JavaScript disabled.

**`POST /analyze/extract/`** — multipart, field `file`.

```json
{
  "ok": true,
  "text": "…extracted text…",
  "filename": "essay.docx",
  "kind": "docx",
  "pages": null,
  "notes": ["Skipped 1 table. Only body paragraphs are analyzed."],
  "words": 612,
  "token": "…signed upload token…"
}
```

On refusal: HTTP 400 with `{"ok": false, "error": "This file is named .pdf but isn't a PDF."}`. The `token` is signed by the server, tied to the account and valid for six hours; it is what lets the saved document record that it came from a file, without trusting the browser.

**`POST /analysis/<uuid>/rename/`** — form field `title`.

```json
{"ok": true, "title": "Final essay", "display_name": "Final essay"}
```

## Rules that apply to every route

- **Authentication.** Everything except the landing page, about page and account pages requires a session. Anonymous requests are redirected to the login page.
- **Ownership.** Documents are looked up only through `Analysis.objects.for_user(request.user)`. Another user's document returns **404**, not 403, so its existence is never revealed.
- **CSRF.** Every POST requires a token, including logout and the JSON endpoints.
- **Method.** Actions that change or delete data reject GET with 405.
- **Identifiers.** UUIDs, so URLs cannot be enumerated.

## The JSON export

`report.json` is the structured form of an entire analysis: document metadata, the result with its probability, confidence and uncertainty, every signal with its finding and caveat, every measured feature with its value and description, the writing profile, every sentence with its score, matched patterns, and the limitations. It is the right starting point for anything you want to build on top.
