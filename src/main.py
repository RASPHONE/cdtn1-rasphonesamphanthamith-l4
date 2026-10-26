from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.errors import AppError, HTTP_BY_CODE
from src.routes.health import router as health_router
from src.routes.appointments import router as appointments_router
from src.routes.technician_skills import router as technician_skills_router

def create_app() -> FastAPI:
    app = FastAPI(
        title="Mekong Mobile L4",
        description="Technician Assignment and Appointment Scheduling",
        version="0.2.0",
    )

    app.include_router(health_router)
    app.include_router(appointments_router)
    app.include_router(technician_skills_router)

    @app.exception_handler(AppError)
    async def app_error_handler(request, exc: AppError):
        status_code = HTTP_BY_CODE.get(exc.code, 422)

        payload = {
            "error": exc.code,
            "message": exc.message,
        }

        if exc.details is not None:
            payload["details"] = exc.details

        return JSONResponse(status_code=status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request, exc: RequestValidationError):
        details = []

        for error in exc.errors():
            location_parts = [
                str(part)
                for part in error.get("loc", [])
                if part != "body"
            ]

            details.append(
                {
                    "field": ".".join(location_parts),
                    "message": error.get("msg"),
                }
            )

        return JSONResponse(
            status_code=400,
            content={
                "error": "bad_request",
                "message": "Request data is missing or malformed.",
                "details": details,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request, exc: Exception):
        # Do not leak stack traces, SQL, or internal details.
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "Unexpected server error.",
            },
        )

    return app


app = create_app()
