# TESTING.md — Brasaland staff auth API

Test plan for ticket AUTH-088. The cases below are implemented in `tests/`. One earlier reproduction test, `tests/test_refresh_token_persists.py`, checks the double-open database question. Application code was not changed. Dev dependencies are pytest, pytest-cov, and httpx.

Source of behavior: `services/api` on `feature/auth-frontend` (`services/api/app/routers/users.py`, `services/api/app/routers/auth.py`, `services/api/app/routers/profiles.py`, `services/api/app/security.py`, `services/api/app/database.py`, `services/api/app/deps.py`, `services/api/app/models.py`).

Case IDs are stable. A later test should carry the ID in its name, for example `test_users_e1_duplicate_email`.

## 1. Purpose and scope

The suite will prove what each authentication endpoint decides for the inputs below: whether an account is created, whether a session is issued or rejected, and whether a profile or refresh token is changed. The coverage target for the auth module is 70%, not 100%.

Serialization and framework internals are out of scope. The suite does not assert JSON key order, content types, OpenAPI schema, FastAPI's validation-error envelope, status-line text, or how Pydantic and PyJWT are implemented. Where this plan names a reason such as "Incorrect email or password" or "Session expired", that string is the decision the application code raises in `HTTPException.detail`, not a snapshot of the framework's error document.

In scope:

- `POST /users`
- `POST /auth/login`
- `GET /auth/me`
- `PUT /profiles/me`
- `POST /auth/logout`
- `POST /auth/refresh`

Out of scope:

- `GET /health` in `services/api/app/main.py` (no authentication decision)
- CORS, the seed script, hash encoding, iteration count, and JWT claim layout except where a claim changes the decision (`exp`, `type`, `sub`, `jti`)
- The static client under `uis/backoffice`
- Two stored rows with the same email inserted outside `create_user`. Registration already rejects duplicates (USERS-E1, USERS-E3).
- The `put_my_profile` branch that returns "Not authenticated" when `update_profile` finds no row. `current_user_email` already requires that row in the same request, so the branch is unreachable in one request.

`services/api/tests/test_auth.py` already contains one chained test. This plan does not change that file. The cases below are the contract for the AUTH-088 suite.

Each endpoint table includes the AUTH-088 minimum (one happy, one edge, one failure) and the extra cases from section 3. Tier is `happy`, `edge`, or `failure`.

## 2. Planned test matrix

### POST /users

Registration. `RegisterUser` lowercases and strips email, requires a password of at least one character, and `create_user` refuses an email that is already stored.

| Case ID | Tier | Input condition | Expected business outcome | Implemented |
| --- | --- | --- | --- | --- |
| USERS-H1 | happy | New email and a non-empty password. Email may contain surrounding spaces and uppercase letters. | Account is created. The stored email is the trimmed lowercase address. Name, phone, and address are empty. The password is not part of the returned profile. The same password can later be used to sign in. | yes |
| USERS-E1 | edge | Email that already belongs to an account, repeated exactly. | Registration is rejected. Reason: "An account with this email already exists". The original account is unchanged. | yes |
| USERS-F1 | failure | Email that is present but not an address, such as `not-an-email`. | Registration is rejected before an account is created. The error identifies the email field. The exact sentence "Enter a valid email (example: name@email.com)" is not required. | yes |
| USERS-E2 | edge | Email is valid and password is an empty string. | Registration is rejected before an account is created. | yes |
| USERS-E3 | edge | Email differs from an existing account only by letter case or surrounding spaces. | Registration is rejected as a duplicate. Reason: "An account with this email already exists". | yes |
| USERS-E4 | edge | Password is a single space. | Account is created. Signing in with that same space succeeds. Signing in with an empty password does not. | yes |

### POST /auth/login

`LoginBody` strips and lowercases email and does not check the registration email pattern. `authenticate_user` returns no user for an unknown email and for a wrong password. Both become the same rejection.

