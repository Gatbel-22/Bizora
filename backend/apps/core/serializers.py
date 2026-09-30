from rest_framework import serializers


class TenantPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """A foreign-key field that only accepts records from the caller's own business.

    Without this, a user could attach another business's category to their product
    by guessing its ID. Use it for every relation to a business-owned record.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("pk_field", serializers.UUIDField())
        super().__init__(**kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        request = self.context.get("request")
        business = getattr(request, "business", None)
        if business is None:
            return queryset.none()
        return queryset.filter(business=business)


def ensure_unique_in_business(
    model,
    business,
    field,
    value,
    instance=None,
    message="This value is already in use.",
):
    """Case-insensitive uniqueness check scoped to one business."""
    queryset = model.objects.filter(business=business, **{f"{field}__iexact": value})
    if instance is not None:
        queryset = queryset.exclude(pk=instance.pk)
    if queryset.exists():
        raise serializers.ValidationError(message)
