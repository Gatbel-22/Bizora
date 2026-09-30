from decimal import Decimal

from rest_framework import serializers

from apps.businesses.models import Role
from apps.core.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS
from apps.core.serializers import (
    TenantPrimaryKeyRelatedField,
    ensure_unique_in_business,
)

from . import services
from .models import (
    QUANTITY_DECIMAL_PLACES,
    QUANTITY_MAX_DIGITS,
    AdjustmentType,
    Category,
    Product,
    StockMovement,
    Supplier,
)


def _money_field(**kwargs):
    return serializers.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        min_value=Decimal("0"),
        **kwargs,
    )


def _quantity_field(**kwargs):
    return serializers.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        min_value=Decimal("0"),
        **kwargs,
    )


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "product_count", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_name(self, value):
        value = value.strip()
        ensure_unique_in_business(
            Category,
            self.context["request"].business,
            "name",
            value,
            self.instance,
            "You already have a category with this name.",
        )
        return value


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ("id", "name", "phone", "email", "address", "notes", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_name(self, value):
        value = value.strip()
        ensure_unique_in_business(
            Supplier,
            self.context["request"].business,
            "name",
            value,
            self.instance,
            "You already have a supplier with this name.",
        )
        return value


class ProductSerializer(serializers.ModelSerializer):
    category = TenantPrimaryKeyRelatedField(
        queryset=Category.objects.all(), required=False, allow_null=True
    )
    supplier = TenantPrimaryKeyRelatedField(
        queryset=Supplier.objects.all(), required=False, allow_null=True
    )
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)
    selling_price = _money_field()
    purchase_price = _money_field(required=False)
    min_stock_threshold = _quantity_field(required=False)
    opening_stock = _quantity_field(required=False, write_only=True)
    stock_status = serializers.CharField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "sku",
            "category",
            "category_name",
            "supplier",
            "supplier_name",
            "description",
            "purchase_price",
            "selling_price",
            "current_stock",
            "min_stock_threshold",
            "unit",
            "stock_status",
            "is_active",
            "opening_stock",
            "created_at",
            "updated_at",
        )
        # Stock can only change through a recorded movement, never by editing a product.
        read_only_fields = ("id", "current_stock", "created_at", "updated_at")

    def validate_sku(self, value):
        value = (value or "").strip().upper()
        if not value:
            return None
        ensure_unique_in_business(
            Product,
            self.context["request"].business,
            "sku",
            value,
            self.instance,
            "This SKU is already in use. Please choose another SKU.",
        )
        return value

    def validate(self, attrs):
        if self.instance is not None and "opening_stock" in getattr(self, "initial_data", {}):
            raise serializers.ValidationError(
                {
                    "opening_stock": "Opening stock can only be set when creating a product. "
                    "Use Adjust stock instead."
                }
            )
        return attrs

    def create(self, validated_data):
        opening_stock = validated_data.pop("opening_stock", Decimal("0"))
        return services.create_product(opening_stock=opening_stock, **validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        membership = getattr(self.context.get("request"), "membership", None)
        # Cost prices are sensitive: staff never receive them.
        if membership is None or membership.role == Role.STAFF:
            data.pop("purchase_price", None)
        return data


class StockAdjustmentSerializer(serializers.Serializer):
    adjustment_type = serializers.ChoiceField(choices=AdjustmentType.choices)
    quantity = _quantity_field()
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    unit_cost = _money_field(required=False, allow_null=True)

    def validate(self, attrs):
        kind = attrs["adjustment_type"]
        if kind != AdjustmentType.COUNT and attrs["quantity"] <= 0:
            raise serializers.ValidationError({"quantity": "Quantity must be greater than zero."})
        if kind != AdjustmentType.STOCK_IN and not attrs.get("note", "").strip():
            raise serializers.ValidationError(
                {"note": "Please add a short reason for this change."}
            )
        attrs["note"] = attrs.get("note", "").strip()
        return attrs


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True, default=None)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=""
    )

    class Meta:
        model = StockMovement
        fields = (
            "id",
            "product",
            "product_name",
            "product_sku",
            "movement_type",
            "quantity_change",
            "stock_after",
            "unit_cost",
            "note",
            "reference_type",
            "reference_id",
            "created_by_name",
            "created_at",
        )
        read_only_fields = fields
