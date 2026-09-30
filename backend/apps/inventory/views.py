from django.db.models import Count, ProtectedError
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.businesses.permissions import IsBusinessMember, IsOwnerOrManager
from apps.core.views import TenantScopedMixin

from . import services
from .exceptions import InsufficientStockError, NoStockChangeError
from .filters import ProductFilter, StockMovementFilter
from .models import Category, Product, StockMovement, Supplier
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    StockAdjustmentSerializer,
    StockMovementSerializer,
    SupplierSerializer,
)


class ReadAnyWriteManagerMixin:
    """Every team member can read; only owners and managers can change things."""

    def get_permissions(self):
        if getattr(self, "action", None) in ("list", "retrieve"):
            return [IsBusinessMember()]
        return [IsOwnerOrManager()]


class CategoryViewSet(ReadAnyWriteManagerMixin, TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Category.objects.annotate(product_count=Count("products")).order_by("name")
    serializer_class = CategorySerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    search_fields = ("name",)

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError(
                "This category still has products. Move those products to another category first."
            ) from None


class SupplierViewSet(ReadAnyWriteManagerMixin, TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Supplier.objects.order_by("name")
    serializer_class = SupplierSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    search_fields = ("name", "phone", "email")


class ProductViewSet(ReadAnyWriteManagerMixin, TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category", "supplier")
    serializer_class = ProductSerializer
    # No DELETE: products are deactivated instead, so history is never orphaned.
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_class = ProductFilter
    search_fields = ("name", "sku", "category__name")
    ordering_fields = ("name", "selling_price", "current_stock", "created_at")
    ordering = ("name",)

    @extend_schema(request=StockAdjustmentSerializer, responses=StockMovementSerializer)
    @action(detail=True, methods=["post"], url_path="stock")
    def stock(self, request, pk=None):
        """Receive stock, remove stock, or set the counted quantity."""
        product = self.get_object()  # scoped to the caller's business: other tenants get 404
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            movement = services.adjust_stock(
                business=request.business,
                product_id=product.pk,
                user=request.user,
                **serializer.validated_data,
            )
        except InsufficientStockError as exc:
            raise ValidationError({"quantity": [str(exc)]}) from None
        except NoStockChangeError as exc:
            raise ValidationError({"quantity": [str(exc)]}) from None
        return Response(StockMovementSerializer(movement).data, status=201)


class StockMovementViewSet(
    TenantScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """The stock history. Read-only, and limited to owners and managers."""

    queryset = StockMovement.objects.select_related("product", "created_by")
    serializer_class = StockMovementSerializer
    permission_classes = [IsOwnerOrManager]
    filterset_class = StockMovementFilter
    search_fields = ("product__name", "product__sku", "note")
    ordering_fields = ("created_at",)
    ordering = ("-created_at",)