| Case ID | Tier | Input condition | Expected business outcome | Implemented |
| --- | --- | --- | --- | --- |
| LOGIN-H1 | happy | Email and password of an existing account. | A usable access token and a usable refresh token are issued for that account. | yes |
| LOGIN-E1 | edge | Existing account, password is an empty string. | Sign-in is rejected. Reason: "Incorrect email or password". No tokens are issued. | yes |
| LOGIN-F1 | failure | Existing account, password is wrong and non-empty. | Sign-in is rejected. Reason: "Incorrect email or password". No tokens are issued. | yes |
| LOGIN-F2 | failure | Email that matches no account, any password. | Sign-in is rejected with the same reason as LOGIN-F1. No tokens are issued. | yes |
| LOGIN-E2 | edge | Email is an empty string, or only spaces. | Sign-in is rejected. Reason: "Incorrect email or password". No access token and no refresh token are issued. The same wording as a wrong password is intentional: the response does not reveal whether the email exists. | yes |
| LOGIN-E3 | edge | Existing account, email uses different letter case and surrounding spaces, password is correct. | Sign-in succeeds and tokens are issued for the stored lowercase email. | yes |

### GET /auth/me

Requires an access token whose subject is still a stored user (`current_user_email`). Expired tokens and tokens of the wrong type are rejected inside `decode_token` before the profile is read.

| Case ID | Tier | Input condition | Expected business outcome | Implemented |
| --- | --- | --- | --- | --- |
| ME-H1 | happy | Access token from LOGIN-H1 for an account whose profile was updated. | The decision is to return that account's email, name, phone, and address. | yes |
| ME-E1 | edge | Access token for an account that has never updated its profile. | The decision is to return that email with empty name, phone, and address. | yes |
| ME-F1 | failure | Access token whose `exp` is clearly in the past, such as several minutes ago. Do not use the exact second where `exp` equals now. | The caller is rejected. Reason: "Session expired". No profile is returned. | yes |
| ME-F2 | failure | No Authorization credentials. | The caller is rejected. Reason: "Not authenticated". | yes |
| ME-F3 | failure | A valid refresh token is presented where an access token is required. | The caller is rejected. Reason: "Invalid token". | yes |
| ME-F4 | failure | Authorization value is not a token this API signed. | The caller is rejected. Reason: "Invalid token". | yes |
| ME-E2 | edge | Access token was valid when issued, and that user row has since been removed. | The caller is rejected. Reason: "Not authenticated". This is a different decision from ME-F4. | yes |

### PUT /profiles/me

The route rejects the update when name, phone, or address is empty after stripping. A successful update stores the stripped values and leaves email unchanged.

| Case ID | Tier | Input condition | Expected business outcome | Implemented |
| --- | --- | --- | --- | --- |
| PROFILE-H1 | happy | Valid access token. Name, phone, and address each contain non-space characters, with leading or trailing spaces. | The profile is saved. Stored name, phone, and address are the stripped values. Email is unchanged. A later `GET /auth/me` returns those stripped values. | yes |
| PROFILE-E1 | edge | Valid access token. Name is only spaces. Phone and address are non-empty. | The update is rejected. Reason: "Name, phone, and address are required". The stored profile is unchanged. | yes |
| PROFILE-F1 | failure | Access token whose `exp` is clearly in the past, such as several minutes ago. Body would otherwise be a valid profile. Do not use the exact second where `exp` equals now. | The update is rejected. Reason: "Session expired". The stored profile is unchanged. | yes |
| PROFILE-E2 | edge | Valid access token. Phone is an empty string. Name and address are non-empty. | The update is rejected. Reason: "Name, phone, and address are required". The stored profile is unchanged. | yes |
| PROFILE-F2 | failure | No Authorization credentials. Body is a valid profile. | The update is rejected. Reason: "Not authenticated". The stored profile is unchanged. | yes |

### POST /auth/logout

