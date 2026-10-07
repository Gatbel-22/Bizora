from django.db import models


class PaymentMethod(models.TextChoices):
    CASH = "CASH", "Cash"
    MOBILE_MONEY = "MOBILE_MONEY", "Mobile money"
    BANK_TRANSFER = "BANK_TRANSFER", "Bank transfer"
    CREDIT = "CREDIT", "Credit"
    OTHER = "OTHER", "Other"


# Methods that actually move money. "Credit" is a promise to pay, not a payment.
SETTLEMENT_CHOICES = [
    (method.value, method.label) for method in PaymentMethod if method != PaymentMethod.CREDIT
]
