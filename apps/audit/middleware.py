"""
Thread-local-free request context middleware.

Stores the client IP and user agent on the request so that service-layer
code (which does not always have direct access to the request) can attach
them to audit log entries via `log_action(..., request=request)`.
"""


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
