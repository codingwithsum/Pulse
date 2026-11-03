from django.db import models
from apps.core.models import TimeStampedModel

class Department(TimeStampedModel):
    """
    Represents an authorized Rajkot Municipal Corporation department
    (e.g., Engineering & Roads, Water Works, Drainage & Sewerage).
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.SlugField(max_length=50, unique=True, help_text="e.g. engineering-roads, water-works")
    description = models.TextField(blank=True)
    head_title = models.CharField(max_length=150, blank=True, help_text="e.g. Executive Engineer (Roads)")
    head_email = models.EmailField(blank=True, help_text="Official RMC municipal email address")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Municipal Department'
        verbose_name_plural = 'Municipal Departments'

    def __str__(self):
        return self.name


class CivicCategory(TimeStampedModel):
    """
    Granular civic issue category mapped directly to a responsible municipal department.
    """
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=50, unique=True, help_text="e.g. potholes, water-contamination")
    keywords_en = models.TextField(blank=True, help_text="Comma-separated English keywords")
    keywords_gu = models.TextField(blank=True, help_text="Comma-separated Gujarati keywords (e.g. ખાડા, ગટર)")
    keywords_hi = models.TextField(blank=True, help_text="Comma-separated Hindi keywords (e.g. गंदा पानी)")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['department', 'name']
        verbose_name = 'Civic Category'
        verbose_name_plural = 'Civic Categories'
        unique_together = ('department', 'name')

    def __str__(self):
        return f"{self.name} ({self.department.code})"


class CivicLocation(TimeStampedModel):
    """
    RMC administrative geography covering 3 zones and 18 municipal wards with gazetteer landmarks.
    """
    ZONE_CHOICES = [
        ('WEST', 'West Zone'),
        ('CENTRAL', 'Central Zone'),
        ('EAST', 'East Zone'),
    ]

    zone = models.CharField(max_length=20, choices=ZONE_CHOICES, db_index=True)
    ward_number = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    ward_name = models.CharField(max_length=150, help_text="e.g. Ward 7 - Amin Marg / Race Course")
    known_landmarks = models.TextField(
        blank=True,
        help_text="Landmarks in Gujarati & English for entity matching (e.g. Prem Mandir, Kotecha Chowk, Trikon Baug)"
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        ordering = ['zone', 'ward_number']
        verbose_name = 'Civic Location / Ward'
        verbose_name_plural = 'Civic Locations / Wards'
        unique_together = ('zone', 'ward_number')

    def __str__(self):
        if self.ward_number:
            return f"Ward {self.ward_number}: {self.ward_name} ({self.get_zone_display()})"
        return f"{self.ward_name} ({self.get_zone_display()})"
