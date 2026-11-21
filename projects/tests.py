from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.testutils import PASSWORD, ROLE_MANAGER, ROLE_MEMBER, ROLE_VIEWER, make_user, setup_roles

from .models import Milestone, Project, ProjectMember


class ProjectTestBase(TestCase):
    def setUp(self):
        setup_roles()
        self.admin = make_user("boss", superuser=True)
        self.manager = make_user("mgr", ROLE_MANAGER)
        self.other_manager = make_user("mgr2", ROLE_MANAGER)
        self.dev = make_user("dev", ROLE_MEMBER)
        self.viewer = make_user("view", ROLE_VIEWER)
        self.outsider = make_user("out", ROLE_MEMBER)
        self.project = Project.objects.create(name="Alpha", code="ALPHA", manager=self.manager)
        ProjectMember.objects.create(project=self.project, user=self.dev)
        ProjectMember.objects.create(project=self.project, user=self.viewer)

    def login(self, username):
        self.client.login(username=username, password=PASSWORD)


class ProjectCrudTests(ProjectTestBase):
    def test_team_member_cannot_create_project(self):
        self.login("dev")
        self.assertEqual(self.client.get(reverse("projects:create")).status_code, 403)

    def test_manager_creates_project_and_is_set_as_manager(self):
        self.login("mgr")
        res = self.client.post(
            reverse("projects:create"),
            {"name": "Beta", "code": "beta-1", "status": "planning", "health": "green", "budget": "500", "actual_cost": "0"},
        )
        project = Project.objects.get(name="Beta")
        self.assertRedirects(res, project.get_absolute_url())
        self.assertEqual(project.manager, self.manager)
        self.assertEqual(project.code, "BETA-1")  # clean_code upper-cases

    def test_form_validation(self):
        self.login("mgr")
        res = self.client.post(
            reverse("projects:create"),
            {"name": "Bad", "code": "ALPHA", "status": "planning", "health": "green", "budget": "-5",
             "actual_cost": "0", "start_date": "2026-05-10", "end_date": "2026-05-01"},
        )
        errors = res.context["form"].errors
        self.assertIn("code", errors)       # duplicate
        self.assertIn("budget", errors)     # negative
        self.assertIn("end_date", errors)   # before start

    def test_only_own_manager_can_edit_and_delete(self):
        self.login("mgr2")
        self.assertEqual(self.client.get(reverse("projects:update", args=[self.project.pk])).status_code, 404)
        self.login("dev")
        self.assertEqual(self.client.get(reverse("projects:update", args=[self.project.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("projects:delete", args=[self.project.pk])).status_code, 403)

    def test_manager_edit_and_delete(self):
        self.login("mgr")
        res = self.client.post(
            reverse("projects:update", args=[self.project.pk]),
            {"name": "Alpha 2", "code": "ALPHA", "status": "active", "health": "amber", "budget": "10", "actual_cost": "1"},
        )
        self.assertRedirects(res, self.project.get_absolute_url())
        self.project.refresh_from_db()
        self.assertEqual((self.project.name, self.project.health, self.project.manager), ("Alpha 2", "amber", self.manager))
        # GET shows confirmation; only POST deletes
        self.assertEqual(self.client.get(reverse("projects:delete", args=[self.project.pk])).status_code, 200)
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())
        self.client.post(reverse("projects:delete", args=[self.project.pk]))
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())


class VisibilityTests(ProjectTestBase):
    def test_outsider_gets_404_members_get_200_admin_sees_all(self):
        url = reverse("projects:detail", args=[self.project.pk])
        self.login("out")
        self.assertEqual(self.client.get(url).status_code, 404)
        self.login("dev")
        self.assertEqual(self.client.get(url).status_code, 200)
        self.login("boss")
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_list_only_shows_visible_projects(self):
        Project.objects.create(name="Secret", code="SEC", manager=self.other_manager)
        self.login("dev")
        names = [p.name for p in self.client.get(reverse("projects:list")).context["projects"]]
        self.assertEqual(names, ["Alpha"])

    def test_list_filters_and_search(self):
        Project.objects.create(name="Gamma", code="GAM", manager=self.manager, status="active")
        self.login("mgr")
        res = self.client.get(reverse("projects:list"), {"status": "active"})
        self.assertEqual([p.name for p in res.context["projects"]], ["Gamma"])
        res = self.client.get(reverse("projects:list"), {"q": "alp"})
        self.assertEqual([p.name for p in res.context["projects"]], ["Alpha"])

    def test_detail_context(self):
        self.login("mgr")
        ctx = self.client.get(reverse("projects:detail", args=[self.project.pk])).context
        self.assertTrue(ctx["can_manage"])
        self.assertEqual(set(ctx["task_counts"]), {"todo", "in_progress", "review", "blocked", "done"})
        self.login("dev")
        ctx = self.client.get(reverse("projects:detail", args=[self.project.pk])).context
        self.assertFalse(ctx["can_manage"])
        self.assertTrue(ctx["can_contribute"])
        self.login("view")
        self.assertFalse(self.client.get(reverse("projects:detail", args=[self.project.pk])).context["can_contribute"])


