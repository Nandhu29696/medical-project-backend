from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.clinical.models import Consultation
from apps.notifications.models import Notification


@receiver(post_delete, sender=Consultation)
def remove_consultation_notifications(sender, instance, **kwargs):
    """A deleted consultation takes its in-app notifications with it, so no bell item
    ever links to a page that no longer exists. Email / WhatsApp logs are kept."""
    Notification.objects.filter(link=f"/consultations/{instance.pk}").delete()
