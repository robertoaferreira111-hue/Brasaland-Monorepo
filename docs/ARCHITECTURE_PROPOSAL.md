# Backend Architecture Proposal — Brasaland

This document proposes the backend architecture for Brasaland Digital. It is a design document. It does not add a FastAPI application, endpoints, schemas, or configuration files.

The proposal follows the repository as it exists today: the public site in `uis/website`, the in-memory operations code in `src/`, and the monorepo rule in `README.md` that backends live in `services/` as one FastAPI application. Router layout follows the official FastAPI guide for larger applications: one package, `main.py` as the entrypoint, and one `APIRouter` per domain.

## 1. Architecture recommendation

**Pattern: one modular monolith.** A single FastAPI process, with modules split by business domain. Each domain has its own router, schemas, and service functions. The process is one deployable. The modules are not separate services.

### Why this fits Brasaland

Brasaland is a grilled-food chain founded in 2008 in Medellín. `CONTEXT.md` describes 14 company-owned restaurants, about 115 employees, a headquarters in Medellín, and a commercial office in Miami. Brasaland Digital reports to CTO Nicolás Park. The public stakeholder is Marketing Manager Camila Ospina. The only HTTP client in the repository is the static website in `uis/website`.

That site is one product with several sections, not several products. `uis/website/README.md` states that Locations, Menu, and Contact are sections of the landing page, and that Brasa Points opens `application.html`. The registration form cannot be built without the restaurant list: `validation.js` selects a city from the country, then a favorite restaurant from the country and city. Those 14 names live in that file. The locations section on `index.html` does not print them. It states 10 restaurants in Medellín, Bogotá, and Cali, and 4 in Miami and Orlando, with the hours from `CONTEXT.md`. Both views describe the same chain. One process lets the locations module and the loyalty module read one catalog.

The operations code in `src/` is a second set of rules (menu items, sales, waste, margins). It is a TypeScript library over arrays, invoked by `src/demo.ts`. It is not a running service and it has no HTTP entrypoint. It does not yet need its own deployable. `README.md` already tells the team to keep one FastAPI app and to add routers as domains appear, extracting a worker only when a job must run separately.

The workload in front of the team is concrete and small: publish the restaurant list, publish menu facts when the site has them, and accept a Brasa Points registration that `validation.js` currently only simulates. `package.json` at the root runs `typecheck` and `demo`. Nothing in the repo serves HTTP except the static site documented on port 3000. Independent scaling per domain is not a property of this system.

### Why other patterns were not selected

**MVC.** MVC puts views on the server next to controllers. The views already exist as `index.html` and `application.html`. `tsconfig.json` excludes `uis` from the TypeScript program. Moving those pages into the API would undo a separation the repository already has.

**One horizontal layering with no domain modules.** A single router file could list every path. The audiences are different. Guests use the website. Operations calculations in `src/utils/transformations.ts` use rent, utilities, staff counts, waiter names, and waste cost. A guest registration and a waste report are not the same responsibility. Domain modules keep those apart inside the one app.

**Serverless functions.** The repository has no function configuration. `.devcontainer/devcontainer.json` forwards long-lived ports `3000` and `8000`. The country → city → restaurant rule is one workflow. Splitting it across functions would add network boundaries the form does not have today.

**Microservices.** `README.md` says to avoid many services early and to add endpoints to the same FastAPI app. A locations service and a loyalty service would each need the same 14 restaurants, which `validation.js` currently keeps in one file (`CITIES` and `LOCATIONS`). `services/README.md` allows a subfolder per service and cites examples such as a worker. That option stays available later. This proposal uses one subfolder, `services/api/`, because nothing in the repo yet needs a second process. The confirmation email promised by the success copy in `CONTEXT.md` is not a mailer in this repository, so it is not a reason to add a worker now.

**Online ordering is not a domain of this API.** `CONTEXT.md` says the form is not a reservation or an order. `index.html` and `application.html` both tell the guest to call or visit, and that online ordering is coming later.

## 2. Backend responsibilities and domains

Four responsibilities are visible in the repository. Three are public and match the website. The fourth is internal and already implemented as TypeScript. It stays out of the public routers.

### Locations (public)

**Responsibility.** Serve the restaurant directory the landing page and the loyalty form both need.

