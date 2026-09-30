class TenantScopedMixin:
    """Restricts a viewset to the caller's business and stamps new rows."""

    tenant_field = "business"

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        return queryset.filter(**{self.tenant_field: self.request.business})

    def perform_create(self, serializer):
        extra = {self.tenant_field: self.request.business}
        if hasattr(serializer.Meta.model, "created_by"):
            extra["created_by"] = self.request.user
        serializer.save(**extra)

    def perform_update(self, serializer):
        extra = {}
        if hasattr(serializer.Meta.model, "updated_by"):
            extra["updated_by"] = self.request.user
        serializer.save(**extra)
