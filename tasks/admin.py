from django.contrib import admin

from .models import Task, TaskComment


class CommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "assignee", "status", "priority", "due_date")
    list_filter = ("status", "priority", "project")
    search_fields = ("title", "description")
    inlines = [CommentInline]
