from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.core.models import TenantModel, TimeStampedModel
from apps.core.money import CURRENCY_CHOICES, DEFAULT_CURRENCY


class BusinessType(models.TextChoices):
    RETAIL = "RETAIL", "Retail shop"
    SUPERMARKET = "SUPERMARKET", "Small supermarket"
    WHOLESALE = "WHOLESALE", "Wholesaler"
    PHARMACY = "PHARMACY", "Pharmacy"
    RESTAURANT = "RESTAURANT", "Restaurant"
    SALON = "SALON", "Salon / barbershop"
    SERVICE = "SERVICE", "Service business"
    OTHER = "OTHER", "Other"


class DateFormat(models.TextChoices):
    DMY = "DD/MM/YYYY", "DD/MM/YYYY"
    MDY = "MM/DD/YYYY", "MM/DD/YYYY"
    YMD = "YYYY-MM-DD", "YYYY-MM-DD"


class Role(models.TextChoices):
    OWNER = "OWNER", "Owner"
    MANAGER = "MANAGER", "Manager"
    STAFF = "STAFF", "Staff"


class Business(TimeStampedModel):
    """The tenant. Every business-owned record points back to one of these."""

    name = models.CharField(max_length=150)
    business_type = models.CharField(
        max_length=20, choices=BusinessType.choices, default=BusinessType.OTHER
    )
    owner_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    country = models.CharField(max_length=100, default="South Sudan")
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default=DEFAULT_CURRENCY)
    tax_name = models.CharField(max_length=30, blank=True)
    default_tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    logo = models.ImageField(upload_to="business_logos/", null=True, blank=True)
    date_format = models.CharField(
        max_length=10, choices=DateFormat.choices, default=DateFormat.DMY
    )
    timezone = models.CharField(max_length=50, default="Africa/Juba")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "businesses"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Branch(TenantModel):
    """A location. MVP has one primary branch, but the table is ready for more."""

    name = models.CharField(max_length=150)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "branches"
        constraints = [
            models.UniqueConstraint(fields=["business", "name"], name="unique_branch_name"),
            models.UniqueConstraint(
                fields=["business"],
                condition=Q(is_primary=True),
                name="unique_primary_branch_per_business",
            ),
        ]

    def __str__(self):
        return f"{self.business} - {self.name}"


class BusinessMembership(TimeStampedModel):
    """Links a user to a business with a role."""

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STAFF)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "user"], name="unique_membership"),
        ]
        indexes = [models.Index(fields=["user", "is_active"])]

    def __str__(self):
        return f"{self.user} - {self.business} ({self.role})"
