from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

from projects.models import Project


class ProgressUpdate(models.Model):
    """A status report a team member posts against a project."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="progress_updates")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    summary = models.TextField()
    blockers = models.TextField(blank=True)
    percent_complete = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    health = models.CharField(
        max_length=10, choices=Project.HEALTH_CHOICES, blank=True,
        help_text="If chosen, the project's health is updated to this value.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.project.code} update {self.created_at:%Y-%m-%d}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.health:  # a report can change the project's overall health
            Project.objects.filter(pk=self.project_id).update(health=self.health)


class Issue(models.Model):
    SEVERITY_CHOICES = [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")]
    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="issues")
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="reported_issues"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_issues"
    )
    due_date = models.DateField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.project.code}] {self.title}"

    def get_absolute_url(self):
        return reverse("monitoring:issue_update", args=[self.pk])

    def save(self, *args, **kwargs):
        if self.status in ("resolved", "closed"):
            self.resolved_at = self.resolved_at or timezone.now()
        else:
            self.resolved_at = None
        super().save(*args, **kwargs)
