from django.contrib import admin

from .models import Analysis, Feature, SentenceAnalysis


class SentenceInline(admin.TabularInline):
    model = SentenceAnalysis
    extra = 0
    fields = ("sentence_index", "text", "ai_probability", "confidence")
    readonly_fields = fields
    can_delete = False
    show_change_link = True


class FeatureInline(admin.TabularInline):
    model = Feature
    extra = 0
    fields = ("category", "feature_name", "feature_value")
    readonly_fields = fields
    can_delete = False


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "status", "result_label", "word_count", "is_demo", "created_at")
    list_filter = ("status", "result_label", "source_type", "is_demo", "created_at")
    search_fields = ("title", "filename", "user__username")
    readonly_fields = ("id", "text_hash", "created_at", "updated_at")
    inlines = [SentenceInline, FeatureInline]


@admin.register(SentenceAnalysis)
class SentenceAnalysisAdmin(admin.ModelAdmin):
    list_display = ("analysis", "sentence_index", "ai_probability", "confidence")
    search_fields = ("text",)


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ("analysis", "category", "feature_name", "feature_value")
    list_filter = ("category",)
