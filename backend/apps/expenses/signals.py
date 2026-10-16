from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.businesses.models import Business

from .services import ensure_default_categories


@receiver(post_save, sender=Business)
def create_default_expense_categories(sender, instance, created, **kwargs):
    if created:
        ensure_default_categories(instance)
