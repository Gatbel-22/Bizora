from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.core.models import TenantModel
from apps.core.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS
from apps.core.payments import PaymentMethod
from apps.inventory.models import QUANTITY_DECIMAL_PLACES, QUANTITY_MAX_DIGITS


def money_field(**kwargs):
    return models.DecimalField(
        max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, **kwargs
    )


class SaleStatus(models.TextChoices):
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class SaleSequence(models.Model):
    """Per-business counter behind sale numbers (S-000001, S-000002, ...)."""

    business = models.OneToOneField(
        "businesses.Business", on_delete=models.CASCADE, related_name="sale_sequence"
    )
    last_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Sale sequence for {self.business}"


class Sale(TenantModel):
    """A completed (or later cancelled) sale.

    Never edited; mistakes are cancelled and re-entered.
    """

    number = models.CharField(max_length=30)
    customer = models.ForeignKey(
        "customers.Customer",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="sales",
    )  # empty for walk-in customers
    sold_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=10, choices=SaleStatus.choices, default=SaleStatus.COMPLETED
    )
    subtotal = money_field()  # sum of the lines (after any line discounts)
    discount = money_field(default=0)  # extra discount on the whole sale
    total = money_field()
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    amount_paid = money_field()
    outstanding_amount = money_field(default=0)  # becomes a customer debt
    note = models.CharField(max_length=255, blank=True)
    # Sent by the app so a retried request can't create the same sale twice.
    client_reference = models.UUIDField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    cancel_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-sold_at"]
        constraints = [
            models.UniqueConstraint(fields=["business", "number"], name="unique_sale_number"),
            models.UniqueConstraint(
                fields=["business", "client_reference"],
                name="unique_sale_client_reference",
            ),
            models.CheckConstraint(condition=Q(subtotal__gte=0), name="sale_subtotal_gte_0"),
            models.CheckConstraint(condition=Q(discount__gte=0), name="sale_discount_gte_0"),
            models.CheckConstraint(
                condition=Q(discount__lte=F("subtotal")),
                name="sale_discount_lte_subtotal",
            ),
            models.CheckConstraint(condition=Q(total__gte=0), name="sale_total_gte_0"),
            models.CheckConstraint(condition=Q(amount_paid__gte=0), name="sale_paid_gte_0"),
            models.CheckConstraint(
                condition=Q(amount_paid__lte=F("total")), name="sale_paid_lte_total"
            ),
            models.CheckConstraint(
                condition=Q(outstanding_amount=F("total") - F("amount_paid")),
                name="sale_outstanding_matches",
            ),
        ]
        indexes = [
            models.Index(fields=["business", "-sold_at"]),
            models.Index(fields=["business", "customer"]),
            models.Index(fields=["business", "status"]),
        ]

    def __str__(self):
        return self.number


class SaleItem(TenantModel):
    """One line of a sale. Name, price and cost are copied so history never changes."""

    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name="items")
    product = models.ForeignKey(
        "inventory.Product", on_delete=models.PROTECT, related_name="sale_items"
    )
    product_name = models.CharField(max_length=150)
    sku = models.CharField(max_length=50, blank=True)
    unit = models.CharField(max_length=10)
    quantity = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS, decimal_places=QUANTITY_DECIMAL_PLACES
    )
    unit_price = money_field()
    unit_cost = money_field()  # purchase price at the time: used for profit
    discount = money_field(default=0)
    line_total = money_field()

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="saleitem_quantity_gt_0"),
            models.CheckConstraint(condition=Q(unit_price__gte=0), name="saleitem_price_gte_0"),
            models.CheckConstraint(condition=Q(unit_cost__gte=0), name="saleitem_cost_gte_0"),
            models.CheckConstraint(condition=Q(discount__gte=0), name="saleitem_discount_gte_0"),
            models.CheckConstraint(condition=Q(line_total__gte=0), name="saleitem_total_gte_0"),
        ]
        indexes = [models.Index(fields=["business", "product"])]


class SalePayment(TenantModel):
    """Money received at the time of the sale."""

    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name="payments")
    amount = money_field()
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="salepayment_amount_gt_0"),
        ]
