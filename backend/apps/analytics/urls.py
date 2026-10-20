from django.urls import path

from .views import DashboardView, ProfitView

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("profit/", ProfitView.as_view(), name="profit"),
]