class MemberAndMilestoneTests(ProjectTestBase):
    def test_add_and_remove_member(self):
        self.login("mgr")
        res = self.client.post(
            reverse("projects:member_add", args=[self.project.pk]), {"user": self.outsider.pk, "role_in_project": "QA"}
        )
        self.assertRedirects(res, self.project.get_absolute_url())
        member = ProjectMember.objects.get(project=self.project, user=self.outsider)
        url = reverse("projects:member_remove", args=[self.project.pk, member.pk])
        self.assertEqual(self.client.get(url).status_code, 405)      # POST only
        self.client.post(url)
        self.assertFalse(ProjectMember.objects.filter(pk=member.pk).exists())

    def test_cannot_add_existing_member_or_manager(self):
        self.login("mgr")
        for user in (self.dev, self.manager):
            res = self.client.post(reverse("projects:member_add", args=[self.project.pk]), {"user": user.pk})
            self.assertIn("user", res.context["form"].errors)

    def test_team_member_cannot_add_members(self):
        self.login("dev")
        res = self.client.post(reverse("projects:member_add", args=[self.project.pk]), {"user": self.outsider.pk})
        self.assertEqual(res.status_code, 403)

    def test_milestone_lifecycle_and_validation(self):
        self.project.start_date = date(2026, 1, 10)
        self.project.save()
        self.login("mgr")
        url = reverse("projects:milestone_create", args=[self.project.pk])
        bad = self.client.post(url, {"title": "Too early", "due_date": "2026-01-01", "status": "pending"})
        self.assertIn("due_date", bad.context["form"].errors)
        self.client.post(url, {"title": "Beta", "due_date": "2026-03-01", "status": "pending"})
        milestone = Milestone.objects.get(title="Beta")
        self.client.post(
            reverse("projects:milestone_update", args=[milestone.pk]),
            {"title": "Beta", "due_date": "2026-03-01", "status": "achieved"},
        )
        milestone.refresh_from_db()
        self.assertIsNotNone(milestone.completed_at)
        self.client.post(reverse("projects:milestone_delete", args=[milestone.pk]))
        self.assertFalse(Milestone.objects.filter(pk=milestone.pk).exists())


class SessionAndCookieTests(ProjectTestBase):
    def test_recent_projects_stored_in_session(self):
        other = Project.objects.create(name="Other", code="OTH", manager=self.manager)
        self.login("mgr")
        self.client.get(reverse("projects:detail", args=[self.project.pk]))
        self.client.get(reverse("projects:detail", args=[other.pk]))
        self.client.get(reverse("projects:detail", args=[self.project.pk]))
        self.assertEqual(self.client.session["recent_projects"], [self.project.pk, other.pk])
        recent = self.client.get(reverse("projects:list")).context["recent_projects"]
        self.assertEqual([p.pk for p in recent], [self.project.pk, other.pk])

    def test_view_mode_cookie(self):
        self.login("mgr")
        res = self.client.post(reverse("projects:set_view_mode"), {"mode": "table", "next": reverse("projects:list")})
        self.assertRedirects(res, reverse("projects:list"))
        self.assertEqual(res.cookies["view_mode"].value, "table")
        self.assertEqual(self.client.get(reverse("projects:list")).context["view_mode"], "table")

    def test_invalid_view_mode_and_open_redirect(self):
        self.login("mgr")
        self.assertEqual(self.client.post(reverse("projects:set_view_mode"), {"mode": "evil"}).status_code, 400)
        res = self.client.post(reverse("projects:set_view_mode"), {"mode": "card", "next": "https://evil.example/"})
        self.assertRedirects(res, reverse("projects:list"))
