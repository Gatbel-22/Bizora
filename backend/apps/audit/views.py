from rest_framework import mixins, viewsets

from apps.businesses.permissions import IsOwner
from apps.core.views import TenantScopedMixin

from .filters import AuditLogFilter
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(
    TenantScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """The business's activity history. Read-only and visible to the owner only."""

    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsOwner]
    filterset_class = AuditLogFilter
    search_fields = ("object_label", "actor_name", "action")
    ordering_fields = ("created_at",)
    ordering = ("-created_at",)
