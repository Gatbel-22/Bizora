from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from .models import AuditLog

# is the single entry point for writing audit entries.
# Any code in Bizora records history through record():


def _json_safe(value):
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _is_blank(value):
    return value is None or value == ""


def snapshot(instance, fields):
    """Current values of the named model fields (foreign keys are read as raw IDs)."""
    values = {}
    for name in fields:
        field = instance._meta.get_field(name)
        values[name] = getattr(instance, field.attname)
    return values


def diff(before, after):
    """Fields whose value differs between two snapshots. None and "" count as the same."""
    changes = {}
    for name in [*before, *[key for key in after if key not in before]]:
        old, new = before.get(name), after.get(name)
        if old == new or (_is_blank(old) and _is_blank(new)):
            continue
        changes[name] = {"old": _json_safe(old), "new": _json_safe(new)}
    return changes


def record(
    *,
    business,
    actor,
    action,
    obj=None,
    object_type="",
    object_id="",
    object_label="",
    changes=None,
    metadata=None,
):
    """Write one audit entry. Call it inside the same transaction as the change itself."""
    if obj is not None:
        object_type = object_type or obj._meta.model_name
        object_id = object_id or str(obj.pk)
        object_label = object_label or str(obj)
    actor_name = (getattr(actor, "full_name", "") or getattr(actor, "email", "")) if actor else ""
    return AuditLog.objects.create(
        business=business,
        actor=actor,
        actor_name=actor_name or "System",
        action=action,
        object_type=object_type,
        object_id=object_id,
        object_label=object_label[:200],
        changes=changes or {},
        metadata=metadata or {},
    )
