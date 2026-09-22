from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PasteTextForm
from .models import Analysis
from .services.text_stats import READING_WPM, compute_text_stats


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


@login_required
def analyze(request: HttpRequest) -> HttpResponse:
    """The editor. Saves pasted text as a new Analysis owned by the user."""
    form = PasteTextForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        text = form.cleaned_data["text"]
        stats = compute_text_stats(text)
        analysis = Analysis.objects.create(
            user=request.user,
            source_type=Analysis.SourceType.PASTE,
            title=form.cleaned_data["title"],
            original_text=text,
            word_count=stats.words,
            sentence_count=stats.sentences,
            paragraph_count=stats.paragraphs,
        )
        messages.success(request, f"Saved \u201c{analysis.display_name}\u201d.")
        return redirect("analyzer:detail", analysis_id=analysis.pk)

    editor_config = {
        "maxChars": settings.ANALYSIS_MAX_CHARS,
        "minWords": settings.ANALYSIS_MIN_WORDS,
        "readingWpm": READING_WPM,
    }
    return render(request, "analyzer/analyze.html", {"form": form, "editor_config": editor_config})


@login_required
def analysis_detail(request: HttpRequest, analysis_id) -> HttpResponse:
    analysis = owned_analysis_or_404(request, analysis_id)
    return render(request, "analyzer/analysis_detail.html", {"analysis": analysis})


@login_required
@require_POST
def analysis_delete(request: HttpRequest, analysis_id) -> HttpResponse:
    analysis = owned_analysis_or_404(request, analysis_id)
    name = analysis.display_name
    analysis.delete()
    messages.success(request, f"Deleted \u201c{name}\u201d.")
    return redirect("analyzer:dashboard")