**Data.** The public catalog in `validation.js`: country `Colombia` or `United States`; cities Medellín, Bogotá, Cali, Miami, and Orlando; the 14 restaurant names grouped under those cities. Hours published in `CONTEXT.md` are Mon–Sun 11:00 AM–10:00 PM. This is not the operations `Location` in `src/types/models.ts`, which uses country `"USA"` and adds rent, utilities, staff count, manager, and status. `src/types/sampleData.ts` also uses different names (for example `Brasaland Medellín Centro` and `Brasaland Miami Beach`) and only five rows.

**Resources.**

| Method | Path | Role |
| --- | --- | --- |
| `GET` | `/locations` | List public restaurants. Query params `country` and `city` support the form’s dependent lists. |
| `GET` | `/locations/{location_id}` | One public restaurant. |

**Why it is separate.** The website can show locations without creating a member. Loyalty needs to filter this catalog. Mixing member writes into this router would couple a directory to personal data.

### Menu (public)

**Responsibility.** Serve menu items when the site has a menu to show. `uis/website/README.md` states that the current pages do not list dishes or prices, because the briefing does not provide them.

**Data.** The public read model should follow `MenuItem` in `src/types/models.ts` for fields a guest can see: `name`, `category` (`Meat`, `Side`, `Beverage`, `Dessert`, `Combo`), `basePrice` as `{ USD, COP }`, `allergens`, `status`, and availability in Colombia and the United States (`isAvailableInColombia`, `isAvailableInUSA`). `ingredientCost` is an operations cost. It is not a guest-facing field.

**Resources.**

| Method | Path | Role |
| --- | --- | --- |
| `GET` | `/menu` | List items. A `country` query limits items to those available in that country. |
| `GET` | `/menu/{item_id}` | One item. |

**Why it is separate.** Menu availability is a product fact. It is not a loyalty field and it is not a sale. `src/utils/validations.ts` already validates menu items on their own (`validateMenuItem`).

### Loyalty members

**Responsibility.** Accept a Brasa Points registration. The program replaces paper stamp cards. `CONTEXT.md` sets the earn rule at 1 point per $10,000 COP or $5 USD, and requires the guest to be 18 or older.

**Data.** The form fields in `CONTEXT.md` and `application.html`. There is no member type in `src/types/models.ts`. The record the API would store is: full name, email, phone, country, city, optional favorite location, dietary preferences, how the guest found Brasaland, date of birth, terms accepted, and whether they want email offers. A server-assigned id and a registration timestamp can be added on the stored record. They are not form fields.

**Resources.**

| Method | Path | Role |
| --- | --- | --- |
| `POST` | `/loyalty/members` | Create a member when the body passes the same rules as `validation.js`. |

**Why it is separate.** This is the only write, and it holds personal data (name, email, phone, date of birth). Locations and menu are public reads. Putting the write on those routers would let a directory module own guest identity.

The success panel in `application.html` tells the guest a confirmation email is coming. No mail sender exists in the repository. This domain accepts and validates the registration. It does not include an email worker.

### Operations (internal, not on the public API)

**Responsibility.** The calculations already implemented for staff use: filter and search locations, menu items, and sales (`src/utils/collections.ts`, `src/utils/search.ts`); revenue, margin, waste cost, average ticket, and the Colombia-versus-USA comparison (`src/utils/transformations.ts`).

**Data.** `SaleTransaction`, `WasteRecord`, and the full `Location` record, including `monthlyRentCost`, `averageMonthlyUtilities`, `staffCount`, and `manager`. Currency conversion in `transformations.ts` uses a fixed `USD_TO_COP = 4000`. That rate is code in the demo utilities. It is not the Brasa Points earn rule.

**Resources.** No public paths. This domain lives in `app/internal/operations.py`, which is the place the official FastAPI multi-file guide uses for code outside the public routers. `main.py` does not include it. A staff-facing router would be a later file under `app/routers/` plus an `include_router` call. It is kept here so rent, waste, and sales are not added to `/locations` or `/loyalty/members`.

**Why it is separate.** A guest registration and a waste report fail in different ways and expose different data. `validation.js` never reads rent or waste. `validateLocation` in `src/utils/validations.ts` never reads the loyalty form.

### Application health

`GET /health` reports that the process is up. It is not a business domain. It lives on the application entrypoint so the domain routers stay limited to locations, menu, and loyalty. `.devcontainer/devcontainer.json` forwards port `8000`, and no process listens there today. The health route is how local development would see that the API is the process on that port.

## 3. Proposed backend folder structure

