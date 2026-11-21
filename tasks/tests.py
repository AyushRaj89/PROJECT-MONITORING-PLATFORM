from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.testutils import PASSWORD, ROLE_MANAGER, ROLE_MEMBER, ROLE_VIEWER, make_user, setup_roles
from projects.models import Milestone, Project, ProjectMember

from .models import Task, TaskComment


class TaskTestBase(TestCase):
    def setUp(self):
        setup_roles()
        self.manager = make_user("mgr", ROLE_MANAGER)
        self.dev = make_user("dev", ROLE_MEMBER)
        self.dev2 = make_user("dev2", ROLE_MEMBER)
        self.viewer = make_user("view", ROLE_VIEWER)
        self.outsider = make_user("out", ROLE_MEMBER)
        self.project = Project.objects.create(name="Alpha", code="ALPHA", manager=self.manager)
        self.other_project = Project.objects.create(name="Other", code="OTH", manager=self.manager)
        for u in (self.dev, self.dev2, self.viewer):
            ProjectMember.objects.create(project=self.project, user=u)
        self.today = timezone.localdate()

    def login(self, username):
        self.client.login(username=username, password=PASSWORD)

    def new_task(self, **kw):
        defaults = {"project": self.project, "title": "Build API", "created_by": self.manager, "assignee": self.dev}
        defaults.update(kw)
        return Task.objects.create(**defaults)


class TaskCreateTests(TaskTestBase):
    def url(self):
        return reverse("tasks:create", args=[self.project.pk])

    def test_member_creates_task(self):
        self.login("dev")
        res = self.client.post(
            self.url(),
            {"title": "Write docs", "assignee": self.dev2.pk, "status": "todo", "priority": "high", "estimated_hours": "3"},
        )
        task = Task.objects.get(title="Write docs")
        self.assertRedirects(res, task.get_absolute_url())
        self.assertEqual((task.project, task.created_by, task.assignee), (self.project, self.dev, self.dev2))

    def test_assignee_and_milestone_must_belong_to_project(self):
        foreign = Milestone.objects.create(project=self.other_project, title="M", due_date=self.today)
        self.login("mgr")
        res = self.client.post(
            self.url(),
            {"title": "X", "assignee": self.outsider.pk, "milestone": foreign.pk, "status": "todo", "priority": "low"},
        )
        self.assertIn("assignee", res.context["form"].errors)
        self.assertIn("milestone", res.context["form"].errors)

    def test_past_due_date_rejected_for_new_task(self):
        self.login("mgr")
        past = (self.today - timedelta(days=2)).isoformat()
        res = self.client.post(self.url(), {"title": "X", "status": "todo", "priority": "low", "due_date": past})
        self.assertIn("due_date", res.context["form"].errors)

    def test_viewer_and_outsider_cannot_create(self):
        self.login("view")
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        self.login("out")
        self.assertEqual(self.client.get(self.url()).status_code, 404)


class TaskUpdateTests(TaskTestBase):
    def test_assignee_marks_done_sets_completed_and_progress(self):
        task = self.new_task()
        self.login("dev")
        res = self.client.post(reverse("tasks:set_status", args=[task.pk]), {"status": "done"})
        self.assertRedirects(res, task.get_absolute_url())
        task.refresh_from_db()
        self.assertIsNotNone(task.completed_at)
        self.assertEqual(self.project.progress, 100)
        self.client.post(reverse("tasks:set_status", args=[task.pk]), {"status": "todo"})
        task.refresh_from_db()
        self.assertIsNone(task.completed_at)

    def test_invalid_status_is_rejected(self):
        task = self.new_task()
        self.login("dev")
        self.client.post(reverse("tasks:set_status", args=[task.pk]), {"status": "nonsense"})
        task.refresh_from_db()
        self.assertEqual(task.status, "todo")

    def test_unrelated_member_cannot_edit_or_delete(self):
        task = self.new_task()
        self.login("dev2")
        self.assertEqual(self.client.get(reverse("tasks:update", args=[task.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("tasks:delete", args=[task.pk])).status_code, 403)

    def test_status_change_requires_post(self):
        task = self.new_task()
        self.login("dev")
        self.assertEqual(self.client.get(reverse("tasks:set_status", args=[task.pk])).status_code, 405)

    def test_manager_edits_and_deletes(self):
        task = self.new_task()
        self.login("mgr")
        res = self.client.post(
            reverse("tasks:update", args=[task.pk]),
            {"title": "Renamed", "assignee": self.dev2.pk, "status": "in_progress", "priority": "high"},
        )
        self.assertRedirects(res, task.get_absolute_url())
        task.refresh_from_db()
        self.assertEqual((task.title, task.assignee), ("Renamed", self.dev2))
        res = self.client.post(reverse("tasks:delete", args=[task.pk]))
        self.assertRedirects(res, self.project.get_absolute_url())
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())


class CommentTests(TaskTestBase):
    def test_member_can_comment_viewer_cannot(self):
        task = self.new_task()
        url = reverse("tasks:comment_add", args=[task.pk])
        self.login("dev2")
        self.client.post(url, {"body": "Looks good"})
        self.assertEqual(TaskComment.objects.get().author, self.dev2)
        self.client.post(url, {"body": "x"})  # too short
        self.assertEqual(TaskComment.objects.count(), 1)
        self.login("view")
        self.assertEqual(self.client.post(url, {"body": "Hello there"}).status_code, 403)
        ctx = self.client.get(reverse("tasks:detail", args=[task.pk])).context
        self.assertFalse(ctx["can_comment"])


class TaskListTests(TaskTestBase):
    def test_filters(self):
        self.new_task(title="Late one", due_date=self.today - timedelta(days=3), assignee=self.dev)
        self.new_task(title="Mine done", status="done", assignee=self.dev)
        self.new_task(title="Unassigned", assignee=None, priority="critical")
        self.login("dev")
        def titles(**params):
            return sorted(t.title for t in self.client.get(reverse("tasks:list"), params).context["tasks"])
        self.assertEqual(titles(overdue="on"), ["Late one"])
        self.assertEqual(titles(assignee="none"), ["Unassigned"])
        self.assertEqual(titles(assignee="me", status="done"), ["Mine done"])
        self.assertEqual(titles(priority="critical"), ["Unassigned"])
        self.assertEqual(titles(q="late"), ["Late one"])

    def test_outsider_sees_nothing_and_my_tasks_grouping(self):
        self.new_task(title="A", assignee=self.dev)
        self.new_task(title="B", assignee=self.dev, status="done")
        self.login("out")
        self.assertEqual(len(self.client.get(reverse("tasks:list")).context["tasks"]), 0)
        self.login("dev")
        ctx = self.client.get(reverse("tasks:mine")).context
        self.assertEqual(ctx["open_count"], 1)
        self.assertEqual([t.title for t in ctx["grouped"]["Done"]], ["B"])
