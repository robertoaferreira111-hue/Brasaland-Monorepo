# Add a Brasaland UI section from CONTEXT.md

**Scope:** agent-requested. Use this when the task is to add one section or view to a Brasaland UI.

## Objective

Add one visible section or view to a single existing app under `uis/`, using only company facts that appear in the root `CONTEXT.md`.

This skill does one thing. It does not create a new app, change `CONTEXT.md`, or restyle an unrelated page.

## Inputs

Provide all three. If any input is missing, stop and ask.

| Input | Required value |
| --- | --- |
| Target app | A directory that already exists under `uis/` and has a README. Today that is `uis/website/` or `uis/backoffice/`. |
| Source passage | The `CONTEXT.md` heading or paragraph this view is allowed to use. |
| Destination | The file inside the target app to edit, or a new file path inside that same app. |

## Expected output

- One section or view in the destination file.
- Visible markup in that app (HTML, or the template language that app's README already uses). The new copy is not delivered only as a `console.log` or a terminal print.
- Wording limited to the source passage plus labels that do not state new business facts.
- When the target is `uis/website/` and a class list or `tailwind.css` input changes, `styles.css` rebuilt by the existing script.

## Steps

1. Read `CONTEXT.md`, `memory-bank/techContext.md`, the target app README, and `.agents/rules/uis-apps.md`.
2. Reject the task if the target app directory does not exist or has no README.
3. Write the section from the source passage only.
4. If the edit is under `uis/website/` and utility classes changed, run `npm run build:css` from `uis/website/`.
5. Check the acceptance criteria below. A failed criterion means the skill output is not done.

## Acceptance criteria

Each line is pass or fail.

1. **Facts.** Pass only if every company fact in the new section (names, counts, places, currencies, programme names, needs) is present in `CONTEXT.md`. A fact that appears only in `uis/website/` or in the old website specification is a fail.
2. **On screen.** Pass only if the new section is in the app's rendered markup. A comment, script log, or README-only mention is a fail.
3. **One app.** Pass only if the diff stays inside the target app. An edit under `uis/website/` that also creates or edits `uis/backoffice/`, or the reverse, is a fail.
4. **Separate layout.** Pass only if the change does not import or copy a layout, stylesheet, or page from the other UI app.
5. **CSS build.** If any file under `uis/website/` changed, pass only if `npm run build:css` run from `uis/website/` exits 0. If any file under `uis/backoffice/` changed, pass only if `npm run build:css` run from `uis/backoffice/` exits 0. If that app did not change, its build criterion does not apply.
6. **No invented commands.** Pass only if the change does not add a lint script, a test script, a Docker Compose file, or a package manager other than the npm lockfile that app already has.
7. **Protected paths.** Pass only if the diff does not modify `CONTEXT.md`, any template README, `.project_instructions/`, or the product folders `agents/`, `skills/`, `mcps/`, `workflows/`, `data/`, and `infra/`.
