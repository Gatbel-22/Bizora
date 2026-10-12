from django.db import IntegrityError
from django.db.models import Count
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.businesses.permissions import IsBusinessMember, IsOwnerOrManager
from apps.core.views import TenantScopedMixin
from apps.inventory.exceptions import InsufficientStockError

from . import services
from .exceptions import SaleError
from .filters import SaleFilter
from .models import Sale
from .receipts import build_receipt
from .serializers import (
    SaleCancelSerializer,
    SaleCreateSerializer,
    SaleListSerializer,
    SaleSerializer,
)


class SaleViewSet(
    TenantScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Sales can be recorded by any team member. They are never edited, only cancelled."""

    queryset = Sale.objects.select_related("customer", "created_by", "cancelled_by")
    filterset_class = SaleFilter
    search_fields = ("number", "customer__name", "note")
    ordering_fields = ("sold_at", "total", "number")
    ordering = ("-sold_at",)

    def get_permissions(self):
        if getattr(self, "action", None) == "cancel":
            return [IsOwnerOrManager()]
        return [IsBusinessMember()]

    def get_serializer_class(self):
        return SaleListSerializer if getattr(self, "action", None) == "list" else SaleSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, "action", None) == "list":
            return queryset.annotate(item_count=Count("items"))
        return queryset.prefetch_related("items", "payments")

    def _existing_sale(self, reference):
        """A sale already saved under this reference (the request was retried)."""
        if not reference:
            return None
        return self.get_queryset().filter(client_reference=reference).first()

    @extend_schema(request=SaleCreateSerializer, responses=SaleSerializer)
    def create(self, request, *args, **kwargs):
        context = self.get_serializer_context()
        serializer = SaleCreateSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        reference = data.get("client_reference")

        existing = self._existing_sale(reference)
        if existing is not None:
            return Response(SaleSerializer(existing, context=context).data, status=200)

        try:
            sale = services.create_sale(
                business=request.business,
                user=request.user,
                customer=data.get("customer"),
                items=[
                    {
                        "product_id": item["product"].pk,
                        "quantity": item["quantity"],
                        "discount": item["discount"],
                    }
                    for item in data["items"]
                ],
                discount=data["discount"],
                payment_method=data["payment_method"],
                amount_paid=data.get("amount_paid"),
                due_date=data.get("due_date"),
                note=data.get("note", ""),
                client_reference=reference,
            )
        except SaleError as exc:
            raise ValidationError({exc.field: [str(exc)]}) from None
        except InsufficientStockError as exc:
            raise ValidationError({"items": [str(exc)]}) from None
        except IntegrityError:
            # Two identical requests raced; the other one won. Return its sale.
            existing = self._existing_sale(reference)
            if existing is None:
                raise
            return Response(SaleSerializer(existing, context=context).data, status=200)

        sale = self.get_queryset().get(pk=sale.pk)
        return Response(SaleSerializer(sale, context=context).data, status=201)

    @extend_schema(request=SaleCancelSerializer, responses=SaleSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a sale: stock returns and an unpaid debt is voided. Owners and managers only."""
        sale = self.get_object()
        serializer = SaleCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.cancel_sale(
                business=request.business,
                sale_id=sale.pk,
                user=request.user,
                reason=serializer.validated_data["reason"].strip(),
            )
        except SaleError as exc:
            raise ValidationError({exc.field: [str(exc)]}) from None
        sale = self.get_queryset().get(pk=sale.pk)
        return Response(SaleSerializer(sale, context=self.get_serializer_context()).data)

    @extend_schema(responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=["get"])
    def receipt(self, request, pk=None):
        """Everything needed to print or share a receipt for this sale."""
        return Response(build_receipt(self.get_object(), request.business))
