from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BusinessView, MembershipViewSet

router = DefaultRouter()
router.include_root_view = False
router.register("members", MembershipViewSet, basename="member")

urlpatterns = [
    path("", BusinessView.as_view(), name="business"),
    path("", include(router.urls)),
]
