class AppError(Exception):
    """
    Application/business error.

    This class must NOT know HTTP status codes.
    HTTP mapping happens in the presentation layer / error handler.
    """

    def __init__(self, code: str, message: str, details=None):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


HTTP_BY_CODE = {
    # 400 - malformed or missing request data
    "bad_request": 400,
    "invalid_pagination": 400,

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
    "proficiency_out_of_range": 422,
    "category_inactive": 422,
    "ticket_not_found_or_unassigned": 422,
}
