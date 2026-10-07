from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.core.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS
from apps.core.payments import SETTLEMENT_CHOICES
from apps.core.serializers import TenantPrimaryKeyRelatedField

from . import services
from .models import Customer, CustomerPayment, PaymentAllocation, Receivable


def _positive_money(**kwargs):
    return serializers.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        min_value=Decimal("0.01"),
        **kwargs,
    )


def _read_only_money():
    return serializers.DecimalField(
        max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, read_only=True
    )


class CustomerSerializer(serializers.ModelSerializer):
    outstanding_balance = _read_only_money()
    overdue_balance = _read_only_money()

    class Meta:
        model = Customer
        fields = (
            "id",
            "name",
            "phone",
            "email",
            "address",
            "notes",
            "is_active",
            "outstanding_balance",
            "overdue_balance",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def validate_name(self, value):
        return value.strip()


class ReceivableSerializer(serializers.ModelSerializer):
    customer = TenantPrimaryKeyRelatedField(queryset=Customer.objects.all())
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    original_amount = _positive_money()
    balance = _read_only_money()
    days_outstanding = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Receivable
        fields = (
            "id",
            "customer",
            "customer_name",
            "original_amount",
            "amount_paid",
            "balance",
            "issue_date",
            "due_date",
            "days_outstanding",
            "status",
            "note",
            "reference_type",
            "reference_id",
            "created_at",
        )
        read_only_fields = (
            "id",
            "amount_paid",
            "reference_type",
            "reference_id",
            "created_at",
        )

    def validate(self, attrs):
        issue_date = attrs.get("issue_date") or timezone.localdate()
        due_date = attrs.get("due_date")
        if due_date and due_date < issue_date:
            raise serializers.ValidationError(
                {"due_date": "The due date can't be before the date the debt was created."}
            )
        return attrs

    def create(self, validated_data):
        # amount_paid can't be set by the caller; stock-style rule: only services change it.
        return services.create_receivable(user=validated_data.pop("created_by"), **validated_data)


class PaymentAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAllocation
        fields = ("receivable", "amount")
        read_only_fields = fields


class CustomerPaymentSerializer(serializers.ModelSerializer):
    customer = TenantPrimaryKeyRelatedField(queryset=Customer.objects.all())
    receivable = TenantPrimaryKeyRelatedField(
        queryset=Receivable.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=""
    )
    amount = _positive_money()
    method = serializers.ChoiceField(choices=SETTLEMENT_CHOICES)
    allocations = PaymentAllocationSerializer(many=True, read_only=True)

    class Meta:
        model = CustomerPayment
        fields = (
            "id",
            "customer",
            "customer_name",
            "receivable",
            "amount",
            "method",
            "note",
            "allocations",
            "created_by_name",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def validate(self, attrs):
        receivable = attrs.get("receivable")
        if receivable is not None and receivable.customer_id != attrs["customer"].pk:
            raise serializers.ValidationError(
                {"receivable": "That debt belongs to a different customer."}
            )
        return attrs
