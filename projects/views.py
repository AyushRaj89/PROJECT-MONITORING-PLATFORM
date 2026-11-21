from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import SuspiciousOperation
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .access import can_contribute, can_manage_project, get_visible_project, require_manage
from .forms import MemberForm, MilestoneForm, ProjectFilterForm, ProjectForm
from .models import Milestone, Project, ProjectMember

VIEW_MODES = ("card", "table")


# --------------------------------------------------------------------------- projects
@login_required
def project_list(request):
    """Search / filter / sort / paginate the projects the user can see (GET form)."""
    projects = Project.objects.visible_to(request.user).select_related("manager")

    form = ProjectFilterForm(request.GET or None)
    if form.is_valid():
        data = form.cleaned_data
        if data["q"]:
            projects = projects.filter(
                Q(name__icontains=data["q"]) | Q(code__icontains=data["q"]) | Q(client_name__icontains=data["q"])
            )
        if data["status"]:
            projects = projects.filter(status=data["status"])
        if data["health"]:
            projects = projects.filter(health=data["health"])
        if data["sort"]:
            projects = projects.order_by(data["sort"])

    page_obj = Paginator(projects, 9).get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)

    # Session (Unit VI): ids of recently opened projects, newest first.
    recent_ids = request.session.get("recent_projects", [])
    by_id = {p.pk: p for p in Project.objects.visible_to(request.user).filter(pk__in=recent_ids)}
    recent_projects = [by_id[i] for i in recent_ids if i in by_id]

    return render(
        request,
        "projects/project_list.html",
        {
            "form": form,
            "page_obj": page_obj,
            "projects": page_obj.object_list,
            "querystring": params.urlencode(),            # keep filters when paging
            "view_mode": request.COOKIES.get("view_mode", "card"),   # cookie (Unit VI)
            "recent_projects": recent_projects,
        },
    )


@login_required
def project_detail(request, pk):
    project = get_visible_project(request.user, pk)

    # Remember this project in the session (most recent first, max 5).
    recent = [i for i in request.session.get("recent_projects", []) if i != project.pk]
    request.session["recent_projects"] = ([project.pk] + recent)[:5]

    counts = {row["status"]: row["n"] for row in project.tasks.values("status").annotate(n=Count("id"))}
    task_counts = {key: counts.get(key, 0) for key, _ in project.tasks.model.STATUS_CHOICES}

    return render(
        request,
        "projects/project_detail.html",
        {
            "project": project,
            "members": project.members.select_related("user"),
            "milestones": project.milestones.all(),
            "tasks": project.tasks.select_related("assignee")[:10],
            "task_counts": task_counts,
            "open_issues": project.issues.exclude(status__in=["resolved", "closed"]).select_related("owner"),
            "updates": project.progress_updates.select_related("author")[:5],
            "can_manage": can_manage_project(request.user, project),
            "can_contribute": can_contribute(request.user, project),
        },
    )


@login_required
@permission_required("projects.add_project", raise_exception=True)
def project_create(request):
    if request.method == "POST":
        form = ProjectForm(request.POST, user=request.user)
        if form.is_valid():
            project = form.save(commit=False)
            if not request.user.is_superuser:
                project.manager = request.user
            project.save()
            messages.success(request, f"Project {project.code} created.")
            return redirect(project)  # POST -> redirect (Unit IV)
    else:
        form = ProjectForm(user=request.user)
    return render(request, "projects/project_form.html", {"form": form, "is_edit": False})


@login_required
def project_update(request, pk):
    project = get_visible_project(request.user, pk)
    require_manage(request.user, project)
    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Project updated.")
            return redirect(project)
    else:
        form = ProjectForm(instance=project, user=request.user)
    return render(request, "projects/project_form.html", {"form": form, "project": project, "is_edit": True})


@login_required
def project_delete(request, pk):
    """GET shows a confirmation page, POST deletes."""
    project = get_visible_project(request.user, pk)
    require_manage(request.user, project)
    if request.method == "POST":
        project.delete()
        messages.success(request, "Project deleted.")
        return redirect("projects:list")
    return render(request, "projects/project_confirm_delete.html", {"project": project})


# --------------------------------------------------------------------------- team members
@login_required
def member_add(request, project_pk):
    project = get_visible_project(request.user, project_pk)
    require_manage(request.user, project)
    if request.method == "POST":
        form = MemberForm(request.POST, project=project)
        if form.is_valid():
            member = form.save()
            messages.success(request, f"{member.user.username} added to the project.")
            return redirect(project)
    else:
        form = MemberForm(project=project)
    return render(request, "projects/member_form.html", {"form": form, "project": project})


@login_required
@require_POST
def member_remove(request, project_pk, pk):
    project = get_visible_project(request.user, project_pk)
    require_manage(request.user, project)
    member = get_object_or_404(ProjectMember, pk=pk, project=project)
    member.delete()
    messages.success(request, "Member removed.")
    return redirect(project)


# --------------------------------------------------------------------------- milestones
@login_required
def milestone_create(request, project_pk):
    project = get_visible_project(request.user, project_pk)
    require_manage(request.user, project)
    if request.method == "POST":
        form = MilestoneForm(request.POST, project=project)
        if form.is_valid():
            form.save()
            messages.success(request, "Milestone added.")
            return redirect(project)
    else:
        form = MilestoneForm(project=project)
    return render(request, "projects/milestone_form.html", {"form": form, "project": project, "is_edit": False})


def _get_milestone_for_manager(user, pk):
    milestone = get_object_or_404(Milestone.objects.select_related("project"), pk=pk)
    project = get_visible_project(user, milestone.project_id)
    require_manage(user, project)
    return milestone, project


@login_required
def milestone_update(request, pk):
    milestone, project = _get_milestone_for_manager(request.user, pk)
    if request.method == "POST":
        form = MilestoneForm(request.POST, instance=milestone, project=project)
        if form.is_valid():
            form.save()
            messages.success(request, "Milestone updated.")
            return redirect(project)
    else:
        form = MilestoneForm(instance=milestone, project=project)
    return render(
        request,
        "projects/milestone_form.html",
        {"form": form, "project": project, "milestone": milestone, "is_edit": True},
    )


@login_required
def milestone_delete(request, pk):
    milestone, project = _get_milestone_for_manager(request.user, pk)
    if request.method == "POST":
        milestone.delete()
        messages.success(request, "Milestone deleted.")
        return redirect(project)
    return render(request, "projects/milestone_confirm_delete.html", {"milestone": milestone, "project": project})


# --------------------------------------------------------------------------- cookie preference
@login_required
@require_POST
def set_view_mode(request):
    """Store the user's list layout choice (card/table) in a cookie."""
    mode = request.POST.get("mode")
    if mode not in VIEW_MODES:
        raise SuspiciousOperation("Invalid view mode.")  # -> custom 400 page
    next_url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = reverse("projects:list")
    response = redirect(next_url)
    response.set_cookie("view_mode", mode, max_age=60 * 60 * 24 * 30, samesite="Lax")
    return response
