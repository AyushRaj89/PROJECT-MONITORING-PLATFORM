from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("projects/", include("projects.urls")),
    path("tasks/", include("tasks.urls")),
    path("", include("monitoring.urls")),   # dashboard, issues, reports, JSON data
]

# Error handling (Unit II)
handler400 = "monitoring_platform.views.bad_request"
handler403 = "monitoring_platform.views.permission_denied"
handler404 = "monitoring_platform.views.page_not_found"
handler500 = "monitoring_platform.views.server_error"