Logout revokes every refresh-token row for the access token's email. It does not revoke the access token. That leftover access is a known limitation of this stateless JWT, not accepted product behavior. The existing chained test in `services/api/tests/test_auth.py` currently expects `GET /auth/me` to succeed after logout. Production code is not changed for that.

| Case ID | Tier | Input condition | Expected business outcome | Implemented |
| --- | --- | --- | --- | --- |
| LOGOUT-H1 | happy | Valid access token for an account that has a stored refresh token. | That account's refresh tokens are no longer active. The presented refresh token cannot obtain a new pair. | yes |
| LOGOUT-E1 | edge | Valid access token for an account that has no refresh-token rows. | Logout still completes. A later sign-in can still issue a new pair. | yes |
| LOGOUT-F1 | failure | Credentials are missing or are not an access token this API signed. A refresh token for the account is stored. | Logout is rejected. That refresh token remains active and can still obtain a new pair. | yes |
| LOGOUT-E2 | known gap | After LOGOUT-H1, the same access token is sent to `GET /auth/me`. | The profile is still returned. This is a known limitation, not a success case. The later test is named `test_logout_e2_known_gap` and is not counted as proof that logout is complete. | yes |

### POST /auth/refresh

A refresh token must be signed by this API, unexpired, of type `refresh`, carry a non-empty `jti`, match a stored row for a user who still exists, and then that `jti` is revoked as the new pair is issued.

| Case ID | Tier | Input condition | Expected business outcome | Implemented |
| --- | --- | --- | --- | --- |
| REFRESH-H1 | happy | Refresh token just issued by login, still stored. | A new access token and a new refresh token are issued. The presented refresh token can no longer be used. The new access token can read `/auth/me`. | yes |
| REFRESH-E1 | edge | `refresh_token` is an empty string. | The request is rejected before a new pair is issued. | yes |
| REFRESH-F1 | failure | Refresh token whose `exp` is clearly in the past, such as several minutes ago, and whose `jti` is still stored. Do not use the exact second where `exp` equals now. | The request is rejected. Reason: "Session expired". The stored `jti` is not replaced. | yes |
| REFRESH-F2 | failure | Refresh token that was already rotated or revoked. It is otherwise unexpired and well formed. | The request is rejected. Reason: "Invalid token". This is a different decision from REFRESH-F1. | yes |
| REFRESH-F3 | failure | An unexpired access token is sent in `refresh_token`. | The request is rejected. Reason: "Invalid token". | yes |
| REFRESH-F4 | failure | Unexpired refresh token whose user row has been removed. The `jti` is still stored. | The request is rejected. Reason: "Invalid token". No new pair is issued. | yes |
| REFRESH-F5 | failure | Signed, unexpired refresh token whose `jti` claim is missing or empty. | The request is rejected. Reason: "Invalid token". | yes |

## 3. Cases beyond the minimum

AUTH-088 requires one happy, one edge, and one failure case per endpoint. These additional cases are still decisions the current code makes.

| Case ID | Why it is worth a separate case |
| --- | --- |
| USERS-E2 | An empty password is the field boundary: length must be at least 1, so no account is stored. |
| USERS-E3 | Email is lowercased and stripped before the duplicate check, so case and surrounding spaces are not a second account. |
| USERS-E4 | The password is hashed exactly as received, so a single space is a real password and an empty string is not. |
| LOGIN-F2 | Unknown email and wrong password share one rejection, so the decision does not reveal which check failed. |
| LOGIN-E2 | A blank email is rejected with the same generic reason as a wrong password, and no token is issued. That avoids revealing which emails exist. |
| LOGIN-E3 | Login strips and lowercases email, so the stored address still matches. |
| ME-F2 | Missing credentials are "Not authenticated", which is a different decision from an expired or malformed token. |
| ME-F3 | A refresh token is rejected as the wrong type, not accepted as a session. |
| ME-F4 | A value this API did not sign is "Invalid token", distinct from a deleted user. |
| ME-E2 | A signed access token whose user row is gone is "Not authenticated", not "Invalid token". |
| PROFILE-E2 | Any one of the three fields being empty rejects the whole update; the check is not "name only". |
| PROFILE-F2 | An unauthenticated update must not change the stored profile. |
| LOGOUT-E2 | Known gap, not an extra acceptance case. Logout does not invalidate the access token. Record it with `test_logout_e2_known_gap`. Do not change production code and do not present it as correct logout. |
| REFRESH-F2 | A reused `jti` is an inactive refresh token ("Invalid token"), not an expired signature. |
| REFRESH-F3 | Token type is checked; an access token cannot be exchanged for a new pair. |
| REFRESH-F4 | A refresh token for a removed user is rejected even when the `jti` row is still stored. |
| REFRESH-F5 | A missing or empty `jti` is rejected before the stored-row check. |

