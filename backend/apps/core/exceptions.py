from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

ERROR_CODES = {
    400: "validation_error",
    401: "not_authenticated",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    429: "throttled",
}


def api_exception_handler(exc, context):
    """All errors look like: {"error": {"code", "message", "details"}}."""
    response = exception_handler(exc, context)

    if response is None:
        if isinstance(exc, IntegrityError):
            return Response(
                {
                    "error": {
                        "code": "conflict",
                        "message": "This record conflicts with existing data.",
                        "details": {},
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        return None  # Django's normal 500 handling (no stack trace when DEBUG is off)

    data = response.data
    code = ERROR_CODES.get(response.status_code, "error")
    details = {}

    if response.status_code == 400:
        message = "Please correct the highlighted fields."
        details = data if isinstance(data, dict) else {"non_field_errors": data}
    elif isinstance(data, dict) and "detail" in data:
        message = str(data["detail"])
    else:
        message = "Something went wrong."

    response.data = {"error": {"code": code, "message": message, "details": details}}
    return response
