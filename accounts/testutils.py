"""Small helpers shared by the test modules of all apps."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command

from .roles import ROLE_MANAGER, ROLE_MEMBER, ROLE_VIEWER  # noqa: F401  (re-exported for tests)

User = get_user_model()
PASSWORD = "pass12345"


def setup_roles():
    call_command("setup_roles", verbosity=0)


def make_user(username, role=None, superuser=False):
    if superuser:
        return User.objects.create_superuser(username, f"{username}@example.com", PASSWORD)
    user = User.objects.create_user(username, f"{username}@example.com", PASSWORD)
    if role:
        user.groups.add(Group.objects.get(name=role))
    return user
