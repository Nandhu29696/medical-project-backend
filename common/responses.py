from rest_framework.response import Response


def success_response(data=None, message="Operation successful.", status_code=200):
    return Response(
        {"success": True, "message": message, "data": data if data is not None else {}},
        status=status_code,
    )


def error_response(message="Request failed.", errors=None, code="ERROR", status_code=400):
    return Response(
        {"success": False, "message": message, "errors": errors or {}, "code": code},
        status=status_code,
    )
