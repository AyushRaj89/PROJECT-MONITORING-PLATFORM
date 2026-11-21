import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from projects.access import can_manage_project, get_visible_project, require_contribute
from projects.models import Milestone, Project
from tasks.models import Task

from .forms import IssueFilterForm, IssueForm, ProgressUpdateForm
from .models import Issue, ProgressUpdate
from .services import portfolio_summary, project_summary, tasks_completed_by_month


@login_required
def dashboard(request):
    """Landing page after login: portfolio numbers + my work + recent activity."""
    visible = Project.objects.visible_to(request.user)
    today = timezone.localdate()
    my_tasks = (
        Task.objects.filter(project__in=visible, assignee=request.user)
        .exclude(status="done").select_related("project")[:8]
    )
    return render(
        request,
        "monitoring/dashboard.html",
        {
            "summary": portfolio_summary(request.user),
            "my_tasks": my_tasks,
            "recent_projects": visible.select_related("manager")[:5],
            "upcoming_milestones": Milestone.objects.filter(
                project__in=visible, status__in=["pending", "in_progress"], due_date__gte=today
            ).select_related("project").order_by("due_date")[:5],
            "recent_updates": ProgressUpdate.objects.filter(project__in=visible).select_related("project", "author")[:5],
        },
    )


# --------------------------------------------------------------------------- progress updates
@login_required
@permission_required("monitoring.add_progressupdate", raise_exception=True)
def progress_update_create(request, project_pk):
    project = get_visible_project(request.user, project_pk)
    require_contribute(request.user, project)
    if request.method == "POST":
        form = ProgressUpdateForm(request.POST)
        if form.is_valid():
            update = form.save(commit=False)
            update.project = project
            update.author = request.user
            update.save()
            messages.success(request, "Progress update posted.")
            return redirect(project)
    else:
        form = ProgressUpdateForm(initial={"percent_complete": project.progress})
    return render(request, "monitoring/update_form.html", {"form": form, "project": project})


# --------------------------------------------------------------------------- issues
@login_required
def issue_list(request):
    issues = Issue.objects.filter(project__in=Project.objects.visible_to(request.user)).select_related(
        "project", "owner", "reported_by"
    )
    form = IssueFilterForm(request.GET or None, user=request.user)
    if form.is_valid():
        d = form.cleaned_data
        if d["q"]:
            issues = issues.filter(Q(title__icontains=d["q"]) | Q(description__icontains=d["q"]))
        if d["project"]:
            issues = issues.filter(project=d["project"])
        if d["severity"]:
            issues = issues.filter(severity=d["severity"])
        if d["status"]:
            issues = issues.filter(status=d["status"])

    page_obj = Paginator(issues, 15).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(
        request,
        "monitoring/issue_list.html",
        {"form": form, "page_obj": page_obj, "issues": page_obj.object_list, "querystring": params.urlencode()},
    )


@login_required
@permission_required("monitoring.add_issue", raise_exception=True)
def issue_create(request, project_pk):
    project = get_visible_project(request.user, project_pk)
    require_contribute(request.user, project)
    if request.method == "POST":
        form = IssueForm(request.POST, project=project)
        if form.is_valid():
            issue = form.save(commit=False)
            issue.reported_by = request.user
            issue.save()
            messages.success(request, "Issue reported.")
            return redirect("monitoring:issue_list")
    else:
        form = IssueForm(project=project)
    return render(request, "monitoring/issue_form.html", {"form": form, "project": project, "is_edit": False})


@login_required
def issue_update(request, pk):
    issue = get_object_or_404(Issue.objects.select_related("project"), pk=pk)
    project = get_visible_project(request.user, issue.project_id)
    allowed = (
        can_manage_project(request.user, project)
        or issue.reported_by_id == request.user.id
        or issue.owner_id == request.user.id
    )
    if not allowed or not request.user.has_perm("monitoring.change_issue"):
        raise PermissionDenied("You cannot edit this issue.")
    if request.method == "POST":
        form = IssueForm(request.POST, instance=issue, project=project)
        if form.is_valid():
            form.save()
            messages.success(request, "Issue updated.")
            return redirect("monitoring:issue_list")
    else:
        form = IssueForm(instance=issue, project=project)
    return render(
        request, "monitoring/issue_form.html", {"form": form, "project": project, "issue": issue, "is_edit": True}
    )


# --------------------------------------------------------------------------- reports
@login_required
def year_report(request, year):
    """Tasks completed per month in a year. The URL uses a regular expression
    (re_path) so only a 4-digit year such as /reports/2026/ matches."""
    year = int(year)
    if not 2000 <= year <= 2100:
        raise Http404("Year out of range.")
    visible = Project.objects.visible_to(request.user)
    monthly = tasks_completed_by_month(visible, year)
    rows = [{"month": m, "completed": n} for m, n in monthly.items()]
    return render(
        request,
        "monitoring/year_report.html",
        {"year": year, "rows": rows, "total": sum(monthly.values()), "prev_year": year - 1, "next_year": year + 1},
    )


@login_required
@require_GET
def export_tasks_csv(request, project_pk):
    """Download a project's tasks as a CSV file (HttpResponse with a file attachment)."""
    project = get_visible_project(request.user, project_pk)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{project.code}-tasks.csv"'
    writer = csv.writer(response)
    writer.writerow(["ID", "Title", "Status", "Priority", "Assignee", "Due date", "Estimated hours"])
    for t in project.tasks.select_related("assignee"):
        writer.writerow([
            t.pk, t.title, t.get_status_display(), t.get_priority_display(),
            t.assignee.username if t.assignee else "", t.due_date or "",
            t.estimated_hours if t.estimated_hours is not None else "",
        ])
    return response


# --------------------------------------------------------------------------- JSON for charts
@login_required
@require_GET
def dashboard_data(request):
    """JSON for dashboard charts (fetch('/api/dashboard/') from your JavaScript)."""
    return JsonResponse(portfolio_summary(request.user))


@login_required
@require_GET
def project_data(request, pk):
    """JSON summary of one project (task counts, milestones, issues, budget)."""
    project = get_visible_project(request.user, pk)
    return JsonResponse(project_summary(project))
