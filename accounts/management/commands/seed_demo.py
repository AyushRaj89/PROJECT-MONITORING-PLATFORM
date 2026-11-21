from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Profile
from accounts.roles import ROLE_MANAGER, ROLE_MEMBER, ROLE_VIEWER
from monitoring.models import Issue, ProgressUpdate
from projects.models import Milestone, Project, ProjectMember
from tasks.models import Task, TaskComment

User = get_user_model()
PASSWORD = "demo12345"


class Command(BaseCommand):
    help = "Create demo users, projects, tasks, updates and issues so the frontend has data to show."

    def handle(self, *args, **options):
        call_command("setup_roles", verbosity=0)
        if Project.objects.filter(code="WEB-REDESIGN").exists():
            self.stdout.write("Demo data already exists - nothing to do.")
            return

        today = timezone.localdate()
        d = lambda days: today + timedelta(days=days)  # noqa: E731

        def user(username, first, last, role=None, superuser=False, designation=""):
            if superuser:
                u = User.objects.create_superuser(username, f"{username}@example.com", "admin12345")
            else:
                u = User.objects.create_user(username, f"{username}@example.com", PASSWORD)
                u.groups.add(Group.objects.get(name=role))
            u.first_name, u.last_name = first, last
            u.save()
            Profile.objects.create(user=u, designation=designation)
            return u

        user("admin", "Site", "Admin", superuser=True, designation="Administrator")
        mgr = user("manager1", "Meera", "Shah", ROLE_MANAGER, designation="Project Manager")
        mgr2 = user("manager2", "Rohan", "Verma", ROLE_MANAGER, designation="Project Manager")
        dev1 = user("member1", "Aarav", "Singh", ROLE_MEMBER, designation="Backend Developer")
        dev2 = user("member2", "Isha", "Kapoor", ROLE_MEMBER, designation="UI Developer")
        qa = user("member3", "Kabir", "Das", ROLE_MEMBER, designation="QA Engineer")
        client = user("viewer1", "Client", "Contact", ROLE_VIEWER, designation="Client")

        web = Project.objects.create(
            name="Website Redesign", code="WEB-REDESIGN", manager=mgr, client_name="Acme Corp",
            description="Redesign the corporate website.", status="active", health="amber",
            start_date=d(-60), end_date=d(30), budget=500000, actual_cost=320000,
        )
        app = Project.objects.create(
            name="Mobile App", code="MOBILE-APP", manager=mgr2, client_name="Globex",
            description="Customer mobile app.", status="planning", health="green",
            start_date=d(10), end_date=d(120), budget=900000, actual_cost=0,
        )
        Project.objects.create(
            name="Data Migration", code="DATA-MIG", manager=mgr, client_name="Initech",
            status="completed", start_date=d(-150), end_date=d(-20), budget=200000, actual_cost=185000,
        )

        for u, role in ((dev1, "Backend"), (dev2, "Frontend"), (qa, "QA"), (client, "Client")):
            ProjectMember.objects.create(project=web, user=u, role_in_project=role)
        ProjectMember.objects.create(project=app, user=dev1, role_in_project="Backend")

        m1 = Milestone.objects.create(project=web, title="Design approved", due_date=d(-30), status="achieved")
        m2 = Milestone.objects.create(project=web, title="Beta release", due_date=d(10), status="in_progress")
        Milestone.objects.create(project=web, title="Go live", due_date=d(30))
        Milestone.objects.create(project=app, title="Requirements sign-off", due_date=d(20))

        rows = [
            (web, m1, "Create wireframes", dev2, "done", "medium", d(-40)),
            (web, m1, "Design system", dev2, "done", "high", d(-32)),
            (web, m2, "Build home page", dev2, "in_progress", "high", d(5)),
            (web, m2, "Contact form API", dev1, "review", "medium", d(3)),
            (web, m2, "Fix login redirect bug", dev1, "blocked", "critical", d(-3)),
            (web, m2, "Cross-browser testing", qa, "todo", "medium", d(8)),
            (web, None, "Write deployment guide", None, "todo", "low", d(25)),
            (app, None, "Collect requirements", dev1, "in_progress", "high", d(15)),
        ]
        tasks = []
        for project, ms, title, assignee, status, priority, due in rows:
            tasks.append(Task.objects.create(
                project=project, milestone=ms, title=title, assignee=assignee, created_by=project.manager,
                status=status, priority=priority, due_date=due, estimated_hours=8,
            ))
        TaskComment.objects.create(task=tasks[4], author=dev1, body="Waiting for the auth team to review the fix.")
        TaskComment.objects.create(task=tasks[4], author=mgr, body="I will chase them today.")

        ProgressUpdate.objects.create(
            project=web, author=mgr, summary="Design phase complete, development under way.",
            blockers="Login bug blocked by auth review.", percent_complete=40, health="amber",
        )
        Issue.objects.create(project=web, title="Server timeout on image upload", severity="high",
                             reported_by=qa, owner=dev1, due_date=d(7))
        Issue.objects.create(project=web, title="Fonts not loading on Safari", severity="low", reported_by=qa, owner=dev2)

        self.stdout.write(self.style.SUCCESS(
            "Demo data created.\n"
            "  admin / admin12345 (superuser)\n"
            f"  manager1, manager2, member1, member2, member3, viewer1 / {PASSWORD}"
        ))
