"""
Detector interface and implementations.

    BaseDetector          the contract: features in, DetectionResult out
    DemoDetector          deterministic heuristics over measured features.
                          Labelled DEMO everywhere it appears. Not trained on
                          anything, so it has no measured accuracy and never
                          claims one.
    TrainedDetector       a scikit-learn model loaded from ml/models/. Available
                          only when a model file exists; nothing is faked when
                          it doesn't.
    get_detector()        returns the trained model if present, else the demo.

Vocabulary, kept strictly separate:
    probability   the estimated AI-associated signal, 0-1
    confidence    how much the evidence supports that estimate, 0-1
    uncertainty   1 - confidence, reported alongside it

Below ANALYSIS_MIN_WORDS the result is INSUFFICIENT_EVIDENCE with no
probability at all, rather than a number nobody should rely on.
"""
from __future__ import annotations

import logging
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path

from django.conf import settings

from .signals import FAMILIES, FAMILY_DESCRIPTIONS, SIGNALS, Signal, contribution


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))

logger = logging.getLogger("authentitext")

DEMO_VERSION = "demo-0.1"
DEMO_NOTICE = "DEMO ANALYSIS \u2014 not a real prediction"
MIN_SIGNALS = 5              # below this, evidence is too thin to combine
FULL_EVIDENCE_WORDS = 400    # confidence from length saturates here


@dataclass
class SignalScore:
    key: str
    family: str
    family_label: str
    label: str
    feature: str
    value: float | None
    score: float | None      # 0-1 contribution toward the AI-associated signal
    weight: float
    text: str
    caveat: str


@dataclass
class DetectionResult:
    label: str                      # Analysis.ResultLabel value
    probability: float | None
    confidence: float | None
    uncertainty: float | None
    model_version: str
    is_demo: bool
    notice: str = ""
    reasons: list[str] = field(default_factory=list)
    families: list[dict] = field(default_factory=list)
    signals: list[SignalScore] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {**asdict(self), "signals": [asdict(s) for s in self.signals]}


class BaseDetector:
    """Every detector takes the measured features and returns a DetectionResult."""

    version: str = ""
    is_demo: bool = False

    def analyze(self, features: dict[str, float | None], *, word_count: int) -> DetectionResult:
        raise NotImplementedError

    def sentence_scores(self, sentences: list[dict], features: dict,
                        document_probability: float | None = None) -> list[dict]:
        """One {"score": float | None, "reasons": [str]} per sentence."""
        return [{"score": None, "reasons": []} for _ in sentences]


def insufficient(word_count: int, version: str, is_demo: bool, reasons: list[str]) -> DetectionResult:
    return DetectionResult(
        label="insufficient_evidence", probability=None, confidence=None, uncertainty=None,
        model_version=version, is_demo=is_demo, reasons=reasons,
    )


