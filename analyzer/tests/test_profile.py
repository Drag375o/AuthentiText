"""Phase 7: the writing profile across a user's documents."""
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from analyzer.models import Analysis
from analyzer.services.profile import build_writing_profile
from analyzer.services.stylometry import PROFILE_DIMENSIONS

ESSAY = ("My grandmother kept her recipes on the backs of electricity bills, in pencil. "
         "Half of them are unreadable now, stained with turmeric and something like tamarind. "
         "I still can't make her dal taste right, though I have tried for years. "
         "Nobody measured anything in that kitchen, and a pinch meant her pinch, not mine. ") * 4
REPORT = ("The dataset was partitioned into training, development and test sets for the experiments. "
          "Stratified sampling was applied to ensure a balanced class distribution across all splits. "
          "The resulting distribution is reported in the table below for every annotation dimension. "
          "It is important to note that the classes remain imbalanced despite this procedure. ") * 4


class FakeAnalysis:
    """A stand-in with just the attributes the profile builder reads."""

    def __init__(self, pk, name, scores, words=400, created_at=None):
        from django.utils import timezone
        self.pk, self.word_count = pk, words
        self.display_name = name
        self.created_at = created_at or timezone.now()
        self.report = {"profile": [{"key": d.key, "label": d.label, "score": scores.get(d.key)}
                                   for d in PROFILE_DIMENSIONS]}


class ProfileBuilderTests(SimpleTestCase):
    def test_reports_spread_rather_than_a_single_average(self):
        profile = build_writing_profile([
            FakeAnalysis(1, "Essay", {"formality": 20, "vocabulary_diversity": 60}),
            FakeAnalysis(2, "Report", {"formality": 80, "vocabulary_diversity": 64}),
        ])
        formality = next(row for row in profile["rows"] if row["key"] == "formality")
        self.assertEqual((formality["low"], formality["high"], formality["spread"]), (20, 80, 60))
        self.assertEqual(formality["median"], 50)
        self.assertEqual(len(formality["points"]), 2)

    def test_the_widest_dimension_is_named_only_when_it_is_wide(self):
        wide = build_writing_profile([FakeAnalysis(1, "A", {"formality": 10}),
                                      FakeAnalysis(2, "B", {"formality": 90})])
        narrow = build_writing_profile([FakeAnalysis(1, "A", {"formality": 50}),
                                        FakeAnalysis(2, "B", {"formality": 54})])
        self.assertEqual(wide["widest"]["key"], "formality")
        self.assertIsNone(narrow["widest"])

    def test_a_single_document_has_no_spread(self):
        profile = build_writing_profile([FakeAnalysis(1, "Only", {"formality": 40})])
        row = next(r for r in profile["rows"] if r["key"] == "formality")
        self.assertIsNone(row["spread"])
        self.assertEqual(row["median"], 40)
        self.assertFalse(profile["enough"])

    def test_missing_scores_are_reported_as_not_measured(self):
        profile = build_writing_profile([FakeAnalysis(1, "A", {"formality": None})])
        row = next(r for r in profile["rows"] if r["key"] == "formality")
        self.assertEqual(row["count"], 0)
        self.assertIsNone(row["median"])

    def test_no_documents(self):
        profile = build_writing_profile([])
        self.assertEqual(profile["documents"], 0)
        self.assertEqual(profile["total_words"], 0)
        self.assertTrue(all(row["count"] == 0 for row in profile["rows"]))


class ProfilePageTests(TestCase):
    url = reverse("analyzer:profile")

    def setUp(self):
        self.user = User.objects.create_user("ayesha", password="pw-123-long-enough")
        self.other = User.objects.create_user("other", password="pw-123-long-enough")
        self.client.force_login(self.user)

    def analyze(self, title, text):
        self.client.post(reverse("analyzer:analyze"), {"title": title, "text": text})
        return Analysis.objects.get(title=title)

    def test_requires_login(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.url), f"{reverse('accounts:login')}?next={self.url}")

    def test_empty_state(self):
        response = self.client.get(self.url)
        self.assertContains(response, "No profile yet.")
        self.assertContains(response, reverse("analyzer:analyze"))

    def test_one_document_explains_the_missing_spread(self):
        self.analyze("Essay", ESSAY)
        response = self.client.get(self.url)
        self.assertContains(response, "there is no spread to show yet")
        self.assertContains(response, "Essay")

    def test_two_documents_show_dots_and_a_range(self):
        self.analyze("Essay", ESSAY)
        self.analyze("Report", REPORT)
        response = self.client.get(self.url)
        self.assertContains(response, "profile-dot")
        self.assertContains(response, "profile-range")
        self.assertContains(response, "Feature scores, not personality judgments.")
        self.assertContains(response, "different genres, not that your writing is inconsistent")

    def test_only_this_users_analyzed_documents_appear(self):
        self.analyze("Essay", ESSAY)
        Analysis.objects.create(user=self.other, title="Theirs", original_text=ESSAY)
        Analysis.objects.create(user=self.user, title="Not analyzed", original_text=ESSAY)
        response = self.client.get(self.url)
        self.assertContains(response, "Essay")
        self.assertNotContains(response, "Theirs")
        self.assertNotContains(response, "Not analyzed")
        self.assertEqual(response.context["profile"]["documents"], 1)

    def test_dots_link_to_their_document(self):
        essay = self.analyze("Essay", ESSAY)
        self.assertContains(self.client.get(self.url), reverse("analyzer:detail", args=[essay.pk]))
