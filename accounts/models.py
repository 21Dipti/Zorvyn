from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    VIEWER = 'viewer'
    ANALYST = 'analyst'
    ADMIN = 'admin'

    ROLE_CHOICES = [
        (VIEWER, 'Viewer'),
        (ANALYST, 'Analyst'),
        (ADMIN, 'Admin'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=VIEWER)

    class Meta:
        db_table = 'accounts_user'

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'

    @property
    def is_admin_role(self):
        return self.role == self.ADMIN or self.is_superuser

    @property
    def is_analyst_or_above(self):
        return self.role in (self.ANALYST, self.ADMIN) or self.is_superuser
