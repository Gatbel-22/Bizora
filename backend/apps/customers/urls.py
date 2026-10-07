from rest_framework.routers import DefaultRouter

from .views import CustomerPaymentViewSet, CustomerViewSet, ReceivableViewSet

router = DefaultRouter()
router.include_root_view = False
router.register("customers", CustomerViewSet, basename="customer")
router.register("receivables", ReceivableViewSet, basename="receivable")
router.register("customer-payments", CustomerPaymentViewSet, basename="customer-payment")

urlpatterns = router.urls
