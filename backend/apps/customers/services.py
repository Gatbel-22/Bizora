from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.audit import services as audit

from .exceptions import NothingOwedError, OverpaymentError
from .models import Customer, CustomerPayment, PaymentAllocation, Receivable


@transaction.atomic
def create_receivable(
    *,
    business,
    customer,
    original_amount,
    user,
    due_date=None,
    issue_date=None,
    note="",
    reference_type="",
    reference_id=None,
):
    """Record that a customer owes money. Credit sales (Step 7) call this too."""
    receivable = Receivable.objects.create(
        business=business,
        customer=customer,
        original_amount=original_amount,
        issue_date=issue_date or timezone.localdate(),
        due_date=due_date,
        note=note,
        reference_type=reference_type,
        reference_id=reference_id,
        created_by=user,
    )
    audit.record(
        business=business,
        actor=user,
        action="receivable.created",
        obj=receivable,
        object_label=f"Debt for {customer.name}",
        metadata={
            "customer": customer.name,
            "amount": str(original_amount),
            "due_date": due_date.isoformat() if due_date else None,
        },
    )
    return receivable


@transaction.atomic
def record_customer_payment(
    *, business, customer_id, amount, method, user, receivable_id=None, note=""
):
    """Apply a payment to a customer's debts, oldest due date first.

    The customer's row is locked, so two payments can't both use the same balance.
    Paying more than is owed is refused.
    """
    customer = Customer.objects.select_for_update().get(pk=customer_id, business=business)

    debts = Receivable.objects.select_for_update().filter(business=business, customer=customer)
    debts = debts.open()
    if receivable_id is not None:
        debts = debts.filter(pk=receivable_id)
    open_debts = list(
        debts.order_by(F("due_date").asc(nulls_last=True), "issue_date", "created_at")
    )

    if not open_debts:
        if receivable_id is not None:
            raise NothingOwedError("That debt is already paid, or doesn't belong to this customer.")
        raise NothingOwedError()

    owed = sum(debt.balance for debt in open_debts)
    if amount > owed:
        raise OverpaymentError(owed)

    payment = CustomerPayment.objects.create(
        business=business,
        customer=customer,
        amount=amount,
        method=method,
        note=note,
        created_by=user,
    )

    remaining = amount
    for debt in open_debts:
        if remaining <= 0:
            break
        applied = min(debt.balance, remaining)
        debt.amount_paid += applied
        debt.updated_by = user
        debt.save(update_fields=["amount_paid", "updated_by", "updated_at"])
        PaymentAllocation.objects.create(payment=payment, receivable=debt, amount=applied)
        remaining -= applied

    audit.record(
        business=business,
        actor=user,
        action="payment.recorded",
        obj=payment,
        object_label=customer.name,
        metadata={"amount": str(amount), "method": method, "note": note},
    )
    return payment
