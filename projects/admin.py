from django.contrib import admin

from .models import Milestone, Project, ProjectMember


class MemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 0


class MilestoneInline(admin.TabularInline):
    model = Milestone
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "manager", "status", "health", "end_date")
    list_filter = ("status", "health")
    search_fields = ("name", "code", "client_name")
    inlines = [MemberInline, MilestoneInline]
