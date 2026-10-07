from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = (
            "id",
            "action",
            "object_type",
            "object_id",
            "object_label",
            "actor_name",
            "changes",
            "metadata",
            "created_at",
        )
        read_only_fields = fields
