import json

from django.test import TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from accounts.testutils import PASSWORD, ROLE_MANAGER, ROLE_MEMBER, ROLE_VIEWER, make_user, setup_roles
from projects.models import Project, ProjectMember
from tasks.models import Task

from .models import Issue, ProgressUpdate


class MonitoringTestBase(TestCase):
    def setUp(self):
        setup_roles()
        self.manager = make_user("mgr", ROLE_MANAGER)
        self.dev = make_user("dev", ROLE_MEMBER)
        self.viewer = make_user("view", ROLE_VIEWER)
        self.outsider = make_user("out", ROLE_MEMBER)
        self.project = Project.objects.create(name="Alpha", code="ALPHA", manager=self.manager, status="active")
        for u in (self.dev, self.viewer):
            ProjectMember.objects.create(project=self.project, user=u)

    def login(self, username):
        self.client.login(username=username, password=PASSWORD)


class DashboardTests(MonitoringTestBase):
    def test_dashboard_summary(self):
        Task.objects.create(project=self.project, title="T1", assignee=self.dev, status="done")
        Task.objects.create(project=self.project, title="T2", assignee=self.dev)
        Issue.objects.create(project=self.project, title="Down", severity="critical", reported_by=self.dev)
        self.login("dev")
        summary = self.client.get(reverse("monitoring:dashboard")).context["summary"]
        self.assertEqual(summary["projects_total"], 1)
        self.assertEqual(summary["my_open_tasks"], 1)
        self.assertEqual(summary["tasks_by_status"]["done"], 1)
        self.assertEqual(summary["issues_critical"], 1)

    def test_counts_not_inflated_by_multiple_members(self):
        # Alpha has two members; a join must not duplicate the project in totals.
        self.login("mgr")
        summary = self.client.get(reverse("monitoring:dashboard")).context["summary"]
        self.assertEqual(summary["projects_total"], 1)
        self.assertEqual(sum(summary["projects_by_status"].values()), 1)

    def test_outsider_dashboard_is_empty(self):
        self.login("out")
        summary = self.client.get(reverse("monitoring:dashboard")).context["summary"]
        self.assertEqual((summary["projects_total"], summary["tasks_total"]), (0, 0))

    def test_json_endpoints(self):
        Task.objects.create(project=self.project, title="T1", status="done")
        self.login("dev")
        data = json.loads(self.client.get(reverse("monitoring:dashboard_data")).content)
        self.assertEqual(data["projects_total"], 1)
        data = json.loads(self.client.get(reverse("monitoring:project_data", args=[self.project.pk])).content)
        self.assertEqual((data["code"], data["progress"]), ("ALPHA", 100))
        self.login("out")
        self.assertEqual(self.client.get(reverse("monitoring:project_data", args=[self.project.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("monitoring:dashboard_data")).status_code, 405)


class ProgressUpdateTests(MonitoringTestBase):
    def test_member_posts_update_and_health_changes(self):
        self.login("dev")
        url = reverse("monitoring:update_create", args=[self.project.pk])
        res = self.client.post(url, {"summary": "Week one finished", "percent_complete": 25, "health": "amber"})
        self.assertRedirects(res, self.project.get_absolute_url())
        self.assertEqual(ProgressUpdate.objects.get().author, self.dev)
        self.project.refresh_from_db()
        self.assertEqual(self.project.health, "amber")

    def test_validation_and_permissions(self):
        self.login("dev")
        url = reverse("monitoring:update_create", args=[self.project.pk])
        res = self.client.post(url, {"summary": "short", "percent_complete": 150})
        self.assertIn("summary", res.context["form"].errors)
        self.assertIn("percent_complete", res.context["form"].errors)
        self.login("view")
        self.assertEqual(self.client.get(url).status_code, 403)
        self.login("out")
        self.assertEqual(self.client.get(url).status_code, 404)


class IssueTests(MonitoringTestBase):
    def test_report_edit_resolve_issue(self):
        self.login("dev")
        res = self.client.post(
            reverse("monitoring:issue_create", args=[self.project.pk]),
            {"title": "Login broken", "severity": "high", "status": "open", "owner": self.manager.pk},
        )
        self.assertRedirects(res, reverse("monitoring:issue_list"))
        issue = Issue.objects.get()
        self.assertEqual(issue.reported_by, self.dev)
        self.client.post(
            reverse("monitoring:issue_update", args=[issue.pk]),
            {"title": "Login broken", "severity": "high", "status": "resolved", "owner": self.manager.pk},
        )
        issue.refresh_from_db()
        self.assertIsNotNone(issue.resolved_at)

    def test_owner_must_be_project_member_and_unrelated_cannot_edit(self):
        self.login("dev")
        res = self.client.post(
            reverse("monitoring:issue_create", args=[self.project.pk]),
            {"title": "X", "severity": "low", "status": "open", "owner": self.outsider.pk},
        )
        self.assertIn("owner", res.context["form"].errors)
        issue = Issue.objects.create(project=self.project, title="Mgr issue", reported_by=self.manager)
        self.assertEqual(self.client.get(reverse("monitoring:issue_update", args=[issue.pk])).status_code, 403)

    def test_list_filters(self):
        Issue.objects.create(project=self.project, title="A", severity="critical")
        Issue.objects.create(project=self.project, title="B", severity="low")
        self.login("dev")
        res = self.client.get(reverse("monitoring:issue_list"), {"severity": "critical"})
        self.assertEqual([i.title for i in res.context["issues"]], ["A"])


class ReportTests(MonitoringTestBase):
    def test_year_report_regex_url(self):
        year = timezone.localdate().year
        Task.objects.create(project=self.project, title="Done", status="done")
        self.login("dev")
        res = self.client.get(f"/reports/{year}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["total"], 1)
        self.assertEqual(len(res.context["rows"]), 12)
        self.assertEqual(resolve(f"/reports/{year}/").url_name, "year_report")
        # the regular expression only accepts exactly four digits
        self.assertEqual(self.client.get("/reports/26/").status_code, 404)
        self.assertEqual(self.client.get("/reports/20266/").status_code, 404)
        self.assertEqual(self.client.get("/reports/1850/").status_code, 404)

    def test_csv_export(self):
        Task.objects.create(project=self.project, title="Row one", assignee=self.dev)
        self.login("dev")
        res = self.client.get(reverse("monitoring:tasks_csv", args=[self.project.pk]))
        self.assertEqual(res["Content-Type"], "text/csv")
        self.assertIn("ALPHA-tasks.csv", res["Content-Disposition"])
        self.assertIn("Row one", res.content.decode())
        self.login("out")
        self.assertEqual(self.client.get(reverse("monitoring:tasks_csv", args=[self.project.pk])).status_code, 404)


class ErrorPageTests(MonitoringTestBase):
    def test_custom_404_template(self):
        self.login("dev")
        res = self.client.get("/no/such/page/")
        self.assertEqual(res.status_code, 404)
        self.assertTemplateUsed(res, "errors/404.html")

    def test_custom_403_template(self):
        self.login("view")
        res = self.client.get(reverse("projects:create"))
        self.assertEqual(res.status_code, 403)
        self.assertTemplateUsed(res, "errors/403.html")
