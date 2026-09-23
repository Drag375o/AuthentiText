"""Phase 5: statistical, semantic and stylometric features."""
import math
from unittest import mock

from django.test import SimpleTestCase, TestCase, override_settings

from analyzer.services import embeddings
from analyzer.services.embeddings import BaseEmbedder, TfidfEmbedder, get_embedder
from analyzer.services.preprocessing import preprocess
from analyzer.services.semantics import MIN_SENTENCES, compute_semantics
from analyzer.services.statistics_features import (burstiness, compute_statistics, ngram_repeat_rate,
                                                   normalized_entropy, shannon_entropy, zipf_slope)
from analyzer.services.stylometry import PROFILE_DIMENSIONS, build_profile, compute_stylometry, scale
from analyzer.services.syntax import compute_syntax

from collections import Counter

EVEN = ("The system provides many benefits. The system offers many benefits. The system supports many features. "
        "The system enables many functions. The system delivers many results.")
VARIED = ("My grandmother kept her recipes on the backs of electricity bills. Half are unreadable. Turmeric. "
          "I still can't make her dal taste right, though I have tried for years in three cities. Nobody measured.")


class EntropyAndBurstinessTests(SimpleTestCase):
    def test_entropy_of_known_distributions(self):
        self.assertEqual(shannon_entropy(Counter("aaaa")), 0.0)          # one symbol
        self.assertEqual(shannon_entropy(Counter("ab")), 1.0)            # two equal symbols: 1 bit
        self.assertEqual(shannon_entropy(Counter("abcd")), 2.0)          # four equal symbols: 2 bits
        self.assertIsNone(shannon_entropy(Counter()))

    def test_normalized_entropy_is_one_when_all_words_are_distinct(self):
        self.assertAlmostEqual(normalized_entropy(Counter("abcd")), 1.0)
        self.assertLess(normalized_entropy(Counter("aaab")), 1.0)

    def test_burstiness_scale(self):
        self.assertEqual(burstiness([10, 10, 10, 10]), -1.0)             # perfectly regular
        self.assertGreater(burstiness([1, 1, 30, 1, 40]), 0)             # bursty
        self.assertIsNone(burstiness([5, 5]))                            # too few sentences

    def test_ngram_repeat_rate_by_hand(self):
        # "a b a b": bigrams (a,b) x2, (b,a) x1 -> 2 of 3 are repeats
        self.assertAlmostEqual(ngram_repeat_rate(["a", "b", "a", "b"], 2), 2 / 3)
        self.assertEqual(ngram_repeat_rate(["a", "b", "c"], 2), 0.0)
        self.assertIsNone(ngram_repeat_rate(["a"], 2))

    def test_zipf_slope_is_negative_and_needs_vocabulary(self):
        counts = Counter({f"w{i}": 100 // (i + 1) for i in range(15)})
        self.assertLess(zipf_slope(counts), 0)
        self.assertIsNone(zipf_slope(Counter("abc")))

    def test_formulaic_text_is_more_predictable_than_varied_text(self):
        even, _ = compute_statistics(preprocess(EVEN))
        varied, _ = compute_statistics(preprocess(VARIED))
        self.assertLess(even["word_entropy"], varied["word_entropy"])
        self.assertGreater(even["bigram_repeat_rate"], varied["bigram_repeat_rate"])
        self.assertLess(even["sentence_length_burstiness"], varied["sentence_length_burstiness"])

    def test_distinctive_terms_prefer_rare_words(self):
        _, details = compute_statistics(preprocess(VARIED))
        terms = [t["term"].lower() for t in details["distinctive_terms"]]
        self.assertIn("turmeric", terms)
        self.assertNotIn("year", terms[:3])

    def test_a_repeated_common_word_does_not_outrank_a_rare_specific_one(self):
        """Regression: linear term frequency let "useful" (repeated, ordinary) beat
        "LoRaWAN" (rare, specific). Sublinear damping fixes the ranking."""
        text = ("LoRaWAN is useful for sensors. Zigbee is useful for lighting. "
                "Wi-Fi is useful for video. Bluetooth is useful for headphones.")
        _, details = compute_statistics(preprocess(text))
        terms = [t["term"].lower() for t in details["distinctive_terms"]]
        self.assertLess(terms.index("lorawan"), terms.index("useful"))
        self.assertLess(terms.index("zigbee"), terms.index("useful"))

    def test_terms_are_shown_as_they_appear_not_as_dictionary_forms(self):
        """Regression: the lemma of "data" is "datum", which nobody writes."""
        _, details = compute_statistics(preprocess(
            "The data from the sensors is noisy. Sensor data arrives late. Better data helps."))
        self.assertIn("data", [t["term"] for t in details["distinctive_terms"]])
        self.assertNotIn("datum", [t["term"] for t in details["distinctive_terms"]])


class SemanticTests(SimpleTestCase):
    def test_identical_sentences_reach_full_similarity(self):
        features, _ = compute_semantics(preprocess("The cat sat. The cat sat. A dog barked loudly. Rain fell today."))
        self.assertAlmostEqual(features["max_sentence_similarity"], 1.0, places=5)

    def test_redundant_text_scores_higher_than_varied_text(self):
        redundant, _ = compute_semantics(preprocess(EVEN))
        varied, _ = compute_semantics(preprocess(VARIED))
        self.assertGreater(redundant["semantic_redundancy"], varied["semantic_redundancy"])
        self.assertLess(redundant["semantic_diversity"], varied["semantic_diversity"])

    def test_unrelated_sentences_are_not_reported_as_similar(self):
        features, details = compute_semantics(preprocess(VARIED))
        self.assertLess(features["max_sentence_similarity"], 0.5)
        self.assertEqual([p for p in details["similar_pairs"] if p["near_duplicate"]], [])

    def test_short_documents_return_none_rather_than_a_guess(self):
        features, details = compute_semantics(preprocess("One. Two. Three."))
        self.assertIsNone(features["local_coherence"])
        self.assertIn(str(MIN_SENTENCES), details["semantics_skipped"])

    def test_result_records_which_backend_produced_it(self):
        _, details = compute_semantics(preprocess(VARIED))
        self.assertEqual(details["embedding_backend"], "tfidf")
        self.assertFalse(details["embedding_captures_paraphrase"])


class EmbedderSelectionTests(SimpleTestCase):
    def setUp(self):
        get_embedder.cache_clear()
        self.addCleanup(get_embedder.cache_clear)

    def test_encoded_rows_are_unit_length(self):
        import numpy as np
        vectors = TfidfEmbedder().encode(["the cat sat", "a dog barked", "the cat sat again"])
        self.assertTrue(np.allclose(np.linalg.norm(vectors, axis=1), 1.0))

    def test_tfidf_backend_is_forced(self):
        with override_settings(EMBEDDING_BACKEND="tfidf"):
            self.assertIsInstance(get_embedder(), TfidfEmbedder)

    def test_auto_falls_back_when_the_transformer_is_unavailable(self):
        with override_settings(EMBEDDING_BACKEND="auto"), \
                mock.patch.object(embeddings, "SentenceTransformerEmbedder", side_effect=ImportError("not installed")):
            self.assertIsInstance(get_embedder(), TfidfEmbedder)

    def test_explicit_transformer_backend_fails_loudly(self):
        with override_settings(EMBEDDING_BACKEND="sentence-transformers"), \
                mock.patch.object(embeddings, "SentenceTransformerEmbedder", side_effect=ImportError("not installed")), \
                self.assertRaises(ImportError):
            get_embedder()

    def test_a_custom_embedder_is_used_end_to_end(self):
        """Proves the adapter is swappable without touching the analysis code."""
        import numpy as np

        class ConstantEmbedder(BaseEmbedder):
            key, label, description = "constant", "Constant", "Test double."
            redundancy_threshold = 0.5

            def encode(self, texts):
                return np.ones((len(texts), 3)) / math.sqrt(3)   # every sentence identical

        with mock.patch.object(embeddings, "get_embedder", return_value=ConstantEmbedder()), \
                mock.patch("analyzer.services.semantics.get_embedder", return_value=ConstantEmbedder()):
            features, details = compute_semantics(preprocess(VARIED))
        self.assertEqual(details["embedding_backend"], "constant")
        self.assertAlmostEqual(features["semantic_redundancy"], 1.0)
        self.assertAlmostEqual(features["semantic_diversity"], 0.0, places=5)


class StylometryTests(SimpleTestCase):
    def measure(self, text):
        doc = preprocess(text)
        return compute_stylometry(doc, compute_syntax(doc))

    def test_formality_separates_registers(self):
        casual = self.measure("I can't believe we did it. We were so tired, but we kept going.")
        formal = self.measure("The experimental results indicate a significant correlation between the variables.")
        self.assertLess(casual["formality_score"], 40)
        self.assertGreater(formal["formality_score"], 60)

    def test_personal_voice_markers(self):
        casual = self.measure("I can't believe we did it. My hands were shaking.")
        self.assertGreater(casual["first_person_ratio"], 0.2)
        self.assertGreater(casual["contraction_ratio"], 0)
        self.assertEqual(self.measure("The door was opened.")["first_person_ratio"], 0)

    def test_scale_clamps_and_interpolates(self):
        self.assertEqual(scale(0.55, 0.55, 0.85), 0)
        self.assertEqual(scale(0.70, 0.55, 0.85), 50)
        self.assertEqual(scale(0.99, 0.55, 0.85), 100)
        self.assertEqual(scale(0.10, 0.55, 0.85), 0)
        self.assertIsNone(scale(None, 0, 1))

    def test_profile_covers_every_dimension_and_tolerates_missing_features(self):
        profile = build_profile({"mattr": 0.7})
        self.assertEqual(len(profile), len(PROFILE_DIMENSIONS))
        self.assertEqual(profile[0]["score"], 50)
        self.assertIsNone(profile[1]["score"])
        for dimension in profile:
            self.assertTrue(dimension["description"].endswith("."))


class DisplayPrecisionTests(SimpleTestCase):
    """Regression: rounding hid real differences when comparing two documents."""

    def test_small_percentages_keep_a_decimal(self):
        from analyzer.templatetags.analysis_format import feature_display
        self.assertEqual(feature_display(0.012, "ratio"), "1.2%")
        self.assertEqual(feature_display(0.006, "ratio"), "0.6%")
        self.assertEqual(feature_display(0.235, "ratio"), "24%")
        self.assertEqual(feature_display(0.0, "ratio"), "0%")

    def test_small_numbers_are_not_rounded_to_zero(self):
        from analyzer.templatetags.analysis_format import feature_display
        self.assertEqual(feature_display(-0.04, "number"), "-0.04")
        self.assertEqual(feature_display(-0.31, "number"), "-0.31")
        self.assertEqual(feature_display(6.47, "number"), "6.5")


class UnavailableFeatureTests(TestCase):
    """A blank value must say why it is blank: an em dash alone reads as a broken page."""

    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user("ayesha", password="pw-123-long-enough")
        self.client.force_login(self.user)

    def test_single_paragraph_explains_the_missing_opening_closing_measure(self):
        from django.urls import reverse
        from analyzer.models import Analysis
        text = ("The dataset was partitioned into training and test sets for our experiments. "
                "We applied stratified sampling to keep the class balance across all splits. "
                "The result is reported in the table below. Every annotation dimension is covered. ") * 3
        self.client.post(reverse("analyzer:analyze"), {"text": text})
        analysis = Analysis.objects.get()
        self.assertEqual(analysis.paragraph_count, 1)
        page = self.client.get(reverse("analyzer:detail", args=[analysis.pk]))
        self.assertContains(page, "Not measured")
        self.assertContains(page, "a single-paragraph text has no separate opening and closing")

    def test_every_nullable_feature_has_a_reason(self):
        """Any feature the pipeline can leave as None must explain itself."""
        from analyzer.services.features import BY_NAME
        from analyzer.services.pipeline import run_pipeline
        result = run_pipeline("One short line. Another one here.")
        missing = [name for name, value in result.features.items()
                   if value is None and not BY_NAME[name].unavailable]
        self.assertEqual(missing, [])
