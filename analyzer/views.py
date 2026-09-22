from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Analysis


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
