from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator

from .models import Profile
from .roles import ALL_ROLES

User = get_user_model()

phone_validator = RegexValidator(r"^\+?[0-9 \-]{7,15}$", "Enter a valid phone number (7-15 digits).")


class RegisterForm(UserCreationForm):
    """Sign-up form: built-in UserCreationForm + email, names and profile fields."""

    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20, required=False, validators=[phone_validator])
    designation = forms.CharField(max_length=100, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            Profile.objects.update_or_create(
                user=user,
                defaults={
                    "phone": self.cleaned_data.get("phone", ""),
                    "designation": self.cleaned_data.get("designation", ""),
                },
            )
        return user


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is used by another account.")
        return email


class ProfileForm(forms.ModelForm):
    phone = forms.CharField(max_length=20, required=False, validators=[phone_validator])

    class Meta:
        model = Profile
        fields = ("phone", "designation")


class RoleForm(forms.Form):
    role = forms.ChoiceField(choices=[(r, r) for r in ALL_ROLES])
