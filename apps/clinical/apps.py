from django.apps import AppConfig


class ClinicalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.clinical"
    label = "clinical"

    def ready(self):
        from apps.clinical import signals  # noqa: F401  (connects the receivers)
