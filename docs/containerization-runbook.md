# Containerization runbook (infra-40)

## Local (development)

```bash
cp .env.example .env   # if needed; .env is gitignored
docker compose up --build
```

Uses [`docker-compose.yml`](../docker-compose.yml): bind mounts + Uvicorn `--reload`.

- Website: http://127.0.0.1:3000  
- Backoffice: http://127.0.0.1:3001  
- API health: http://127.0.0.1:8000/health  

- **Browser → API (local):** `http://127.0.0.1:8000`  
- **Browser → API (VPS / remote host):** `http://<hostname>:8000` (see `session.js`)  
- **Container → API:** `http://api:8000` (`API_INTERNAL_URL`)

If `/health` resets right after `compose up`, wait a few seconds for the reloader to finish.

```bash
docker compose exec api python -m app.seed
docker compose config --no-interpolate --quiet
```

## Production (VPS)

Use [`docker-compose.prod.yml`](../docker-compose.prod.yml) (no bind mounts, no `--reload`).

Full procedure, risks, rollback, and **approval gate**: [`docs/vps-deployment.md`](vps-deployment.md).

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

Set `JWT_SECRET` and `CORS_ORIGINS` in the server `.env` only.

## Notes

- UIs are static HTML (not Next.js); ports and single-UI-container layout match the assignment.
- `services/api/requirements.txt` is pinned from `uv.lock`.
