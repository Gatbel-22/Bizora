import django_filters

from .models import AuditLog


class AuditLogFilter(django_filters.FilterSet):
    object_type = django_filters.CharFilter()
    object_id = django_filters.CharFilter()
    action = django_filters.CharFilter()
    actor = django_filters.UUIDFilter(field_name="actor_id")
    date_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = AuditLog
        fields = []
