FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    BRASALAND_ROOT=/opt/brasaland

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y dumb-init \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.6 /uv /uvx /bin/
COPY services/api/pyproject.toml services/api/uv.lock ./

FROM base AS development

RUN uv sync --frozen --no-install-project
COPY services/api/app ./app
COPY services/telemetry /opt/brasaland/services/telemetry
COPY services/reporting /opt/brasaland/services/reporting
COPY data/pipelines /opt/brasaland/data/pipelines
COPY data/process /opt/brasaland/data/process
RUN uv sync --frozen

EXPOSE 8000
ENTRYPOINT ["dumb-init", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production

RUN uv sync --frozen --no-dev --no-install-project
COPY services/api/app ./app
COPY services/telemetry /opt/brasaland/services/telemetry
COPY services/reporting /opt/brasaland/services/reporting
COPY data/pipelines /opt/brasaland/data/pipelines
COPY data/process /opt/brasaland/data/process
RUN uv sync --frozen --no-dev

EXPOSE 8000
ENTRYPOINT ["dumb-init", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
