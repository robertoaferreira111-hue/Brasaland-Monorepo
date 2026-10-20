# FastAPI backend container (ticket #infra-40 / Phase 2).
# App root: services/api — entry point app.main:app — port 8000.
# Python >=3.12 matches services/api/pyproject.toml.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install uv (assignment: uv pip install -r requirements.txt).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Pinned requirements exported from uv.lock (production deps only; no .env).
COPY api/requirements.txt ./requirements.txt
RUN uv pip install --system -r requirements.txt

# Application source (tests/ excluded via .dockerignore).
COPY api/ ./

EXPOSE 8000

# Bind 0.0.0.0 so other containers / host-published ports can reach the API.
# --reload supports Compose bind-mount development workflow.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
