# Required project structure

## App location
`uis/talent-pipeline-tracker/`

## Folders
- `app/` — App Router pages
- `app/candidates/[id]/` — candidate detail (`GET /records/:id`)
- `app/candidates/[id]/edit/` — edit form (`PUT /records/:id`)
- `app/candidates/new/` — register form (`POST /records`)
- `components/`
- `hooks/`
- `types/`
- `lib/` (API client / helpers)

## Env
- `.env.example` committed
- `.env.local` not committed (`NEXT_PUBLIC_API_URL`)

## API base
`https://playground.4geeks.com/tracker/api/v1`
Docs: `https://playground.4geeks.com/tracker/api/v1/docs`
