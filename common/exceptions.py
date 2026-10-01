from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc, context):
    """
    Normalizes all DRF error responses to the project-wide envelope:
    {"success": false, "message": str, "errors": dict, "code": str}
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        return response

    original = response.data
    code = getattr(exc, "default_code", "error")
    code = str(code).upper() if code else "ERROR"

    if isinstance(original, dict) and "detail" in original and len(original) == 1:
        message = str(original["detail"])
        errors = {}
    elif isinstance(original, dict):
        message = "Validation failed."
        errors = original
    elif isinstance(original, list):
        message = "Validation failed."
        errors = {"non_field_errors": original}
    else:
        message = str(original)
        errors = {}

    response.data = {
        "success": False,
        "message": message,
        "errors": errors,
        "code": code,
    }
    return response
