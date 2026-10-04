from django.db import migrations

PREFIX = "/consultations/"


def remove_orphans(apps, schema_editor):
    """Delete bell notifications whose consultation no longer exists (dead links)."""
    Notification = apps.get_model("notifications", "Notification")
    Consultation = apps.get_model("clinical", "Consultation")
    existing = {str(pk) for pk in Consultation.objects.values_list("pk", flat=True)}
    orphan_ids = [
        n.pk
        for n in Notification.objects.filter(link__startswith=PREFIX).only("pk", "link")
        if n.link[len(PREFIX) :].strip("/") not in existing
    ]
    Notification.objects.filter(pk__in=orphan_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0003_contactpreference_messagetemplate_and_more"),
        ("clinical", "0003_consultation_reminder_sent_at"),
    ]

    operations = [migrations.RunPython(remove_orphans, migrations.RunPython.noop)]
