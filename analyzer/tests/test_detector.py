"""Phase 6: the detector interface, the demo scorer, and the trained path."""
import json
import tempfile
from pathlib import Path

from django.test import SimpleTestCase, TestCase, override_settings
from django.contrib.auth.models import User
from django.urls import reverse

from analyzer.models import Analysis
from analyzer.services.detector import (DEMO_NOTICE, BaseDetector, DemoDetector, TrainedDetector,
                                        get_detector, model_path)
from analyzer.services.signals import SIGNALS, contribution

HUMAN_ISH = {f.feature: v for f, v in zip(SIGNALS, [0.0, 0.05, 0.95, 0.10, 0.95, 0.0, 0.55, 0.99, 0.04, 0.02])}
AI_ISH = {f.feature: v for f, v in zip(SIGNALS, [3.0, 0.45, 0.60, 0.45, 0.45, 0.4, 0.15, 0.90, 0.0, 0.0])}


class SignalScalingTests(SimpleTestCase):
    def test_contribution_handles_both_directions_and_clamps(self):
        rising = next(s for s in SIGNALS if s.high > s.low)
        falling = next(s for s in SIGNALS if s.high < s.low)
        self.assertEqual(contribution(rising, rising.low), 0.0)
        self.assertEqual(contribution(rising, rising.high), 1.0)
        self.assertEqual(contribution(falling, falling.low), 0.0)
        self.assertEqual(contribution(falling, falling.high), 1.0)
        self.assertEqual(contribution(rising, rising.high * 10), 1.0)
        self.assertIsNone(contribution(rising, None))

    def test_every_signal_carries_a_caveat(self):
        for signal in SIGNALS:
            self.assertTrue(signal.caveat.endswith("."), signal.key)


class DemoDetectorTests(SimpleTestCase):
    def setUp(self):
        self.detector = DemoDetector()

    def analyze(self, features, words=500):
        return self.detector.analyze(features, word_count=words)

    def test_short_text_gets_insufficient_evidence_and_no_number(self):
        result = self.analyze(AI_ISH, words=40)
        self.assertEqual(result.label, "insufficient_evidence")
        self.assertIsNone(result.probability)
        self.assertIsNone(result.confidence)
        self.assertIn("40 words", result.reasons[0])

    def test_direction_of_the_score(self):
        self.assertLess(self.analyze(HUMAN_ISH).probability, self.analyze(AI_ISH).probability)

    def test_it_is_deterministic(self):
        self.assertEqual(self.analyze(AI_ISH).probability, self.analyze(AI_ISH).probability)

    def test_always_marked_as_a_demo(self):
        result = self.analyze(AI_ISH)
        self.assertTrue(result.is_demo)
        self.assertEqual(result.notice, DEMO_NOTICE)
        self.assertEqual(result.model_version, "demo-0.1")

    def test_confidence_rises_with_length(self):
        short = self.analyze(AI_ISH, words=160)
        long = self.analyze(AI_ISH, words=900)
        self.assertLess(short.confidence, long.confidence)
        self.assertIn("confidence rises", short.reasons[0])

    def test_disagreeing_families_lower_confidence(self):
        mixed = {**HUMAN_ISH, "formulaic_phrases_per_100": 3.0, "marker_initial_ratio": 0.45}
        agreeing = self.analyze(HUMAN_ISH, words=900)
        disagreeing = self.analyze(mixed, words=900)
        self.assertLess(disagreeing.confidence, agreeing.confidence)
        self.assertIn("disagree", " ".join(disagreeing.reasons))

    def test_low_confidence_reports_uncertain_rather_than_a_band(self):
        result = self.analyze(AI_ISH, words=160)
        if result.confidence < DemoDetector.UNCERTAIN_BELOW:
            self.assertEqual(result.label, "uncertain")

    def test_probability_and_confidence_are_independent(self):
        """Same text characteristics, different amount of evidence: the estimate
        must not move, but how much it can be trusted must."""
        short = self.analyze(AI_ISH, words=160)
        long = self.analyze(AI_ISH, words=900)
        self.assertEqual(short.probability, long.probability)
        self.assertLess(short.confidence, long.confidence)
        for result in (short, long):
            self.assertAlmostEqual(result.confidence + result.uncertainty, 1.0, places=3)

    def test_missing_features_reduce_coverage_then_refuse(self):
        partial = self.analyze({"formulaic_phrases_per_100": 3.0}, words=900)
        self.assertEqual(partial.label, "insufficient_evidence")

    def test_no_result_claims_certainty(self):
        for features in (HUMAN_ISH, AI_ISH):
            result = self.analyze(features)
            text = " ".join([result.label, *result.reasons, *(s.text for s in result.signals)]).lower()
            for phrase in ["definitely", "certainly", "proves", "written by ai"]:
                self.assertNotIn(phrase, text)


