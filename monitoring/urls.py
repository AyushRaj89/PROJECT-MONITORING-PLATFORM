from django.urls import path, re_path

from . import views

app_name = "monitoring"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # progress updates
    path("projects/<int:project_pk>/updates/new/", views.progress_update_create, name="update_create"),
    # issues
    path("issues/", views.issue_list, name="issue_list"),
    path("projects/<int:project_pk>/issues/new/", views.issue_create, name="issue_create"),
    path("issues/<int:pk>/edit/", views.issue_update, name="issue_update"),
    # reports - regular expression in the URL (Unit II): exactly four digits
    re_path(r"^reports/(?P<year>[0-9]{4})/$", views.year_report, name="year_report"),
    path("projects/<int:project_pk>/tasks.csv", views.export_tasks_csv, name="tasks_csv"),
    # JSON for charts
    path("api/dashboard/", views.dashboard_data, name="dashboard_data"),
    path("api/projects/<int:pk>/", views.project_data, name="project_data"),
]
