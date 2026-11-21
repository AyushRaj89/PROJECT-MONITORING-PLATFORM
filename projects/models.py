from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone


class ProjectQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Superusers see every project; others see projects they manage or belong to."""
        if user.is_superuser:
            return self
        return self.filter(Q(manager=user) | Q(members__user=user)).distinct()


class Project(models.Model):
    STATUS_CHOICES = [
        ("planning", "Planning"),
        ("active", "Active"),
        ("on_hold", "On Hold"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    HEALTH_CHOICES = [("green", "On track"), ("amber", "At risk"), ("red", "Off track")]

    name = models.CharField(max_length=200)
    code = models.SlugField(max_length=30, unique=True, help_text="Short unique key, e.g. PMP-01")
    description = models.TextField(blank=True)
    client_name = models.CharField(max_length=200, blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="managed_projects"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planning")
    health = models.CharField(max_length=10, choices=HEALTH_CHOICES, default="green")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    actual_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProjectQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_absolute_url(self):
        return reverse("projects:detail", args=[self.pk])

    @property
    def is_overdue(self):
        return bool(
            self.end_date
            and self.end_date < timezone.localdate()
            and self.status not in ("completed", "cancelled")
        )

    @property
    def progress(self):
        """Percent of tasks that are done (0-100); 0 when there are no tasks."""
        total = self.tasks.count()
        if not total:
            return 0
        return round(self.tasks.filter(status="done").count() * 100 / total)

    @property
    def budget_used_percent(self):
        if not self.budget:
            return 0
        return round(float(self.actual_cost) * 100 / float(self.budget), 1)

    def is_member(self, user):
        """True for the manager and anyone added as a team member."""
        return self.manager_id == user.id or self.members.filter(user=user).exists()


class ProjectMember(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships"
    )
    role_in_project = models.CharField(max_length=100, blank=True, help_text="e.g. Backend Dev, QA")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "user")
        ordering = ["joined_at"]

    def __str__(self):
        return f"{self.user} in {self.project.code}"


class Milestone(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("achieved", "Achieved"),
        ("missed", "Missed"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    completed_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["due_date"]

    def __str__(self):
        return f"{self.project.code}: {self.title}"

    def save(self, *args, **kwargs):
        if self.status == "achieved" and not self.completed_at:
            self.completed_at = timezone.localdate()
        elif self.status != "achieved":
            self.completed_at = None
        super().save(*args, **kwargs)
