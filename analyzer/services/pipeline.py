"""
The analysis pipeline: text in, features out, saved to the database.

run_pipeline() is pure (no database), so it can be tested and reused directly.
analyze_document() runs it for a saved Analysis and stores the results in one
transaction. On any error it logs the details, marks the analysis as failed,
and never exposes internals to the user.

    original text
      -> preprocess (paragraphs, spaCy per paragraph, English check)
      -> document statistics
      -> lexical features
      -> syntactic features (POS, parse depth, clauses, voice)
      -> discourse markers, formulaic phrases, sentence openings
      -> statistical features (entropy, burstiness, n-gram repetition)
      -> semantic features (sentence embeddings: similarity, coherence, redundancy)
      -> stylometric features and the 0-100 Writing Profile
      -> detector: document and sentence AI-associated signal
      -> sentence rows + feature rows + report
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from .detector import DetectionResult, get_detector
from .discourse import compute_discourse
from .document_stats import compute_document_stats
from .features import BY_NAME
from .lexical import RARE_ZIPF, compute_lexical, zipf
from .preprocessing import ProcessedDocument, Sentence, preprocess
from .semantics import compute_semantics
from .statistics_features import compute_statistics
from .stylometry import build_profile, compute_stylometry
from .syntax import compute_syntax, sentence_syntax

logger = logging.getLogger("authentitext")

PIPELINE_VERSION = "0.7.0"


@dataclass
class PipelineResult:
    processed: ProcessedDocument
    features: dict[str, float | None]
    sentences: list[dict]
    report: dict
    detection: "DetectionResult | None" = None
    timings_ms: dict[str, int] = field(default_factory=dict)


def sentence_signals(sentence: Sentence) -> dict:
    """Per-sentence measurements stored in SentenceAnalysis.signals."""
    words = sentence.words
    alpha = [w for w in words if w.is_alpha]
    forms = [w.norm for w in words]
    return {
        "words": len(words),
        "characters": sentence.end - sentence.start,
        "avg_word_length": round(sum(len(w.text) for w in alpha) / len(alpha), 2) if alpha else None,
        "punctuation": sum(1 for t in sentence.tokens if t.is_punct),
        "type_token_ratio": round(len(set(forms)) / len(forms), 3) if forms else None,
        "content_word_ratio": round(sum(1 for w in words if w.is_content) / len(words), 3) if words else None,
        "rare_words": sum(1 for w in alpha if w.pos != "PROPN" and zipf(w.norm) < RARE_ZIPF),
        "first_word": words[0].norm if words else "",
    }


def run_pipeline(text: str) -> PipelineResult:
    timings: dict[str, int] = {}

    def timed(name, fn, *args):
        started = time.perf_counter()
        value = fn(*args)
        timings[name] = round((time.perf_counter() - started) * 1000)
        return value

    processed = timed("preprocess", preprocess, text)
    document = timed("document_stats", compute_document_stats, processed)
    lexical, lexical_details = timed("lexical", compute_lexical, processed)
    syntax = timed("syntax", compute_syntax, processed)
    discourse, discourse_details = timed("discourse", compute_discourse, processed)
    statistical, statistical_details = timed("statistics", compute_statistics, processed)
    semantic, semantic_details = timed("semantics", compute_semantics, processed)
    stylometric = timed("stylometry", compute_stylometry, processed, syntax)

    closest = {row["index"]: row for row in semantic_details.get("sentence_similarity", [])}
    repeated_openings = {index for group in discourse_details.get("repeated_openings", [])
                         for index in group["sentences"]}
    markers_by_sentence: dict[int, list[str]] = {}
    for pattern in discourse_details["patterns"]:
        for _, _, sentence_index in pattern["spans"]:
            markers_by_sentence.setdefault(sentence_index, []).append(pattern["category"])
    sentences = timed("sentences", lambda: [
        {"index": s.index, "text": processed.text_of(s.start, s.end), "start": s.start, "end": s.end,
         "signals": {**sentence_signals(s), **sentence_syntax(s), "paragraph": s.paragraph, "heading": s.is_heading,
                     "markers": sorted(set(markers_by_sentence.get(s.index, []))),
                     "closest_sentence": closest.get(s.index, {}).get("closest"),
                     "closest_similarity": closest.get(s.index, {}).get("similarity"),
                     "repeated_opening": s.index in repeated_openings}}
        for s in processed.sentences
    ])

    features = {**document, **lexical, **syntax, **discourse, **statistical, **semantic, **stylometric}
    unknown = set(features) - set(BY_NAME)
    assert not unknown, f"Unregistered features: {unknown}"   # every feature needs a label and explanation

    detector = get_detector()
    started = time.perf_counter()
    detection = detector.analyze(features, word_count=int(features["word_count"] or 0))
    timings["detection"] = round((time.perf_counter() - started) * 1000)
    for sentence, scored in zip(sentences, detector.sentence_scores(sentences, features, detection.probability)):
        sentence["ai_probability"] = scored["score"]
        sentence["signals"]["signal_reasons"] = scored["reasons"]

    notes = []
    if processed.language != "en":
        notes.append("This text doesn't read as English. AuthentiText currently analyzes English only, so these results aren't reliable.")
    report = {
        **lexical_details,
        **discourse_details,
        **statistical_details,
        **semantic_details,
        "profile": build_profile(features),
        "detection": {**detection.as_dict(),
                      "heatmap_note": getattr(detector, "heatmap_note", lambda _: "")(detection)},
        "sentence_lengths": [s["signals"]["words"] for s in sentences],
        "language_checked": processed.language_checked,
        "notes": notes,
        "timings_ms": timings,
    }
    return PipelineResult(processed, features, sentences, report, detection, timings)


def save_results(analysis, result: PipelineResult) -> None:
    from analyzer.models import Feature, SentenceAnalysis

    with transaction.atomic():
        analysis.sentences.all().delete()
        analysis.features.all().delete()
        SentenceAnalysis.objects.bulk_create([
            SentenceAnalysis(analysis=analysis, sentence_index=s["index"], text=s["text"],
                             start_char=s["start"], end_char=s["end"], signals=s["signals"],
                             ai_probability=s.get("ai_probability"))
            for s in result.sentences
        ])
        Feature.objects.bulk_create([
            Feature(analysis=analysis, feature_name=name, feature_value=float(value), category=BY_NAME[name].category)
            for name, value in result.features.items() if value is not None
        ])
        f = result.features
        analysis.word_count = int(f["word_count"])
        analysis.sentence_count = int(f["sentence_count"])
        analysis.paragraph_count = int(f["paragraph_count"])
        analysis.language = result.processed.language
        detection = result.detection
        analysis.result_label = detection.label
        analysis.ai_probability = detection.probability
        analysis.confidence = detection.confidence
        analysis.uncertainty = detection.uncertainty
        analysis.model_version = detection.model_version
        analysis.is_demo = detection.is_demo
        analysis.report = result.report
        analysis.pipeline_version = PIPELINE_VERSION
        analysis.processed_at = timezone.now()
        analysis.processing_ms = sum(result.timings_ms.values())
        analysis.status = analysis.Status.COMPLETE
        analysis.save()


def analyze_document(analysis) -> bool:
    """Run and save the pipeline. Returns False (and marks the analysis failed) on error."""
    try:
        result = run_pipeline(analysis.original_text)
        save_results(analysis, result)
        logger.info("Analyzed %s in %s ms %s", analysis.pk, analysis.processing_ms, result.timings_ms)
        return True
    except Exception:
        logger.exception("Pipeline failed for analysis %s", analysis.pk)
        analysis.status = analysis.Status.FAILED
        analysis.save(update_fields=["status", "updated_at"])
        return False
