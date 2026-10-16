from django.db.models.functions import Lower

from .defaults import DEFAULT_CATEGORIES
from .models import ExpenseCategory


def ensure_default_categories(business):
    """Give a business the standard expense categories it doesn't already have."""
    existing = set(
        ExpenseCategory.objects.filter(business=business)
        .annotate(lowered=Lower("name"))
        .values_list("lowered", flat=True)
    )
    ExpenseCategory.objects.bulk_create(
        [
            ExpenseCategory(business=business, name=name, affects_profit=affects_profit)
            for name, affects_profit in DEFAULT_CATEGORIES
            if name.lower() not in existing
        ]
    )
