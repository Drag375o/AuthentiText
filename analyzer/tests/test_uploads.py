from django.test import SimpleTestCase, override_settings

from analyzer.services.parser import extract_text
from analyzer.services.uploads import UploadRejected, safe_filename, validate_upload

from .files import (EXE_BYTES, PARAGRAPH_1, PARAGRAPH_2, add_to_zip, make_docx, make_pdf,
                    make_zip_bomb, upload)


def extract(name, data):
    return extract_text(validate_upload(upload(name, data)))


class FilenameTests(SimpleTestCase):
    def test_path_traversal_is_stripped(self):
        for raw, safe in [("../../etc/passwd.txt", "passwd.txt"), ("..\\..\\Windows\\win.ini.txt", "win.ini.txt"),
                          ("C:\\Users\\me\\essay.docx", "essay.docx"), ("/abs/path/report.pdf", "report.pdf")]:
            with self.subTest(raw=raw):
                self.assertEqual(safe_filename(raw), safe)

    def test_control_characters_removed_and_length_capped(self):
        self.assertEqual(safe_filename("bad\x00na\u202eme.txt"), "badname.txt")
        long = safe_filename("a" * 400 + ".pdf")
        self.assertTrue(long.endswith(".pdf"))
        self.assertLessEqual(len(long), 150)

    def test_empty_name_gets_placeholder(self):
        self.assertEqual(safe_filename("..."), "document")


class ValidationTests(SimpleTestCase):
    def rejects(self, name, data, message_part):
        with self.assertRaises(UploadRejected) as ctx:
            validate_upload(upload(name, data))
        self.assertIn(message_part, str(ctx.exception))

    def test_unsupported_and_legacy_extensions(self):
        self.rejects("photo.png", b"\x89PNG", "Upload a TXT, PDF or DOCX file.")
        self.rejects("old.doc", b"\xd0\xcf\x11\xe0", "save it as .docx")
        self.rejects("macro.docm", b"PK\x03\x04", "Macro-enabled")

    def test_renamed_executable_is_rejected_for_every_type(self):
        self.rejects("essay.pdf", EXE_BYTES, "isn't a PDF")
        self.rejects("essay.docx", EXE_BYTES, "isn't a Word document")
        self.rejects("essay.txt", EXE_BYTES, "binary data")

    def test_empty_file(self):
        self.rejects("empty.txt", b"", "empty")

    @override_settings(MAX_UPLOAD_SIZE_MB=1)
    def test_oversized_file(self):
        self.rejects("big.txt", b"a" * (1024 * 1024 + 1), "The limit is 1 MB")

    def test_zip_that_isnt_a_word_document(self):
        import io, zipfile
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            z.writestr("hello.txt", "hi")
        self.rejects("fake.docx", buffer.getvalue(), "isn't a valid .docx")

    def test_macro_inside_docx_is_rejected(self):
        self.rejects("sneaky.docx", add_to_zip(make_docx(), "word/vbaProject.bin", b"macro"), "Macro-enabled")

    def test_zip_bomb_is_rejected_before_parsing(self):
        self.rejects("bomb.docx", make_zip_bomb(60), "more data than we can safely open")


class ExtractionTests(SimpleTestCase):
    def test_txt_utf8_with_bom_and_crlf(self):
        result = extract("notes.txt", "\ufeffCaf\u00e9 one.\r\n\r\nTwo.".encode("utf-8"))
        self.assertEqual(result.text, "Caf\u00e9 one.\n\nTwo.")

    def test_txt_utf16_and_cp1252(self):
        self.assertEqual(extract("u16.txt", "Na\u00efve text.".encode("utf-16")).text, "Na\u00efve text.")
        self.assertEqual(extract("win.txt", "\u201cQuoted\u201d caf\u00e9".encode("cp1252")).text, "\u201cQuoted\u201d caf\u00e9")

    def test_pdf_keeps_paragraphs_despite_line_wrapping(self):
        result = extract("recipes.pdf", make_pdf())
        self.assertEqual(result.text, f"{PARAGRAPH_1}\n\n{PARAGRAPH_2}")
        self.assertEqual(result.pages, 1)

    def test_pdf_rejoins_hyphenated_words(self):
        from analyzer.services.parser import _join_block_lines
        self.assertEqual(_join_block_lines("an exam-\nple of wrap-\nping\ntext"), "an example of wrapping text")

    def test_password_protected_pdf(self):
        with self.assertRaisesMessage(UploadRejected, "password-protected"):
            extract("locked.pdf", make_pdf(password="secret"))

    def test_scanned_pdf_without_text(self):
        with self.assertRaisesMessage(UploadRejected, "no selectable text"):
            extract("scan.pdf", make_pdf(text=False))

    @override_settings(PDF_MAX_PAGES=2)
    def test_pdf_page_limit(self):
        with self.assertRaisesMessage(UploadRejected, "The limit is 2"):
            extract("long.pdf", make_pdf(pages=3))

    def test_docx_paragraphs_and_table_note(self):
        result = extract("essay.docx", make_docx(table=True))
        self.assertEqual(result.text, f"{PARAGRAPH_1}\n\n{PARAGRAPH_2}")
        self.assertEqual(result.notes, ["Skipped 1 table. Only body paragraphs are analyzed."])

    @override_settings(ANALYSIS_MAX_CHARS=50)
    def test_extracted_text_over_limit(self):
        with self.assertRaisesMessage(UploadRejected, "The limit is 50"):
            extract("long.txt", b"word " * 20)

    def test_whitespace_only_file(self):
        with self.assertRaisesMessage(UploadRejected, "doesn't contain any text"):
            extract("blank.txt", b"  \n\n \t ")
