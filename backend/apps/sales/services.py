from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit import services as audit
from apps.core.money import quantize_money
from apps.core.payments import PaymentMethod
from apps.customers import services as customer_services
from apps.customers.models import Receivable
from apps.inventory import services as inventory
from apps.inventory.models import MovementType, Product

from .exceptions import SaleError
from .models import Sale, SaleItem, SalePayment, SaleSequence, SaleStatus

ZERO = Decimal("0")


def _next_number(business):
    """Next sale number for this business. Locks the counter so numbers never repeat."""
    sequence, _ = SaleSequence.objects.select_for_update().get_or_create(business=business)
    sequence.last_number += 1
    sequence.save(update_fields=["last_number"])
    return f"S-{sequence.last_number:06d}"


@transaction.atomic
def create_sale(
    *,
    business,
    user,
    items,
    payment_method,
    customer=None,
    discount=ZERO,
    amount_paid=None,
    due_date=None,
    note="",
    client_reference=None,
):
    """Record a sale: stock out, payment, debt for any unpaid part, and an audit entry.

    All or nothing: if any step fails, nothing is saved (not even the sale number).
    `items` is a list of {"product_id", "quantity", "discount"}.
    """
    currency = business.currency
    if not items:
        raise SaleError("Add at least one item to the sale.", field="items")

    if customer is not None:
        if customer.business_id != business.pk:
            raise SaleError("Customer not found.", field="customer")
        if not customer.is_active:
            raise SaleError("This customer is inactive.", field="customer")

    # Lock every product up front, always in the same order, so two sales that
    # share products can't deadlock each other or both take the last item.
    product_ids = {item["product_id"] for item in items}
    locked = Product.objects.select_for_update().filter(business=business, pk__in=product_ids)
    products = {product.pk: product for product in locked.order_by("pk")}
    if len(products) != len(product_ids):
        raise SaleError("One of the products could not be found.", field="items")

    lines = []
    subtotal = ZERO
    for item in items:
        product = products[item["product_id"]]
        quantity = item["quantity"]
        if quantity <= 0:
            raise SaleError("Quantities must be greater than zero.", field="items")
        if not product.is_active:
            raise SaleError(f"{product.name} is inactive and can't be sold.", field="items")

        line_discount = quantize_money(item.get("discount", ZERO), currency)
        gross = quantize_money(quantity * product.selling_price, currency)
        if line_discount > gross:
            raise SaleError(
                f"The discount for {product.name} is more than its price.",
                field="items",
            )
        line_total = gross - line_discount
        lines.append((product, quantity, line_discount, line_total))
        subtotal += line_total

    discount = quantize_money(discount, currency)
    if discount > subtotal:
        raise SaleError("The discount can't be more than the sale total.", field="discount")
    total = subtotal - discount
    if total <= 0:
        raise SaleError("The sale total must be greater than zero.", field="items")

    # Payment: the amount paid now; whatever is left becomes a debt for the customer.
    if payment_method == PaymentMethod.CREDIT:
        if amount_paid:
            raise SaleError(
                "A credit sale has nothing paid up front. Choose a payment method, "
                "or leave the amount paid empty.",
                field="amount_paid",
            )
        paid = ZERO
    else:
        paid = total if amount_paid is None else quantize_money(amount_paid, currency)
        if paid <= 0:
            raise SaleError(
                "Enter the amount received, or choose Credit if nothing was paid.",
                field="amount_paid",
            )
        if paid > total:
            raise SaleError(
                "The amount received can't be more than the total.", field="amount_paid"
            )

    outstanding = total - paid
    if outstanding > 0 and customer is None:
        raise SaleError("Choose a customer to sell on credit.", field="customer")
    if due_date is not None and due_date < timezone.localdate():
        raise SaleError("The due date can't be in the past.", field="due_date")

    sale = Sale.objects.create(
        business=business,
        number=_next_number(business),
        customer=customer,
        sold_at=timezone.now(),
        subtotal=subtotal,
        discount=discount,
        total=total,
        payment_method=payment_method,
        amount_paid=paid,
        outstanding_amount=outstanding,
        note=note,
        client_reference=client_reference,
        created_by=user,
    )

    for product, quantity, line_discount, line_total in lines:
        SaleItem.objects.create(
            business=business,
            sale=sale,
            product=product,
            product_name=product.name,
            sku=product.sku or "",
            unit=product.unit,
            quantity=quantity,
            unit_price=product.selling_price,
            unit_cost=product.purchase_price,
            discount=line_discount,
            line_total=line_total,
            created_by=user,
        )
        # Raises InsufficientStockError if there isn't enough, which undoes the whole sale.
        inventory.record_movement(
            business=business,
            product_id=product.pk,
            movement_type=MovementType.SALE,
            change=-quantity,
            user=user,
            note=f"Sale {sale.number}",
            reference_type="sale",
            reference_id=sale.pk,
        )

    if paid > 0:
        SalePayment.objects.create(
            business=business,
            sale=sale,
            amount=paid,
            method=payment_method,
            created_by=user,
        )

    if outstanding > 0:
        customer_services.create_receivable(
            business=business,
            customer=customer,
            original_amount=outstanding,
            user=user,
            due_date=due_date,
            note=f"Credit sale {sale.number}",
            reference_type="sale",
            reference_id=sale.pk,
        )

    audit.record(
        business=business,
        actor=user,
        action="sale.created",
        obj=sale,
        object_label=sale.number,
        metadata={
            "total": str(total),
            "payment_method": str(payment_method),
            "amount_paid": str(paid),
            "outstanding": str(outstanding),
            "customer": customer.name if customer else None,
            "items": len(lines),
        },
    )
    return sale


@transaction.atomic
def cancel_sale(*, business, sale_id, user, reason):
    """Cancel a sale: stock goes back, an unpaid debt is voided. Nothing is deleted."""
    sale = Sale.objects.select_for_update().get(pk=sale_id, business=business)
    if sale.status == SaleStatus.CANCELLED:
        raise SaleError("This sale has already been cancelled.")

    debt = (
        Receivable.objects.select_for_update()
        .filter(
            business=business,
            reference_type="sale",
            reference_id=sale.pk,
            voided_at__isnull=True,
        )
        .first()
    )
    if debt is not None and debt.amount_paid > 0:
        raise SaleError(
            "The customer has already paid towards this sale's debt, so it can't be cancelled."
        )

    for item in sale.items.order_by("product_id"):
        inventory.record_movement(
            business=business,
            product_id=item.product_id,
            movement_type=MovementType.SALE_CANCELLED,
            change=item.quantity,
            user=user,
            note=f"Cancelled {sale.number}",
            reference_type="sale",
            reference_id=sale.pk,
        )

    if debt is not None:
        customer_services.void_receivable(debt, user=user)

    sale.status = SaleStatus.CANCELLED
    sale.cancelled_at = timezone.now()
    sale.cancelled_by = user
    sale.cancel_reason = reason
    sale.updated_by = user
    sale.save(
        update_fields=[
            "status",
            "cancelled_at",
            "cancelled_by",
            "cancel_reason",
            "updated_by",
            "updated_at",
        ]
    )

    audit.record(
        business=business,
        actor=user,
        action="sale.cancelled",
        obj=sale,
        object_label=sale.number,
        metadata={"reason": reason, "total": str(sale.total)},
    )
    return sale
