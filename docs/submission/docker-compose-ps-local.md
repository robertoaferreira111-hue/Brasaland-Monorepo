# Local docker compose evidence
Captured: 2026-10-20T23:57:30Z

```
NAME              IMAGE           COMMAND                  SERVICE   CREATED          STATUS          PORTS
brasaland-api-1   brasaland-api   "uvicorn app.main:ap…"   api       55 minutes ago   Up 32 seconds   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
brasaland-ui-1    brasaland-ui    "docker-entrypoint.s…"   ui        55 minutes ago   Up 32 seconds   0.0.0.0:3000-3001->3000-3001/tcp, [::]:3000-3001->3000-3001/tcp
```

## Smoke
- health: {"status":"ok"}
- website: 200
- backoffice: 200
- dns: {"status":"ok"}

VPS: waived by instructor (rubric item added after assignment start).
