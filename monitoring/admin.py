from django.contrib import admin

from .models import Issue, ProgressUpdate


@admin.register(ProgressUpdate)
class ProgressUpdateAdmin(admin.ModelAdmin):
    list_display = ("project", "author", "percent_complete", "health", "created_at")
    list_filter = ("health", "project")


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "severity", "status", "owner")
    list_filter = ("severity", "status", "project")
    search_fields = ("title",)
