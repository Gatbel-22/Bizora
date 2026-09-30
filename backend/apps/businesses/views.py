from rest_framework import generics, mixins, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.core.views import TenantScopedMixin

from . import services
from .models import BusinessMembership, Role
from .permissions import IsBusinessMember, IsOwner, IsOwnerOrManager
from .serializers import (
    BusinessSerializer,
    MembershipCreateSerializer,
    MembershipSerializer,
    MembershipUpdateSerializer,
)


class BusinessView(generics.RetrieveUpdateAPIView):
    """The caller's own business profile. Any member can read; only the owner can edit."""

    serializer_class = BusinessSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsOwner()]
        return [IsBusinessMember()]

    def get_object(self):
        return self.request.business


class MembershipViewSet(
    TenantScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Team management: owners/managers can view, only the owner can add or change."""

    queryset = BusinessMembership.objects.select_related("user").order_by("created_at")
    http_method_names = ["get", "post", "patch", "head", "options"]
    search_fields = ("user__full_name", "user__email")
    filterset_fields = ("role", "is_active")

    def get_permissions(self):
        if getattr(self, "action", None) in ("create", "update", "partial_update"):
            return [IsOwner()]
        return [IsOwnerOrManager()]

    def get_serializer_class(self):
        action = getattr(self, "action", None)
        if action == "create":
            return MembershipCreateSerializer
        if action in ("update", "partial_update"):
            return MembershipUpdateSerializer
        return MembershipSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = services.add_staff_member(
            business=request.business, **serializer.validated_data
        )
        return Response(MembershipSerializer(membership).data, status=201)

    def perform_update(self, serializer):
        if serializer.instance.role == Role.OWNER:
            raise PermissionDenied("The owner's access can't be changed.")
        super().perform_update(serializer)