The tree is the layout to create when the API is implemented. This milestone does not create these directories. The path is under `services/` because `README.md` places the company API there, not at the repository root. `services/` today contains only its README files.

```text
services/api/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI instance, include_router, CORS
│   ├── dependencies.py             # dependencies shared by more than one router
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py               # settings read from the environment
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── locations.py            # public restaurant directory
│   │   ├── menu.py                 # public menu
│   │   └── loyalty.py              # Brasa Points registration
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── locations.py            # public location request and response shapes
│   │   ├── menu.py                 # public menu shapes, USD and COP kept distinct
│   │   └── loyalty.py              # registration body and result
│   ├── services/
│   │   ├── __init__.py
│   │   ├── locations.py            # the 14-restaurant catalog and its filters
│   │   ├── menu.py                 # availability by country
│   │   └── loyalty.py              # form rules that must hold on the server
│   ├── models/
│   │   ├── __init__.py
│   │   └── loyalty.py              # stored member shape, separate from the HTTP body
│   └── internal/
│       ├── __init__.py
│       └── operations.py           # sales, waste, full Location; not mounted on the app
├── tests/
│   ├── test_locations.py
│   ├── test_menu.py
│   └── test_loyalty.py
├── requirements.txt                # declared when the app is implemented; absent today
└── README.md                       # how to run the app and which variables it reads
```

`app/__init__.py` and the other `__init__.py` files make these directories Python packages, which is what the FastAPI multi-file guide requires so `main.py` can import `app.routers`.

| Path | Responsibility |
| --- | --- |
| `app/main.py` | Builds the FastAPI app, attaches CORS from settings, includes the three domain routers, and defines `GET /health`. |
| `app/dependencies.py` | Dependencies used by more than one router. Domain-specific checks stay next to that domain. |
| `app/core/config.py` | Reads the API’s environment variables in one place. Routers do not hardcode origins. |
| `app/routers/` | HTTP only: status codes, query and path params, and a call into the matching service. One file per domain. |
| `app/schemas/` | Pydantic shapes for JSON in and JSON out. Public location schema omits rent, staff, and manager. |
| `app/services/` | Business rules. Loyalty rules match `validation.js` and `CONTEXT.md`. Location filtering matches `CITIES` and `LOCATIONS`. |
| `app/models/` | The stored member, including fields the client does not send. No other model is proposed, because no store exists yet for menu or locations beyond the catalog the service module would hold. |
| `app/internal/` | The operations domain from `src/`. Same role as `app/internal/` in the official FastAPI multi-file example: code that is not a public router. `main.py` does not import it into the public route map. |
| `tests/` | One module per domain, same split as the routers. The repository has no Python test runner today. This folder is the convention for when tests are added. |
| `services/api/README.md` | Run instructions for this app, parallel to `uis/website/README.md`. |

`src/` stays the TypeScript operations library. The Python API does not replace it. `packages/shared/types/index.ts` is still the template placeholder (`Id`, `BaseEntity`) and is not the Brasaland model. Public field names should follow `CONTEXT.md` and `validation.js` for the website, and `src/types/models.ts` for menu fields a guest can see.

`app/services/` means business-logic modules inside the API package. It is not a second company service under the monorepo `services/` folder. Sales and waste stay in `app/internal/operations.py`. Exposing them later means a new router, schema, and service with the same shape, not new fields on `routers/locations.py`.

## 4. FastAPI router and endpoint organization

Routes are grouped by domain. Each file under `app/routers/` creates an `APIRouter` with a prefix and an OpenAPI tag, which is the standard FastAPI way to keep path operations in separate modules and still serve one application.

| Router module | Prefix | Tag | Handlers |
| --- | --- | --- | --- |
| `app/routers/locations.py` | `/locations` | `locations` | List and fetch public restaurants. |
| `app/routers/menu.py` | `/menu` | `menu` | List and fetch public menu items. |
| `app/routers/loyalty.py` | `/loyalty` | `loyalty` | Create a member. |

`app/main.py` imports those routers and registers them with `include_router`. After registration the paths are `/locations`, `/locations/{location_id}`, `/menu`, `/menu/{item_id}`, and `/loyalty/members`. `GET /health` is declared on `main.py` because it describes the process, not a domain.

