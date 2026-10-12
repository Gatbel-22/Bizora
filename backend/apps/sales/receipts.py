def build_receipt(sale, business):
    """Everything a receipt needs, in one plain structure the app can print or share."""
    return {
        "id": sale.pk,
        "business": {
            "name": business.name,
            "address": business.address,
            "phone": business.phone,
            "currency": business.currency,
        },
        "number": sale.number,
        "status": sale.status,
        "sold_at": sale.sold_at,
        "served_by": sale.created_by.full_name if sale.created_by else "",
        "customer": sale.customer.name if sale.customer else None,
        "items": [
            {
                "name": item.product_name,
                "unit": item.unit,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "discount": item.discount,
                "line_total": item.line_total,
            }
            for item in sale.items.all()
        ],
        "subtotal": sale.subtotal,
        "discount": sale.discount,
        "total": sale.total,
        "payment_method": sale.payment_method,
        "amount_paid": sale.amount_paid,
        "outstanding_amount": sale.outstanding_amount,
        "payments": [
            {
                "amount": payment.amount,
                "method": payment.method,
                "paid_at": payment.created_at,
            }
            for payment in sale.payments.all()
        ],
        "note": sale.note,
        "cancelled_at": sale.cancelled_at,
        "cancel_reason": sale.cancel_reason,
    }
