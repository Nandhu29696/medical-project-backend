import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.notifications.services import send_due_reminders


class Command(BaseCommand):
    help = (
        "Send email/WhatsApp/in-app reminders for consultations starting within "
        "REMINDER_HOURS_BEFORE hours. Use --loop to keep running "
        "(local alternative to Celery beat)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--loop", action="store_true", help="Run forever, checking every interval."
        )
        parser.add_argument(
            "--interval", type=int, default=15, help="Minutes between checks (with --loop)."
        )

    def handle(self, *args, loop=False, interval=15, **options):
        while True:
            count = send_due_reminders()
            self.stdout.write(
                f"Sent {count} reminder(s) for consultations in the next "
                f"{settings.REMINDER_HOURS_BEFORE} hours."
            )
            if not loop:
                return
            time.sleep(max(1, interval) * 60)