Handlers stay thin. A locations handler reads `country` and `city`, calls `services/locations.py`, and returns the public schema. It does not decide which of the 14 restaurants belong to Medellín. A loyalty handler accepts the body schema and calls `services/loyalty.py`. The service rejects a city that is not in that country, a restaurant that is not in that city, a phone whose country code does not match (`+57` for Colombia, `+1` for the United States), a name of fewer than two words, an invalid email, a missing source, an age under 18, or terms that were not accepted. Those are the checks in `validation.js` and the messages in its `ERRORS` object.

Shared dependencies belong in `app/dependencies.py` and are attached either on the `APIRouter` or when the router is included. The public website routes do not share a dependency today: there is no auth in the repository, and this proposal does not add one. The dependency module exists so a later internal router can require a check once, on the router, instead of inside every handler. Domain rules are not dependencies. They are service functions.

Representative behavior, not implementation:

- `GET /locations?country=Colombia&city=Medellín` returns El Poblado, Laureles, Envigado, and Sabaneta. It does not return rent or a manager.
- `GET /locations?country=United%20States&city=Miami` returns Brickell and Coral Gables. The country value is `United States`, the label in `validation.js` and `CONTEXT.md`, not `USA` from `src/types/models.ts`.
- `GET /menu?country=Colombia` returns items with `isAvailableInColombia` set, using the `Price` pair `USD` and `COP`.
- `POST /loyalty/members` with a valid body returns the outcome the page already shows: the registration was accepted. The body includes the form fields. The response does not claim an email was sent, because no mailer exists.
- An invalid body uses the existing sentences, for example “You must be 18 or older to register for Brasa Points” and “You must accept the Brasa Points program terms to continue.”

## 5. FastAPI project conventions

These conventions come from the FastAPI documentation for multi-file applications and for CORS, applied to the domains above.

The official multi-file example is `app/main.py`, `app/dependencies.py`, `app/routers/`, and `app/internal/`, with `__init__.py` so each directory is a package. This proposal keeps that shape and does not mount `app/internal/`. It adds four modules the example does not need, each with a limited scope: `schemas/` is the JSON contract only, `services/` is business rules only, `models/` is the stored member only, and `core/config.py` is environment variables only. Public routes stay in `routers/`.

**Routers.** One `APIRouter` per domain, with `prefix` and `tags`, included from `main.py`. The official guide describes `APIRouter` as a small FastAPI for one group of paths, and shows `prefix`, `tags`, and router-level `dependencies` so those are not copied onto every operation. A single router file for the whole company would hide the boundary between a public directory and a member write.

**Pydantic schemas.** Request and response models live in `app/schemas/`, one module per domain. FastAPI uses these models as the HTTP contract. The loyalty request schema is the form. The locations response schema is the public restaurant, not the operations `Location` type.

**Models.** `app/models/loyalty.py` is the stored member. It may include an id and a timestamp that the request schema does not. Menu and location catalogs are not given persistence models in this proposal. The website’s catalog is a fixed list in `validation.js`, and the operations samples are in-memory arrays in `src/types/sampleData.ts`. Inventing a database for them is not justified by the repository. There is no `pyproject.toml`, `requirements.txt`, or database configuration.

**Services.** Rules live in `app/services/`. Handlers call them. That keeps `validate`-style logic, already isolated in `src/utils/validations.ts` on the TypeScript side, equally isolated on the Python side. The loyalty service is the server copy of `validation.js`. The locations service is the server copy of `CITIES` and `LOCATIONS`.

**Configuration.** `app/core/config.py` is the only module that reads process environment variables for the API. The values are named in section 6. They are not read inside routers.

**Dependencies.** `app/dependencies.py` is for checks shared across routers. The official guide puts those in `dependencies.py` and attaches them to an `APIRouter`. Business validation stays in services so it can be tested without an HTTP call.

**Testing.** `tests/` mirrors the domains. The repo’s current check is `npm run typecheck` for `src/` only. Python tests do not exist, and this document does not add them. When they are added, loyalty tests should cover the dependent city and restaurant rules, and location tests should assert that rent and manager are absent from the public schema.

**Error handling.** Unknown ids and invalid registration bodies raise `HTTPException`, which is the mechanism the FastAPI guide uses for a missing resource. Loyalty error details reuse the strings in `validation.js` so the page and the API do not disagree. A missing restaurant is a 404 on the locations router. A registration that fails the form rules is a client error on the loyalty router, not a 404.

**API versioning.** Paths are unversioned (`/locations`, not `/v1/locations`). One unpublished API and one static site do not have a second contract to preserve. A version prefix can be added on `include_router` later without moving domain modules. Adding it now would be a prefix with no second client.

