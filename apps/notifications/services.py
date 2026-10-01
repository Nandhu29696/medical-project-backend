"""
Patient messaging. `dispatch()` is the single entry point: it creates the in-app
notification, works out which channels the person can be reached on, renders the
templates and delivers (in the background by default). Every attempt is recorded in
NotificationLog, including ones skipped on purpose.
"""

import logging
import re
import threading
from datetime import timedelta

from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone

from apps.notifications.defaults import DEFAULT_TEMPLATES
from apps.notifications.models import (
    ContactPreference,
    MessageEvent,
    MessageTemplate,
    Notification,
    NotificationCategory,
    NotificationChannel,
    NotificationLog,
    NotificationStatus,
)
from apps.notifications.providers import DeliveryError, email_mode, send_email, send_whatsapp

logger = logging.getLogger(__name__)


# --- in-app --------------------------------------------------------------------------------------


def notify(recipient, title, message="", link="", category=NotificationCategory.SYSTEM):
    """Create an in-app notification (bell menu). Silently ignores a missing recipient."""
    if recipient is None:
        return None
    return Notification.objects.create(
        recipient=recipient, title=title, message=message, link=link, category=category
    )


# --- templates & contacts ---------------------------------------------------------------------


def ensure_default_templates():
    for (event, channel), values in DEFAULT_TEMPLATES.items():
        MessageTemplate.objects.get_or_create(
            event=event,
            channel=channel,
            defaults={
                "subject": values.get("subject", ""),
                "body": values["body"],
                "whatsapp_params": values.get("whatsapp_params", []),
                "is_active": values.get("is_active", True),
            },
        )


def get_template(event, channel):
    template = MessageTemplate.objects.filter(event=event, channel=channel).first()
    if template is None and (event, channel) in DEFAULT_TEMPLATES:
        ensure_default_templates()
        template = MessageTemplate.objects.filter(event=event, channel=channel).first()
    return template


def preferences_for(user):
    prefs, _ = ContactPreference.objects.get_or_create(user=user)
    return prefs


class _Blank(dict):
    def __missing__(self, key):
        return ""


def render(text, context):
    try:
        return text.format_map(_Blank(context))
    except (ValueError, IndexError):
        # A stray brace in an edited template: send it as written rather than failing.
        return text


