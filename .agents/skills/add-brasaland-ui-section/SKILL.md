# Add a Brasaland UI section from CONTEXT.md

**Scope:** agent-requested. Use this when the task is to add one section or view to a Brasaland UI.

## Objective

Add one visible section or view to a single existing app under `uis/`, using only company facts that appear in the root `CONTEXT.md` (and supplier facts from `Supplier-Directory-CONTEXT.md` when the target is the backoffice supplier desk).

This skill does one thing. It does not create a new app, change `CONTEXT.md`, or restyle an unrelated page.

## Inputs

Provide all three. If any input is missing, stop and ask.

| Input | Required value |
| --- | --- |
| Target app | A directory that already exists under `uis/` and has a README (`uis/website/` or `uis/backoffice/`). |
| Source passage | The `CONTEXT.md` / `Supplier-Directory-CONTEXT.md` heading or paragraph this view is allowed to use. |
| Destination | The file inside the target app to edit, or a new file path inside that same app. |

## Expected output

- One section or view in the destination file.
- Visible markup in that app.
- Wording limited to the source passage plus labels that do not state new business facts.
- When the target is `uis/website/` and a class list or `tailwind.css` input changes, `styles.css` rebuilt by the existing script.

## Steps

1. Read `CONTEXT.md`, `memory-bank/techContext.md`, the target app README, and `.agents/rules/uis-apps.md`.
2. Reject the task if the target app directory does not exist or has no README.
3. Write the section from the source passage only.
4. If the edit is under `uis/website/` and utility classes changed, run `npm run build:css` from `uis/website/`.
5. If the edit is under `uis/backoffice/` and touches API/session behaviour, keep using `js/session.js` rather than inventing a second auth client.
6. Check the acceptance criteria below.

## Acceptance criteria

1. **Facts.** Every company fact in the new section is present in the allowed context files.
2. **On screen.** The new section is in the app's rendered markup.
3. **One app.** The diff stays inside the target app.
4. **Separate layout.** No import/copy of layout/stylesheet/page from the other UI app.
5. **CSS build.** If `uis/website/` files changed, `npm run build:css` from that folder exits 0.
6. **No invented commands.** No new lint/test/Docker inventiveness unless the task asks for it.
7. **Protected paths.** Diff does not modify protected paths listed in `AGENTS.md` unless explicitly requested.
