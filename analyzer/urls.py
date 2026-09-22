from django.urls import path

from . import views

app_name = "analyzer"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("analysis/<uuid:analysis_id>/", views.analysis_detail, name="detail"),
    path("analysis/<uuid:analysis_id>/delete/", views.analysis_delete, name="delete"),
]
