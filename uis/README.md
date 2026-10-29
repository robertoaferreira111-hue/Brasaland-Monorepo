# `uis` folder

This folder contains **all projects with a user interface** for the cross-functional AI Engineering company project — for example: a public website, admin dashboard frontend, ecommerce UI, customer portals, Streamlit/Gradio app or other frontend-only tools.

The two main projects stored here are:

- **`website`** — the company's public-facing web presence.
- **`backoffice`** — the internal admin application. This is the ideal place to develop multiple solutions within a single project: authentication, people management, operations management, internal communication, and other back-office capabilities.

Organize `uis/` by **different concerns** — each subfolder covers a distinct area of the company (for example, public web vs internal operations) and includes its own technical and functional documentation.

- **Main purpose**: to centralize in a single place all frontend applications that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the applications you add, their objective, the technology used, and how to run them.

## `website` — Brasaland public site

Milestone 1 corporate website. Next.js App Router + TypeScript + Tailwind (same React pattern as the talent pipeline tracker). Base language: English. Facts come from the root `CONTEXT.md`.

```bash
cd uis/website
npm install
npm run dev
```

Open `http://127.0.0.1:3000`. See [website/README.md](./website/README.md).

## `backoffice` — supplier directory

Procurement directory for Lucía Fernández, with staff sign-in on the same static app. HTML, CSS, and JavaScript. It calls the supplier API in `services/api`. Supplier routes require a JWT. `/login/` and `/register/` are public. The directory and `/account/profile/` redirect to `/login/` when `localStorage` has no access token. A 401 clears the session and returns to login. The public website navigation is unchanged.

```bash
cd uis/backoffice
npx http-server . -p 3001 -a 0.0.0.0
```

See [backoffice/README.md](./backoffice/README.md).

## `talent-pipeline-tracker` — Brasaland People & Talent

Milestone 3 internal talent pipeline tracker (Next.js App Router + TypeScript + Tailwind). Used by People & Talent to manage the Executive Assistant search.

```bash
cd uis/talent-pipeline-tracker
cp .env.example .env.local
npm install
npm run dev
```

See [talent-pipeline-tracker/README.md](./talent-pipeline-tracker/README.md).

> _Estas instrucciones también están disponibles en [español](./README.es.md)._