class DemoDetector(BaseDetector):
    """
    Deterministic, transparent, and explicitly not a trained model.

    Each signal in signals.py contributes a 0-1 value; the score is their
    weighted mean. Confidence combines how much text there is, how many signals
    could be measured, and how much the signal families agree. Wide disagreement
    lowers confidence, which is the honest response to mixed evidence.
    """

    version = DEMO_VERSION
    is_demo = True

    LABEL_BANDS = [(0.34, "likely_human"), (0.52, "possibly_ai_assisted"), (1.01, "likely_ai_associated")]
    UNCERTAIN_BELOW = 0.45   # confidence under this reports "uncertain" instead of a band
    # Per-sentence repetition anchors: a type-token ratio at or above LOW
    # contributes nothing, at or below HIGH contributes fully.
    SENTENCE_REPETITION_LOW = 0.75
    SENTENCE_REPETITION_HIGH = 0.45

    def score_signals(self, features: dict[str, float | None]) -> list[SignalScore]:
        scored = []
        for signal in SIGNALS:
            value = features.get(signal.feature)
            score = contribution(signal, value)
            text = signal.high_text if (score or 0) >= 0.5 else signal.low_text
            scored.append(SignalScore(
                key=signal.key, family=signal.family, family_label=FAMILIES[signal.family],
                label=signal.label, feature=signal.feature, value=value, score=score,
                weight=signal.weight, text=text, caveat=signal.caveat,
            ))
        return scored

    @staticmethod
    def weighted_mean(scores: list[SignalScore]) -> float | None:
        usable = [s for s in scores if s.score is not None]
        total = sum(s.weight for s in usable)
        if not total:
            return None
        return sum(s.score * s.weight for s in usable) / total

    def family_scores(self, scores: list[SignalScore]) -> list[dict]:
        families = []
        for key, label in FAMILIES.items():
            members = [s for s in scores if s.family == key and s.score is not None]
            families.append({
                "key": key, "label": label, "description": FAMILY_DESCRIPTIONS[key],
                "score": self.weighted_mean(members) if members else None,
                "signals": [s.key for s in members],
            })
        return families

    def confidence_from(self, word_count: int, scores: list[SignalScore], families: list[dict]) -> tuple[float, list[str]]:
        reasons = []
        usable = [s for s in scores if s.score is not None]
        length_factor = min(1.0, word_count / FULL_EVIDENCE_WORDS)
        if length_factor < 1.0:
            reasons.append(f"Only {word_count} words; confidence rises up to about {FULL_EVIDENCE_WORDS}.")

        coverage = len(usable) / len(SIGNALS)
        if coverage < 1.0:
            missing = [s.label for s in scores if s.score is None]
            reasons.append(f"Could not measure: {', '.join(missing)}.")

        family_values = [f["score"] for f in families if f["score"] is not None]
        spread = statistics.pstdev(family_values) if len(family_values) > 1 else 0.0
        agreement = max(0.0, 1.0 - spread * 2)
        if agreement < 0.6:
            reasons.append("Signal families disagree with one another.")

        confidence = length_factor * 0.4 + coverage * 0.2 + agreement * 0.4
        return round(min(1.0, confidence), 3), reasons

    def label_for(self, probability: float, confidence: float) -> str:
        if confidence < self.UNCERTAIN_BELOW:
            return "uncertain"
        for ceiling, label in self.LABEL_BANDS:
            if probability < ceiling:
                return label
        return "likely_ai_associated"

    def analyze(self, features: dict[str, float | None], *, word_count: int) -> DetectionResult:
        minimum = settings.ANALYSIS_MIN_WORDS
        if word_count < minimum:
            return insufficient(word_count, self.version, True, [
                f"This text has {word_count} words; at least {minimum} are needed for a usable estimate.",
                "Short texts do not contain enough variation in sentence length, vocabulary or structure to measure.",
            ])

        scores = self.score_signals(features)
        probability = self.weighted_mean(scores)
        if probability is None or len([s for s in scores if s.score is not None]) < MIN_SIGNALS:
            return insufficient(word_count, self.version, True,
                                ["Too few signals could be measured in this text."])

        families = self.family_scores(scores)
        confidence, reasons = self.confidence_from(word_count, scores, families)
        return DetectionResult(
            label=self.label_for(probability, confidence),
            probability=round(probability, 3),
            confidence=confidence,
            uncertainty=round(1 - confidence, 3),
            model_version=self.version,
            is_demo=True,
            notice=DEMO_NOTICE,
            reasons=reasons,
            families=families,
            signals=scores,
        )

    SENTENCE_MIN_WORDS = 3            # below this there is nothing to measure
    NEIGHBOUR_LOW = 0.20              # similarity to the closest other sentence
    NEIGHBOUR_HIGH = 0.70
    LENGTH_MATCH_WITHIN = 0.20        # a length within 20% of the mean counts as conforming
    EVEN_DOCUMENT_CV = 0.40           # ... but only matters when the document is unusually even
    BASELINE_REASON = ("Marked at the document's overall level: nothing in this sentence itself stands out.")

    def sentence_evidence(self, sentence: dict, features: dict) -> tuple[float, list[str]] | None:
        """
        How much of the document's signal this one sentence carries, 0-1, and
        why. Only things measurable inside a single sentence, or the sentence's
        own part in a document-wide pattern: stock phrases and discourse
        markers, repetition within the sentence, ordinary vocabulary, an opening
        shared with other sentences, a length matching the document average, and
        resemblance to its closest neighbour.
        """
        signals = sentence["signals"]
        if signals["words"] < self.SENTENCE_MIN_WORDS:
            return None

        parts: list[tuple[float, float, str]] = []   # (value, weight, reason when it counts)

        markers = signals.get("markers") or []
        if "academic_formula" in markers:
            parts.append((1.0, 1.0, "Contains a stock phrase from the pattern library."))
        else:
            parts.append((0.5 if markers else 0.0, 1.0, "Contains a discourse marker."))

        ratio = signals.get("type_token_ratio")
        span = self.SENTENCE_REPETITION_LOW - self.SENTENCE_REPETITION_HIGH
        repetition = 0.0 if ratio is None else clamp01((self.SENTENCE_REPETITION_LOW - ratio) / span)
        parts.append((repetition, 0.8, "Words repeat within the sentence."))

        parts.append((0.0 if signals.get("rare_words") else 1.0, 0.5, "No uncommon vocabulary."))

        parts.append((1.0 if signals.get("repeated_opening") else 0.0, 0.6,
                      "Begins with the same two words as another sentence."))

        # Conforming to the average only means something when the document's
        # lengths are unusually even; in varied prose it is unremarkable.
        mean_length = features.get("sentence_length_mean") or 0
        variation = features.get("sentence_length_cv")
        if mean_length and variation is not None and variation < self.EVEN_DOCUMENT_CV:
            distance = abs(signals["words"] - mean_length) / mean_length
            parts.append((clamp01(1 - distance), 0.6,
                          "Its length matches the average, in a document of unusually even sentences."
                          if distance <= self.LENGTH_MATCH_WITHIN else ""))

        similarity = signals.get("closest_similarity")
        neighbour = 0.0 if similarity is None else clamp01(
            (similarity - self.NEIGHBOUR_LOW) / (self.NEIGHBOUR_HIGH - self.NEIGHBOUR_LOW))
        parts.append((neighbour, 0.8, "Very close in meaning to another sentence."))

        total = sum(weight for _, weight, _ in parts)
        evidence = sum(value * weight for value, weight, _ in parts) / total
        reasons = [reason for value, _, reason in parts if reason and value >= 0.5]
        return evidence, reasons

    def sentence_scores(self, sentences: list[dict], features: dict,
                        document_probability: float | None = None) -> list[dict]:
        """
        Per-sentence marks, centred on the document's own score.

        The evidence above says which sentences carry more of the signal than
        their neighbours; the document score says how strong that signal is
        overall. Combining them means the marks show *where* a document's signal
        sits without ever contradicting the headline: a document at 11% has
        mostly low marks, one at 45% has marks spread either side of 45%.
        """
        empty = [{"score": None, "reasons": []} for _ in sentences]
        if document_probability is None:
            return empty

        measured = [self.sentence_evidence(sentence, features) for sentence in sentences]
        values = [entry[0] for entry in measured if entry is not None]
        if not values:
            return empty

        average = sum(values) / len(values)
        results = []
        for entry in measured:
            if entry is None:
                results.append({"score": None, "reasons": ["Too short to measure on its own."]})
                continue
            evidence, reasons = entry
            score = round(clamp01(document_probability + (evidence - average)), 3)
            results.append({"score": score, "reasons": reasons or [self.BASELINE_REASON]})
        return results

    def heatmap_note(self, result: DetectionResult) -> str:
        """
        Explains a quiet heatmap under a document that scored highly.

        Some evidence belongs to the whole set, not to any sentence: how evenly
        lengths are spread, how far meanings travel across the text, whether
        contractions appear anywhere at all. When most of the score comes from
        those, the interface says so rather than spreading the blame evenly.
        """
        scored = [s for s in result.signals if s.score is not None]
        if not scored or result.probability is None:
            return ""
        weighted = {s.key: s.score * s.weight for s in scored}
        total = sum(weighted.values())
        if total <= 0:
            return ""
        local_keys = {s.key for s in SIGNALS if s.local}
        diffuse = sum(value for key, value in weighted.items() if key not in local_keys) / total
        if diffuse < 0.55:
            return ""
        names = sorted(((s.label, weighted[s.key]) for s in scored
                        if s.key not in local_keys and weighted[s.key] > 0), key=lambda pair: -pair[1])[:3]
        if not names:
            return ""
        listed = ", ".join(label.lower() for label, _ in names)
        return (f"Most of this document's signal comes from patterns across the whole text "
                f"({listed}) rather than from anything inside a particular sentence.")


