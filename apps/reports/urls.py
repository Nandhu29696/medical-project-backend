from django.urls import path

from apps.leads.views import LeadExportView
from apps.reports.views import (
    ConversionsReportView,
    DashboardSummaryView,
    FollowupsReportView,
    LeadFunnelView,
    LeadsReportView,
    LeadTrendView,
    SalesPerformanceView,
    SourcePerformanceView,
)

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("dashboard/lead-funnel/", LeadFunnelView.as_view(), name="dashboard-lead-funnel"),
    path("dashboard/lead-trend/", LeadTrendView.as_view(), name="dashboard-lead-trend"),
    path(
        "dashboard/source-performance/",
        SourcePerformanceView.as_view(),
        name="dashboard-source-performance",
    ),
    path(
        "dashboard/sales-performance/",
        SalesPerformanceView.as_view(),
        name="dashboard-sales-performance",
    ),
    path("reports/leads/", LeadsReportView.as_view(), name="reports-leads"),
    path("reports/conversions/", ConversionsReportView.as_view(), name="reports-conversions"),
    path("reports/followups/", FollowupsReportView.as_view(), name="reports-followups"),
    path("reports/export/", LeadExportView.as_view(), name="reports-export"),
]
