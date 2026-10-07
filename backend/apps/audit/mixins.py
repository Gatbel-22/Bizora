from django.db import transaction

from . import services


class AuditedMixin:
    """Logs create / update / delete in the same transaction as the change.

    Put it before TenantScopedMixin and set `audit_fields` to the model fields to track.
    """

    audit_fields = ()

    def _audit(self, action, **kwargs):
        services.record(
            business=self.request.business,
            actor=self.request.user,
            action=action,
            **kwargs,
        )

    def perform_create(self, serializer):
        with transaction.atomic():
            super().perform_create(serializer)
            instance = serializer.instance
            changes = services.diff({}, services.snapshot(instance, self.audit_fields))
            self._audit(f"{instance._meta.model_name}.created", obj=instance, changes=changes)

    def perform_update(self, serializer):
        before = services.snapshot(serializer.instance, self.audit_fields)
        with transaction.atomic():
            super().perform_update(serializer)
            instance = serializer.instance
            changes = services.diff(before, services.snapshot(instance, self.audit_fields))
            if changes:  # saving without changing anything isn't worth logging
                self._audit(
                    f"{instance._meta.model_name}.updated",
                    obj=instance,
                    changes=changes,
                )

    def perform_destroy(self, instance):
        kind = instance._meta.model_name
        object_id, label = str(instance.pk), str(instance)
        before = services.snapshot(instance, self.audit_fields)
        with transaction.atomic():
            super().perform_destroy(instance)
            self._audit(
                f"{kind}.deleted",
                object_type=kind,
                object_id=object_id,
                object_label=label,
                changes=services.diff(before, {}),
            )