**Separation of concerns.** HTTP in routers, JSON contracts in schemas, rules in services, stored shape in models, process settings in `core/config.py`. A change to the Medellín restaurant list is a change in `services/locations.py`. A change to the registration JSON is a change in `schemas/loyalty.py`. Those are different edits.

## 6. Frontend and backend architecture

### Where each side lives

| Concern | Place in this repo | Owns |
| --- | --- | --- |
| Public pages | `uis/website/` (`index.html`, `application.html`, `styles.css`) | Layout, copy, the ordering notice, and the success panel. |
| Browser checks | `uis/website/validation.js` | Immediate field errors and the dependent dropdowns. |
| Website toolchain | `uis/website/package.json` | Tailwind build only (`tailwindcss` 3.4.17). |
| Operations library | `src/` | In-memory menu, sales, waste, and location rules. Not imported by the website. `tsconfig.json` excludes `uis`. |
| Future API | `services/api/` as specified above | Public HTTP contract and the rules that must hold when the browser is skipped. |
| Shared types package | `packages/shared/` | Placeholder only. Not the contract between the site and the API. |

`README.md` is the monorepo map: user interfaces under `uis/`, the company API under `services/`, cross-cutting documents under `docs/`. This file is the cross-cutting document. The website README remains the run guide for the site.

### Responsibility boundary

The browser may keep checking the form before the request. That is the behavior of the `submit` listener in `validation.js`: it calls `preventDefault`, runs `validateAll`, and on success hides the form and shows `#success`. It does not send the data anywhere.

The API owns whether a registration is accepted. The same rules run there because a client can skip `validation.js`. The page still explains errors next to fields. The API returns the same sentences. Keeping the row is a later choice: section 7 does not select a database, because the repository has none.

The API does not render HTML and does not own the “online ordering coming soon” banner. The website does not own the stored member and does not import `src/utils`.

### API communication

The site will send and receive JSON.

- Registration: `POST /loyalty/members` with `Content-Type: application/json`, replacing the simulated success path.
- Restaurant lists: `GET /locations` with `country` and `city`, so `CITIES` and `LOCATIONS` in `validation.js` can be loaded from the API instead of remaining a second copy. Until that switch, the service module and `validation.js` must list the same 14 names.
- Menu: `GET /menu` when the landing page has dishes to show. The current pages do not.

The website does not call the operations functions over HTTP. Those stay in `src/` until an internal router is justified.

### Environment variables

No application environment file exists. `.gitignore` does not mention `.env`. The names below are the configuration this design needs. They are not implemented here.

| Variable | Read by | Purpose |
| --- | --- | --- |
| `API_BASE_URL` | `uis/website` | Origin of the API. The HTML does not embed a host. |
| `CORS_ORIGINS` | `services/api` via `app/core/config.py` | Comma-separated browser origins allowed to call the API. |

A database URL is not listed. The repository has no database.

### CORS

Once the site and the API are different origins, the browser enforces CORS. The FastAPI CORS documentation defines an origin as scheme, host, and port. `http://127.0.0.1:3000` and an API on another port are different origins. The official `CORSMiddleware` is attached in `main.py`. `allow_origins` is the list from `CORS_ORIGINS`. A wildcard origin is not used. The same documentation states that `allow_origins=["*"]` cannot be combined with credentialed requests, and that explicit origins are the configuration that allows a browser page to call the API. The registration body contains personal data, so the allow-list is the specific website origins, not every origin.

### Development environment

`uis/website/README.md` serves the site with `npx http-server . -p 3000`. `.devcontainer/devcontainer.json` forwards `3000` and `8000`. Port `8000` has no server today. The local API port to document in `services/api/README.md` is `8000`, because that forward already exists. Local `CORS_ORIGINS` includes the website origin on port 3000. Local `API_BASE_URL` points at the API on port 8000. The devcontainer also installs Python 3.12 and runs `uv sync` only if `pyproject.toml` exists. It does not. Dependencies are declared when the app is created, not in this document.

### Production environment

No deploy manifest, Dockerfile, or `docker-compose.yml` is in the repository. This proposal does not add one. The HTML canonical URLs use `https://brasaland.com`. That is the production website origin to place in `CORS_ORIGINS` when a host is actually deployed. The production API host is not in the repo. It is the production value of `API_BASE_URL` and must be set outside the source, the same way the local value is.