class DetectorSelectionTests(SimpleTestCase):
    def setUp(self):
        get_detector.__wrapped__ if hasattr(get_detector, "__wrapped__") else None

    def test_demo_is_used_when_no_model_is_trained(self):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(DETECTOR_MODEL_PATH=str(Path(tmp) / "missing.joblib")):
                self.assertIsInstance(get_detector(), DemoDetector)

    def test_trained_backend_fails_loudly_when_the_model_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(DETECTOR_BACKEND="trained", DETECTOR_MODEL_PATH=str(Path(tmp) / "missing.joblib")), \
                    self.assertRaises(FileNotFoundError):
                get_detector()

    def test_a_custom_detector_satisfies_the_interface(self):
        class AlwaysUncertain(BaseDetector):
            version, is_demo = "test-1", False

            def analyze(self, features, *, word_count):
                from analyzer.services.detector import DetectionResult
                return DetectionResult("uncertain", 0.5, 0.1, 0.9, self.version, False)

        result = AlwaysUncertain().analyze({}, word_count=500)
        self.assertEqual((result.label, result.model_version), ("uncertain", "test-1"))


class TrainedDetectorTests(SimpleTestCase):
    """Trains a real model on synthetic data: this proves the machinery works
    end to end. It says nothing about accuracy on real text."""

    def build_model(self, tmp: Path) -> Path:
        from ml.training.train_baseline import train
        rows = []
        for i in range(30):
            rows.append({"label": "human", "text": " ".join(
                f"Sentence {i} number {j} wanders somewhere new with unusual words like turmeric and tamarind." for j in range(12))})
            rows.append({"label": "ai", "text": " ".join(
                "It is important to note that the system provides many benefits for all users." for _ in range(12))})
        data = tmp / "labelled.jsonl"
        data.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        report = train(data, tmp / "model.joblib", version="test-baseline")
        self.assertGreater(report.examples, 20)
        return tmp / "model.joblib"

    def test_train_then_load_then_predict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.build_model(Path(tmp))
            detector = TrainedDetector(path)
            self.assertFalse(detector.is_demo)
            self.assertEqual(detector.version, "test-baseline")
            self.assertIn("accuracy", detector.metrics)
            self.assertTrue(detector.feature_names)

            from analyzer.services.pipeline import run_pipeline
            features = run_pipeline(" ".join(
                "It is important to note that the system provides many benefits for all users." for _ in range(20))).features
            result = detector.analyze(features, word_count=int(features["word_count"]))
            self.assertIsNotNone(result.probability)
            self.assertFalse(result.is_demo)
            self.assertEqual(result.model_version, "test-baseline")

    def test_training_refuses_tiny_or_unbalanced_data(self):
        from ml.training.train_baseline import train
        with tempfile.TemporaryDirectory() as tmp:
            tiny = Path(tmp) / "tiny.jsonl"
            tiny.write_text(json.dumps({"text": "Hello there.", "label": "human"}), encoding="utf-8")
            with self.assertRaisesMessage(ValueError, "at least 20"):
                train(tiny, Path(tmp) / "m.joblib")

            rows = [{"text": f"Document number {i} with some words in it.", "label": "human"} for i in range(24)]
            rows += [{"text": "One lonely ai document.", "label": "ai"}]
            unbalanced = Path(tmp) / "unbalanced.jsonl"
            unbalanced.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
            with self.assertRaisesMessage(ValueError, "Unbalanced"):
                train(unbalanced, Path(tmp) / "m.joblib")

    def test_training_rejects_bad_labels(self):
        from ml.training.train_baseline import train
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.jsonl"
            bad.write_text(json.dumps({"text": "Hi.", "label": "maybe"}), encoding="utf-8")
            with self.assertRaisesMessage(ValueError, "must be 'human' or 'ai'"):
                train(bad, Path(tmp) / "m.joblib")


class DetectionInPipelineTests(TestCase):
    TEXT = ("My grandmother kept her recipes on the backs of electricity bills. Half of them are unreadable now. "
            "I still can't make her dal taste right. ") * 12

    def setUp(self):
        self.user = User.objects.create_user("ayesha", password="pw-123-long-enough")
        self.client.force_login(self.user)

    def test_saving_stores_a_result_and_sentence_scores(self):
        self.client.post(reverse("analyzer:analyze"), {"text": self.TEXT})
        analysis = Analysis.objects.get()
        self.assertTrue(analysis.result_label)
        self.assertTrue(analysis.is_demo)
        self.assertEqual(analysis.model_version, "demo-0.1")
        self.assertIsNotNone(analysis.ai_probability)
        self.assertTrue(analysis.sentences.exclude(ai_probability=None).exists())

    def test_result_page_shows_the_demo_notice_and_never_claims_certainty(self):
        self.client.post(reverse("analyzer:analyze"), {"text": self.TEXT})
        page = self.client.get(reverse("analyzer:detail", args=[Analysis.objects.get().pk]))
        self.assertContains(page, "DEMO ANALYSIS")
        self.assertContains(page, "Signal breakdown")
        self.assertContains(page, "Sentence heatmap")
        self.assertContains(page, "characteristics associated with AI-generated examples")
        self.assertNotContains(page, "definitely")
        self.assertNotContains(page, "written by AI.")

    def test_short_document_shows_insufficient_evidence(self):
        self.client.post(reverse("analyzer:analyze"), {"text": "A very short note about nothing much at all."})
        analysis = Analysis.objects.get()
        self.assertEqual(analysis.result_label, "insufficient_evidence")
        self.assertIsNone(analysis.ai_probability)
        page = self.client.get(reverse("analyzer:detail", args=[analysis.pk]))
        self.assertContains(page, "Insufficient evidence")
        self.assertContains(page, "at least 150 are needed")
