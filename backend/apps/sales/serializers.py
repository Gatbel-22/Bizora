from decimal import Decimal

from rest_framework import serializers

from apps.businesses.models import Role
from apps.core.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS, quantize_money
from apps.core.payments import PaymentMethod
from apps.core.serializers import TenantPrimaryKeyRelatedField
from apps.customers.models import Customer
from apps.inventory.models import QUANTITY_DECIMAL_PLACES, QUANTITY_MAX_DIGITS, Product

from .models import Sale, SaleItem, SalePayment


def _can_see_costs(request):
    """Cost prices and profit are for owners and managers only."""
    membership = getattr(request, "membership", None)
    return membership is not None and membership.role != Role.STAFF


def _money(**kwargs):
    return serializers.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        min_value=Decimal("0"),
        **kwargs,
    )


class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = (
            "id",
            "product",
            "product_name",
            "sku",
            "unit",
            "quantity",
            "unit_price",
            "unit_cost",
            "discount",
            "line_total",
        )
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not _can_see_costs(self.context.get("request")):
            data.pop("unit_cost", None)
        return data


class SalePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalePayment
        fields = ("id", "amount", "method", "created_at")
        read_only_fields = fields


class SaleSerializer(serializers.ModelSerializer):
    """Full detail of one sale."""

    customer_name = serializers.CharField(source="customer.name", read_only=True, default=None)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=""
    )
    cancelled_by_name = serializers.CharField(
        source="cancelled_by.full_name", read_only=True, default=""
    )
    items = SaleItemSerializer(many=True, read_only=True)
    payments = SalePaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Sale
        fields = (
            "id",
            "number",
            "status",
            "customer",
            "customer_name",
            "sold_at",
            "subtotal",
            "discount",
            "total",
            "payment_method",
            "amount_paid",
            "outstanding_amount",
            "note",
            "items",
            "payments",
            "created_by_name",
            "cancelled_at",
            "cancelled_by_name",
            "cancel_reason",
            "created_at",
        )
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if _can_see_costs(request):
            cost = sum((i.unit_cost * i.quantity for i in instance.items.all()), Decimal("0"))
            cost = quantize_money(cost, request.business.currency)
            data["cost_of_goods_sold"] = cost
            data["gross_profit"] = instance.total - cost
        return data


class SaleListSerializer(serializers.ModelSerializer):
    """Compact version for lists (no line items)."""

    customer_name = serializers.CharField(source="customer.name", read_only=True, default=None)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=""
    )
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Sale
        fields = (
            "id",
            "number",
            "status",
            "customer",
            "customer_name",
            "sold_at",
            "total",
            "amount_paid",
            "outstanding_amount",
            "payment_method",
            "item_count",
            "created_by_name",
        )
        read_only_fields = fields


class SaleItemInputSerializer(serializers.Serializer):
    product = TenantPrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        min_value=Decimal("0.001"),
    )
    discount = _money(required=False, default=Decimal("0"))


class SaleCreateSerializer(serializers.Serializer):
    """What the app sends. Totals are never accepted: the server works them out."""

    customer = TenantPrimaryKeyRelatedField(
        queryset=Customer.objects.all(), required=False, allow_null=True
    )
    items = SaleItemInputSerializer(many=True, allow_empty=False, max_length=100)
    discount = _money(required=False, default=Decimal("0"))
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices)
    amount_paid = _money(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    client_reference = serializers.UUIDField(required=False, allow_null=True)


class SaleCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)
