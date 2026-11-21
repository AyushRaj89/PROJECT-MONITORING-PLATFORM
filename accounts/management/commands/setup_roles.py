from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from accounts.roles import ROLE_PERMISSIONS


class Command(BaseCommand):
    help = "Create the role groups (Project Manager, Team Member, Client Viewer) and assign their permissions."

    def handle(self, *args, **options):
        for role, perms in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role)
            objs = []
            for dotted in perms:
                app_label, codename = dotted.split(".")
                objs.append(Permission.objects.get(content_type__app_label=app_label, codename=codename))
            group.permissions.set(objs)
            if options["verbosity"] > 0:
                self.stdout.write(self.style.SUCCESS(f"{role}: {len(objs)} permissions"))
