from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def superuser_required(view):
    """Login required; logged-in non-superusers get a 403 page (not a redirect loop)."""

    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied("Admins only.")
        return view(request, *args, **kwargs)

    return wrapper
