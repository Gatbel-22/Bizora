from decimal import Decimal

from django.db.models import Count, ProtectedError, Sum
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.audit.mixins import AuditedMixin
from apps.businesses.permissions import IsOwner, IsOwnerOrManager
from apps.core.views import TenantScopedMixin

from .filters import ExpenseFilter
from .models import Expense, ExpenseCategory
from .serializers import ExpenseCategorySerializer, ExpenseSerializer


class ExpenseCategoryViewSet(AuditedMixin, TenantScopedMixin, viewsets.ModelViewSet):
    queryset = ExpenseCategory.objects.annotate(expense_count=Count("expenses")).order_by("name")
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsOwnerOrManager]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    search_fields = ("name",)
    audit_fields = ("name", "affects_profit")

    def perform_destroy(self, instance):
        try:
            super().perform_destroy(instance)
        except ProtectedError:
            raise ValidationError(
                "This category still has expenses. Move those expenses to another category first."
            ) from None


class ExpenseViewSet(AuditedMixin, TenantScopedMixin, viewsets.ModelViewSet):
    """Owners and managers can record and edit expenses; only the owner can delete one."""

    queryset = Expense.objects.select_related("category", "supplier", "created_by")
    serializer_class = ExpenseSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filterset_class = ExpenseFilter
    search_fields = ("description", "notes", "supplier__name", "category__name")
    ordering_fields = ("expense_date", "amount", "created_at")
    ordering = ("-expense_date", "-created_at")
    audit_fields = (
        "category",
        "description",
        "amount",
        "expense_date",
        "payment_method",
        "supplier",
        "notes",
    )

    def get_permissions(self):
        if getattr(self, "action", None) == "destroy":
            return [IsOwner()]
        return [IsOwnerOrManager()]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Total spent and a breakdown by category, for whatever filters are applied."""
        queryset = self.filter_queryset(self.get_queryset()).order_by()
        totals = queryset.aggregate(total=Sum("amount"), count=Count("pk"))
        by_category = (
            queryset.values("category_id", "category__name", "category__affects_profit")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )
        return Response(
            {
                "total": totals["total"] or Decimal("0.00"),
                "count": totals["count"],
                "by_category": [
                    {
                        "category": row["category_id"],
                        "name": row["category__name"],
                        "affects_profit": row["category__affects_profit"],
                        "total": row["total"],
                    }
                    for row in by_category
                ],
            }
        )