## 4. Decisions

These replace the earlier open questions.

1. **Expiry.** ME-F1, PROFILE-F1, and REFRESH-F1 use a token that is clearly expired, such as several minutes ago, or a frozen clock. The exact second where `exp` equals now is out of scope.

2. **Bad registration email.** USERS-F1 checks that no account is created and that the error identifies the email field. It does not lock the sentence "Enter a valid email (example: name@email.com)". That text is frontend copy, and the 422 document is framework output.

3. **Logout and the access token.** LOGOUT-E2 is a known limitation, not correct behavior. The later test is named `test_logout_e2_known_gap`. Production code stays as it is. See section 7.

4. **Blank email on login.** LOGIN-E2 stays. The generic "Incorrect email or password" is the decision, and the test must also show that no token is issued.

5. **Two database connections.** `get_users_table` and `get_refresh_table` each open `data/auth.json`. A lost refresh token would be a bug, not normal behavior. `tests/test_refresh_token_persists.py` registered a user, logged in, and found the refresh row still stored. `POST /auth/refresh` with that token returned a new pair. The loss did not reproduce, so REFRESH-H1 stays a normal success case. The two handles remain a structural risk if a later run drops the row; that result would be a bug to report, not a planned failure.

6. **User deleted during profile update.** Left untested. One request cannot reach that branch, and the coverage target is 70%, not 100%.

7. **Two rows with the same email.** Out of scope. Registration already blocks duplicates.

## 5. How to run the tests

The authentication API project root is `services/api` (not the monorepo root). From that directory:

```bash
cd services/api
uv sync
uv run pytest
```

`uv sync` installs the dev group: pytest, pytest-cov, and httpx. `uv run pytest` runs every module under `tests/`. Each test uses its own temporary database, so order does not matter and nothing is written to `data/auth.json`.

Coverage:

```bash
uv run pytest --cov=app --cov-report=term-missing
```

TypeScript utilities (Next.js backoffice):

```bash
cd uis/backoffice
npx jest --coverage
```

## 6. Coverage results

Verified on the final audit from `services/api`:

```bash
uv run pytest --cov=app --cov-report=term-missing
```

**44 passed**, package coverage **93%** (260 statements, 19 missed). Above the 70% target. No files were excluded and no `pragma: no cover` was added.

Earlier in the project: after Prompt 2 the suite was smaller; after `test_me_signed_token_without_subject` coverage moved from 92% to 93%. After API-042 the suite grew to 44 tests and stayed at 93%.

`app/security.py` is 100%. Lines still missed on purpose:

| Location | Lines | Why it stays uncovered |
| --- | --- | --- |
| `app/seed.py` | 3–25 | Demo seed script. It is not an authentication endpoint decision. |
| `app/main.py` | 30 | `GET /health` returns a status flag. It makes no authentication decision. |
| `app/database.py` | 99 | `update_profile` returns `None` only when the user row is already gone. |
| `app/routers/auth.py` | 58 | `GET /auth/me` raises "Not authenticated" only when `find_user` misses after `current_user_email` already required that row. |
| `app/routers/profiles.py` | 34 | `PUT /profiles/me` raises "Not authenticated" only when `update_profile` misses after the same check. |

