"""Brasaland supplier directory API with staff JWT auth."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.background import BackgroundTask
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import STORAGE_UNAVAILABLE, StorageError, UNEXPECTED_ERROR
from app.routers import auth, profiles, users
from app.routers.suppliers import router as suppliers_router
from app.routers.telemetry import router as telemetry_ingest_router
from app.telemetry import (
    LOGIN_FAILURE_DETAIL,
    PROTECTED_ROUTE_DETAILS,
    emit_protected_route_unauthenticated,
    emit_request_validation_rejected,
    emit_staff_login_failed,
    emit_storage_unavailable,
)
from app.telemetry_path import ensure_telemetry_on_path

ensure_telemetry_on_path()
from router import router as telemetry_report_router  # noqa: E402

_REPORTING_ROUTER = Path(__file__).resolve().parents[2] / "reporting" / "router.py"
_reporting_spec = importlib.util.spec_from_file_location("brasaland_reporting_router", _REPORTING_ROUTER)
if _reporting_spec is None or _reporting_spec.loader is None:
    raise RuntimeError("services/reporting/router.py is missing")
_reporting_module = importlib.util.module_from_spec(_reporting_spec)
sys.modules["brasaland_reporting_router"] = _reporting_module
_reporting_spec.loader.exec_module(_reporting_module)
reporting_router = _reporting_module.router

logger = logging.getLogger("brasaland.api")

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

app = FastAPI(title="Brasaland Supplier Directory", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3001",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_origin_regex=r"https://.*\.app\.github\.dev",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(suppliers_router)
app.include_router(telemetry_report_router)
app.include_router(telemetry_ingest_router)
app.include_router(reporting_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _route_path(request: Request) -> str:
    return request.url.path


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Keep the existing `{detail}` contract for intentional HTTP errors."""
    background = None
    detail = exc.detail
    path = _route_path(request)
    if (
        exc.status_code == 401
        and isinstance(detail, str)
        and detail == LOGIN_FAILURE_DETAIL
        and path.rstrip("/").endswith("/auth/login")
    ):
        background = BackgroundTask(emit_staff_login_failed)
    elif (
        exc.status_code == 401
        and isinstance(detail, str)
        and detail in PROTECTED_ROUTE_DETAILS
    ):
        background = BackgroundTask(
            emit_protected_route_unauthenticated,
            route=path,
            detail=detail,
        )
    elif exc.status_code == 500 and detail == STORAGE_UNAVAILABLE:
        background = BackgroundTask(
            emit_storage_unavailable,
            route=path,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
        background=background,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Preserve FastAPI's standard 422 validation body shape."""
    errors = exc.errors()
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(errors)},
        background=BackgroundTask(
            emit_request_validation_rejected,
            route=_route_path(request),
            error_count=len(errors) or 1,
        ),
    )


@app.exception_handler(StorageError)
async def storage_exception_handler(
    request: Request, exc: StorageError
) -> JSONResponse:
    """Map storage-boundary failures from any dependency to a safe 500."""
    logger.exception("Storage boundary failure: %s", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": STORAGE_UNAVAILABLE},
        background=BackgroundTask(
            emit_storage_unavailable,
            route=_route_path(request),
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    """Log unexpected failures server-side; never return tracebacks or paths."""
    logger.exception("Unhandled application error: %s", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": UNEXPECTED_ERROR},
    )
