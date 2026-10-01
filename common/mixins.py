class EnvelopeMixin:
    """
    Wraps any 2xx DRF response body that is not already enveloped into the
    standard {"success": true, "message": str, "data": ...} shape.
    Paginated list responses already provide their own envelope and are left untouched.
    """

    success_message = "Operation successful."

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if (
            hasattr(response, "data")
            and isinstance(response.data, dict)
            and "success" in response.data
        ):
            return response
        if response.status_code and 200 <= response.status_code < 300:
            response.data = {
                "success": True,
                "message": self.success_message,
                "data": response.data,
            }
        return response
