from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from analyzer.models import Analysis

JSON = {"HTTP_ACCEPT": "application/json"}


class RenameTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pw-owner-123!")
        self.other = User.objects.create_user("other", password="pw-other-123!")
        self.analysis = Analysis.objects.create(user=self.owner, title="Draft", original_text="Some words about recipes and family history here.")
        self.url = reverse("analyzer:rename", args=[self.analysis.pk])
        self.client.force_login(self.owner)

    def test_json_rename(self):
        response = self.client.post(self.url, {"title": "  Final   essay  "}, **JSON)
        self.assertEqual(response.json(), {"ok": True, "title": "Final essay", "display_name": "Final essay"})
        self.analysis.refresh_from_db()
        self.assertEqual(self.analysis.title, "Final essay")

    def test_plain_form_rename_redirects_with_message(self):
        response = self.client.post(self.url, {"title": "Final essay"}, follow=True)
        self.assertRedirects(response, reverse("analyzer:detail", args=[self.analysis.pk]))
        self.assertContains(response, "Renamed to \u201cFinal essay\u201d.")

    def test_empty_name_falls_back_to_text(self):
        data = self.client.post(self.url, {"title": "   "}, **JSON).json()
        self.assertEqual(data["title"], "")
        self.assertEqual(data["display_name"], "Some words about recipes and family\u2026")

    def test_too_long_is_rejected(self):
        response = self.client.post(self.url, {"title": "x" * 201}, **JSON)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Keep the name under 200 characters.")
        self.analysis.refresh_from_db()
        self.assertEqual(self.analysis.title, "Draft")

    def test_other_user_gets_404(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.url, {"title": "Hacked"}, **JSON).status_code, 404)
        self.analysis.refresh_from_db()
        self.assertEqual(self.analysis.title, "Draft")

    def test_anonymous_redirected(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url, {"title": "x"}).status_code, 302)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.url, {"title": "x"}, **JSON).status_code, 403)

    def test_title_is_escaped_on_page(self):
        self.client.post(self.url, {"title": "<script>alert(1)</script>"}, **JSON)
        page = self.client.get(reverse("analyzer:detail", args=[self.analysis.pk]))
        self.assertNotContains(page, "<script>alert(1)</script>")
        self.assertContains(page, "&lt;script&gt;alert(1)&lt;/script&gt;")


class ConfirmDialogTests(TestCase):
    def test_dialog_is_on_every_page(self):
        response = self.client.get(reverse("core:landing"))
        self.assertContains(response, "data-confirm-dialog", count=1)
        self.assertContains(response, "js/confirm-dialog.js")

    def test_delete_form_is_wired_to_dialog(self):
        user = User.objects.create_user("owner", password="pw-owner-123!")
        analysis = Analysis.objects.create(user=user, title="Essay", original_text="Text.")
        self.client.force_login(user)
        response = self.client.get(reverse("analyzer:detail", args=[analysis.pk]))
        self.assertContains(response, 'data-confirm-title="Delete this analysis?"')
        self.assertContains(response, 'data-confirm-label="Delete"')
        self.assertContains(response, "This can't be undone.")
        self.assertContains(response, 'data-confirm-name="Essay"')