class TrainedDetector(BaseDetector):
    """
    A trained scikit-learn classifier (see ml/training/train_baseline.py).

    The bundle records the exact feature order and the metrics measured on a
    held-out split, so the interface can report real performance instead of a
    claim. Raises FileNotFoundError when no model has been trained.
    """

    is_demo = False

    def __init__(self, path: Path):
        import joblib

        bundle = joblib.load(path)
        self.model = bundle["model"]
        self.feature_names: list[str] = bundle["feature_names"]
        self.metrics: dict = bundle.get("metrics", {})
        self.version = bundle.get("version", "trained-unknown")
        self.trained_on = bundle.get("trained_on", "")

    def analyze(self, features: dict[str, float | None], *, word_count: int) -> DetectionResult:
        minimum = settings.ANALYSIS_MIN_WORDS
        if word_count < minimum:
            return insufficient(word_count, self.version, False, [
                f"This text has {word_count} words; at least {minimum} are needed for a usable estimate.",
            ])
        missing = [name for name in self.feature_names if features.get(name) is None]
        if missing:
            return insufficient(word_count, self.version, False,
                                [f"Could not measure {len(missing)} of the features this model needs."])

        row = [[float(features[name]) for name in self.feature_names]]
        probability = float(self.model.predict_proba(row)[0][1])
        # Confidence from how far the estimate sits from the undecided middle,
        # tempered by the model's own measured accuracy.
        separation = abs(probability - 0.5) * 2
        accuracy = float(self.metrics.get("accuracy", 0.5))
        confidence = round(min(1.0, separation * accuracy), 3)
        label = ("likely_ai_associated" if probability >= 0.65 else
                 "possibly_ai_assisted" if probability >= 0.45 else "likely_human")
        if confidence < 0.45:
            label = "uncertain"
        return DetectionResult(
            label=label, probability=round(probability, 3), confidence=confidence,
            uncertainty=round(1 - confidence, 3), model_version=self.version, is_demo=False,
            reasons=[f"Trained on {self.trained_on}." if self.trained_on else ""],
        )


def model_path() -> Path:
    return Path(getattr(settings, "DETECTOR_MODEL_PATH", "") or Path(settings.BASE_DIR) / "ml" / "models" / "baseline.joblib")


def get_detector() -> BaseDetector:
    """The trained model when one exists, otherwise the clearly labelled demo."""
    backend = getattr(settings, "DETECTOR_BACKEND", "auto")
    path = model_path()
    if backend in ("auto", "trained"):
        try:
            detector = TrainedDetector(path)
            logger.info("Detector: %s", detector.version)
            return detector
        except FileNotFoundError:
            if backend == "trained":
                raise
        except Exception:
            logger.exception("Could not load the trained detector at %s", path)
            if backend == "trained":
                raise
    return DemoDetector()
