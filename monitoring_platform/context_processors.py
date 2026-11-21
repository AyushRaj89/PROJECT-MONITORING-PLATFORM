from accounts.roles import ROLE_MANAGER, ROLE_VIEWER, user_role


def roles(request):
    """Make the current user's role available in every template."""
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated):
        return {}
    role = user_role(user)
    return {
        "user_role": role,
        "is_manager": role == ROLE_MANAGER or user.is_superuser,
        "is_viewer": role == ROLE_VIEWER,
    }
