# `services` folder

This folder contains **all the backend services** (APIs and background workers) related to the company for the cross-functional AI Engineering project.

Each subfolder inside `services/` must correspond to **one specific service** (for example: `admin-api`, `data-processor-worker`) and include its own technical and functional documentation.

- **Main purpose**: to centralize all the backend logic, APIs, and queue consumers that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the services you add, their objective, the technology used, and how to run them.

## `api` — supplier directory and staff auth

FastAPI + TinyDB service used by `uis/backoffice` on port **8000**. Supplier routes require a staff JWT. Register and login stay public.

```bash
cd services/api
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`uv run seed` loads the supplier list and creates `staff@brasaland.com` / `demo-password` when that account is missing. See [api/README.md](./api/README.md).

> _Spanish version: [README.es.md](./README.es.md)._