### What this avoids

The site and the API stay in different folders with different toolchains (`uis/website/package.json` versus a future Python dependency file under `services/api/`). The JSON contract is the schemas, not a shared import. `packages/shared` is not on that path today.

## 7. Technical decisions and rationale

### One FastAPI application under `services/api/`

- **Decision.** One process, one package, domain modules inside it. No second service and no project at the repository root.
- **Reason.** `README.md` specifies one company API. The only client is `uis/website`. Loyalty and the public restaurant list share one catalog in `validation.js`.
- **Tradeoff.** A single process is restarted and deployed as a unit. A failure in one domain takes the process with it.
- **Consequence.** New public capabilities are new routers in this app. A worker is a later `services/` subfolder, and only for a job that must leave the request cycle. The confirmation email is a candidate later. It is not designed here.

### Domain routers instead of one router module

- **Decision.** `locations`, `menu`, and `loyalty` are separate `APIRouter` modules with prefixes and tags.
- **Reason.** The website already treats those as different sections, and the write of personal data is only on loyalty.
- **Tradeoff.** More files than a single `main.py` of routes.
- **Consequence.** `include_router` in `main.py` is the full public route map. OpenAPI groups match the business.

### Public location schema is not the operations `Location`

- **Decision.** `/locations` returns the marketing catalog: name, city, country `Colombia` or `United States`, and published hours. It does not return the `Location` fields used by `scoreLocationPerformance` and `calculateLocationMargin`.
- **Reason.** `sampleData.ts` and `models.ts` describe internal operations, including cost and manager, and they use `"USA"` plus different restaurant names. The site uses the 14 names in `validation.js`.
- **Tradeoff.** Two location shapes exist until someone deliberately maps them. The API does not pretend they are already the same list.
- **Consequence.** Country on the public API is `United States`. Code that reads `src/types/models.ts` continues to use `"USA"` until a mapping is written. That mapping is not implied by this proposal.

### Schemas, services, and the loyalty model are different modules

- **Decision.** HTTP shapes in `schemas/`, rules in `services/`, stored member in `models/loyalty.py` only.
- **Reason.** The form body and a stored member are not the same record. The stored member needs an id and a timestamp. The operations `Price` and `Location` types must not leak into the registration JSON.
- **Tradeoff.** A field that exists in both the body and the stored record is named in two places.
- **Consequence.** A contract change and a storage change are separate edits. Menu `ingredientCost` cannot appear on `GET /menu` unless the menu schema names it.

### Server-side copy of the form rules

- **Decision.** `services/loyalty.py` enforces the `validation.js` rules and returns that file’s error sentences.
- **Reason.** Submit currently never leaves the browser. After `POST` exists, the browser check is only a convenience.
- **Tradeoff.** The rules live in JavaScript and in Python until the dropdowns are loaded from `GET /locations`.
- **Consequence.** Tests for the service, when written, should use the same messages. A drift between the two files is a defect in the catalog, not a styling issue.

### Points and menu money stay in two currencies

- **Decision.** Money in the public menu schema is the `Price` pair `{ USD, COP }` from `src/types/models.ts`. The loyalty earn rule stays the `CONTEXT.md` rule (1 point per $10,000 COP or $5 USD). The API does not adopt `USD_TO_COP = 4000` from `transformations.ts` as a member-point rate.
- **Reason.** Colombia and Florida are both in the business. The demo conversion rate and the loyalty threshold are different facts.
- **Tradeoff.** Callers must handle two numbers, or a points rule stated per currency, instead of one integer.
- **Consequence.** A single unlabeled amount is not a valid menu price or a valid points explanation on this API.

### Configuration by environment, explicit CORS origins

- **Decision.** `API_BASE_URL` for the website and `CORS_ORIGINS` for the API. `CORSMiddleware` allow-list. No wildcard origin.
- **Reason.** The documented site port is 3000 and the forwarded API port is 8000, so local development is cross-origin. The registration body is personal data.
- **Tradeoff.** Each environment must set both values. A missing origin looks like a failed form after `validation.js` has already passed.
- **Consequence.** Origins are not written into `index.html`. `GET /health` from the site is the local check that the browser can reach the API.

### No API version prefix and no auth

