from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from projects.access import can_manage_project, get_visible_project, require_contribute
from projects.models import Project

from .forms import TaskCommentForm, TaskFilterForm, TaskForm, TaskStatusForm
from .models import Task


def _visible_tasks(user):
    return Task.objects.filter(project__in=Project.objects.visible_to(user)).select_related(
        "project", "assignee", "milestone"
    )


def _get_task(user, pk):
    """Fetch a task the user is allowed to see (404 otherwise)."""
    task = get_object_or_404(_visible_tasks(user), pk=pk)
    return task


def _can_edit(user, task):
    return can_manage_project(user, task.project) or task.created_by_id == user.id or task.assignee_id == user.id


def _can_delete(user, task):
    return can_manage_project(user, task.project) or task.created_by_id == user.id


@login_required
def task_list(request):
    tasks = _visible_tasks(request.user)
    form = TaskFilterForm(request.GET or None, user=request.user)
    if form.is_valid():
        d = form.cleaned_data
        if d["q"]:
            tasks = tasks.filter(Q(title__icontains=d["q"]) | Q(description__icontains=d["q"]))
        if d["project"]:
            tasks = tasks.filter(project=d["project"])
        if d["status"]:
            tasks = tasks.filter(status=d["status"])
        if d["priority"]:
            tasks = tasks.filter(priority=d["priority"])
        if d["assignee"] == "me":
            tasks = tasks.filter(assignee=request.user)
        elif d["assignee"] == "none":
            tasks = tasks.filter(assignee__isnull=True)
        if d["overdue"]:
            tasks = tasks.filter(due_date__lt=timezone.localdate()).exclude(status="done")

    page_obj = Paginator(tasks, 15).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(
        request,
        "tasks/task_list.html",
        {"form": form, "page_obj": page_obj, "tasks": page_obj.object_list, "querystring": params.urlencode()},
    )


@login_required
def my_tasks(request):
    """Tasks assigned to the logged-in user, grouped by status."""
    tasks = _visible_tasks(request.user).filter(assignee=request.user)
    grouped = {label: [t for t in tasks if t.status == key] for key, label in Task.STATUS_CHOICES}
    # Same data with the status key included, for board columns.
    columns = [
        {"key": key, "label": label, "tasks": [t for t in tasks if t.status == key]}
        for key, label in Task.STATUS_CHOICES
    ]
    return render(
        request,
        "tasks/my_tasks.html",
        {
            "tasks": tasks,
            "grouped": grouped,
            "columns": columns,
            "status_choices": Task.STATUS_CHOICES,
            "open_count": tasks.exclude(status="done").count(),
            "overdue_count": tasks.filter(due_date__lt=timezone.localdate()).exclude(status="done").count(),
        },
    )


@login_required
def task_detail(request, pk):
    task = _get_task(request.user, pk)
    return render(
        request,
        "tasks/task_detail.html",
        {
            "task": task,
            "comments": task.comments.select_related("author"),
            "comment_form": TaskCommentForm(),
            "status_form": TaskStatusForm(initial={"status": task.status}),
            "can_edit": _can_edit(request.user, task),
            "can_delete": _can_delete(request.user, task),
            "can_comment": request.user.has_perm("tasks.add_taskcomment"),
        },
    )


@login_required
@permission_required("tasks.add_task", raise_exception=True)
def task_create(request, project_pk):
    project = get_visible_project(request.user, project_pk)
    require_contribute(request.user, project)
    if request.method == "POST":
        form = TaskForm(request.POST, project=project)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.save()
            messages.success(request, "Task created.")
            return redirect(task)  # POST -> redirect
    else:
        form = TaskForm(project=project)
    return render(request, "tasks/task_form.html", {"form": form, "project": project, "is_edit": False})


@login_required
def task_update(request, pk):
    task = _get_task(request.user, pk)
    if not _can_edit(request.user, task) or not request.user.has_perm("tasks.change_task"):
        raise PermissionDenied("You cannot edit this task.")
    if request.method == "POST":
        form = TaskForm(request.POST, instance=task, project=task.project)
        if form.is_valid():
            form.save()
            messages.success(request, "Task updated.")
            return redirect(task)
    else:
        form = TaskForm(instance=task, project=task.project)
    return render(
        request, "tasks/task_form.html", {"form": form, "project": task.project, "task": task, "is_edit": True}
    )


@login_required
def task_delete(request, pk):
    task = _get_task(request.user, pk)
    if not _can_delete(request.user, task) or not request.user.has_perm("tasks.delete_task"):
        raise PermissionDenied("You cannot delete this task.")
    if request.method == "POST":
        project = task.project
        task.delete()
        messages.success(request, "Task deleted.")
        return redirect(project)
    return render(request, "tasks/task_confirm_delete.html", {"task": task})


@login_required
@require_POST
def task_set_status(request, pk):
    """Quick status change (e.g. from a dropdown on the task page or a board)."""
    task = _get_task(request.user, pk)
    if not _can_edit(request.user, task) or not request.user.has_perm("tasks.change_task"):
        raise PermissionDenied("You cannot change this task.")
    form = TaskStatusForm(request.POST)
    if form.is_valid():
        task.status = form.cleaned_data["status"]
        task.save()
        messages.success(request, f"Status changed to {task.get_status_display()}.")
    else:
        messages.error(request, "Invalid status.")
    return redirect(task)


@login_required
@require_POST
def task_comment_add(request, pk):
    task = _get_task(request.user, pk)
    if not request.user.has_perm("tasks.add_taskcomment"):
        raise PermissionDenied("You cannot comment on tasks.")
    form = TaskCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.task = task
        comment.author = request.user
        comment.save()
        messages.success(request, "Comment added.")
    else:
        messages.error(request, "; ".join(e for errs in form.errors.values() for e in errs))
    return redirect(task)
