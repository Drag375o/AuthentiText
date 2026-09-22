"""
Storage for writing analyses.

Design notes
- The user's original text is stored untouched in Analysis.original_text.
  Processed representations are derived from it and never written back.
- Primary keys are UUIDs so analysis URLs can't be guessed by counting.
  Ownership is still always checked (see AnalysisQuerySet.for_user).
- Probabilities are nullable: "insufficient evidence" is a real outcome and is
  stored as no probability, never as a made-up number.
"""
from __future__ import annotations

import hashlib
import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

UNIT_INTERVAL = [MinValueValidator(0.0), MaxValueValidator(1.0)]


def unit_interval_check(field: str, name: str) -> models.CheckConstraint:
    """Database-level guarantee that a nullable score stays within [0, 1]."""
    return models.CheckConstraint(
        condition=Q(**{f"{field}__isnull": True}) | Q(**{f"{field}__gte": 0.0, f"{field}__lte": 1.0}),
        name=name,
    )


def hash_text(text: str) -> str:
    """SHA-256 of the exact original text. Used to spot re-analysis of the same document."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class AnalysisQuerySet(models.QuerySet):
    def for_user(self, user) -> "AnalysisQuerySet":
        """The only way views should look up analyses. Anonymous users get nothing."""
        if not getattr(user, "is_authenticated", False):
            return self.none()
        return self.filter(user=user)


class Analysis(models.Model):
    class SourceType(models.TextChoices):
        PASTE = "paste", "Pasted text"
        UPLOAD = "upload", "Uploaded file"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    class ResultLabel(models.TextChoices):
        LIKELY_HUMAN = "likely_human", "Likely human"
        POSSIBLY_AI_ASSISTED = "possibly_ai_assisted", "Possibly AI-assisted"
        LIKELY_AI_ASSOCIATED = "likely_ai_associated", "Likely AI-associated"
        UNCERTAIN = "uncertain", "Uncertain"
        INSUFFICIENT_EVIDENCE = "insufficient_evidence", "Insufficient evidence"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="analyses")

    # Source
    title = models.CharField(max_length=200, blank=True)
    source_type = models.CharField(max_length=10, choices=SourceType.choices, default=SourceType.PASTE)
    filename = models.CharField(max_length=255, blank=True)
    original_text = models.TextField()
    text_hash = models.CharField(max_length=64, db_index=True, editable=False)
    language = models.CharField(max_length=10, default="en")

    # Document statistics
    word_count = models.PositiveIntegerField(default=0)
    sentence_count = models.PositiveIntegerField(default=0)
    paragraph_count = models.PositiveIntegerField(default=0)

    # Result (null until computed, or when evidence is insufficient)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    result_label = models.CharField(max_length=24, choices=ResultLabel.choices, blank=True)
    ai_probability = models.FloatField(null=True, blank=True, validators=UNIT_INTERVAL)
    confidence = models.FloatField(null=True, blank=True, validators=UNIT_INTERVAL)
    uncertainty = models.FloatField(null=True, blank=True, validators=UNIT_INTERVAL)
    model_version = models.CharField(max_length=50, blank=True)
    is_demo = models.BooleanField(default=False, help_text="True when produced by the labelled demo detector.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AnalysisQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "analyses"
        indexes = [models.Index(fields=["user", "-created_at"])]
        constraints = [
            unit_interval_check("ai_probability", "analysis_ai_probability_0_1"),
            unit_interval_check("confidence", "analysis_confidence_0_1"),
            unit_interval_check("uncertainty", "analysis_uncertainty_0_1"),
        ]

    def __str__(self) -> str:
        return self.display_name

    def save(self, *args, **kwargs):
        self.text_hash = hash_text(self.original_text)
        super().save(*args, **kwargs)

    @property
    def display_name(self) -> str:
        if self.title:
            return self.title
        if self.filename:
            return self.filename
        preview = " ".join(self.original_text.split()[:6])
        return f"{preview}\u2026" if preview else "Untitled analysis"


class SentenceAnalysis(models.Model):
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE, related_name="sentences")
    sentence_index = models.PositiveIntegerField()
    text = models.TextField()
    # Character offsets into Analysis.original_text, so the viewer can
    # highlight the exact span without re-segmenting.
    start_char = models.PositiveIntegerField()
    end_char = models.PositiveIntegerField()
    ai_probability = models.FloatField(null=True, blank=True, validators=UNIT_INTERVAL)
    confidence = models.FloatField(null=True, blank=True, validators=UNIT_INTERVAL)
    signals = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["analysis", "sentence_index"]
        verbose_name_plural = "sentence analyses"
        constraints = [
            models.UniqueConstraint(fields=["analysis", "sentence_index"], name="unique_sentence_per_analysis"),
            models.CheckConstraint(condition=Q(end_char__gte=models.F("start_char")), name="sentence_span_ordered"),
            unit_interval_check("ai_probability", "sentence_ai_probability_0_1"),
            unit_interval_check("confidence", "sentence_confidence_0_1"),
        ]

    def __str__(self) -> str:
        return f"{self.analysis_id} #{self.sentence_index}"


class Feature(models.Model):
    class Category(models.TextChoices):
        DOCUMENT = "document", "Document"
        LEXICAL = "lexical", "Lexical"
        SYNTACTIC = "syntactic", "Syntactic"
        LINGUISTIC = "linguistic", "Linguistic"
        STATISTICAL = "statistical", "Statistical"
        SEMANTIC = "semantic", "Semantic"
        STYLOMETRIC = "stylometric", "Stylometric"
        STRUCTURAL = "structural", "Structural"

    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE, related_name="features")
    feature_name = models.CharField(max_length=80)
    feature_value = models.FloatField()
    category = models.CharField(max_length=12, choices=Category.choices)

    class Meta:
        ordering = ["category", "feature_name"]
        constraints = [
            models.UniqueConstraint(fields=["analysis", "feature_name"], name="unique_feature_per_analysis"),
        ]

    def __str__(self) -> str:
        return f"{self.feature_name}={self.feature_value:.4g}"
