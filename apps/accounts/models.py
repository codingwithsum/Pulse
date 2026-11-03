from django.db import models
from django.contrib.auth.models import User
from apps.core.models import TimeStampedModel
from apps.master_data.models import Department, CivicLocation

class StaffProfile(TimeStampedModel):
    """
    Extends standard Django user model with municipal role, department assignment, and ward scope.
    """
    ROLE_CHOICES = [
        ('MUNICIPAL_COMMISSIONER', 'Municipal Commissioner / Executive Admin'),
        ('DEPT_HEAD', 'Department Head (Executive Engineer)'),
        ('WARD_OFFICER', 'Ward Officer (Flying Squad / Field Inspector)'),
        ('ANALYST', 'Civic Intelligence Analyst'),
        ('AUDITOR', 'Quality & Compliance Auditor'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    employee_id = models.CharField(max_length=50, unique=True, help_text="Official RMC employee registration ID")
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='ANALYST', db_index=True)
    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='staff_members',
        help_text="Required for Department Heads"
    )
    assigned_ward = models.ForeignKey(
        CivicLocation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_officers',
        help_text="Required for Ward Officers"
    )
    phone_number = models.CharField(max_length=20, blank=True, help_text="Official staff contact number")

    class Meta:
        verbose_name = 'Staff Profile'
        verbose_name_plural = 'Staff Profiles'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"
