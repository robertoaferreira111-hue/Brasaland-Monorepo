# `uis` folder

This folder contains **all projects with a user interface** for the cross-functional AI Engineering company project — for example: a public website, admin dashboard frontend, ecommerce UI, customer portals, Streamlit/Gradio app or other frontend-only tools.

The two main projects stored here are:

- **`website`** — the company's public-facing web presence.
- **`backoffice`** — the internal admin application. This is the ideal place to develop multiple solutions within a single project: authentication, people management, operations management, internal communication, and other back-office capabilities.

Organize `uis/` by **different concerns** — each subfolder covers a distinct area of the company (for example, public web vs internal operations) and includes its own technical and functional documentation.

- **Main purpose**: to centralize in a single place all frontend applications that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the applications you add, their objective, the technology used, and how to run them.

## `website` — Brasaland public site

Milestone 1 corporate website. Static HTML, Tailwind utility classes, and `validation.js`. Base language: English. Facts come from the root `CONTEXT.md`.

```bash
cd uis/website
npx http-server . -p 3000 -a 0.0.0.0
```

See [website/README.md](./website/README.md).

## `backoffice` — Brasaland staff app

Next.js app for staff sign-in. It does not change the public website.

```bash
cd uis/backoffice
npm install
npm run dev
```

Open `http://127.0.0.1:3001`. `/login` and `/register` are public. `/account` redirects to `/login` when `localStorage` has no JWT. The API URL defaults to `http://127.0.0.1:8000` (`NEXT_PUBLIC_API_URL`).

Start the matching API first (from repo root):

```bash
cd services/api && uv sync && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then run the backoffice (`npm run dev` on port 3001). The public `website` app does not use this API.

See [backoffice/README.md](./backoffice/README.md).

> _Estas instrucciones también están disponibles en [español](./README.es.md)._
