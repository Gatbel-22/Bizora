import django_filters
from django.utils import timezone

from apps.core.payments import SETTLEMENT_CHOICES

from .models import Customer, CustomerPayment, Receivable, ReceivableStatus


class CustomerFilter(django_filters.FilterSet):
    is_active = django_filters.BooleanFilter()
    has_balance = django_filters.BooleanFilter(method="filter_has_balance")
    overdue = django_filters.BooleanFilter(method="filter_overdue")

    class Meta:
        model = Customer
        fields = []

    def filter_has_balance(self, queryset, name, value):
        if value:
            return queryset.filter(outstanding_balance__gt=0)
        return queryset.filter(outstanding_balance=0)

    def filter_overdue(self, queryset, name, value):
        if value:
            return queryset.filter(overdue_balance__gt=0)
        return queryset.filter(overdue_balance=0)


class ReceivableFilter(django_filters.FilterSet):
    customer = django_filters.UUIDFilter(field_name="customer_id")
    status = django_filters.ChoiceFilter(choices=ReceivableStatus.choices, method="filter_status")
    is_open = django_filters.BooleanFilter(method="filter_is_open")

    class Meta:
        model = Receivable
        fields = []

    def filter_status(self, queryset, name, value):
        today = timezone.localdate()
        if value == ReceivableStatus.PAID:
            return queryset.paid()
        if value == ReceivableStatus.OVERDUE:
            return queryset.overdue(today)
        if value == ReceivableStatus.DUE_SOON:
            return queryset.due_soon(today)
        return queryset.current(today)

    def filter_is_open(self, queryset, name, value):
        return queryset.open() if value else queryset.paid()


class CustomerPaymentFilter(django_filters.FilterSet):
    customer = django_filters.UUIDFilter(field_name="customer_id")
    method = django_filters.ChoiceFilter(choices=SETTLEMENT_CHOICES)
    date_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = CustomerPayment
        fields = []
