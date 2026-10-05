# Company facts come from CONTEXT.md

**Scope:** always active

**Applies to:** every file the agent reads or edits in this repository.

## Rule

Use the root `CONTEXT.md` as the only source of Brasaland company facts. That includes the company description, people, locations, counts, currencies, programme names, and the forward work of each department.

Do not invent company data. Do not fill gaps from the Milestone 1 website, from `CONTEXT.es.md`, from memory, or from a generic restaurant template.

If a fact is not in `CONTEXT.md`:

- Leave it out of copy, fixtures, and comments that claim to describe the business.
- Mark it as an open question, or stop and ask.
- Do not add the fact to `CONTEXT.md` unless the developer explicitly confirms that edit. `CONTEXT.md` is protected in `AGENTS.md`.

`memory-bank/projectbrief.md` restates the briefing for session startup. If it ever disagrees with `CONTEXT.md`, `CONTEXT.md` wins, and the agent stops to report the mismatch.
