# Services

Typed data-access functions for the Talent Tracker API. Components and feature hooks must call these modules instead of using `fetch` directly.

| Module | Functions |
| --- | --- |
| `records.ts` | `listCandidates`, `getCandidate`, `createCandidate`, `updateCandidate`, `patchCandidate` |
| `notes.ts` | `listNotes`, `addNote`, `deleteNote` |
| `index.ts` | Re-exports |

HTTP transport lives in `lib/httpClient.ts`. Types live in `types/api.ts`.
