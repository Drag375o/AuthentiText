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
        self.assertNotContains(response, "Latest analysis")

    def test_widgets_appear_once_a_document_is_analyzed(self):
        self.analyze("Essay")
        response = self.client.get(self.url)
        for text in ("Documents analyzed", "Average length", "Latest analysis", "Last 8 weeks",
                     "Needs attention", "Recent analyses"):
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

    def test_result_counts_add_up_and_are_summarised_in_one_line(self):
        self.analyze("One")
        self.analyze("Two")
        response = self.client.get(self.url)
        self.assertEqual(sum(row["count"] for row in response.context["results"]), 2)
        label = response.context["results"][0]["label"]
        self.assertContains(response, f"2 &times; {label}")

    def test_it_does_not_repeat_the_profile_page(self):
        self.analyze("Essay")
        response = self.client.get(self.url)
        self.assertNotContains(response, "profile-dot")
        self.assertNotContains(response, "Median formality")

    def test_latest_and_average_use_analyzed_documents_only(self):
        """A document that was never analyzed has no result and no word count,
        so it must not become the "latest analysis" or drag the average to zero."""
        essay = self.analyze("Essay")
        Analysis.objects.create(user=self.user, title="Pending", original_text=ESSAY)   # newer, unanalyzed
        response = self.client.get(self.url)
        self.assertEqual(response.context["latest"], essay)
        self.assertEqual(response.context["average_words"], essay.word_count)
        self.assertContains(response, "Pending")   # still listed, so it can be found and analyzed




class ActivityTests(TestCase):
    """The activity chart and the attention list, which are what the dashboard
    offers that the profile and results pages do not."""

    url = reverse("analyzer:dashboard")

    def setUp(self):
        self.user = User.objects.create_user("ayesha", password="pw-123-long-enough")
        self.client.force_login(self.user)

    def analyzed(self, title, days_ago=0):
        from datetime import timedelta
        from django.utils import timezone
        self.client.post(reverse("analyzer:analyze"), {"title": title, "text": ESSAY})
        analysis = Analysis.objects.get(title=title)
        if days_ago:
            when = timezone.now() - timedelta(days=days_ago)
            Analysis.objects.filter(pk=analysis.pk).update(created_at=when, processed_at=when)
            analysis.refresh_from_db()
        return analysis

    def test_weeks_are_counted_into_the_right_buckets(self):
        from analyzer.services.activity import weekly_activity
        self.analyzed("This week")
        self.analyzed("Three weeks ago", days_ago=21)
        activity = weekly_activity(list(Analysis.objects.all()))
        self.assertEqual(len(activity["weeks"]), 8)
        self.assertEqual(activity["documents"], 2)
        self.assertTrue(activity["weeks"][-1].is_current)
        self.assertEqual(activity["weeks"][-1].documents, 1)
        self.assertEqual(sum(week.documents for week in activity["weeks"]), 2)

    def test_bars_are_scaled_against_the_busiest_week(self):
        from analyzer.services.activity import weekly_activity
        self.analyzed("One")
        self.analyzed("Two")
        self.analyzed("Older", days_ago=14)
        activity = weekly_activity(list(Analysis.objects.all()))
        self.assertEqual(max(week.height for week in activity["weeks"]), 100)
        two_weeks_ago = next(week for week in activity["weeks"] if week.documents == 1)
        self.assertEqual(two_weeks_ago.height, 50)

    def test_documents_outside_the_window_are_left_out(self):
        from analyzer.services.activity import weekly_activity
        self.analyzed("Ancient", days_ago=200)
        activity = weekly_activity(list(Analysis.objects.all()))
        self.assertEqual(activity["documents"], 0)
        self.assertFalse(activity["any"])

    def test_empty_history_says_so(self):
        self.analyzed("Ancient", days_ago=200)
        self.assertContains(self.client.get(self.url), "Nothing analyzed in the last 8 weeks.")

    def test_attention_lists_pending_failed_and_outdated(self):
        from analyzer.services.activity import attention_items
        from analyzer.services.pipeline import PIPELINE_VERSION
        Analysis.objects.create(user=self.user, title="Never run", original_text=ESSAY)
        Analysis.objects.create(user=self.user, title="Broken", original_text=ESSAY,
                                status=Analysis.Status.FAILED)
        old = self.analyzed("Old pipeline")
        Analysis.objects.filter(pk=old.pk).update(pipeline_version="0.1.0")
        items = attention_items(Analysis.objects.for_user(self.user), PIPELINE_VERSION)
        self.assertEqual([item["tone"] for item in items], ["warn", "high", "ok"])
        self.assertEqual([item["analysis"].title for item in items], ["Never run", "Broken", "Old pipeline"])

        response = self.client.get(self.url)
        self.assertContains(response, "was never analyzed.")
        self.assertContains(response, "failed to analyze.")
        self.assertContains(response, "older version of the pipeline")

    def test_several_of_a_kind_are_summarised_on_one_line(self):
        from analyzer.services.activity import attention_items
        from analyzer.services.pipeline import PIPELINE_VERSION
        for index in range(3):
            Analysis.objects.create(user=self.user, title=f"Pending {index}", original_text=ESSAY)
        items = attention_items(Analysis.objects.for_user(self.user), PIPELINE_VERSION)
        self.assertEqual(items[0]["count"], 3)
        self.assertIn("2 other document", items[0]["text"])

    def test_nothing_waiting_says_so(self):
        self.analyzed("Done")
        self.assertContains(self.client.get(self.url), "Everything is analyzed and up to date.")

    def test_attention_never_shows_another_users_document(self):
        from analyzer.services.activity import attention_items
        from analyzer.services.pipeline import PIPELINE_VERSION
        other = User.objects.create_user("other", password="pw-123-long-enough")
        Analysis.objects.create(user=other, title="Theirs", original_text=ESSAY)
        items = attention_items(Analysis.objects.for_user(self.user), PIPELINE_VERSION)
        self.assertEqual(items, [])
