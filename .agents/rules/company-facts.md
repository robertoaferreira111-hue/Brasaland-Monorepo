# Company facts come from CONTEXT.md

**Scope:** always active

**Applies to:** every file the agent reads or edits in this repository.

## Rule

Use the root `CONTEXT.md` as the primary source of Brasaland company facts (description, people, locations, counts, currencies, programme names, forward work).

For supplier directory field names, categories, and statuses, also use `Supplier-Directory-CONTEXT.md`.

Do not invent company data. Do not fill gaps from memory or a generic restaurant template.

If a fact is not in those context files:

- Leave it out of copy, fixtures, and comments that claim to describe the business.
- Mark it as an open question, or stop and ask.
- Do not add the fact to `CONTEXT.md` unless the developer explicitly confirms that edit.

`memory-bank/projectbrief.md` restates the briefing for session startup. If it ever disagrees with `CONTEXT.md`, `CONTEXT.md` wins, and the agent stops to report the mismatch.
