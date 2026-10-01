from rest_framework.throttling import AnonRateThrottle


class PublicLeadRateThrottle(AnonRateThrottle):
    scope = "public_lead"
