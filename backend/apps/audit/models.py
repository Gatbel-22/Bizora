from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class AuditLog(TimeStampedModel):
    """A permanent record of who did what, and when. Never edited or deleted."""

    business = models.ForeignKey(
        "businesses.Business", on_delete=models.PROTECT, related_name="audit_logs"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    # Copied at write time so the log still reads correctly if the user is removed.
    actor_name = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=50)  # e.g. "product.updated"
    object_type = models.CharField(max_length=50)  # e.g. "product"
    object_id = models.CharField(max_length=64, blank=True)
    object_label = models.CharField(max_length=200, blank=True)  # e.g. the product's name
    changes = models.JSONField(default=dict, blank=True)  # {"field": {"old": ..., "new": ...}}
    metadata = models.JSONField(default=dict, blank=True)  # extra context for the action

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["business", "-created_at"]),
            models.Index(fields=["business", "object_type", "object_id"]),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Audit log entries are permanent and can't be edited.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit log entries are permanent and can't be deleted.")

    def __str__(self):
        return f"{self.actor_name} {self.action} {self.object_label}"
