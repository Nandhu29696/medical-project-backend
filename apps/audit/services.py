from apps.audit.models import AuditLog

SENSITIVE_KEYS = {"password", "token", "refresh", "access", "otp", "secret"}


def _strip_sensitive(values):
    if not isinstance(values, dict):
        return values
    return {k: ("***" if k.lower() in SENSITIVE_KEYS else v) for k, v in values.items()}


def _client_ip(request):
    if not request:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_action(
    action, entity_type, entity_id="", actor=None, old_values=None, new_values=None, request=None
):
    """Create an AuditLog row. Never persists passwords, tokens, OTPs, or secrets."""
    AuditLog.objects.create(
        actor=actor if actor and getattr(actor, "is_authenticated", True) else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else "",
        old_values=_strip_sensitive(old_values),
        new_values=_strip_sensitive(new_values),
        ip_address=_client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:255] if request else None),
    )
