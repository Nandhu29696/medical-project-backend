from apps.leads.models import Lead, LeadStatusHistory


def change_status(lead: Lead, new_status: str, changed_by=None, note: str = "") -> Lead:
    old_status = lead.status
    lead.status = new_status
    lead.save(update_fields=["status", "updated_at"])

    LeadStatusHistory.objects.create(
        lead=lead,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        note=note,
    )
    return lead
