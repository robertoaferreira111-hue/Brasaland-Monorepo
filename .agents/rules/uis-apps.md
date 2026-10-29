# UI apps follow their own README

**Scope:** file-pattern

**Globs:** `uis/**`

## Rule

This rule applies when a change creates or edits any file matching `uis/**`.

- Follow the stack and run instructions in that app's own README.
- **`uis/website/`:** Next.js App Router + TypeScript + Tailwind v4 public site. Dev: `npm run dev` from `uis/website/` (port 3000). Build: `npm run build`. Follow that app's README.
- **`uis/backoffice/`:** Next.js App Router + TypeScript + Tailwind v4 staff desk documented in `uis/backoffice/README.md`. Dev: `npm run dev` from `uis/backoffice/` (port 3001). Session/API calls go through `lib/session.ts` to `services/api`.
- **`uis/talent-pipeline-tracker/`:** Next.js App Router talent tracker. Follow that app's README.
- If a new app directory under `uis/` has no README, stop and ask. Do not invent a framework.
- Keep `uis/website/` and `uis/backoffice/` as separate apps. Do not import a layout, stylesheet, or page from one into the other.
- Company facts rendered in the UI must pass `.agents/rules/company-facts.md`.
