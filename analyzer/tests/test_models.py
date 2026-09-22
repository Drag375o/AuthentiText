from django.contrib.auth.models import AnonymousUser, User
from django.db import IntegrityError, transaction
from django.test import TestCase

from analyzer.models import Analysis, Feature, SentenceAnalysis, hash_text


def make_analysis(user, text="The quick brown fox jumps over the lazy dog.", **extra):
    return Analysis.objects.create(user=user, original_text=text, **extra)


class AnalysisModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("a", password="x")

    def test_text_hash_is_computed_on_save(self):
        analysis = make_analysis(self.user, text="Hello world.")
        self.assertEqual(analysis.text_hash, hash_text("Hello world."))
        self.assertEqual(len(analysis.text_hash), 64)

    def test_original_text_is_stored_verbatim(self):
        raw = "  Tabs\tand\n\nnewlines  kept.  \u00e9 "
        analysis = make_analysis(self.user, text=raw)
        analysis.refresh_from_db()
        self.assertEqual(analysis.original_text, raw)

    def test_uuid_primary_key(self):
        self.assertEqual(len(str(make_analysis(self.user).pk)), 36)

    def test_display_name_fallbacks(self):
        self.assertEqual(make_analysis(self.user, title="Essay").display_name, "Essay")
        self.assertEqual(make_analysis(self.user, filename="draft.docx").display_name, "draft.docx")
        self.assertTrue(make_analysis(self.user, text="one two three four five six seven").display_name.endswith("\u2026"))

    def test_probabilities_are_constrained_to_unit_interval(self):
        for field in ("ai_probability", "confidence", "uncertainty"):
            with self.subTest(field=field), self.assertRaises(IntegrityError), transaction.atomic():
                make_analysis(self.user, **{field: 1.5})

    def test_insufficient_evidence_stores_no_probability(self):
        analysis = make_analysis(self.user, result_label=Analysis.ResultLabel.INSUFFICIENT_EVIDENCE)
        self.assertIsNone(analysis.ai_probability)

    def test_newest_first(self):
        first, second = make_analysis(self.user), make_analysis(self.user)
        self.assertEqual(list(Analysis.objects.all()), [second, first])

    def test_for_user_scopes_and_hides_from_anonymous(self):
        other = User.objects.create_user("b", password="x")
        mine, theirs = make_analysis(self.user), make_analysis(other)
        self.assertEqual(list(Analysis.objects.for_user(self.user)), [mine])
        self.assertNotIn(theirs, Analysis.objects.for_user(self.user))
        self.assertEqual(Analysis.objects.for_user(AnonymousUser()).count(), 0)


class ChildModelTests(TestCase):
    def setUp(self):
        self.analysis = make_analysis(User.objects.create_user("a", password="x"))

    def test_sentence_index_unique_per_analysis(self):
        SentenceAnalysis.objects.create(analysis=self.analysis, sentence_index=0, text="A.", start_char=0, end_char=2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SentenceAnalysis.objects.create(analysis=self.analysis, sentence_index=0, text="B.", start_char=3, end_char=5)

    def test_sentence_span_must_be_ordered(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SentenceAnalysis.objects.create(analysis=self.analysis, sentence_index=1, text="x", start_char=9, end_char=2)

    def test_feature_name_unique_per_analysis(self):
        Feature.objects.create(analysis=self.analysis, feature_name="ttr", feature_value=0.7, category="lexical")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Feature.objects.create(analysis=self.analysis, feature_name="ttr", feature_value=0.6, category="lexical")

    def test_deleting_analysis_cascades(self):
        SentenceAnalysis.objects.create(analysis=self.analysis, sentence_index=0, text="A.", start_char=0, end_char=2)
        Feature.objects.create(analysis=self.analysis, feature_name="ttr", feature_value=0.7, category="lexical")
        self.analysis.delete()
        self.assertEqual(SentenceAnalysis.objects.count() + Feature.objects.count(), 0)
