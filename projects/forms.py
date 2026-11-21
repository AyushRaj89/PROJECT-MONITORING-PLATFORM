from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from accounts.roles import ROLE_MANAGER

from .models import Milestone, Project, ProjectMember

User = get_user_model()

DATE_INPUT = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


def _label(user):
    return user.get_full_name() or user.username


class ProjectForm(forms.ModelForm):
    """Create / edit a project. Only admins can pick the manager; for a manager
    the field is removed and the view assigns the logged-in user."""

    class Meta:
        model = Project
        fields = [
            "name", "code", "description", "client_name", "manager", "status", "health",
            "start_date", "end_date", "budget", "actual_cost",
        ]
        widgets = {"start_date": DATE_INPUT, "end_date": DATE_INPUT}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None and not user.is_superuser:
            del self.fields["manager"]
        else:
            managers = User.objects.filter(Q(groups__name=ROLE_MANAGER) | Q(is_superuser=True)).distinct()
            self.fields["manager"].queryset = managers
            self.fields["manager"].label_from_instance = _label

    def clean_code(self):
        return self.cleaned_data["code"].upper()

    def clean_budget(self):
        value = self.cleaned_data["budget"]
        if value < 0:
            raise forms.ValidationError("Budget cannot be negative.")
        return value

    def clean_actual_cost(self):
        value = self.cleaned_data["actual_cost"]
        if value < 0:
            raise forms.ValidationError("Actual cost cannot be negative.")
        return value

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "End date cannot be before the start date.")
        return cleaned


class ProjectFilterForm(forms.Form):
    """GET form (Unit IV): search + filter + sort the project list."""

    SORT_CHOICES = [
        ("-created_at", "Newest first"),
        ("name", "Name A-Z"),
        ("end_date", "Deadline (soonest)"),
        ("-budget", "Budget (highest)"),
    ]

    q = forms.CharField(required=False, label="Search")
    status = forms.ChoiceField(required=False, choices=[("", "All statuses")] + Project.STATUS_CHOICES)
    health = forms.ChoiceField(required=False, choices=[("", "Any health")] + Project.HEALTH_CHOICES)
    sort = forms.ChoiceField(required=False, choices=SORT_CHOICES)


class MemberForm(forms.ModelForm):
    class Meta:
        model = ProjectMember
        fields = ["user", "role_in_project"]

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        candidates = (
            User.objects.filter(is_active=True)
            .exclude(pk=project.manager_id)
            .exclude(project_memberships__project=project)
            .order_by("username")
        )
        self.fields["user"].queryset = candidates
        self.fields["user"].label_from_instance = _label

    def save(self, commit=True):
        member = super().save(commit=False)
        member.project = self.project
        if commit:
            member.save()
        return member


class MilestoneForm(forms.ModelForm):
    class Meta:
        model = Milestone
        fields = ["title", "description", "due_date", "status"]
        widgets = {"due_date": DATE_INPUT}

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project

    def clean_due_date(self):
        due = self.cleaned_data["due_date"]
        if self.project.start_date and due < self.project.start_date:
            raise forms.ValidationError("Milestone cannot be due before the project starts.")
        return due

    def save(self, commit=True):
        milestone = super().save(commit=False)
        milestone.project = self.project
        if commit:
            milestone.save()
        return milestone
