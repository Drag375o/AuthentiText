from django.urls import path

from . import views

app_name = "analyzer"

urlpatterns = [
    path("analyze/", views.analyze, name="analyze"),
    path("analyze/extract/", views.extract, name="extract"),
    path("compare/", views.compare, name="compare"),
    path("profile/", views.writing_profile, name="profile"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("analysis/<uuid:analysis_id>/", views.analysis_detail, name="detail"),
    path("analysis/<uuid:analysis_id>/run/", views.analysis_run, name="run"),
    path("analysis/<uuid:analysis_id>/rename/", views.analysis_rename, name="rename"),
    path("analysis/<uuid:analysis_id>/report.<str:extension>", views.analysis_report, name="report"),
    path("analysis/<uuid:analysis_id>/delete/", views.analysis_delete, name="delete"),
]
