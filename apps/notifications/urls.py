from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.notifications.views import (
    ContactPreferenceView,
    MessageTemplateViewSet,
    MessagingStatusView,
    NotificationLogViewSet,
    NotificationViewSet,
    RunRemindersView,
    TestMessageView,
)

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")
router.register("messaging/templates", MessageTemplateViewSet, basename="message-template")
router.register("messaging/logs", NotificationLogViewSet, basename="message-log")

urlpatterns = [
    path("me/contact-preferences/", ContactPreferenceView.as_view(), name="contact-preferences"),
    path("messaging/status/", MessagingStatusView.as_view(), name="messaging-status"),
    path("messaging/test/", TestMessageView.as_view(), name="messaging-test"),
    path("messaging/reminders/run/", RunRemindersView.as_view(), name="messaging-reminders-run"),
    path("", include(router.urls)),
]
