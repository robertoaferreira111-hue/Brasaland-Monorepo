# Brasaland backoffice

Next.js staff app for sign-in, registration, and the protected account page. The public website in `uis/website` is a separate app and does not check for a session.

## Run

```bash
cd uis/backoffice
npm install
npm run dev
```

Open `http://127.0.0.1:3001`.

The API base URL is `NEXT_PUBLIC_API_URL`. Copy `.env.example` to `.env.local` to change it. The default is `http://127.0.0.1:8000`.

## Routes

- Public in this app: `/login`, `/register`.
- Protected in this app: `/account` only. `app/account/layout.tsx` wraps the page in a client `AuthGuard` that reads the JWT from `localStorage` and redirects to `/login` when it is missing. There is no `middleware.ts`.
- `/` sends you to `/account` when a token is stored, and to `/login` otherwise.
- The public website in `uis/website` is a separate app. It is not behind this guard and needs no token.

## Account profile

- Loads the signed-in user with `GET /auth/me` and shows email as read-only.
- Edits name, phone, and address with `PUT /profiles/me`.
- Both authenticated calls send `Authorization: Bearer <token>`.
- Refreshing `/account` keeps the session while the token remains in `localStorage`.

## Session

Login calls `POST /auth/login`. Registration calls `POST /users`, then `POST /auth/login` with the same email and password. Both store the JWT in `localStorage`. Protected calls send `Authorization: Bearer <token>`.

Logout calls `POST /auth/logout` when possible, then always clears the local session and opens `/login`. A protected `401` tries `POST /auth/refresh` once when a refresh token exists. If refresh fails or is missing, the session is cleared once and the app opens `/login` without a redirect loop.

There is no `middleware.ts`. The token is in `localStorage`, so the guard is a client check.