The three "user already gone" lines are one request path. `current_user_email` rejects a missing user before the handler runs, so a single request does not reach them. The coverage target is 70%, not 100%.

## 7. AI-assisted findings

**Logout does not revoke the access token (LOGOUT-E2).** `POST /auth/logout` deletes refresh-token rows for that user and leaves the access token usable until it expires. With a stateless JWT this is a known limitation, not accepted logout behavior. The existing chained test in `services/api/tests/test_auth.py` asserts that `GET /auth/me` still succeeds after logout. The planned case is named `test_logout_e2_known_gap` so the suite records the gap without calling it correct. Production code was not changed.

**Refresh token was not lost when login opened the database twice.** Login opens the user table and the refresh-token table through separate TinyDB handles, so a refresh token might have been lost. `tests/test_refresh_token_persists.py` logged in, found that one refresh row was still stored, and then used it in a later `POST /auth/refresh`. That sequence kept the token, so this was not a bug. The check is one request after another. It does not show what happens when two requests write at the same time.

**No expected-failure bug was fixed in the coverage step.** The suite had no `xfail` test. `test_logout_e2_known_gap` passes because it records the current limitation: the access token still works after logout. That was an approved known gap, not a failing test, so production code was left unchanged.

## 8. TypeScript auth utilities

Jest is configured for the Next.js backoffice, which is the TypeScript project that contains the auth utilities. The config is `uis/backoffice/jest.config.js` (CommonJS, matching that package). Dev dependencies there are `jest`, `@types/jest`, and `ts-jest`.

From `uis/backoffice`:

```bash
npx jest --coverage
```

There is no TypeScript password-hashing function and no TypeScript token-signing function. Those decisions live in `services/api/app/security.py`. They were not copied into the frontend.

`uis/backoffice/lib/api.ts` also exports HTTP calls (`login`, `registerUser`, `getMe`, `updateProfile`, `logout`, `apiFetch`). Those perform network requests. This step tests `toErrorMessage` only. The fetch calls were not mocked.

Each row is one happy-path test and one failure-mode test.

