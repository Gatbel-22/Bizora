from rest_framework.routers import DefaultRouter

from .views import AuditLogViewSet

router = DefaultRouter()
router.include_root_view = False
router.register("audit-log", AuditLogViewSet, basename="audit-log")

urlpatterns = router.urls
