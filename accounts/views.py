from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .decorators import superuser_required
from .forms import ProfileForm, RegisterForm, RoleForm, UserUpdateForm
from .models import Profile
from .roles import ALL_ROLES, ROLE_MEMBER, user_role

User = get_user_model()


def register(request):
    """Sign up. New users always start as 'Team Member'; an admin can promote them."""
    if request.user.is_authenticated:
        return redirect("monitoring:dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            group, _ = Group.objects.get_or_create(name=ROLE_MEMBER)
            user.groups.add(group)
            login(request, user)
            messages.success(request, "Welcome! Your account has been created.")
            return redirect("monitoring:dashboard")  # POST -> redirect (Unit IV)
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    """View and edit your own details."""
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=profile_obj)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile")
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileForm(instance=profile_obj)
    return render(
        request,
        "accounts/profile.html",
        {"user_form": user_form, "profile_form": profile_form, "role": user_role(request.user)},
    )


@superuser_required
def user_list(request):
    """Admin-only: list users with their role so roles can be changed."""
    users = User.objects.prefetch_related("groups").order_by("username")
    rows = [{"user": u, "role": user_role(u), "form": RoleForm(initial={"role": user_role(u)})} for u in users]
    return render(request, "accounts/user_list.html", {"rows": rows, "roles": ALL_ROLES})


@superuser_required
@require_POST
def change_role(request, pk):
    target = get_object_or_404(User, pk=pk)
    form = RoleForm(request.POST)
    if target.is_superuser:
        messages.error(request, "Admin accounts are managed from the Django admin site.")
    elif form.is_valid():
        target.groups.remove(*Group.objects.filter(name__in=ALL_ROLES))
        group, _ = Group.objects.get_or_create(name=form.cleaned_data["role"])
        target.groups.add(group)
        messages.success(request, f"{target.username} is now {group.name}.")
    else:
        messages.error(request, "Invalid role.")
    return redirect("accounts:user_list")