| Function | File | Happy path | Failure mode |
| --- | --- | --- | --- |
| `readAccessToken` | `lib/token.jest.test.ts` | Returns the stored token without surrounding spaces | Missing or blank token is null |
| `readRefreshToken` | `lib/token.jest.test.ts` | Returns the stored refresh token without surrounding spaces | Missing or blank token is null |
| `hasAccessTokenIn` | `lib/token.jest.test.ts` | True when a token is stored | False when the token is blank |
| `writeSession` | `lib/token.jest.test.ts` | Stores trimmed access and refresh tokens | Blank access is not stored; blank refresh is removed |
| `clearSession` | `lib/token.jest.test.ts` | Removes both tokens | An empty store stays empty |
| `authorizationValue` | `lib/token.jest.test.ts` | Builds `Bearer <token>` | An empty token is not a usable credential |
| `getAccessToken` | `lib/token.jest.test.ts` | Reads the browser access token | No browser returns null |
| `getRefreshToken` | `lib/token.jest.test.ts` | Reads the browser refresh token | No browser returns null |
| `hasAccessToken` | `lib/token.jest.test.ts` | True when the browser holds a token | No browser is false |
| `setTokens` | `lib/token.jest.test.ts` | Saves the session in the browser | No browser does nothing |
| `clearTokens` | `lib/token.jest.test.ts` | Removes the browser session | No browser does nothing |
| `readSessionTokens` | `lib/token.jest.test.ts` | Accepts `access_token` and `refresh_token` | A body with no access token is rejected |
| `sessionClearedOnUnauthorized` | `lib/token.jest.test.ts` | A 401 that was not refreshed clears the session | A refreshed 401, or a non-401, does not |
| `notifySessionExpired` | `lib/token.jest.test.ts` | Notifies away from `/login` | No notice on `/login`, and no browser does not throw |
| `invalidateSession` | `lib/token.jest.test.ts` | Clears tokens and notifies once | No browser does not throw |
| `sessionStillActive` | `lib/token.jest.test.ts` | True while an access token is stored | False when it is missing |
| `resetSessionLifecycleForTests` | `lib/token.jest.test.ts` | A later expiry can notify again | Resetting does not create a session |
| `emailFieldError` | `lib/credentials.jest.test.ts` | A trimmed email is accepted | A non-address is rejected |
| `passwordFieldError` | `lib/credentials.jest.test.ts` | A non-empty password is accepted and not trimmed | An empty password is rejected |
| `authCredentials` | `lib/credentials.jest.test.ts` | Returns the trimmed email and the original password | A bad email or empty password returns null |
| `withoutSecret` | `lib/credentials.jest.test.ts` | A message without the password is kept | A message that repeats the password is hidden |
| `readProfile` | `lib/profile.jest.test.ts` | Reads a flat profile | A non-record becomes an empty profile |
| `nameFieldError` | `lib/profile.jest.test.ts` | A non-blank name is accepted | A blank name is rejected |
| `phoneFieldError` | `lib/profile.jest.test.ts` | A non-blank phone is accepted | A blank phone is rejected |
| `addressFieldError` | `lib/profile.jest.test.ts` | A non-blank address is accepted | A blank address is rejected |
| `profileUpdatePayload` | `lib/profile.jest.test.ts` | Returns the trimmed fields | Any blank field returns null |
| `mergeSavedProfile` | `lib/profile.jest.test.ts` | Keeps the saved fields | Empty saved fields fall back |
| `isProtectedPath` | `lib/isProtectedPath.jest.test.ts` | `/account` and paths under it are protected | `/login`, `/register`, and `/accounts` are not |
| `publicErrorText` | `lib/publicErrorText.jest.test.ts` | A safe API detail is shown | An empty, token-shaped, or non-JSON body is hidden |
| `toErrorMessage` | `lib/toErrorMessage.jest.test.ts` | An ordinary error message is shown | Session expiry is hidden; a network failure is explained |

Verified on the final audit from `uis/backoffice`:

```bash
npx jest --coverage
```

**9 suites, 66 tests, all passed.** Statement coverage for measured `lib` files: **66.29%**. `credentials.ts`, `routes.ts`, and `token.ts` are 100%. The lower total is mostly untested HTTP functions in `api.ts`. The grading criterion for TypeScript is that Jest tests exist and pass; there is no separate Jest percentage target in AUTH-088.

## 9. Optional extras (API-042 and FE-019)

### API-042 — non-`/auth` endpoint groups

This branch’s FastAPI app has no suppliers (or other inventory) router. The only endpoint groups outside `app/routers/auth.py` are:

- `users` — `POST /users` in `app/routers/users.py` (ticket example lists “users”)
- `profiles` — `PUT /profiles/me` in `app/routers/profiles.py` (contact fields for the signed-in staff member)

Both groups use real business rules: duplicate email, email format, required profile fields, and unauthenticated updates.

Modules: `tests/test_api042_users.py`, `tests/test_api042_profiles.py`. Each has one happy-path, one edge-case, and one failure-mode test.

Run only the extra suite and measure those routers:

```bash
cd services/api
uv run pytest tests/test_api042_users.py tests/test_api042_profiles.py \
  --cov=app.routers.users --cov=app.routers.profiles --cov-report=term-missing
```

Measured coverage on those modules: **users 100%**, **profiles 93%**, **combined 96%** (above the 60% target). The one missed line in `profiles.py` is the unreachable “user gone mid-request” branch already documented in section 6.

Full auth suite after adding the extras (must stay green and not drop below 70%):

```bash
uv run pytest --cov=app --cov-report=term-missing
```

Verified on the final audit with the full suite: **44 passed**, package coverage **93%**.

### FE-019 — frontend utilities in `__tests__/`

