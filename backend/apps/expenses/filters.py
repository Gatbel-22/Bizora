import django_filters

from apps.core.payments import SETTLEMENT_CHOICES

from .models import Expense


class ExpenseFilter(django_filters.FilterSet):
    category = django_filters.UUIDFilter(field_name="category_id")
    supplier = django_filters.UUIDFilter(field_name="supplier_id")
    payment_method = django_filters.ChoiceFilter(choices=SETTLEMENT_CHOICES)
    date_from = django_filters.DateFilter(field_name="expense_date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="expense_date", lookup_expr="lte")
    min_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="gte")
    max_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="lte")

    class Meta:
        model = Expense
        fields = []
