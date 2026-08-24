# GTM Waterfall Enrichment

A self-hosted, open-source alternative to [Clay](https://clay.com) — a lead
enrichment waterfall + ICP scoring + CRM sync engine, built on FastAPI.

This is a portfolio/learning project demonstrating GTM (go-to-market)
engineering: waterfall enrichment across multiple free-tier data providers,
cost-per-field tracking, config-driven ICP scoring, and CRM sync — all without
a single hardcoded provider order or scoring weight.

**Status: actively being built.** See [CLAUDE.md](CLAUDE.md) for the exact
build order and what's done vs. pending. The short version: contacts, bulk CSV
import, waterfall enrichment, and ICP scoring are live behind API endpoints;
HubSpot sync is built but not yet wired to a route (see
[Known gaps](#known-gaps) below).

## What this is NOT

There is **no authentication**. Every endpoint, including `/docs` and
`/openapi.json`, is open in every environment. This is intentional — it's
meant to run self-hosted behind your own network boundary (a VPN, a private
subnet, an authenticating reverse proxy), not exposed to the public internet.
See [Deployment notes](#deployment-notes) before running this anywhere other
than your own machine.

## Architecture

```
  Trigger                Waterfall Enrichment              Scoring                CRM Sync
┌───────────┐      ┌──────────────────────────┐      ┌───────────────┐      ┌──────────────┐
│ CSV bulk  │      │ Per field (email/phone/   │      │ ICP scoring   │      │ Push         │
│ import,   │ ───▶ │ company), try providers   │ ───▶ │ against a     │ ───▶ │ qualified    │
│ or POST   │      │ in priority order         │      │ config-driven │      │ contacts to  │
│ .../enrich│      │ (WaterfallConfig) until   │      │ profile       │      │ HubSpot      │
└───────────┘      │ one hits.                 │      │ (ICPConfig).  │      │ (built, not  │
                    │                          │      │ Normalized    │      │ yet routed — │
                    │ Every attempt — hit or   │      │ to 0-100 over │      │ see Known    │
                    │ miss — logs an           │      │ only the      │      │ gaps below)  │
                    │ EnrichmentJob with cost  │      │ criteria      │      └──────────────┘
                    │ (credits_used) and       │      │ configured.   │
                    │ provider_name.           │      └───────────────┘
                    └──────────────────────────┘
```

**Why waterfall order matters:** free-tier enrichment providers have wildly
different coverage and cost. Trying the cheapest/free option first and only
falling through to a paid fallback on a miss is what keeps a bulk enrichment
run affordable — the same reason real GTM/RevOps teams chain providers instead
of picking just one.

**Why config-driven, not hardcoded:** both the provider order
(`WaterfallConfig`) and the ICP scoring weights (`ICPConfig`) live in the
database, not in Python constants. Tightening the ICP definition or
reprioritizing a provider is a data change, not a deploy.

## Data model

| Table | Purpose |
|---|---|
| `companies` | Target company: domain (de-dup key), name, industry, employee_count, revenue_range |
| `contacts` | A raw or enriched contact: name, email, title, company FK, enrichment_status, icp_score |
| `enrichment_jobs` | Audit trail: every waterfall attempt (hit or miss), which provider, cost, result |
| `waterfall_config` | Which providers to try per field, in what order, enabled/disabled |
| `icp_configs` | ICP scoring weights per criterion — industry, employee count range, revenue range, title keywords |

## Tech stack

FastAPI (async) · Pydantic v2 · SQLAlchemy 2.0 (async) · PostgreSQL · Redis ·
Alembic · httpx · Taskiq (background job infra, not yet wired to a job)

## API endpoints (current)

| Method | Path | What it does |
|---|---|---|
| `POST` | `/api/v1/contacts/bulk` | CSV upload. Row-tolerant — a bad row is reported with its row number, not a reason to reject the whole file. Rows sharing a `company_domain` resolve to one `Company`. |
| `GET` | `/api/v1/contacts/{id}` | Fetch a contact. |
| `POST` | `/api/v1/contacts/{id}/enrich` | Runs the waterfall (email/phone/company) against one contact, logs every attempt, updates the contact on a hit. |
| `POST` | `/api/v1/contacts/{id}/score` | Scores a contact against the active `ICPConfig`, persists `icp_score`, returns the per-criterion breakdown. |
| `GET` | `/health` | Liveness check. |
| `GET` | `/docs`, `/redoc`, `/openapi.json` | Interactive API docs (unauthenticated by design — see [What this is NOT](#what-this-is-not)). |

## Enrichment providers

| Provider | Field(s) | Live mode | Mock mode |
|---|---|---|---|
| Hunter.io | email | Implemented — real API call | Returns a fake `first.last@domain` email |
| Apollo.io | email, phone, company | Deliberate TODO stub — returns a clear miss, not a faked success (Apollo's free tier needs separate endpoints per lookup type; wasn't safe to build blind without a real key to verify against) | Returns fake data for whichever field was requested |
| HubSpot (CRM sync) | — | Implemented — real API call | Returns a fake `mock-hubspot-{id}` external id |

Leave a provider's API key unset (`HUNTER_API_KEY`, `APOLLO_API_KEY`,
`HUBSPOT_PRIVATE_APP_TOKEN` in `.env`) and its client runs in mock mode — the
whole waterfall is testable end-to-end with zero live credentials.

## Setup

```bash
git clone https://github.com/Hasee10/gtm-waterfall-enrichment
cd gtm-waterfall-enrichment/backend
cp .env.example .env               # then fill in whatever you have — everything
                                    # has a mock-mode fallback except the DB
uv sync --extra dev
```

Point `DATABASE_URL` at a real Postgres instance (or leave the `POSTGRES_*`
defaults if you're running one locally), then run migrations:

```bash
uv run alembic upgrade head
```

Seed at least one `WaterfallConfig` row per field you want to enrich, and one
`ICPConfig` row, before calling `/enrich` or `/score` — there's no CRUD
endpoint for either table yet (see [Known gaps](#known-gaps)), so this means a
direct DB insert for now. Example (email waterfall, Hunter then Apollo):

```sql
INSERT INTO waterfall_configs (field_type, provider_name, priority_order, enabled)
VALUES ('email', 'hunter', 1, true), ('email', 'apollo', 2, true);

INSERT INTO icp_configs (enabled, target_industries, industry_weight, title_keywords, title_weight)
VALUES (true, 'Software,SaaS', 50, 'VP,Director,Head,Chief', 50);
```

Run the app:

```bash
uv run fastapi dev src/interfaces/main.py
```

`/docs` is at `http://localhost:8000/docs`.

### Tests

```bash
cd backend
uv run pytest tests/unit           # no external dependencies required
uv run pytest tests/integration    # Docker-gated (Postgres via testcontainers)
```

## Deployment notes

- **No auth.** Put this behind a VPN, a private subnet, or an authenticating
  reverse proxy — never expose it directly to the internet as-is.
- Set unique database and Redis passwords (avoid the `.env.example` defaults).
- Restrict `CORS_ORIGINS` to specific domains in production (default is `*`).
- Set `ENVIRONMENT=production` to enable the environment-aware defaults
  (docs hidden unless `ENABLE_DOCS_IN_PRODUCTION=true`, etc.).

## Known gaps

Tracked honestly rather than silently glossed over — these are real,
acknowledged limitations of the current build, not bugs:

- **No CRUD endpoints for `WaterfallConfig` or `ICPConfig` yet.** Both are
  seeded via direct DB inserts. An admin UI or config API is natural future
  work.
- **HubSpot sync isn't wired to a route.** The client (`HubSpotClient`) and
  service method (`ContactService.sync_to_crm`) exist and are tested, but no
  endpoint calls them yet — the project's own goal ("sync *qualified* leads")
  implies a scoring threshold gate should exist first, which hasn't been
  designed yet.
- **HubSpot sync is create-only.** There's no `hubspot_contact_id` column on
  `Contact`, so repeated syncs for the same contact would create duplicate CRM
  records rather than update one.
- **`Contact` has no `phone` column.** The waterfall can attempt a phone
  lookup and will log the `EnrichmentJob`, but there's nowhere on `Contact` to
  write a found phone number back to yet.
- **Apollo's live mode isn't implemented.** It correctly reports a miss
  (rather than silently faking a success) if a real `APOLLO_API_KEY` is set,
  since Apollo's free tier needs separate endpoints per lookup type that
  weren't safe to build blind.
- **`docs/`** still contains the original FastAPI-boilerplate documentation
  site (mkdocs, unrelated to this project) from before this repo was
  repurposed. Left untouched — cleaning it up is outside any build step so
  far.

## License

MIT
