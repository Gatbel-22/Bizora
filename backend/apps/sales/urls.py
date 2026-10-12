from rest_framework.routers import DefaultRouter

from .views import SaleViewSet

router = DefaultRouter()
router.include_root_view = False
router.register("sales", SaleViewSet, basename="sale")

urlpatterns = router.urls