Jest was already configured for `uis/backoffice`. FE-019 adds `uis/backoffice/__tests__/` with one happy-path and one failure-mode test for each of three utilities:

| Function | Why | File |
| --- | --- | --- |
| `isProtectedPath` | Decides which routes need a session | `__tests__/isProtectedPath.test.ts` |
| `withoutSecret` | Hides passwords from error text | `__tests__/withoutSecret.test.ts` |
| `profileUpdatePayload` | Accepts or rejects a profile edit | `__tests__/profileUpdatePayload.test.ts` |

Run only the FE-019 suite:

```bash
cd uis/backoffice
npx jest --coverage --testPathPatterns=__tests__
```

Result: **3 suites, 6 tests, all passed**.

Run the full frontend Jest suite (Prompt 4 + FE-019):

```bash
cd uis/backoffice
npx jest --coverage
```

Verified on the final audit: **9 suites, 66 tests, all passed**. Statement coverage for measured `lib` files: **66.29%**.

No application bugs were found in the extras step. Authentication tests were not removed or weakened.

## 10. Final audit checklist

Verified against AUTH-088 evaluation criteria. Commands were re-run for this audit. Only this file was edited in the audit step.

| # | Criterion | Result | Evidence |
| --- | --- | --- | --- |
| 1 | `TESTING.md` documents the plan, how to run tests, and coverage | Pass | This file: sections 1–6 (plan, run, coverage), 7 (AI findings), 8–9 (Jest and extras) |
| 2 | `uv run pytest` from the auth project root passes | Pass | From `services/api`: `uv run pytest --cov=app --cov-report=term-missing` → **44 passed**, 4 warnings (Starlette/FastAPI deprecations, not failures) |
| 3 | Every auth endpoint has happy, edge, and failure tests | Pass | Modules `tests/test_register.py`, `test_login.py`, `test_me.py`, `test_profile.py`, `test_logout.py`, `test_refresh.py`; case IDs in section 2 all marked Implemented |
| 4 | Auth module coverage ≥ 70% | Pass | Same command: **TOTAL 93%** (260 stmts, 19 miss). Report includes `app/seed.py` |
| 5 | Tests assert business decisions, not serialization/framework | Pass | Section 1 scope; assertions check outcomes such as account created/rejected, token usable/rejected, `detail` reasons, and stored profile fields — not content-types or JSON key order |
| 6 | If TypeScript auth utilities exist, Jest tests pass | Pass | Utilities in `uis/backoffice/lib/`; `npx jest --coverage` → **66 passed**, 9 suites |
| 7 | AI-assisted finding or bug caught by tests is recorded | Pass | Section 7: logout known gap (LOGOUT-E2); refresh-token double-open check that was not a bug, with sequential-request scope limit |
| 8 | Clear names, consistent structure, brief comments | Pass | Case IDs in test names (`test_users_e1_…`, `test_logout_e2_known_gap`); shared fixtures in `tests/conftest.py` and `tests/support.py` |

Extras (optional backlog):

| Ticket | Result | Evidence |
| --- | --- | --- |
| API-042 | Pass (on this branch’s available groups) | `users` + `profiles` (no suppliers router here); modules `test_api042_*.py`; combined coverage **96%** on those routers |
| FE-019 | Pass | `uis/backoffice/__tests__/` for `isProtectedPath`, `withoutSecret`, `profileUpdatePayload` |

### Remaining gaps (not grading failures)

- Logout does not revoke the access JWT (`test_logout_e2_known_gap`). Documented limitation; product code unchanged.
- Unreachable “user disappeared mid-request” lines in `database.py` / `auth.py` / `profiles.py` stay uncovered on purpose.
- No suppliers (or similar inventory) API on `feature/auth-frontend`; API-042 used `users` and `profiles` instead.
- Jest package statement coverage is 66.29% because `api.ts` HTTP helpers are largely untested; AUTH-088 does not require a Jest coverage percentage.
- `uv run pytest` must be run from `services/api`, not the monorepo root.
