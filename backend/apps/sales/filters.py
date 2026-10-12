import django_filters

from apps.core.payments import PaymentMethod

from .models import Sale, SaleStatus


class SaleFilter(django_filters.FilterSet):
    customer = django_filters.UUIDFilter(field_name="customer_id")
    status = django_filters.ChoiceFilter(choices=SaleStatus.choices)
    payment_method = django_filters.ChoiceFilter(choices=PaymentMethod.choices)
    has_balance = django_filters.BooleanFilter(method="filter_has_balance")
    date_from = django_filters.DateFilter(field_name="sold_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="sold_at", lookup_expr="date__lte")

    class Meta:
        model = Sale
        fields = []

    def filter_has_balance(self, queryset, name, value):
        if value:
            return queryset.filter(outstanding_amount__gt=0)
        return queryset.filter(outstanding_amount=0)
