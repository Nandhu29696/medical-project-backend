from django.utils import timezone

from apps.leads.models import Lead, LeadStatus, LeadStatusHistory
from apps.leads.services.detect_duplicate import is_potential_duplicate, normalize_phone


def create_lead(validated_data, request=None) -> Lead:
    """Creates a lead from public or admin-submitted data, running normalization,
    consent capture, and duplicate detection. Never raises on duplicates —
    it flags them for human review instead of silently dropping them."""
    phone = normalize_phone(validated_data.get("phone", ""))
    validated_data["phone"] = phone

    duplicate = is_potential_duplicate(phone, validated_data.get("product").id)

    consent_given = validated_data.pop("consent_given", False)

    lead = Lead.objects.create(
        **validated_data,
        status=LeadStatus.NEW,
        is_potential_duplicate=duplicate,
        consent_given=consent_given,
        consent_timestamp=timezone.now() if consent_given else None,
    )

    LeadStatusHistory.objects.create(
        lead=lead,
        old_status=None,
        new_status=LeadStatus.NEW,
        changed_by=(
            getattr(request, "user", None) if request and request.user.is_authenticated else None
        ),
        note="Lead created.",
    )
    return lead
