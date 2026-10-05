# UI apps follow their own README

**Scope:** file-pattern

**Globs:** `uis/**`

## Rule

This rule applies when a change creates or edits any file matching `uis/**`.

- Follow the stack and run instructions in that app's own README. For `uis/website/`, that README says static HTML, Tailwind utility classes compiled to `styles.css`, and `validation.js`. The build command is `npm run build:css`, run from `uis/website/`. The documented static server, also from that directory, is `npx http-server . -p 3000 -a 0.0.0.0`.
- If the app directory has no README, stop and ask. Do not invent a framework, a package manager, a lint script, or a test script. `uis/backoffice/` is in that state: the folder is not in the repo.
- Keep `uis/website/` and `uis/backoffice/` as separate apps with separate layouts. Do not import a layout, stylesheet, or page from one into the other. Do not duplicate a page by copying it across those apps.
- Company facts rendered in the UI must pass the always-active rule in `.agents/rules/company-facts.md`.
- Do not add a second copy of an existing website section in the other app just to satisfy a milestone checkbox. Shared domain wording still has to come from `CONTEXT.md`, written for that app's audience.