- **Decision.** Unversioned paths. No authentication module.
- **Reason.** There is one client, the static site, and no auth code or user table in the repo. The assignment scope for this milestone is the proposal, not an auth system.
- **Tradeoff.** A later breaking change has no version to leave behind. Public `POST /loyalty/members` would be callable by any client that passes CORS.
- **Consequence.** Versioning, if needed, is a prefix on `include_router`. Auth, if needed for internal operations, is a dependency on that future router, not a field on the public location schema.

### No database engine in this proposal

- **Decision.** Do not choose a database, ORM, or `DATABASE_URL`.
- **Reason.** None of those exist in the repo. The location list is a constant in `validation.js`. Sales and waste are arrays in `sampleData.ts`.
- **Tradeoff.** The loyalty model describes a stored member without a place to put rows. Implementation will have to choose a store before `POST /loyalty/members` can keep data.
- **Consequence.** That choice is a later change with its own configuration key. It must not be smuggled into this document as if it were already true.

## 8. Risks and points of attention

### Public and operations location models get merged

**What could go wrong.** A locations handler returns the `Location` type from `src/types/models.ts`, or the five sample rows, instead of the 14 public restaurants.

**Why it matters.** Guests would see the wrong names, country `USA` instead of `United States`, and internal values: monthly rent, utilities, staff count, and manager name. The loyalty dropdown would no longer match the site.

**Practice that reduces it.** `schemas/locations.py` is the only response model for that router, and it has no cost or manager fields. `services/locations.py` is the only catalog, aligned with `validation.js`. `tests/test_locations.py`, when added, should fail if a cost field appears. The operations `Location` stays behind the internal boundary in section 2.

### Loyalty rules stay only in the browser

**What could go wrong.** `POST /loyalty/members` writes the body without the service checks, because `validation.js` already validates.

**Why it matters.** The form collects date of birth and requires age 18 or older. It also requires terms, a real country-and-city pair, and a phone prefix that matches the country. Anyone who can call the API can skip the script. The stored data would then contradict the program rules in `CONTEXT.md`.

**Practice that reduces it.** The handler calls `services/loyalty.py` and does not write the body itself. Error details are the `ERRORS` strings. The service is the place those rules live, separate from the router, so they can be reviewed without reading HTML.

### CORS or the API base URL is hardcoded or omitted

**What could go wrong.** The API allows every origin, or it allows none of the website’s origins. Or `application.html` contains a fixed host.

**Why it matters.** The site on port 3000 and an API on port 8000 are different origins, per the FastAPI CORS rules. A wildcard allow-list publishes a personal-data endpoint to every web origin. An empty allow-list makes a valid form look broken after `validateAll` succeeds. A host written into the HTML has to be edited for every environment, and no production API host exists in this repo to hardcode anyway.

**Practice that reduces it.** `CORS_ORIGINS` and `API_BASE_URL` are read from the environment in `config.py` and the website respectively. `main.py` passes that list to `CORSMiddleware`. The values are documented in `services/api/README.md` and `uis/website/README.md` when those files are updated for the API. They are not documented as if they already exist in the site.

### Menu price or points collapse into one number

**What could go wrong.** A menu schema uses a single `price`, or loyalty points reuse `USD_TO_COP = 4000` from `transformations.ts`.

**Why it matters.** The chain sells in Colombia and Florida. `Price` has both `USD` and `COP`. The loyalty threshold in `CONTEXT.md` is $10,000 COP or $5 USD per point. The 4000 rate is a demo constant for operations reports. Using it to explain member points would state a rule the company briefing does not state.

**Practice that reduces it.** `schemas/menu.py` uses the two-currency pair. The loyalty domain documents the earn rule from `CONTEXT.md` and does not import the operations conversion rate. `ingredientCost` stays off the public menu schema.

## 9. Architecture summary

Brasaland’s first API is one FastAPI application at `services/api/`, because the company has one digital team, one public website, and one chain whose city counts are on `index.html` and whose 14 restaurant names are in `validation.js`. Domain routers keep guest reads, menu reads, and member registration apart, and they keep rent, waste, and sales out of those public paths.

The structure is maintainable because each change has a module: catalog rules in services, JSON in schemas, HTTP in routers, settings in `core/config.py`. Future work adds a router in the same app, or a new `services/` subfolder only when a job such as confirmation email must leave the request. The website in `uis/website` remains the client. It will call the API with `API_BASE_URL`, and the API will allow that origin through `CORS_ORIGINS`. No database, auth system, or deploy stack is introduced, because the repository does not contain them.
