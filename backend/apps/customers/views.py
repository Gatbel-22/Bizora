from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.audit.mixins import AuditedMixin
from apps.businesses.permissions import IsBusinessMember, IsOwnerOrManager
from apps.core.views import TenantScopedMixin

from . import services
from .exceptions import NothingOwedError, OverpaymentError
from .filters import CustomerFilter, CustomerPaymentFilter, ReceivableFilter
from .models import Customer, CustomerPayment, Receivable
from .serializers import (
    CustomerPaymentSerializer,
    CustomerSerializer,
    ReceivableSerializer,
)


class CustomerViewSet(AuditedMixin, TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    # No DELETE: customers are deactivated so their history stays intact.
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_class = CustomerFilter
    search_fields = ("name", "phone", "email")
    ordering_fields = ("name", "outstanding_balance", "created_at")
    ordering = ("name",)
    audit_fields = ("name", "phone", "email", "address", "notes", "is_active")

    def get_permissions(self):
        # Staff can look customers up and add new ones at the counter; editing is for managers.
        if getattr(self, "action", None) in ("list", "retrieve", "create"):
            return [IsBusinessMember()]
        return [IsOwnerOrManager()]

    def get_queryset(self):
        return super().get_queryset().with_balances(timezone.localdate())


class ReceivableViewSet(
    TenantScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Debts owed to the business. Manual debts can be added by owners and managers."""

    queryset = Receivable.objects.select_related("customer")
    serializer_class = ReceivableSerializer
    filterset_class = ReceivableFilter
    search_fields = ("customer__name", "note")
    ordering_fields = ("due_date", "issue_date", "original_amount", "created_at")
    ordering = ("-created_at",)

    def get_permissions(self):
        if getattr(self, "action", None) == "create":
            return [IsOwnerOrManager()]
        return [IsBusinessMember()]


class CustomerPaymentViewSet(
    TenantScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Payments received from customers. Any team member can record one."""

    queryset = CustomerPayment.objects.select_related("customer", "created_by").prefetch_related(
        "allocations"
    )
    serializer_class = CustomerPaymentSerializer
    permission_classes = [IsBusinessMember]
    filterset_class = CustomerPaymentFilter
    search_fields = ("customer__name", "note")
    ordering_fields = ("created_at", "amount")
    ordering = ("-created_at",)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        receivable = data.get("receivable")
        try:
            payment = services.record_customer_payment(
                business=request.business,
                customer_id=data["customer"].pk,
                amount=data["amount"],
                method=data["method"],
                user=request.user,
                receivable_id=receivable.pk if receivable else None,
                note=data.get("note", ""),
            )
        except (OverpaymentError, NothingOwedError) as exc:
            raise ValidationError({"amount": [str(exc)]}) from None
        payment = self.get_queryset().get(pk=payment.pk)  # reload with related data for the reply
        return Response(self.get_serializer(payment).data, status=201)
