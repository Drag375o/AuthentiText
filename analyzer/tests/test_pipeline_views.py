from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from analyzer.models import Analysis
from analyzer.services.pipeline import PIPELINE_VERSION

TEXT = ("My grandmother kept her recipes on the backs of electricity bills. "
        "Half of them are unreadable now, stained with turmeric.\n\nI still can't make her dal taste right.")


class AnalyzeRunsPipelineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ayesha", password="pw-123-long-enough")
        self.client.force_login(self.user)

    def test_saving_analyzes_and_stores_rows(self):
        response = self.client.post(reverse("analyzer:analyze"), {"text": TEXT}, follow=True)
        a = Analysis.objects.get()
        self.assertEqual((a.status, a.pipeline_version), ("complete", PIPELINE_VERSION))
        self.assertEqual((a.sentence_count, a.paragraph_count), (3, 2))
        self.assertEqual(a.sentences.count(), 3)
        self.assertTrue(a.features.filter(feature_name="mattr").exists())
        self.assertIsNotNone(a.processed_at)
        self.assertContains(response, "Analyzed \u201c")
        self.assertContains(response, "Sentence rhythm")
        self.assertContains(response, 'id="sentence-chart-data"')
        self.assertContains(response, "Grammar and structure")
        self.assertContains(response, "Pattern explorer")
        self.assertContains(response, 'id="pos-chart-data"')

    def test_failure_keeps_text_and_says_so(self):
        with mock.patch("analyzer.services.pipeline.preprocess", side_effect=RuntimeError("boom")), \
                self.assertLogs("authentitext", level="ERROR") as logs:
            response = self.client.post(reverse("analyzer:analyze"), {"text": TEXT}, follow=True)
        self.assertIn("Pipeline failed", logs.output[0])   # details go to the log, not the page
        a = Analysis.objects.get()
        self.assertEqual(a.status, "failed")
        self.assertEqual(a.original_text, TEXT)
        self.assertContains(response, "the analysis didn")
        self.assertContains(response, "Analyze again")
        self.assertNotContains(response, "boom")

    def test_rerun_endpoint_and_ownership(self):
        a = Analysis.objects.create(user=self.user, original_text=TEXT)
        self.assertContains(self.client.get(reverse("analyzer:detail", args=[a.pk])), "Analyze now")
        self.client.post(reverse("analyzer:run", args=[a.pk]))
        a.refresh_from_db()
        self.assertEqual(a.status, "complete")
        other = User.objects.create_user("other", password="pw-123-long-enough")
        self.client.force_login(other)
        self.assertEqual(self.client.post(reverse("analyzer:run", args=[a.pk])).status_code, 404)

    def test_rerun_replaces_rows_instead_of_duplicating(self):
        self.client.post(reverse("analyzer:analyze"), {"text": TEXT})
        a = Analysis.objects.get()
        self.client.post(reverse("analyzer:run", args=[a.pk]))
        self.assertEqual(a.sentences.count(), 3)

    def test_management_command_processes_pending(self):
        Analysis.objects.create(user=self.user, original_text=TEXT)
        out = StringIO()
        call_command("analyze_pending", stdout=out)
        self.assertIn("Analyzed 1 of 1", out.getvalue())
        call_command("analyze_pending", stdout=(out := StringIO()))
        self.assertIn("Nothing to analyze", out.getvalue())


class PatternExplorerRenderingTests(TestCase):
    def test_matches_are_highlighted_and_escaped(self):
        user = User.objects.create_user("ayesha", password="pw-123-long-enough")
        self.client.force_login(user)
        text = "<b>Bold</b> claim. However, it is important to note that <script>x</script> matters."
        self.client.post(reverse("analyzer:analyze"), {"text": text})
        page = self.client.get(reverse("analyzer:detail", args=[Analysis.objects.get().pk]))
        self.assertContains(page, '<mark class="pattern-mark">it is important to note</mark>')
        self.assertContains(page, '<mark class="pattern-mark">However</mark>')
        self.assertNotContains(page, "<script>x</script>")
        self.assertContains(page, "&lt;script&gt;x&lt;/script&gt;")
