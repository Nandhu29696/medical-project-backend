"""Celery tasks (used when NOTIFICATIONS_DELIVERY=celery and by Celery beat in production)."""

from celery import shared_task

from apps.notifications.services import deliver, send_due_reminders


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def deliver_notification(self, log_id, whatsapp_template_name="", whatsapp_params=None):
    deliver(log_id, whatsapp_template_name, whatsapp_params or [])


@shared_task
def send_consultation_reminders():
    return send_due_reminders()
