from django.contrib.auth.models import User
from django.core import signing
from django.test import Client, TestCase
from django.urls import reverse

from analyzer.models import Analysis
from analyzer.views import UPLOAD_TOKEN_SALT, make_upload_token

from .files import EXE_BYTES, PARAGRAPH_1, make_docx, make_pdf, upload

JSON = {"HTTP_ACCEPT": "application/json"}


class ExtractViewTests(TestCase):
    url = reverse("analyzer:extract")

    def setUp(self):
        self.user = User.objects.create_user("ayesha", password="pw-123-long-enough")
        self.client.force_login(self.user)

    def test_json_extract_pdf(self):
        data = self.client.post(self.url, {"file": upload("../recipes.pdf", make_pdf())}, **JSON).json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["filename"], "recipes.pdf")
        self.assertEqual((data["kind"], data["pages"]), ("pdf", 1))
        self.assertTrue(data["text"].startswith(PARAGRAPH_1))
        self.assertEqual(data["words"], 20)
        self.assertTrue(data["token"])

    def test_nothing_is_stored_on_extract(self):
        self.client.post(self.url, {"file": upload("essay.docx", make_docx())}, **JSON)
        self.assertEqual(Analysis.objects.count(), 0)

    def test_json_rejection_has_clean_message(self):
        response = self.client.post(self.url, {"file": upload("virus.pdf", EXE_BYTES)}, **JSON)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"ok": False, "error": "This file is named .pdf but isn't a PDF."})

    def test_missing_file(self):
        response = self.client.post(self.url, {}, **JSON)
        self.assertEqual(response.json()["error"], "Choose a file to upload.")

    def test_no_js_extract_renders_editor_prefilled(self):
        response = self.client.post(self.url, {"file": upload("essay.docx", make_docx(table=True))})
        self.assertContains(response, PARAGRAPH_1)
        self.assertContains(response, "essay.docx")
        self.assertContains(response, "Skipped 1 table.")

    def test_no_js_rejection_redirects_with_message(self):
        response = self.client.post(self.url, {"file": upload("old.doc", b"x")}, follow=True)
        self.assertRedirects(response, reverse("analyzer:analyze"))
        self.assertContains(response, "save it as .docx")

    def test_login_and_csrf_required(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url, {"file": upload("a.txt", b"hi")}).status_code, 302)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url, {"file": upload("a.txt", b"hi")}).status_code, 403)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


class SaveWithTokenTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ayesha", password="pw-123-long-enough")
        self.client.force_login(self.user)
        self.save_url = reverse("analyzer:analyze")

    def test_valid_token_marks_upload_and_keeps_filename(self):
        token = make_upload_token(self.user, "recipes.pdf", "pdf")
        self.client.post(self.save_url, {"text": "Edited text after upload.", "upload_token": token})
        a = Analysis.objects.get()
        self.assertEqual((a.source_type, a.filename, a.display_name), ("upload", "recipes.pdf", "recipes.pdf"))

    def test_tampered_token_is_ignored(self):
        token = make_upload_token(self.user, "recipes.pdf", "pdf")
        forged = signing.dumps({"u": self.user.pk, "f": "../../evil.pdf", "k": "pdf"}, salt="wrong-salt")
        for bad in [token[:-2] + "xx", forged, "garbage"]:
            self.client.post(self.save_url, {"text": "Some text here.", "upload_token": bad})
        self.assertFalse(Analysis.objects.filter(source_type="upload").exists())
        self.assertEqual(Analysis.objects.filter(filename="").count(), 3)

    def test_token_from_another_user_is_ignored(self):
        other = User.objects.create_user("other", password="pw-123-long-enough")
        token = make_upload_token(other, "theirs.pdf", "pdf")
        self.client.post(self.save_url, {"text": "Some text here.", "upload_token": token})
        self.assertEqual(Analysis.objects.get().source_type, "paste")

    def test_expired_token_is_ignored(self):
        from unittest import mock
        token = make_upload_token(self.user, "old.pdf", "pdf")
        with mock.patch("django.core.signing.time.time", return_value=10**11):
            self.client.post(self.save_url, {"text": "Some text here.", "upload_token": token})
        self.assertEqual(Analysis.objects.get().source_type, "paste")


class NoJsRoundTripTests(TestCase):
    """Without JavaScript the extract view renders the editor at /analyze/extract/.
    Its form must still post to the save view, not back to the extractor."""

    def test_editor_form_posts_to_analyze_after_extract(self):
        user = User.objects.create_user("ayesha", password="pw-123-long-enough")
        self.client.force_login(user)
        page = self.client.post(reverse("analyzer:extract"), {"file": upload("essay.docx", make_docx())})
        self.assertContains(page, f'action="{reverse("analyzer:analyze")}"')
        token = page.context["form"].initial["upload_token"]
        self.client.post(reverse("analyzer:analyze"), {"text": PARAGRAPH_1, "upload_token": token})
        self.assertEqual(Analysis.objects.get().filename, "essay.docx")
