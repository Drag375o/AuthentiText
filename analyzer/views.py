from django.conf import settings
from django.core import signing
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import DocumentForm, RenameForm, UploadForm
from .models import Analysis
from .services.features import BY_NAME
from .services.parser import extract_text
from .services.pipeline import analyze_document
from .services.text_stats import READING_WPM, compute_text_stats
from .services.uploads import UploadRejected, validate_upload

UPLOAD_TOKEN_SALT = "analyzer.upload"


def owned_analysis_or_404(request: HttpRequest, analysis_id) -> Analysis:
    """Another user's analysis returns 404, not 403, so its existence isn't revealed."""
    return get_object_or_404(Analysis.objects.for_user(request.user), pk=analysis_id)


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    analyses = Analysis.objects.for_user(request.user)
    context = {
        "recent": analyses[:8],
        "total": analyses.count(),
        "latest": analyses.first(),
        "average_words": analyses.aggregate(avg=Avg("word_count"))["avg"],
    }
    return render(request, "analyzer/dashboard.html", context)


def make_upload_token(user, filename: str, kind: str) -> str:
    return signing.dumps({"u": user.pk, "f": filename, "k": kind}, salt=UPLOAD_TOKEN_SALT)


def read_upload_token(user, token: str) -> dict | None:
    """The upload details if the token is genuine, recent and belongs to this user."""
    if not token:
        return None
    try:
        data = signing.loads(token, salt=UPLOAD_TOKEN_SALT, max_age=settings.UPLOAD_TOKEN_MAX_AGE)
    except signing.BadSignature:  # includes SignatureExpired
        return None
    return data if data.get("u") == user.pk else None


def editor_context(form: DocumentForm, **extra) -> dict:
    return {
        "form": form,
        "upload_form": extra.pop("upload_form", UploadForm()),
        "editor_config": {
            "maxChars": settings.ANALYSIS_MAX_CHARS,
            "minWords": settings.ANALYSIS_MIN_WORDS,
            "readingWpm": READING_WPM,
            "maxUploadMb": settings.MAX_UPLOAD_SIZE_MB,
            "extractUrl": reverse("analyzer:extract"),
        },
        **extra,
    }


@login_required
def analyze(request: HttpRequest) -> HttpResponse:
    """The editor. Saves the text as a new Analysis owned by the user."""
    form = DocumentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        text = form.cleaned_data["text"]
        upload = read_upload_token(request.user, form.cleaned_data["upload_token"])
        stats = compute_text_stats(text)
        analysis = Analysis.objects.create(
            user=request.user,
            source_type=Analysis.SourceType.UPLOAD if upload else Analysis.SourceType.PASTE,
            filename=upload["f"] if upload else "",
            title=form.cleaned_data["title"],
            original_text=text,
            word_count=stats.words,
            sentence_count=stats.sentences,
            paragraph_count=stats.paragraphs,
        )
        if analyze_document(analysis):
            messages.success(request, f"Analyzed \u201c{analysis.display_name}\u201d.")
        else:
            messages.error(request, "Your text is saved, but the analysis didn't finish. Try again from this page.")
        return redirect("analyzer:detail", analysis_id=analysis.pk)

    upload = read_upload_token(request.user, request.POST.get("upload_token", "")) if request.method == "POST" else None
    return render(request, "analyzer/analyze.html", editor_context(form, upload=upload))


@login_required
@require_POST
def extract(request: HttpRequest) -> HttpResponse:
    """
    Validate an uploaded file and extract its text into the editor.
    JSON for the drag-and-drop uploader; without JavaScript, re-renders the
    editor pre-filled. The file itself is never stored.
    """
    upload_form = UploadForm(request.POST, request.FILES)
    error = None
    result = upload = None
    if upload_form.is_valid():
        try:
            upload = validate_upload(upload_form.cleaned_data["file"])
            result = extract_text(upload)
        except UploadRejected as exc:
            error = str(exc)
    else:
        error = upload_form.errors["file"][0]

    if wants_json(request):
        if error:
            return JsonResponse({"ok": False, "error": error}, status=400)
        stats = compute_text_stats(result.text)
        return JsonResponse({
            "ok": True,
            "text": result.text,
            "filename": upload.filename,
            "kind": result.kind,
            "pages": result.pages,
            "notes": result.notes,
            "words": stats.words,
            "token": make_upload_token(request.user, upload.filename, result.kind),
        })

    if error:
        messages.error(request, error)
        return redirect("analyzer:analyze")
    form = DocumentForm(initial={
        "text": result.text,
        "upload_token": make_upload_token(request.user, upload.filename, result.kind),
    })
    upload_info = {"f": upload.filename, "k": result.kind, "pages": result.pages, "notes": result.notes}
    return render(request, "analyzer/analyze.html", editor_context(form, upload=upload_info))


