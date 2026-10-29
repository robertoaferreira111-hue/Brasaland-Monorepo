"""Brasaland supplier directory API with staff JWT auth."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import STORAGE_UNAVAILABLE, StorageError, UNEXPECTED_ERROR
from app.routers import auth, profiles, users
from app.routers.suppliers import router as suppliers_router

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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    _request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Keep the existing `{detail}` contract for intentional HTTP errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Preserve FastAPI's standard 422 validation body shape."""
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(exc.errors())},
    )


@app.exception_handler(StorageError)
async def storage_exception_handler(
    _request: Request, exc: StorageError
) -> JSONResponse:
    """Map storage-boundary failures from any dependency to a safe 500."""
    logger.exception("Storage boundary failure: %s", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": STORAGE_UNAVAILABLE},
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
