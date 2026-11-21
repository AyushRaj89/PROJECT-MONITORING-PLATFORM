"""Roles are implemented with Django Groups + Permissions (Unit V).

Superusers act as platform admins. Everyone else belongs to one group.
`python manage.py setup_roles` creates the groups and assigns permissions.
"""

ROLE_MANAGER = "Project Manager"
ROLE_MEMBER = "Team Member"
ROLE_VIEWER = "Client Viewer"

ALL_ROLES = [ROLE_MANAGER, ROLE_MEMBER, ROLE_VIEWER]

# group -> list of "app_label.codename" permissions
ROLE_PERMISSIONS = {
    ROLE_MANAGER: [
        "projects.view_project", "projects.add_project", "projects.change_project", "projects.delete_project",
        "projects.add_projectmember", "projects.delete_projectmember",
        "projects.add_milestone", "projects.change_milestone", "projects.delete_milestone",
        "tasks.view_task", "tasks.add_task", "tasks.change_task", "tasks.delete_task",
        "tasks.add_taskcomment",
        "monitoring.add_progressupdate", "monitoring.add_issue", "monitoring.change_issue",
    ],
    ROLE_MEMBER: [
        "projects.view_project",
        "tasks.view_task", "tasks.add_task", "tasks.change_task",
        "tasks.add_taskcomment",
        "monitoring.add_progressupdate", "monitoring.add_issue", "monitoring.change_issue",
    ],
    ROLE_VIEWER: [
        "projects.view_project", "tasks.view_task",
    ],
}


def user_role(user):
    """Return the user's role name ('Admin' for superusers, None if no group)."""
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return "Admin"
    group = user.groups.filter(name__in=ALL_ROLES).first()
    return group.name if group else None
