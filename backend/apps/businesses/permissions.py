from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.permissions import BasePermission

from .models import Role
from .services import get_active_memberships


def resolve_membership(request):
    """The caller's active membership: the one named in X-Business-ID, or their only one."""
    memberships = get_active_memberships(request.user)
    business_id = request.headers.get("X-Business-ID")
    if business_id:
        try:
            return memberships.filter(business_id=business_id).first()
        except DjangoValidationError, ValueError:
            return None
    candidates = list(memberships[:2])
    return candidates[0] if len(candidates) == 1 else None


class IsBusinessMember(BasePermission):
    """Caller must be an active member of a business. Sets request.membership/business."""

    message = "You don't have access to this business."
    allowed_roles = None  # None = any role

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if not hasattr(request, "membership"):
            request.membership = resolve_membership(request)
            request.business = request.membership.business if request.membership else None
        if request.membership is None:
            return False
        if self.allowed_roles is None:
            return True
        return request.membership.role in self.allowed_roles


class IsOwner(IsBusinessMember):
    message = "Only the business owner can do this."
    allowed_roles = {Role.OWNER}


class IsOwnerOrManager(IsBusinessMember):
    message = "Only owners and managers can do this."
    allowed_roles = {Role.OWNER, Role.MANAGER}
