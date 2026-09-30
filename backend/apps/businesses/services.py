from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Branch, Business, BusinessMembership, Role


def get_active_memberships(user):
    return (
        BusinessMembership.objects.select_related("business")
        .filter(user=user, is_active=True, business__is_active=True)
        .order_by("created_at")
    )


@transaction.atomic
def register_business_owner(
    *, full_name, email, password, business_name, business_type, currency, phone=""
):
    User = get_user_model()
    user = User.objects.create_user(
        email=email, password=password, full_name=full_name, phone=phone
    )
    business = Business.objects.create(
        name=business_name,
        business_type=business_type,
        owner_name=full_name,
        email=email,
        phone=phone,
        currency=currency,
    )
    Branch.objects.create(business=business, name="Main Branch", is_primary=True, created_by=user)
    membership = BusinessMembership.objects.create(business=business, user=user, role=Role.OWNER)
    return user, business, membership


@transaction.atomic
def add_staff_member(*, business, full_name, email, password, role, phone=""):
    User = get_user_model()
    user = User.objects.create_user(
        email=email, password=password, full_name=full_name, phone=phone
    )
    return BusinessMembership.objects.create(business=business, user=user, role=role)
