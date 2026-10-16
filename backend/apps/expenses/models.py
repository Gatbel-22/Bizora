from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone

from apps.core.models import TenantModel
from apps.core.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS
from apps.core.payments import PaymentMethod


def money_field(**kwargs):
    return models.DecimalField(
        max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, **kwargs
    )


class ExpenseCategory(TenantModel):
    name = models.CharField(max_length=100)
    # Off for categories that are already counted elsewhere (e.g. stock purchases).
    affects_profit = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "expense categories"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "business", name="unique_expense_category_name_per_business"
            ),
        ]

    def __str__(self):
        return self.name


class Expense(TenantModel):
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name="expenses")
    description = models.CharField(max_length=200)
    amount = money_field()
    expense_date = models.DateField(default=timezone.localdate)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    supplier = models.ForeignKey(
        "inventory.Supplier",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="expenses",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-expense_date", "-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="expense_amount_gt_0"),
        ]
        indexes = [
            models.Index(fields=["business", "-expense_date"]),
            models.Index(fields=["business", "category"]),
        ]

    def __str__(self):
        return self.description
