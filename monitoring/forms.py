from django import forms

from projects.models import Project
from tasks.forms import DATE_INPUT, project_people

from .models import Issue, ProgressUpdate


class ProgressUpdateForm(forms.ModelForm):
    class Meta:
        model = ProgressUpdate
        fields = ["summary", "blockers", "percent_complete", "health"]

    def clean_summary(self):
        summary = self.cleaned_data["summary"].strip()
        if len(summary) < 10:
            raise forms.ValidationError("Please write at least 10 characters.")
        return summary


class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ["title", "description", "severity", "status", "owner", "due_date"]
        widgets = {"due_date": DATE_INPUT}

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.fields["owner"].queryset = project_people(project)
        self.fields["owner"].label_from_instance = lambda u: u.get_full_name() or u.username

    def save(self, commit=True):
        issue = super().save(commit=False)
        issue.project = self.project
        if commit:
            issue.save()
        return issue


class IssueFilterForm(forms.Form):
    """GET form for the issue list."""

    q = forms.CharField(required=False, label="Search")
    project = forms.ModelChoiceField(queryset=Project.objects.none(), required=False, empty_label="All projects")
    severity = forms.ChoiceField(required=False, choices=[("", "Any severity")] + Issue.SEVERITY_CHOICES)
    status = forms.ChoiceField(required=False, choices=[("", "Any status")] + Issue.STATUS_CHOICES)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.visible_to(user)
