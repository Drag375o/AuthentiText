from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from analyzer.models import Analysis


class AnalyzeViewTests(TestCase):
    url = reverse("analyzer:analyze")

    def setUp(self):
        self.user = User.objects.create_user("ayesha", password="pw-123-long-enough")
        self.client.force_login(self.user)

    def test_requires_login(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.url), f"{reverse('accounts:login')}?next={self.url}")

    def test_page_renders_editor_and_config(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Analyze your writing.")
        self.assertContains(response, 'id="editor-config" type="application/json"')
        self.assertContains(response, "js/text-stats.js")
        self.assertContains(response, "Analyze document")

    def test_saves_original_text_exactly(self):
        raw = "  First paragraph, with spaces kept.\r\n\r\nSecond one.  "
        response = self.client.post(self.url, {"title": "  My essay  ", "text": raw})
        analysis = Analysis.objects.get()
        self.assertRedirects(response, reverse("analyzer:detail", args=[analysis.pk]))
        self.assertEqual(analysis.original_text, raw)
        self.assertEqual(analysis.title, "My essay")
        self.assertEqual(analysis.user, self.user)
        self.assertEqual(analysis.source_type, Analysis.SourceType.PASTE)
        self.assertEqual(analysis.status, Analysis.Status.COMPLETE)

    def test_stores_counts(self):
        self.client.post(self.url, {"text": "One two three. Four five!\n\nSix."})
        a = Analysis.objects.get()
        self.assertEqual((a.word_count, a.sentence_count, a.paragraph_count), (6, 3, 2))

    def test_rejects_empty_and_whitespace(self):
        for text in ["", "   \n\n  "]:
            response = self.client.post(self.url, {"text": text})
            self.assertContains(response, "Add some text to analyze first.")
        self.assertEqual(Analysis.objects.count(), 0)

    @override_settings(ANALYSIS_MAX_CHARS=20)
    def test_rejects_over_limit_counting_crlf_once(self):
        # 10 + CRLF + 9 = 20 characters when CRLF counts once: allowed.
        self.client.post(self.url, {"text": "0123456789\r\n012345678"})
        self.assertEqual(Analysis.objects.count(), 1)
        response = self.client.post(self.url, {"text": "x" * 21})
        self.assertContains(response, "The limit is 20")
        self.assertEqual(Analysis.objects.count(), 1)

    def test_saved_message_and_title_fallback(self):
        response = self.client.post(self.url, {"text": "Short note about recipes and memory."}, follow=True)
        self.assertContains(response, "Analyzed \u201cShort note about recipes and memory.\u201d")

    def test_csrf_required(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url, {"text": "Hello there."}).status_code, 403)
