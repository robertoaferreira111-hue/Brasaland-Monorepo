# Brasaland supplier directory

Internal procurement directory for Lucía Fernández. Static HTML, CSS, and JavaScript. Records come from the FastAPI app in `services/api`. Field names, categories, and statuses come from `Supplier-Directory-CONTEXT.md`.

## Run

Start the API from `services/api`:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

If the database is empty, load the context suppliers once:

```bash
uv run seed
```

Serve this folder:

```bash
npx http-server . -p 3001 -a 0.0.0.0
```

Open `http://127.0.0.1:3001`.
