"""Aggregation helpers behind the dashboard, project reports and JSON endpoints."""
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from projects.models import Milestone, Project
from tasks.models import Task

from .models import Issue

OPEN_ISSUE_EXCLUDE = ["resolved", "closed"]


def _counts(qs, field, choices):
    raw = dict(qs.values_list(field).annotate(n=Count("id", distinct=True)))
    return {key: raw.get(key, 0) for key, _ in choices}


def project_summary(project):
    today = timezone.localdate()
    tasks = project.tasks.all()
    open_tasks = tasks.exclude(status="done")
    next_milestone = (
        project.milestones.filter(status__in=["pending", "in_progress"]).order_by("due_date").first()
    )
    open_issues = project.issues.exclude(status__in=OPEN_ISSUE_EXCLUDE)
    return {
        "id": project.pk,
        "code": project.code,
        "name": project.name,
        "status": project.status,
        "health": project.health,
        "progress": project.progress,
        "is_overdue": project.is_overdue,
        "tasks_total": tasks.count(),
        "tasks_by_status": _counts(tasks, "status", Task.STATUS_CHOICES),
        "tasks_by_priority": _counts(tasks, "priority", Task.PRIORITY_CHOICES),
        "tasks_overdue": open_tasks.filter(due_date__lt=today).count(),
        "tasks_unassigned": open_tasks.filter(assignee__isnull=True).count(),
        "milestones_by_status": _counts(project.milestones.all(), "status", Milestone.STATUS_CHOICES),
        "next_milestone": (
            {"title": next_milestone.title, "due_date": next_milestone.due_date.isoformat()}
            if next_milestone else None
        ),
        "issues_open": open_issues.count(),
        "issues_critical": open_issues.filter(severity="critical").count(),
        "budget": float(project.budget),
        "actual_cost": float(project.actual_cost),
        "budget_used_percent": project.budget_used_percent,
    }


def portfolio_summary(user):
    """Numbers for the dashboard: everything the user is allowed to see."""
    today = timezone.localdate()
    projects = Project.objects.visible_to(user)
    ids = projects.values("id")
    tasks = Task.objects.filter(project__in=ids)
    my_open = tasks.filter(assignee=user).exclude(status="done")
    open_issues = Issue.objects.filter(project__in=ids).exclude(status__in=OPEN_ISSUE_EXCLUDE)

    overdue_projects = projects.filter(end_date__lt=today).exclude(status__in=["completed", "cancelled"])
    return {
        "projects_total": projects.count(),
        "projects_by_status": _counts(projects, "status", Project.STATUS_CHOICES),
        "projects_by_health": _counts(projects.filter(status="active"), "health", Project.HEALTH_CHOICES),
        "overdue_projects": list(overdue_projects.values("id", "code", "name", "end_date")[:10]),
        "tasks_total": tasks.count(),
        "tasks_by_status": _counts(tasks, "status", Task.STATUS_CHOICES),
        "tasks_overdue": tasks.filter(due_date__lt=today).exclude(status="done").count(),
        "my_open_tasks": my_open.count(),
        "my_overdue_tasks": my_open.filter(due_date__lt=today).count(),
        "my_due_this_week": my_open.filter(due_date__gte=today, due_date__lte=today + timedelta(days=7)).count(),
        "issues_open": open_issues.count(),
        "issues_critical": open_issues.filter(severity="critical").count(),
    }


def tasks_completed_by_month(projects, year):
    """{1: n, 2: n, ... 12: n} - tasks completed per month of `year`."""
    result = {m: 0 for m in range(1, 13)}
    done = Task.objects.filter(project__in=projects.values("id"), completed_at__year=year)
    for completed_at in done.values_list("completed_at", flat=True):
        result[timezone.localtime(completed_at).month] += 1
    return result
