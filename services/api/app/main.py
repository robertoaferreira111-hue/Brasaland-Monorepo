"""Brasaland supplier directory API with staff JWT auth."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, profiles, users
from app.routers.suppliers import router as suppliers_router

app = FastAPI(title="Brasaland Supplier Directory", version="0.1.0")

_DEFAULT_ORIGINS = [
    "http://127.0.0.1:3001",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]
# Comma-separated extras for VPS / custom hosts (never commit real secrets; origins only).
_EXTRA_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[*_DEFAULT_ORIGINS, *_EXTRA_ORIGINS],
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
