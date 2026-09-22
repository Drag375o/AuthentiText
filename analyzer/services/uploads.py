"""
Upload validation: decide whether a file is safe and supported *before* parsing it.

The file's own bytes decide its type, not its name or the browser's
Content-Type header (both are client-controlled):
  PDF   starts with "%PDF-"
  DOCX  is a ZIP whose [Content_Types].xml declares a Word document
  TXT   decodes as text and contains no NUL bytes
"""
from __future__ import annotations

import io
import os
import re
import unicodedata
import zipfile
from dataclasses import dataclass

from django.conf import settings


class UploadRejected(Exception):
    """A user-facing reason the file can't be used. The message is shown as-is."""


ALLOWED_EXTENSIONS = {".txt": "txt", ".pdf": "pdf", ".docx": "docx"}
LEGACY_HINTS = {
    ".doc": "Older Word files (.doc) aren't supported. Open it in Word and save it as .docx.",
    ".docm": "Macro-enabled Word files aren't accepted. Save it as a regular .docx.",
    ".rtf": "RTF files aren't supported. Save it as .docx or .txt.",
    ".odt": "OpenDocument files aren't supported. Save it as .docx.",
}
MAX_FILENAME_LENGTH = 150
DOCX_MAIN_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str   # sanitised, safe to display and store
    kind: str       # "txt" | "pdf" | "docx"
    data: bytes


def safe_filename(name: str) -> str:
    """Keep only the final path component, drop control characters, cap the length."""
    name = unicodedata.normalize("NFC", name or "")
    name = re.split(r"[\\/]", name)[-1]                      # strips ../ and C:\ paths
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C")
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    stem, ext = os.path.splitext(name)
    if len(name) > MAX_FILENAME_LENGTH:
        name = stem[: MAX_FILENAME_LENGTH - len(ext)].rstrip() + ext
    return name or "document"


def _check_docx_container(data: bytes) -> None:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise UploadRejected("This file isn't a valid .docx document.")
    with archive:
        entries = archive.infolist()
        if len(entries) > settings.DOCX_MAX_ENTRIES:
            raise UploadRejected("This .docx file has an unusual structure and can't be opened safely.")
        uncompressed = sum(e.file_size for e in entries)
        if uncompressed > settings.DOCX_MAX_UNCOMPRESSED_MB * 1024 * 1024:
            raise UploadRejected("This .docx file expands to more data than we can safely open.")
        names = {e.filename for e in entries}
        if any(n.lower().endswith("vbaproject.bin") for n in names):
            raise UploadRejected("Macro-enabled Word files aren't accepted. Save it as a regular .docx.")
        if "[Content_Types].xml" not in names or "word/document.xml" not in names:
            raise UploadRejected("This file isn't a valid .docx document.")
        content_types = archive.read("[Content_Types].xml").decode("utf-8", "replace")
        if DOCX_MAIN_TYPE not in content_types:
            raise UploadRejected("This file isn't a regular Word document (.docx).")


def detect_kind(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"PK\x03\x04"):
        return "zip"
    if b"\x00" not in data or data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "text"
    return None


def validate_upload(uploaded_file) -> ValidatedUpload:
    """Validate a Django UploadedFile. Raises UploadRejected with a user-facing message."""
    filename = safe_filename(getattr(uploaded_file, "name", ""))
    ext = os.path.splitext(filename)[1].lower()

    if ext in LEGACY_HINTS:
        raise UploadRejected(LEGACY_HINTS[ext])
    if ext not in ALLOWED_EXTENSIONS:
        raise UploadRejected("Upload a TXT, PDF or DOCX file.")

    limit = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if uploaded_file.size > limit:
        raise UploadRejected(f"This file is {uploaded_file.size / 1024 / 1024:.1f} MB. The limit is {settings.MAX_UPLOAD_SIZE_MB} MB.")
    if uploaded_file.size == 0:
        raise UploadRejected("This file is empty.")

    data = uploaded_file.read()
    kind = ALLOWED_EXTENSIONS[ext]
    detected = detect_kind(data)

    if kind == "pdf" and detected != "pdf":
        raise UploadRejected("This file is named .pdf but isn't a PDF.")
    if kind == "docx":
        if detected != "zip":
            raise UploadRejected("This file is named .docx but isn't a Word document.")
        _check_docx_container(data)
    if kind == "txt" and detected != "text":
        raise UploadRejected("This file is named .txt but contains binary data.")

    return ValidatedUpload(filename=filename, kind=kind, data=data)
