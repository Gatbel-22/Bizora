from decimal import Decimal

from django.db import transaction

from apps.audit import services as audit

from .exceptions import InsufficientStockError, NoStockChangeError
from .models import AdjustmentType, MovementType, Product, StockMovement


def _apply_movement(
    product,
    *,
    movement_type,
    change,
    user,
    note="",
    unit_cost=None,
    reference_type="",
    reference_id=None,
):
    """Change stock and write the history line. Caller must hold a lock on `product`."""
    new_stock = product.current_stock + change
    if new_stock < 0:
        raise InsufficientStockError(product, product.current_stock, -change)

    product.current_stock = new_stock
    product.updated_by = user
    product.save(update_fields=["current_stock", "updated_by", "updated_at"])

    return StockMovement.objects.create(
        business_id=product.business_id,
        product=product,
        movement_type=movement_type,
        quantity_change=change,
        stock_after=new_stock,
        unit_cost=unit_cost,
        note=note,
        reference_type=reference_type,
        reference_id=reference_id,
        created_by=user,
    )


@transaction.atomic
def record_movement(*, business, product_id, movement_type, change, user, **details):
    """Generic entry point (sales will use this to take stock out)."""
    product = Product.objects.select_for_update().get(pk=product_id, business=business)
    return _apply_movement(
        product, movement_type=movement_type, change=change, user=user, **details
    )


@transaction.atomic
def adjust_stock(*, business, product_id, adjustment_type, quantity, user, note="", unit_cost=None):
    """A manual change made by a person: stock received, stock removed, or a recount."""
    product = Product.objects.select_for_update().get(pk=product_id, business=business)
    stock_before = product.current_stock

    if adjustment_type == AdjustmentType.STOCK_IN:
        movement = _apply_movement(
            product,
            movement_type=MovementType.STOCK_IN,
            change=quantity,
            user=user,
            note=note,
            unit_cost=unit_cost,
        )
    else:
        if adjustment_type == AdjustmentType.STOCK_OUT:
            change = -quantity
        else:  # COUNT: the user tells us what's really on the shelf
            change = quantity - product.current_stock
            if change == 0:
                raise NoStockChangeError()
        movement = _apply_movement(
            product,
            movement_type=MovementType.ADJUSTMENT,
            change=change,
            user=user,
            note=note,
        )

    audit.record(
        business=business,
        actor=user,
        action="product.stock_adjusted",
        obj=product,
        metadata={
            "adjustment_type": adjustment_type,
            "quantity_change": str(movement.quantity_change),
            "stock_before": str(stock_before),
            "stock_after": str(movement.stock_after),
            "note": note,
        },
    )
    return movement


@transaction.atomic
def create_product(*, opening_stock=Decimal("0"), **fields):
    """Create a product; any starting stock is recorded as an OPENING movement."""
    product = Product.objects.create(**fields)
    if opening_stock and opening_stock > 0:
        _apply_movement(
            product,
            movement_type=MovementType.OPENING,
            change=opening_stock,
            user=fields.get("created_by"),
            note="Opening stock",
        )
    return product
