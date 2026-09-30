from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    ProductViewSet,
    StockMovementViewSet,
    SupplierViewSet,
)

router = DefaultRouter()
router.include_root_view = False
router.register("categories", CategoryViewSet, basename="category")
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("products", ProductViewSet, basename="product")
router.register("inventory/movements", StockMovementViewSet, basename="stock-movement")

urlpatterns = router.urls
