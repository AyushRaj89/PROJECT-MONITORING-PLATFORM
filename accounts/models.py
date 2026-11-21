from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Extra details for a user (one-to-one with the built-in User)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20, blank=True)
    designation = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"