# How the document page groups features. Every name must exist in the registry.
FEATURE_GROUPS = {
    "rhythm": ["sentence_length_mean", "sentence_length_median", "sentence_length_std",
               "sentence_length_cv", "sentence_length_min", "sentence_length_max"],
    "vocabulary": ["mattr", "mtld", "type_token_ratio", "hapax_ratio", "lexical_density", "function_word_ratio"],
    "frequency": ["mean_content_zipf", "rare_word_ratio", "common_word_ratio", "long_word_ratio", "avg_word_length"],
    "punctuation": ["commas_per_100", "semicolons_per_100", "colons_per_100", "dashes_per_100",
                    "questions_per_100", "exclamations_per_100", "parentheses_per_100", "quotes_per_100", "ellipses_per_100"],
    "repetition": ["repeated_phrase_count", "repeated_phrase_coverage"],
    "complexity": ["parse_depth_mean", "dependency_distance_mean", "clauses_per_sentence",
                   "subordinate_clauses_per_sentence", "coordination_per_sentence"],
    "pos": ["pos_noun_ratio", "pos_verb_ratio", "pos_adj_ratio", "pos_adv_ratio", "pos_pron_ratio",
            "pos_det_ratio", "pos_adp_ratio", "pos_conj_ratio", "pos_aux_ratio", "pos_propn_ratio", "pos_num_ratio"],
    "openings": ["opening_pattern_diversity", "repeated_opening_ratio", "marker_initial_ratio"],
    "statistical": ["word_entropy", "normalized_entropy", "sentence_length_burstiness",
                    "bigram_repeat_rate", "trigram_repeat_rate", "zipf_slope"],
    "semantic": ["local_coherence", "paragraph_coherence", "semantic_diversity", "semantic_redundancy",
                 "max_sentence_similarity", "opening_closing_similarity"],
    "stylometric": ["formality_score", "first_person_ratio", "contraction_ratio"],
    "discourse": ["transitions_per_100", "contrast_markers_per_100", "cause_effect_markers_per_100",
                  "conclusion_markers_per_100", "emphasis_markers_per_100", "hedges_per_100", "formulaic_phrases_per_100"],
}
PATTERN_EXAMPLES = 3
SIMILAR_PAIRS_SHOWN = 4
# Sentence heatmap bands. Kept here so the template and the legend agree.
SIGNAL_BANDS = ((0.34, "low", "Low signal"), (0.60, "mid", "Medium signal"), (1.01, "high", "High signal"))


def signal_band(probability: float | None) -> tuple[str, str]:
    if probability is None:
        return "none", "Not scored"
    for ceiling, level, label in SIGNAL_BANDS:
        if probability < ceiling:
            return level, label
    return "high", "High signal"


def heatmap_sentences(sentences: list, detection: dict) -> list[dict]:
    """Sentence rows for the interactive viewer, with reasons drawn from the signals."""
    rows: list[dict] = []
    for sentence in sentences:
        level, level_label = signal_band(sentence.ai_probability)
        signals = sentence.signals or {}
        reasons = []
        if signals.get("markers"):
            reasons.append("Opens with or contains a discourse marker.")
        if signals.get("passive"):
            reasons.append("Passive construction.")
        if not signals.get("rare_words"):
            reasons.append("No uncommon vocabulary.")
        if signals.get("type_token_ratio") is not None and signals["type_token_ratio"] < 0.7:
            reasons.append("Words repeat within the sentence.")
        if signals.get("heading"):
            reasons = ["A heading, so it is not scored."]
        rows.append({
            "text": sentence.text, "level": level, "level_label": level_label,
            "index": sentence.sentence_index, "probability": sentence.ai_probability,
            "words": signals.get("words"), "reasons": reasons or ["Nothing notable in this sentence."],
            "paragraph": signals.get("paragraph", 0), "heading": bool(signals.get("heading")), "note": None,
        })
    return rows


def group_by_paragraph(rows: list[dict]) -> list[dict]:
    """Keep the document's shape in the viewer: one block per paragraph, headings on their own."""
    blocks: list[dict] = []
    for row in rows:
        if not blocks or blocks[-1]["paragraph"] != row["paragraph"] or row["heading"] or blocks[-1]["heading"]:
            blocks.append({"paragraph": row["paragraph"], "heading": row["heading"], "sentences": []})
        blocks[-1]["sentences"].append(row)
    return blocks
CONTEXT_CHARS = 70


def similar_pair_rows(analysis: Analysis, sentences: list) -> list[dict]:
    """The most similar sentence pairs, with their text, for the semantics card."""
    by_index = {s.sentence_index: s for s in sentences}
    rows = []
    for pair in analysis.report.get("similar_pairs", [])[:SIMILAR_PAIRS_SHOWN]:
        a, b = by_index.get(pair["a"]), by_index.get(pair["b"])
        if a and b:
            rows.append({**pair, "a_text": a.text, "b_text": b.text})
    return rows


