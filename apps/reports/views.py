from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.models import RoleCode
from apps.followups.models import FollowUp, FollowUpStatus
from apps.leads.models import Lead, LeadStatus
from common.permissions import IsCrmUser
from common.responses import success_response


def _visible_leads(user):
    queryset = Lead.objects.all()
    if user.role == RoleCode.SALES_EXECUTIVE:
        queryset = queryset.filter(assigned_to=user)
    return queryset


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsCrmUser]

    def get(self, request):
        leads = _visible_leads(request.user)
        today = timezone.now().date()
        total = leads.count()
        converted = leads.filter(status=LeadStatus.CONVERTED).count()

        data = {
            "total_leads": total,
            "new_leads": leads.filter(status=LeadStatus.NEW).count(),
            "today_leads": leads.filter(created_at__date=today).count(),
            "pending_followups": FollowUp.objects.filter(
                status=FollowUpStatus.PENDING,
                lead__in=leads,
            ).count(),
            "interested_leads": leads.filter(status=LeadStatus.INTERESTED).count(),
            "converted_leads": converted,
            # Avoid a misleading percentage when there is no data yet.
            "conversion_rate": round((converted / total) * 100, 2) if total else None,
        }
        return success_response(data)


class LeadFunnelView(APIView):
    permission_classes = [IsAuthenticated, IsCrmUser]

    def get(self, request):
        leads = _visible_leads(request.user)
        funnel = list(leads.values("status").annotate(count=Count("id")).order_by("status"))
        return success_response(funnel)


class SourcePerformanceView(APIView):
    permission_classes = [IsAuthenticated, IsCrmUser]

    def get(self, request):
        leads = _visible_leads(request.user)
        data = list(
            leads.exclude(source="")
            .values("source")
            .annotate(total=Count("id"), converted=Count("id", filter=_converted_filter()))
            .order_by("-total")
        )
        return success_response(data)


class SalesPerformanceView(APIView):
    permission_classes = [IsAuthenticated, IsCrmUser]

    def get(self, request):
        leads = _visible_leads(request.user)
        data = list(
            leads.exclude(assigned_to__isnull=True)
            .values("assigned_to__id", "assigned_to__first_name", "assigned_to__last_name")
            .annotate(total=Count("id"), converted=Count("id", filter=_converted_filter()))
            .order_by("-total")
        )
        return success_response(data)


class LeadTrendView(APIView):
    permission_classes = [IsAuthenticated, IsCrmUser]

    def get(self, request):
        leads = _visible_leads(request.user)
        days = int(request.query_params.get("days", 14))
        start = timezone.now().date() - timedelta(days=days - 1)
        trend = []
        counts = {
            row["day"].isoformat(): row["count"]
            for row in (
                leads.filter(created_at__date__gte=start)
                .annotate(day=TruncDate("created_at"))
                .values("day")
                .annotate(count=Count("id"))
            )
        }
        for offset in range(days):
            day = start + timedelta(days=offset)
            trend.append({"date": day.isoformat(), "count": counts.get(day.isoformat(), 0)})
        return success_response(trend)


def _converted_filter():
    from django.db.models import Q

    return Q(status=LeadStatus.CONVERTED)


class LeadsReportView(APIView):
    permission_classes = [IsAuthenticated, IsCrmUser]

    def get(self, request):
        from apps.leads.serializers import LeadListSerializer

        leads = _visible_leads(request.user).select_related("product", "campaign", "assigned_to")
        return success_response(LeadListSerializer(leads, many=True).data)


class ConversionsReportView(APIView):
    permission_classes = [IsAuthenticated, IsCrmUser]

    def get(self, request):
        from apps.leads.serializers import LeadListSerializer

        leads = (
            _visible_leads(request.user)
            .filter(status=LeadStatus.CONVERTED)
            .select_related("product", "campaign", "assigned_to")
        )
        return success_response(LeadListSerializer(leads, many=True).data)


class FollowupsReportView(APIView):
    permission_classes = [IsAuthenticated, IsCrmUser]

    def get(self, request):
        leads = _visible_leads(request.user)
        data = list(
            FollowUp.objects.filter(lead__in=leads)
            .values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        return success_response(data)
