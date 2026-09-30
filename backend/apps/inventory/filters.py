import django_filters

from .models import MovementType, Product, StockMovement, StockStatus


class ProductFilter(django_filters.FilterSet):
    # UUID filters (not model choice filters) so IDs from other businesses reveal nothing.
    category = django_filters.UUIDFilter(field_name="category_id")
    supplier = django_filters.UUIDFilter(field_name="supplier_id")
    is_active = django_filters.BooleanFilter()
    stock_status = django_filters.ChoiceFilter(
        choices=StockStatus.choices, method="filter_stock_status"
    )

    class Meta:
        model = Product
        fields = []

    def filter_stock_status(self, queryset, name, value):
        if value == StockStatus.OUT:
            return queryset.out_of_stock()
        if value == StockStatus.LOW:
            return queryset.low_stock()
        return queryset.in_stock()


class StockMovementFilter(django_filters.FilterSet):
    product = django_filters.UUIDFilter(field_name="product_id")
    movement_type = django_filters.ChoiceFilter(choices=MovementType.choices)
    date_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = StockMovement
        fields = []
