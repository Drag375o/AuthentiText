"""
Text extraction from validated uploads.

Extraction choices (the result becomes the document's original text):
- PDF:  text blocks from PyMuPDF in reading order. Lines inside a block are
        joined with spaces, and words hyphenated across a line break are rejoined,
        so paragraphs survive instead of arriving as hard-wrapped lines.
        Blocks are separated by a blank line.
- DOCX: body paragraphs, separated by a blank line. Headers, footers and
        tables are skipped and reported as notes.
- TXT:  UTF-8 (with or without BOM), UTF-16 with BOM, else Windows-1252.
"""
from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field

from django.conf import settings

from .text_stats import normalize_newlines
from .uploads import UploadRejected, ValidatedUpload

logger = logging.getLogger("authentitext")

GENERIC_FAILURE = "We couldn't process this document. Check that it's a valid PDF, DOCX or TXT file."
HYPHEN_BREAK_RE = re.compile(r"(\w)-\n(\w)")
CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass
class ExtractedText:
    text: str
    kind: str
    pages: int | None = None
    notes: list[str] = field(default_factory=list)


# ---------- TXT ----------

def decode_text(data: bytes) -> str:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def extract_txt(data: bytes) -> ExtractedText:
    text = normalize_newlines(decode_text(data))
    return ExtractedText(text=CONTROL_CHARS_RE.sub("", text), kind="txt")


# ---------- PDF ----------

def _join_block_lines(block_text: str) -> str:
    text = HYPHEN_BREAK_RE.sub(r"\1\2", block_text.strip())
    return re.sub(r"\s*\n\s*", " ", text)


def extract_pdf(data: bytes) -> ExtractedText:
    import pymupdf  # imported lazily: only needed for PDFs

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        raise UploadRejected("This PDF is damaged or can't be opened.")
    with doc:
        if doc.needs_pass:
            raise UploadRejected("This PDF is password-protected. Remove the password and upload it again.")
        if doc.page_count > settings.PDF_MAX_PAGES:
            raise UploadRejected(f"This PDF has {doc.page_count} pages. The limit is {settings.PDF_MAX_PAGES}.")
        paragraphs = []
        for page in doc:
            for block in page.get_text("blocks", sort=True):
                if block[6] != 0:          # 0 = text block, 1 = image block
                    continue
                joined = _join_block_lines(block[4])
                if joined:
                    paragraphs.append(joined)
        pages = doc.page_count
    text = "\n\n".join(paragraphs)
    if not text.strip():
        raise UploadRejected("This PDF has no selectable text. It may be a scan; text recognition (OCR) isn't supported yet.")
    return ExtractedText(text=CONTROL_CHARS_RE.sub("", text), kind="pdf", pages=pages)


# ---------- DOCX ----------

def extract_docx(data: bytes) -> ExtractedText:
    import docx  # python-docx

    try:
        document = docx.Document(io.BytesIO(data))
    except Exception:
        raise UploadRejected("This Word document is damaged or can't be opened.")
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    notes = []
    if document.tables:
        count = len(document.tables)
        notes.append(f"Skipped {count} table{'s' if count != 1 else ''}. Only body paragraphs are analyzed.")
    text = "\n\n".join(paragraphs)
    if not text.strip():
        raise UploadRejected("This Word document has no body text to analyze.")
    return ExtractedText(text=CONTROL_CHARS_RE.sub("", text), kind="docx", notes=notes)


EXTRACTORS = {"txt": extract_txt, "pdf": extract_pdf, "docx": extract_docx}


def extract_text(upload: ValidatedUpload) -> ExtractedText:
    """Extract text, enforce the analysis length limit, and never leak internals."""
    try:
        result = EXTRACTORS[upload.kind](upload.data)
    except UploadRejected:
        raise
    except Exception:
        logger.exception("Extraction failed for %s (%s)", upload.filename, upload.kind)
        raise UploadRejected(GENERIC_FAILURE)

    if not result.text.strip():
        raise UploadRejected("This file doesn't contain any text to analyze.")
    length = len(result.text)
    if length > settings.ANALYSIS_MAX_CHARS:
        raise UploadRejected(
            f"This document has {length:,} characters of text. The limit is {settings.ANALYSIS_MAX_CHARS:,}; split it into smaller files."
        )
    return result
