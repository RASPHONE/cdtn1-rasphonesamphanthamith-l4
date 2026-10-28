class AppError(Exception):
    """
    Application/business error carrying a machine-readable code.

    This class must NOT know HTTP status codes: services raise it, and the
    presentation layer (src/main.py) translates `code` to HTTP via HTTP_BY_CODE.

    - details: optional list of {field, message} for validation errors.
    - extra:   optional dict merged into the JSON body (e.g. {"conflicts": [...]}).
    """

    def __init__(self, code: str, message: str, details=None, extra=None):
        self.code = code
        self.message = message
        self.details = details
        self.extra = extra
        super().__init__(message)


HTTP_BY_CODE = {
    # 400 - malformed or missing request data
    "bad_request": 400,

    # 401 - unauthorized
    "unauthorized": 401,
    "invalid_credentials": 401,

    # 403 - center scoping / QT-14
    "cross_center_access": 403,

    # 404 - resource not found
    "ticket_not_found": 404,
    "appointment_not_found": 404,
    "technician_not_found": 404,
    "skill_not_found": 404,
    "category_not_found": 404,

    # 409 - conflict
    "appointment_conflict": 409,
    "skill_already_exists": 409,

    # 422 - business rule violation
    "technician_not_qualified": 422,
    "ticket_not_assignable": 422,
    "reason_required": 422,
    "appointment_type_deferred": 422,
    "appointment_in_past": 422,
    "invalid_time_range": 422,
    "appointment_completed_cannot_delete": 422,
    "appointment_completed_cannot_update": 422,
    "proficiency_out_of_range": 422,
    "category_inactive": 422,

    # 500 / 503 - server side
    "internal_error": 500,
    "database_unavailable": 503,
}