def normalize_whatsapp_number(raw):
    """Digits with country code (what WhatsApp expects), or "" if unusable."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10:
        digits = settings.WHATSAPP_DEFAULT_COUNTRY_CODE + digits
    return digits if 11 <= len(digits) <= 15 else ""


def is_blocked_email(address):
    domain = (address or "").rsplit("@", 1)[-1].lower()
    return any(domain == d or domain.endswith("." + d) for d in settings.NOTIFICATIONS_SKIP_DOMAINS)


def absolute_link(path):
    if not path:
        return settings.FRONTEND_URL
    return path if path.startswith("http") else f"{settings.FRONTEND_URL}{path}"


def consultation_context(consultation):
    local = timezone.localtime(consultation.scheduled_at)
    return {
        "patient_name": consultation.patient.full_name,
        "doctor_name": consultation.doctor.full_name,
        "date": local.strftime("%a, %d %b %Y"),
        "time": local.strftime("%I:%M %p").lstrip("0"),
        "mode": consultation.get_mode_display(),
    }


# --- dispatch ------------------------------------------------------------------------------------


def dispatch(
    event,
    *,
    user=None,
    email=None,
    phone=None,
    context=None,
    link="",
    in_app=None,
    category=NotificationCategory.SYSTEM,
    deliver_now=False,
):
    """
    Send `event` to a user (respecting their contact preferences) or to raw addresses
    (e.g. a public enquiry). `in_app` = {"title": ..., "message": ...} also creates a bell
    notification for `user`. Returns the NotificationLog rows created.
    """
    if user is not None and in_app:
        notify(user, in_app["title"], in_app.get("message", ""), link, category)

    blocked_user = False
    if user is not None:
        prefs = preferences_for(user)
        if event == MessageEvent.CONSULTATION_REMINDER and not prefs.reminders_enabled:
            return []
        email = user.email if prefs.email_enabled else None
        phone = (prefs.whatsapp_number or user.phone) if prefs.whatsapp_enabled else None
        # Demo/test accounts are never contacted on any channel.
        blocked_user = is_blocked_email(user.email)

    full_name = user.full_name if user is not None else (context or {}).get("full_name", "")
    ctx = {
        "site_name": settings.SITE_NAME,
        "full_name": full_name,
        "first_name": (user.first_name if user is not None else "") or full_name.split(" ")[0],
        "link": absolute_link(link),
        **(context or {}),
    }

    logs = []
    targets = [(NotificationChannel.EMAIL, email), (NotificationChannel.WHATSAPP, phone)]
    for channel, address in targets:
        if not address:
            continue
        template = get_template(event, channel)
        if template is None or not template.is_active:
            continue
        subject = render(template.subject, ctx)
        body = render(template.body, ctx)
        log = NotificationLog(
            recipient=user,
            channel=channel,
            event=event,
            subject=subject[:255],
            body=body,
            to_address=address,
        )
        skip_reason = _skip_reason(channel, address, blocked_user)
        if channel == NotificationChannel.WHATSAPP and not skip_reason:
            log.to_address = normalize_whatsapp_number(address)
        if skip_reason:
            log.status = NotificationStatus.SKIPPED
            log.error = skip_reason
        log.save()
        logs.append(log)
        if log.status == NotificationStatus.PENDING:
            _schedule(log, template, ctx, deliver_now)
    return logs


def _skip_reason(channel, address, blocked_user):
    if blocked_user:
        return "Demo/test account: not contacted."
    if channel == NotificationChannel.EMAIL and is_blocked_email(address):
        return "Demo/test email domain: not contacted."
    if channel == NotificationChannel.WHATSAPP:
        number = normalize_whatsapp_number(address)
        if not number:
            return "Not a valid mobile number for WhatsApp."
        allowed = getattr(settings, "WHATSAPP_TEST_RECIPIENTS", [])
        if allowed and number not in allowed:
            return "Number is not in WHATSAPP_TEST_RECIPIENTS (sandbox mode)."
    return ""


def _schedule(log, template, ctx, deliver_now):
    params = [str(ctx.get(name, "")) for name in (template.whatsapp_params or [])]
    job = (str(log.id), template.whatsapp_template_name, params)
    mode = "sync" if deliver_now else settings.NOTIFICATIONS_DELIVERY
    if mode == "sync":
        deliver(*job)
    elif mode == "celery":
        from apps.notifications.tasks import deliver_notification

        transaction.on_commit(lambda: deliver_notification.delay(*job))
    else:
        transaction.on_commit(
            lambda: threading.Thread(target=_deliver_in_thread, args=job, daemon=True).start()
        )


def _deliver_in_thread(*job):
    close_old_connections()
    try:
        deliver(*job)
    finally:
        close_old_connections()


def deliver(log_id, whatsapp_template_name="", whatsapp_params=None):
    """Send one logged message and record the outcome."""
    log = NotificationLog.objects.filter(pk=log_id, status=NotificationStatus.PENDING).first()
    if log is None:
        return None
    try:
        if log.channel == NotificationChannel.EMAIL:
            log.provider = f"email:{email_mode()}"
            log.provider_message_id = send_email(
                log.to_address, log.subject, log.body, _first_link(log.body)
            )
        elif log.channel == NotificationChannel.WHATSAPP:
            log.provider = f"whatsapp:{settings.WHATSAPP_PROVIDER}"
            log.provider_message_id = send_whatsapp(
                log.to_address, log.body, whatsapp_template_name, whatsapp_params or []
            )
        else:
            raise DeliveryError(f"Channel {log.channel} is not supported yet.")
        log.status = NotificationStatus.SENT
        log.sent_at = timezone.now()
        log.error = ""
    except Exception as exc:  # noqa: BLE001 - any provider failure is recorded, never raised
        logger.warning("Delivery failed for %s: %s", log.pk, exc)
        log.status = NotificationStatus.FAILED
        log.error = str(exc)[:1000]
    log.save(update_fields=["status", "sent_at", "error", "provider", "provider_message_id"])
    return log


def _first_link(text):
    match = re.search(r"https?://\S+", text or "")
    return match.group(0) if match else None


# --- reminders -----------------------------------------------------------------------------------


def send_due_reminders(now=None):
    """Remind patients of consultations starting within REMINDER_HOURS_BEFORE hours."""
    from apps.clinical.models import Consultation, ConsultationStatus

    now = now or timezone.now()
    due = Consultation.objects.select_related("patient", "doctor").filter(
        status=ConsultationStatus.SCHEDULED,
        reminder_sent_at__isnull=True,
        scheduled_at__gt=now,
        scheduled_at__lte=now + timedelta(hours=settings.REMINDER_HOURS_BEFORE),
    )
    count = 0
    for consultation in due:
        ctx = consultation_context(consultation)
        dispatch(
            MessageEvent.CONSULTATION_REMINDER,
            user=consultation.patient,
            context=ctx,
            link=f"/consultations/{consultation.id}",
            in_app={
                "title": "Upcoming consultation",
                "message": f"Dr. {ctx['doctor_name']} · {ctx['date']} at {ctx['time']}",
            },
            category=NotificationCategory.CONSULTATION,
        )
        consultation.reminder_sent_at = now
        consultation.save(update_fields=["reminder_sent_at", "updated_at"])
        count += 1
    return count


# --- sales ---------------------------------------------------------------------------------------


def send_lead_assigned_notification(lead, user):
    """Tell a sales user a lead is theirs: in-app always, email per their preferences."""
    dispatch(
        MessageEvent.LEAD_ASSIGNED,
        user=user,
        context={
            "lead_number": lead.lead_number,
            "customer_name": f"{lead.first_name} {lead.last_name}".strip(),
        },
        link=f"/leads/{lead.id}",
        in_app={
            "title": f"New lead assigned: {lead.lead_number}",
            "message": f"{lead.first_name} {lead.last_name}".strip(),
        },
        category=NotificationCategory.LEAD,
    )
