from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower

from apps.core.models import TenantModel
from apps.core.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS

QUANTITY_MAX_DIGITS = 12
QUANTITY_DECIMAL_PLACES = 3  # allows kilograms/litres, e.g. 2.500


class Unit(models.TextChoices):
    PIECE = "PIECE", "Piece"
    PACK = "PACK", "Pack"
    BOX = "BOX", "Box"
    CARTON = "CARTON", "Carton"
    BOTTLE = "BOTTLE", "Bottle"
    DOZEN = "DOZEN", "Dozen"
    KG = "KG", "Kilogram"
    LITRE = "LITRE", "Litre"


class StockStatus(models.TextChoices):
    IN_STOCK = "in_stock", "In stock"
    LOW = "low", "Low stock"
    OUT = "out", "Out of stock"


class MovementType(models.TextChoices):
    OPENING = "OPENING", "Opening stock"
    STOCK_IN = "STOCK_IN", "Stock received"
    ADJUSTMENT = "ADJUSTMENT", "Manual adjustment"
    SALE = "SALE", "Sale"
    SALE_CANCELLED = "SALE_CANCELLED", "Sale cancelled"


class AdjustmentType(models.TextChoices):
    """What a user can request from the API. Each maps onto a MovementType."""

    STOCK_IN = "STOCK_IN", "Stock received"
    STOCK_OUT = "STOCK_OUT", "Stock removed"
    COUNT = "COUNT", "Stock count"


class Category(TenantModel):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "business", name="unique_category_name_per_business"
            ),
        ]

    def __str__(self):
        return self.name


class Supplier(TenantModel):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "business", name="unique_supplier_name_per_business"
            ),
        ]

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def out_of_stock(self):
        return self.filter(current_stock__lte=0)

    def low_stock(self):
        return self.filter(current_stock__gt=0, current_stock__lte=F("min_stock_threshold"))

    def in_stock(self):
        return self.filter(current_stock__gt=F("min_stock_threshold"))


class Product(TenantModel):
    name = models.CharField(max_length=150)
    # Nullable on purpose: NULLs never collide in the unique (business, sku) constraint, so
    # any number of products can have no SKU while real SKUs stay unique per business.
    sku = models.CharField(max_length=50, null=True, blank=True)  # noqa: DJ001
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="products",
    )
    supplier = models.ForeignKey(
        Supplier,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="products",
    )
    description = models.TextField(blank=True)
    purchase_price = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, default=0
    )
    selling_price = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES, default=0
    )
    # Only ever changed through inventory.services, which records a StockMovement.
    current_stock = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        default=0,
    )
    min_stock_threshold = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        default=0,
    )
    unit = models.CharField(max_length=10, choices=Unit.choices, default=Unit.PIECE)
    is_active = models.BooleanField(default=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["business", "sku"], name="unique_sku_per_business"),
            models.CheckConstraint(condition=Q(current_stock__gte=0), name="product_stock_gte_0"),
            models.CheckConstraint(
                condition=Q(min_stock_threshold__gte=0), name="product_min_stock_gte_0"
            ),
            models.CheckConstraint(
                condition=Q(purchase_price__gte=0), name="product_purchase_price_gte_0"
            ),
            models.CheckConstraint(
                condition=Q(selling_price__gte=0), name="product_selling_price_gte_0"
            ),
        ]
        indexes = [
            models.Index(fields=["business", "name"]),
            models.Index(fields=["business", "is_active"]),
        ]

    def __str__(self):
        return self.name

    @property
    def stock_status(self):
        if self.current_stock <= 0:
            return StockStatus.OUT
        if self.current_stock <= self.min_stock_threshold:
            return StockStatus.LOW
        return StockStatus.IN_STOCK


class StockMovement(TenantModel):
    """One permanent line in a product's stock history. Never edited or deleted."""

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity_change = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS, decimal_places=QUANTITY_DECIMAL_PLACES
    )  # signed: positive adds stock, negative removes it
    stock_after = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS, decimal_places=QUANTITY_DECIMAL_PLACES
    )
    unit_cost = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        null=True,
        blank=True,
    )
    note = models.CharField(max_length=255, blank=True)
    # Lets later features (sales, returns) point back at what caused the movement.
    reference_type = models.CharField(max_length=30, blank=True)
    reference_id = models.UUIDField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(quantity_change=0), name="movement_change_not_zero"
            ),
            models.CheckConstraint(condition=Q(stock_after__gte=0), name="movement_stock_gte_0"),
        ]
        indexes = [
            models.Index(fields=["business", "product", "-created_at"]),
            models.Index(fields=["business", "-created_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Stock movements are permanent records and can't be edited.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Stock movements are permanent records and can't be deleted.")

    def __str__(self):
        return f"{self.product} {self.quantity_change:+}"