def pattern_examples(analysis: Analysis, sentences: list) -> list[dict]:
    """
    Each matched pattern with up to three examples split into (before, match, after),
    so the template can highlight the match while Django escapes everything.
    """
    by_index = {s.sentence_index: s for s in sentences}
    categories = analysis.report.get("pattern_categories", {})
    entries = []
    for pattern in analysis.report.get("patterns", []):
        examples = []
        for start, end, sentence_index in pattern["spans"][:PATTERN_EXAMPLES]:
            sentence = by_index.get(sentence_index)
            if not sentence:
                continue
            a, b = start - sentence.start_char, end - sentence.start_char
            before, after = sentence.text[:a], sentence.text[b:]
            examples.append({
                "before": ("\u2026" + before[-CONTEXT_CHARS:].lstrip()) if len(before) > CONTEXT_CHARS else before,
                "match": sentence.text[a:b],
                "after": (after[:CONTEXT_CHARS].rstrip() + "\u2026") if len(after) > CONTEXT_CHARS else after,
                "sentence": sentence_index,
            })
        entries.append({**pattern, "category_label": categories.get(pattern["category"], pattern["category"]),
                        "count": len(pattern["spans"]), "examples": examples})
    return entries


def feature_rows(values: dict[str, float], names: list[str]) -> list[dict]:
    return [{"spec": BY_NAME[name], "value": values.get(name)} for name in names]


@login_required
def analysis_detail(request: HttpRequest, analysis_id) -> HttpResponse:
    analysis = owned_analysis_or_404(request, analysis_id)
    context = {"analysis": analysis}
    if analysis.is_processed:
        values = {f.feature_name: f.feature_value for f in analysis.features.all()}
        sentences = list(analysis.sentences.all())
        context.update({
            "values": values,
            "groups": {key: feature_rows(values, names) for key, names in FEATURE_GROUPS.items()},
            "sentences": sentences,
            "chart_data": {
                "lengths": [s.signals.get("words", 0) for s in sentences],
                "texts": [s.text[:140] + ("\u2026" if len(s.text) > 140 else "") for s in sentences],
                "mean": values.get("sentence_length_mean"),
            },
            "max_top_word": max((w["count"] for w in analysis.report.get("top_words", [])), default=1),
            "pattern_entries": pattern_examples(analysis, sentences),
            "detection": analysis.report.get("detection", {}),
            "heatmap_sentences": (heat := heatmap_sentences(sentences, analysis.report.get("detection", {}))),
            "heatmap_blocks": group_by_paragraph(heat),
            "profile": analysis.report.get("profile", []),
            "similar_pairs": similar_pair_rows(analysis, sentences),
            "marker_labels": analysis.report.get("pattern_categories", {}),
            "pos_chart": {
                "labels": [BY_NAME[n].label for n in FEATURE_GROUPS["pos"]],
                "values": [round((values.get(n) or 0) * 100, 1) for n in FEATURE_GROUPS["pos"]],
            },
        })
    return render(request, "analyzer/analysis_detail.html", context)


@login_required
@require_POST
def analysis_run(request: HttpRequest, analysis_id) -> HttpResponse:
    """Run (or re-run) the pipeline for a saved document."""
    analysis = owned_analysis_or_404(request, analysis_id)
    if analyze_document(analysis):
        messages.success(request, f"Analyzed \u201c{analysis.display_name}\u201d.")
    else:
        messages.error(request, "The analysis didn't finish. Try again in a moment.")
    return redirect("analyzer:detail", analysis_id=analysis.pk)


@login_required
@require_POST
def analysis_delete(request: HttpRequest, analysis_id) -> HttpResponse:
    analysis = owned_analysis_or_404(request, analysis_id)
    name = analysis.display_name
    analysis.delete()
    messages.success(request, f"Deleted \u201c{name}\u201d.")
    return redirect("analyzer:dashboard")


def wants_json(request: HttpRequest) -> bool:
    return "application/json" in request.headers.get("Accept", "")


@login_required
@require_POST
def analysis_rename(request: HttpRequest, analysis_id) -> HttpResponse:
    """Rename a document. Answers JSON for the inline editor, or redirects for a plain form."""
    analysis = owned_analysis_or_404(request, analysis_id)
    form = RenameForm(request.POST)
    if not form.is_valid():
        error = form.errors["title"][0]
        if wants_json(request):
            return JsonResponse({"ok": False, "error": error}, status=400)
        messages.error(request, error)
        return redirect("analyzer:detail", analysis_id=analysis.pk)

    analysis.title = form.cleaned_data["title"]
    analysis.save(update_fields=["title", "updated_at"])
    if wants_json(request):
        return JsonResponse({"ok": True, "title": analysis.title, "display_name": analysis.display_name})
    messages.success(request, f"Renamed to \u201c{analysis.display_name}\u201d.")
    return redirect("analyzer:detail", analysis_id=analysis.pk)
