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
from .services.parser import extract_text
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
        messages.success(request, f"Saved \u201c{analysis.display_name}\u201d.")
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
