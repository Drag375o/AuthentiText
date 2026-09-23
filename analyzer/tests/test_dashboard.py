"""Phase 7: dashboard widgets."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from analyzer.models import Analysis

ESSAY = ("My grandmother kept her recipes on the backs of electricity bills, in pencil. "
         "Half of them are unreadable now, stained with turmeric and something like tamarind. "
         "I still can't make her dal taste right, though I have tried for years. "
         "Nobody measured anything in that kitchen, and a pinch meant her pinch, not mine. ") * 4


class DashboardTests(TestCase):
    url = reverse("analyzer:dashboard")

    def setUp(self):
        self.user = User.objects.create_user("ayesha", password="pw-123-long-enough")
        self.other = User.objects.create_user("other", password="pw-123-long-enough")
        self.client.force_login(self.user)

    def analyze(self, title):
        self.client.post(reverse("analyzer:analyze"), {"title": title, "text": ESSAY})
        return Analysis.objects.get(title=title)

    def test_requires_login(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.url), f"{reverse('accounts:login')}?next={self.url}")

    def test_empty_state(self):
        response = self.client.get(self.url)
        self.assertContains(response, "No analyses yet.")
        self.assertNotContains(response, "Results so far")   # "Writing profile" also appears in the footer

    def test_widgets_appear_once_a_document_is_analyzed(self):
        self.analyze("Essay")
        response = self.client.get(self.url)
        for text in ("Documents analyzed", "Average length", "Latest analysis", "Writing profile",
                     "Results so far", "Recent analyses"):
            with self.subTest(widget=text):
                self.assertContains(response, text)

    def test_unanalyzed_documents_are_counted_separately(self):
        self.analyze("Essay")
        Analysis.objects.create(user=self.user, title="Pending", original_text=ESSAY)
        response = self.client.get(self.url)
        self.assertEqual(response.context["completed"], 1)
        self.assertEqual(response.context["total"], 2)
        self.assertContains(response, "1 not analyzed yet")

    def test_compare_link_appears_only_with_two_documents(self):
        self.analyze("One")
        self.assertNotContains(self.client.get(self.url), "Compare two")
        self.analyze("Two")
        self.assertContains(self.client.get(self.url), "Compare two")

    def test_only_this_users_documents_are_counted(self):
        self.analyze("Mine")
        Analysis.objects.create(user=self.other, title="Theirs", original_text=ESSAY)
        response = self.client.get(self.url)
        self.assertEqual(response.context["total"], 1)
        self.assertNotContains(response, "Theirs")

    def test_result_counts_add_up(self):
        self.analyze("One")
        self.analyze("Two")
        results = self.client.get(self.url).context["results"]
        self.assertEqual(sum(row["count"] for row in results), 2)
        self.assertTrue(all(row["label"] for row in results))

    def test_latest_and_average_use_analyzed_documents_only(self):
        """A document that was never analyzed has no result and no word count,
        so it must not become the "latest analysis" or drag the average to zero."""
        essay = self.analyze("Essay")
        Analysis.objects.create(user=self.user, title="Pending", original_text=ESSAY)   # newer, unanalyzed
        response = self.client.get(self.url)
        self.assertEqual(response.context["latest"], essay)
        self.assertEqual(response.context["average_words"], essay.word_count)
        self.assertContains(response, "Pending")   # still listed, so it can be found and analyzed
