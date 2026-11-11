import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src import config
from src.config import get_settings
from src.db import DatabaseUnavailableError
from src.errors import HTTP_BY_CODE, AppError
from src.routes.appointments import router as appointments_router
from src.routes.auth import router as auth_router
from src.routes.health import router as health_router
from src.routes.issue_categories import router as issue_categories_router
from src.routes.technician_skills import router as technician_skills_router
from src.routes.tickets import router as tickets_router

logger = logging.getLogger("l4.api")


def configure_logging() -> None:
    logging.basicConfig(
        level=get_settings().log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    if config.RANDOM_JWT_SECRET_IN_USE:
        logger.warning("JWT_SECRET is not set: using a random secret for this process "
                       "(logins end when the API restarts).")

    app = FastAPI(
        title="Mekong Mobile L4",
        description="Technician Assignment and Appointment Scheduling",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        # One id per request: returned in the X-Request-ID header and in 500
        # bodies, and written to every log line about this request.
        request_id = uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%.0f",
            request_id, request.method, request.url.path, response.status_code, elapsed_ms,
        )
        return response

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(appointments_router)
    app.include_router(technician_skills_router)
    app.include_router(tickets_router)
    app.include_router(issue_categories_router)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        status_code = HTTP_BY_CODE.get(exc.code, 422)

        payload = {
            "error": exc.code,
            "message": exc.message,
        }

        if exc.details is not None:
            payload["details"] = exc.details

        if exc.extra:
            payload.update(exc.extra)

        return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        # A body that is not JSON at all has no field to name: Pydantic reports the
        # character position as the location, which is meaningless to the caller.
        if any(error.get("type") == "json_invalid" for error in exc.errors()):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "bad_request",
                    "message": "Request body is not valid JSON.",
                    "details": [{"field": "body", "message": "JSON decode error"}],
                },
            )

        details = []

        for error in exc.errors():
            location_parts = [
                str(part)
                for part in error.get("loc", [])
                if part not in ("body", "query", "path")
            ]

            details.append(
                {
                    "field": ".".join(location_parts),
                    "message": error.get("msg"),
                }
            )

        fields = ", ".join(sorted({d["field"] for d in details if d["field"]}))
        message = "Request data is missing or malformed"
        message += f": {fields}." if fields else "."

        return JSONResponse(
            status_code=400,
            content={
                "error": "bad_request",
                "message": message,
                "details": details,
            },
        )

    # Errors raised by the framework itself (unknown path 404, wrong method 405) use the
    # same envelope as every other error (API contract §1), not FastAPI's {"detail": ...}.
    @app.exception_handler(StarletteHTTPException)
    async def framework_http_error_handler(request: Request, exc: StarletteHTTPException):
        codes = {404: ("not_found", "No such endpoint."),
                 405: ("method_not_allowed", "This method is not allowed on this endpoint.")}
        error, message = codes.get(exc.status_code, ("http_error", "The request could not be processed."))
        return JSONResponse(status_code=exc.status_code, content={"error": error, "message": message},
                            headers=getattr(exc, "headers", None))

    @app.exception_handler(DatabaseUnavailableError)
    async def database_unavailable_handler(request: Request, exc: DatabaseUnavailableError):
        logger.error(
            "request_id=%s database unavailable: %s",
            getattr(request.state, "request_id", "-"), exc,
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": "database_unavailable",
                "message": "The database is temporarily unavailable. Please try again shortly.",
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "-")
        # Full stack trace goes to the server log only, never to the client.
        logger.exception("request_id=%s unhandled error", request_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "Unexpected server error.",
                "request_id": request_id,
            },
        )

    return app


app = create_app()
