from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.core.models import TenantModel, TimeStampedModel
from apps.core.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS
from apps.core.payments import PaymentMethod

DUE_SOON_DAYS = 7  # a debt due within this many days is "due soon"


def money_field(**kwargs):
    return models.DecimalField(
        max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, **kwargs
    )


class CustomerQuerySet(models.QuerySet):
    def with_balances(self, today):
        """Adds outstanding_balance and overdue_balance, calculated from the customer's debts."""
        money = DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
        owed = ExpressionWrapper(
            F("receivables__original_amount") - F("receivables__amount_paid"),
            output_field=money,
        )
        zero = Value(Decimal("0"), output_field=money)
        return self.annotate(
            outstanding_balance=Coalesce(Sum(owed), zero),
            overdue_balance=Coalesce(Sum(owed, filter=Q(receivables__due_date__lt=today)), zero),
        )


class Customer(TenantModel):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    objects = CustomerQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["business", "name"])]

    def __str__(self):
        return self.name


class ReceivableStatus(models.TextChoices):
    CURRENT = "current", "Current"
    DUE_SOON = "due_soon", "Due soon"
    OVERDUE = "overdue", "Overdue"
    PAID = "paid", "Paid"


class ReceivableQuerySet(models.QuerySet):
    def open(self):
        return self.filter(amount_paid__lt=F("original_amount"))

    def paid(self):
        return self.filter(amount_paid=F("original_amount"))

    def overdue(self, today):
        return self.open().filter(due_date__lt=today)

    def due_soon(self, today):
        limit = today + timedelta(days=DUE_SOON_DAYS)
        return self.open().filter(due_date__gte=today, due_date__lte=limit)

    def current(self, today):
        limit = today + timedelta(days=DUE_SOON_DAYS)
        return self.open().filter(Q(due_date__isnull=True) | Q(due_date__gt=limit))


class Receivable(TenantModel):
    """Money a customer owes the business: one credit sale or one manually recorded debt."""

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="receivables")
    original_amount = money_field()
    # Only ever changed by customers.services.record_customer_payment.
    amount_paid = money_field(default=0)
    issue_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    # Lets a credit sale point back at the sale that created this debt (Step 7).
    reference_type = models.CharField(max_length=30, blank=True)
    reference_id = models.UUIDField(null=True, blank=True)

    objects = ReceivableQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(original_amount__gt=0), name="receivable_original_gt_0"
            ),
            models.CheckConstraint(condition=Q(amount_paid__gte=0), name="receivable_paid_gte_0"),
            models.CheckConstraint(
                condition=Q(amount_paid__lte=F("original_amount")),
                name="receivable_paid_lte_original",
            ),
            models.CheckConstraint(
                condition=Q(due_date__isnull=True) | Q(due_date__gte=F("issue_date")),
                name="receivable_due_after_issue",
            ),
        ]
        indexes = [
            models.Index(fields=["business", "customer"]),
            models.Index(fields=["business", "due_date"]),
        ]

    def __str__(self):
        return f"{self.customer} owes {self.original_amount}"

    @property
    def balance(self):
        return self.original_amount - self.amount_paid

    @property
    def days_outstanding(self):
        if self.balance <= 0:
            return None
        return max((timezone.localdate() - self.issue_date).days, 0)

    @property
    def status(self):
        if self.balance <= 0:
            return ReceivableStatus.PAID
        today = timezone.localdate()
        if self.due_date is None:
            return ReceivableStatus.CURRENT
        if self.due_date < today:
            return ReceivableStatus.OVERDUE
        if self.due_date <= today + timedelta(days=DUE_SOON_DAYS):
            return ReceivableStatus.DUE_SOON
        return ReceivableStatus.CURRENT


class CustomerPayment(TenantModel):
    """Money received from a customer. Applied to one or more debts via allocations."""

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="payments")
    amount = money_field()
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="customer_payment_amount_gt_0"),
        ]
        indexes = [models.Index(fields=["business", "customer", "-created_at"])]

    def __str__(self):
        return f"Payment of {self.amount} from {self.customer}"


class PaymentAllocation(TimeStampedModel):
    """How much of a payment went to which debt."""

    payment = models.ForeignKey(
        CustomerPayment, on_delete=models.PROTECT, related_name="allocations"
    )
    receivable = models.ForeignKey(Receivable, on_delete=models.PROTECT, related_name="allocations")
    amount = money_field()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="allocation_amount_gt_0"),
        ]
