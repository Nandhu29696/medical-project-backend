from datetime import timedelta

from django.utils import timezone

from apps.leads.models import Lead

DUPLICATE_WINDOW_HOURS = 72


def normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits


def is_potential_duplicate(phone: str, product_id) -> bool:
    normalized = normalize_phone(phone)
    window_start = timezone.now() - timedelta(hours=DUPLICATE_WINDOW_HOURS)
    return Lead.objects.filter(
        phone__endswith=normalized,
        product_id=product_id,
        created_at__gte=window_start,
    ).exists()
