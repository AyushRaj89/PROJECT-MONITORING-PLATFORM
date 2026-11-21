from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from projects.models import Project

from .models import Task, TaskComment

User = get_user_model()

DATE_INPUT = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


def _label(user):
    return user.get_full_name() or user.username


def project_people(project):
    """Users who belong to a project: its manager plus its team members."""
    return User.objects.filter(
        Q(pk=project.manager_id) | Q(project_memberships__project=project), is_active=True
    ).distinct()


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "assignee", "milestone", "status", "priority", "due_date", "estimated_hours"]
        widgets = {"due_date": DATE_INPUT}

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        # only people / milestones of THIS project can be chosen
        self.fields["assignee"].queryset = project_people(project)
        self.fields["assignee"].label_from_instance = _label
        self.fields["milestone"].queryset = project.milestones.all()

    def clean_due_date(self):
        due = self.cleaned_data.get("due_date")
        is_new = self.instance.pk is None
        if due and is_new and due < timezone.localdate():
            raise forms.ValidationError("Due date cannot be in the past.")
        return due

    def clean_estimated_hours(self):
        hours = self.cleaned_data.get("estimated_hours")
        if hours is not None and hours <= 0:
            raise forms.ValidationError("Estimated hours must be greater than zero.")
        return hours

    def save(self, commit=True):
        task = super().save(commit=False)
        task.project = self.project
        if commit:
            task.save()
        return task


class TaskFilterForm(forms.Form):
    """GET form (Unit IV) for the task list."""

    ASSIGNEE_CHOICES = [("", "Anyone"), ("me", "Assigned to me"), ("none", "Unassigned")]

    q = forms.CharField(required=False, label="Search")
    project = forms.ModelChoiceField(queryset=Project.objects.none(), required=False, empty_label="All projects")
    status = forms.ChoiceField(required=False, choices=[("", "Any status")] + Task.STATUS_CHOICES)
    priority = forms.ChoiceField(required=False, choices=[("", "Any priority")] + Task.PRIORITY_CHOICES)
    assignee = forms.ChoiceField(required=False, choices=ASSIGNEE_CHOICES)
    overdue = forms.BooleanField(required=False, label="Overdue only")

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.visible_to(user)


class TaskStatusForm(forms.Form):
    status = forms.ChoiceField(choices=Task.STATUS_CHOICES)


class TaskCommentForm(forms.ModelForm):
    class Meta:
        model = TaskComment
        fields = ["body"]

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if len(body) < 2:
            raise forms.ValidationError("Comment is too short.")
        return body
