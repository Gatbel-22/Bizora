from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.core.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS
from apps.core.payments import SETTLEMENT_CHOICES
from apps.core.serializers import TenantPrimaryKeyRelatedField, ensure_unique_in_business
from apps.inventory.models import Supplier

from .models import Expense, ExpenseCategory


class ExpenseCategorySerializer(serializers.ModelSerializer):
    expense_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ExpenseCategory
        fields = ("id", "name", "affects_profit", "expense_count", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_name(self, value):
        value = value.strip()
        ensure_unique_in_business(
            ExpenseCategory,
            self.context["request"].business,
            "name",
            value,
            self.instance,
            "You already have an expense category with this name.",
        )
        return value


class ExpenseSerializer(serializers.ModelSerializer):
    category = TenantPrimaryKeyRelatedField(queryset=ExpenseCategory.objects.all())
    supplier = TenantPrimaryKeyRelatedField(
        queryset=Supplier.objects.all(), required=False, allow_null=True
    )
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_affects_profit = serializers.BooleanField(
        source="category.affects_profit", read_only=True
    )
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=""
    )
    amount = serializers.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        min_value=Decimal("0.01"),
    )
    payment_method = serializers.ChoiceField(choices=SETTLEMENT_CHOICES)

    class Meta:
        model = Expense
        fields = (
            "id",
            "description",
            "category",
            "category_name",
            "category_affects_profit",
            "amount",
            "expense_date",
            "payment_method",
            "supplier",
            "supplier_name",
            "notes",
            "created_by_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_description(self, value):
        return value.strip()

    def validate_expense_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("The expense date can't be in the future.")
        return value
