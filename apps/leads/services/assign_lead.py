from apps.leads.models import Lead, LeadStatusHistory


def assign_lead(lead: Lead, assigned_to, changed_by=None) -> Lead:
    previous = lead.assigned_to
    lead.assigned_to = assigned_to
    lead.save(update_fields=["assigned_to", "updated_at"])

    previous_name = previous.full_name if previous else "Unassigned"
    LeadStatusHistory.objects.create(
        lead=lead,
        old_status=lead.status,
        new_status=lead.status,
        changed_by=changed_by,
        note=f"Reassigned from {previous_name} to {assigned_to.full_name}.",
    )
    return lead
