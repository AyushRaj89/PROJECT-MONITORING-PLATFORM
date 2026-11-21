"""Object-level access rules shared by the views.

Model-level rules come from Django permissions (@permission_required);
these helpers add "is this *your* project?" checks on top.
"""
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import Project


def get_visible_project(user, pk):
    """404 (not 403) when the user cannot see the project, so its existence isn't leaked."""
    return get_object_or_404(Project.objects.visible_to(user), pk=pk)


def can_manage_project(user, project):
    return user.is_superuser or project.manager_id == user.id


def require_manage(user, project):
    if not can_manage_project(user, project):
        raise PermissionDenied("Only the project manager can do this.")


def can_contribute(user, project):
    """Members may add tasks/updates/issues; read-only viewers may not."""
    return user.has_perm("tasks.add_task") and (user.is_superuser or project.is_member(user))


def require_contribute(user, project):
    if not can_contribute(user, project):
        raise PermissionDenied("You cannot add or change items in this project.")
