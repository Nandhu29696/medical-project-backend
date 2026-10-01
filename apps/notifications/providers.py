"""Delivery back-ends for email and WhatsApp. Each returns a provider message id or raises."""

import json
import logging
import urllib.error
import urllib.request
from html import escape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


class DeliveryError(Exception):
    pass


# --- Email -------------------------------------------------------------------------------------


def email_mode():
    backend = settings.EMAIL_BACKEND.rsplit(".", 2)[-2] if "." in settings.EMAIL_BACKEND else ""
    return {"smtp": "smtp", "filebased": "file", "console": "console", "locmem": "test"}.get(
        backend, backend or "unknown"
    )


def _brand_color():
    try:
        from apps.branding.models import SiteTheme

        return SiteTheme.load().primary_color
    except Exception:  # noqa: BLE001 - branding must never block an email
        return "#0F9D78"


def render_email_html(subject, body, link=None):
    color = _brand_color()
    paragraphs = "".join(
        f'<p style="margin:0 0 14px;line-height:1.6">{escape(part).replace(chr(10), "<br>")}</p>'
        for part in body.split("\n\n")
    )
    button = (
        f'<p style="margin:22px 0"><a href="{escape(link)}" style="background:{color};color:#fff;'
        "padding:12px 22px;border-radius:999px;text-decoration:none;font-weight:700;"
        'display:inline-block">Open in portal</a></p>'
        if link
        else ""
    )
    return (
        '<div style="background:#f5f5f7;padding:24px 12px;font-family:Arial,Helvetica,sans-serif">'
        '<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:16px;'
        'overflow:hidden;border:1px solid #e6e6ea">'
        f'<div style="background:{color};color:#fff;padding:18px 24px;font-size:18px;'
        f'font-weight:700">{escape(settings.SITE_NAME)}</div>'
        f'<div style="padding:24px;color:#1f2430;font-size:15px">'
        f'<h1 style="font-size:20px;margin:0 0 16px">{escape(subject)}</h1>{paragraphs}{button}'
        "</div>"
        '<div style="padding:14px 24px;background:#fafafa;color:#8a8f99;font-size:12px">'
        "You receive this because you have an account or enquiry with us. "
        "Manage email and WhatsApp preferences in your profile.</div>"
        "</div></div>"
    )


def send_email(to, subject, body, link=None):
    message = EmailMultiAlternatives(subject=subject, body=body, to=[to])
    message.attach_alternative(render_email_html(subject, body, link), "text/html")
    sent = message.send(fail_silently=False)
    if not sent:
        raise DeliveryError("The mail server did not accept the message.")
    return ""


# --- WhatsApp ------------------------------------------------------------------------------------


def whatsapp_configured():
    if settings.WHATSAPP_PROVIDER == "meta":
        return bool(settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID)
    return True


def send_whatsapp(to, body, template_name="", params=None):
    """`to` is digits only with country code, e.g. 919876543210."""
    provider = settings.WHATSAPP_PROVIDER
    if provider == "console":
        logger.info("[WhatsApp console] to=%s template=%s body=%s", to, template_name or "-", body)
        return "console"
    if provider == "meta":
        return _send_meta(to, body, template_name, params or [])
    raise DeliveryError(f"Unknown WHATSAPP_PROVIDER '{provider}'.")


def _send_meta(to, body, template_name, params):
    if not whatsapp_configured():
        raise DeliveryError("WhatsApp Cloud API is not configured (token / phone number id).")
    url = (
        f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    if template_name:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": settings.WHATSAPP_TEMPLATE_LANGUAGE},
                "components": (
                    [
                        {
                            "type": "body",
                            "parameters": [{"type": "text", "text": str(p)[:1000]} for p in params],
                        }
                    ]
                    if params
                    else []
                ),
            },
        }
    else:
        # Free-form text is only delivered inside WhatsApp's 24-hour customer-service window.
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(
            request, timeout=15
        ) as response:  # nosec B310 - fixed https host
            data = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        raise DeliveryError(f"WhatsApp API error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise DeliveryError(f"Could not reach WhatsApp API: {exc.reason}") from exc
    messages = data.get("messages") or [{}]
    return messages[0].get("id", "")
