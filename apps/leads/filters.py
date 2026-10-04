import django_filters

from apps.leads.models import Lead


class LeadFilter(django_filters.FilterSet):
    created_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Lead
        fields = ["status", "priority", "assigned_to", "source", "campaign", "product"]
