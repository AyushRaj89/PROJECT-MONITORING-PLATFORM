from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Profile
from .roles import ROLE_MANAGER, ROLE_MEMBER, ROLE_VIEWER, user_role
from .testutils import PASSWORD, make_user, setup_roles

User = get_user_model()


class AuthTests(TestCase):
    def setUp(self):
        setup_roles()

    def test_anonymous_is_redirected_to_login(self):
        res = self.client.get(reverse("projects:list"))
        self.assertRedirects(res, f"{reverse('accounts:login')}?next={reverse('projects:list')}")

    def test_login_and_logout(self):
        make_user("ayush", ROLE_MEMBER)
        res = self.client.post(reverse("accounts:login"), {"username": "ayush", "password": PASSWORD})
        self.assertRedirects(res, reverse("monitoring:dashboard"))
        self.assertEqual(self.client.get(reverse("monitoring:dashboard")).status_code, 200)
        self.client.post(reverse("accounts:logout"))
        self.assertEqual(self.client.get(reverse("monitoring:dashboard")).status_code, 302)

    def test_wrong_password_shows_form_errors(self):
        make_user("ayush", ROLE_MEMBER)
        res = self.client.post(reverse("accounts:login"), {"username": "ayush", "password": "nope"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.context["form"].non_field_errors())


class RegistrationTests(TestCase):
    def setUp(self):
        setup_roles()

    def data(self, **extra):
        base = {
            "username": "newbie", "first_name": "New", "last_name": "Bie", "email": "new@example.com",
            "phone": "+91 98765 43210", "designation": "Developer",
            "password1": "S3cure-pass-77", "password2": "S3cure-pass-77",
        }
        base.update(extra)
        return base

    def test_register_creates_member_with_profile_and_logs_in(self):
        res = self.client.post(reverse("accounts:register"), self.data())
        self.assertRedirects(res, reverse("monitoring:dashboard"))
        user = User.objects.get(username="newbie")
        self.assertEqual(user_role(user), ROLE_MEMBER)
        self.assertEqual(Profile.objects.get(user=user).designation, "Developer")
        self.assertEqual(self.client.get(reverse("monitoring:dashboard")).status_code, 200)

    def test_duplicate_email_and_bad_phone_rejected(self):
        make_user("other", ROLE_MEMBER)
        res = self.client.post(reverse("accounts:register"), self.data(email="OTHER@example.com", phone="abc"))
        self.assertEqual(res.status_code, 200)
        self.assertIn("email", res.context["form"].errors)
        self.assertIn("phone", res.context["form"].errors)
        self.assertFalse(User.objects.filter(username="newbie").exists())

    def test_password_mismatch_rejected(self):
        res = self.client.post(reverse("accounts:register"), self.data(password2="different-pass-1"))
        self.assertIn("password2", res.context["form"].errors)

    def test_csrf_is_enforced(self):
        from django.test import Client

        strict = Client(enforce_csrf_checks=True)
        self.assertEqual(strict.post(reverse("accounts:register"), self.data()).status_code, 403)


class ProfileAndRoleTests(TestCase):
    def setUp(self):
        setup_roles()
        self.admin = make_user("boss", superuser=True)
        self.manager = make_user("mgr", ROLE_MANAGER)
        self.dev = make_user("dev", ROLE_MEMBER)

    def test_profile_update(self):
        self.client.login(username="dev", password=PASSWORD)
        res = self.client.post(
            reverse("accounts:profile"),
            {"first_name": "Dev", "last_name": "Eloper", "email": "dev@new.com", "phone": "9876543210", "designation": "QA"},
        )
        self.assertRedirects(res, reverse("accounts:profile"))
        self.dev.refresh_from_db()
        self.assertEqual(self.dev.email, "dev@new.com")
        self.assertEqual(self.dev.profile.designation, "QA")

    def test_admin_can_change_role(self):
        self.client.login(username="boss", password=PASSWORD)
        res = self.client.post(reverse("accounts:change_role", args=[self.dev.pk]), {"role": ROLE_VIEWER})
        self.assertRedirects(res, reverse("accounts:user_list"))
        self.assertEqual(user_role(User.objects.get(pk=self.dev.pk)), ROLE_VIEWER)
        self.assertEqual(self.client.get(reverse("accounts:user_list")).status_code, 200)

    def test_manager_cannot_manage_users(self):
        self.client.login(username="mgr", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("accounts:user_list")).status_code, 403)
        res = self.client.post(reverse("accounts:change_role", args=[self.dev.pk]), {"role": ROLE_MANAGER})
        self.assertEqual(res.status_code, 403)

    def test_role_context_available_in_templates(self):
        self.client.login(username="mgr", password=PASSWORD)
        res = self.client.get(reverse("monitoring:dashboard"))
        self.assertEqual(res.context["user_role"], ROLE_MANAGER)
        self.assertTrue(res.context["is_manager"])
