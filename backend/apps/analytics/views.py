from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.businesses.permissions import IsOwnerOrManager

from . import services
from .periods import resolve_period
from .serializers import PeriodQuerySerializer


def _period_from(request):
    serializer = PeriodQuerySerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    return resolve_period(data.get("period"), data.get("date_from"), data.get("date_to"))


class ProfitView(APIView):
    """Estimated profit for a period. Owners and managers only: it includes costs."""

    permission_classes = [IsOwnerOrManager]

    @extend_schema(parameters=[PeriodQuerySerializer], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(services.build_profit_report(request.business, _period_from(request)))


class DashboardView(APIView):
    """The dashboard: figures, charts, snapshots and insights in one request."""

    permission_classes = [IsOwnerOrManager]

    @extend_schema(parameters=[PeriodQuerySerializer], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(services.build_dashboard(request.business, _period_from(request)))
