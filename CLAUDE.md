# Project: gtm-waterfall-enrichment

## Who's building this and why
Haseeb Arshad, Data Science student (FAST NUCES, class of 2027), AI Engineer
at IntegCubes, Founding Engineer at Automata AI. Transitioning into GTM
Engineering as a skill and portfolio project. This repo is a public,
free/open-source alternative to Clay — a self-hosted lead enrichment
waterfall + CRM sync engine, built to demonstrate GTM engineering
competency to future employers/clients (RevOps architecture, API cost
efficiency, clean CRM schemas, scalability).

## What this project IS
A backend service that:
1. Ingests raw contacts (CSV upload or manual entry)
2. Runs waterfall enrichment: tries multiple free-tier data providers in
   priority order per field (email, phone, company data) until one hits,
   logs which provider succeeded and cost
3. Scores enriched leads against a configurable ICP (Ideal Customer Profile)
4. Syncs qualified leads to HubSpot free CRM

## Tech stack (from the boilerplate, keep these)
FastAPI (async), Pydantic v2, SQLAlchemy 2.0 (async), PostgreSQL, Redis,
Alembic for migrations, httpx for outbound API calls.

## Non-negotiable rules
- NEVER hardcode API keys, tokens, or secrets anywhere in code. All
  external credentials come from environment variables via a Pydantic
  Settings class, loaded from .env (which is gitignored). Where a
  provider key isn't available yet, stub the client with a clear
  TODO and a mock/fake response mode so the rest of the pipeline is
  testable without live keys.
- Do not delete or rewrite files outside what a step explicitly asks for.
  If you think something outside scope needs to change, stop and tell
  me instead of doing it.
- After each major step, run the app / relevant tests and report
  whether it actually boots, don't just report code written.
- Keep commits small and scoped to one step at a time — one logical
  change per commit, with a clear message.
- This is a PUBLIC repo. No secrets, no personal data, no real contact
  info in seed/test data — use obviously fake example data only.
- I am learning GTM engineering concepts through this build, so add
  brief comments explaining GTM-specific logic (why waterfall order
  matters, why credits/cost tracking matters, what ICP scoring means)
  — not tutorial-level, just enough that I can explain this system in
  an interview.

## Data model (target — build via Alembic migrations, don't hand-edit DB)
- Company: id, domain, name, industry, employee_count, revenue_range,
  created_at
- Contact: id, first_name, last_name, email (nullable), title,
  company_id (FK), enrichment_status (enum: pending/enriched/failed),
  icp_score (nullable float), created_at
- EnrichmentJob: id, contact_id (FK), field_type (email/phone/company),
  provider_name, status (success/fail), credits_used, result_json,
  attempted_at
- WaterfallConfig: id, field_type, provider_name, priority_order,
  enabled (bool) — this table defines which providers are tried in
  which order per field, so it's configurable without code changes

## Provider clients to build (stubbed until I supply keys)
- Hunter.io (email finder, free tier)
- Apollo.io (free tier lookup)
- HubSpot (CRM push, free tier private app token)
Each as its own class in app/services/providers/, implementing a shared
interface (e.g. `async def find_email(name, domain) -> EnrichmentResult`)
so adding a new provider later doesn't touch the waterfall logic itself.

## Build order (do NOT skip ahead — confirm each step works before next)
1. Strip boilerplate down to what's needed; confirm app still boots
2. Add the 4 models above + Alembic migration; confirm migration runs
   clean against a local Postgres (or SQLite fallback for dev)
3. Build the waterfall enrichment service with stubbed providers
   (mock mode returns fake data when no API key is set)
4. Expose endpoints: POST /contacts/bulk (CSV upload), POST
   /contacts/{id}/enrich, GET /contacts/{id}
5. Add ICP scoring logic + endpoint (config-driven weights, not hardcoded)
6. Add HubSpot sync service (stubbed until token provided)
7. Write README with architecture diagram description (Trigger →
   Waterfall Enrichment → Scoring → CRM Sync) and setup instructions

## Current status
Step 1 done: stripped the boilerplate down to the GTM core and confirmed
it boots. Removed entirely: modules/user, tier, api_keys, rate_limit;
infrastructure/auth, rate_limit, security (production_validator);
interfaces/admin; the cli/ package; the superuser/tier seed scripts and
all their tests. Kept: config/settings, database session, cache (Redis/
Memcached), logging, middleware (security headers, client cache),
taskiq, alembic migrations, modules/common (now houses the shared
http_exceptions.py that used to live under infrastructure/auth), the
Dockerfile.

App is intentionally fully open — no auth stack at all. docs_url/
/openapi.json//redoc are unauthenticated in every environment. Verified
boot with `uvicorn` (CACHE_ENABLED=false CREATE_TABLES_ON_STARTUP=false,
since there's no local Postgres/Redis in this environment) — /health,
/docs, /openapi.json all returned 200. Full unit suite passes (79
passed, 3 skipped — the skips are Postgres/Docker-gated). Ruff clean.

Git remotes: `origin` now points to
github.com/Hasee10/gtm-waterfall-enrichment (SSH — the Git Credential
Manager here is authenticated as a different GitHub account,
techteam-automata, so HTTPS push gets a 403; use
`git@github.com:Hasee10/gtm-waterfall-enrichment.git`). `upstream`
still points to benavlabs/FastAPI-boilerplate so boilerplate fixes can
be pulled later. History was kept (not squashed) per Haseeb's call.

Known stale-but-harmless leftovers, not touched (out of this step's
scope — flagged instead of silently changing per project rules):
- `.github/workflows/tests.yml` and `type-checking.yml` still set an
  unused `SECRET_KEY` env var and have a `cli/` comment. Harmless
  (pydantic-settings ignores unknown env vars by default), but worth
  cleaning up in a later docs/CI pass.

Step 2 done: added the 4 target models as vertical-slice modules under
src/modules/ — companies/models.py, contacts/models.py (+ enums.py for
EnrichmentStatus), enrichment_jobs/models.py (+ enums.py for JobStatus),
waterfall_config/models.py. FieldType (email/phone/company) lives in
modules/common/enums.py since both EnrichmentJob and WaterfallConfig
need it. WaterfallConfig has a unique constraint on
(field_type, provider_name) so a provider can't be double-entered in
one field's priority order. Registered all 4 in modules/__init__.py for
SQLAlchemy/Alembic discovery.

Generated the first Alembic migration (dfae5d3bb7b7) via autogenerate.
No Postgres available in this environment, so verified it against a
throwaway SQLite db (DATABASE_URL=sqlite+aiosqlite:///./gtm_test.db):
upgrade → inspected schema (matches the target data model exactly) →
downgrade → upgrade again, all clean. Settings has no permanent SQLite
fallback wired in — that env var was only for this one-off migration
test, not a code change. Full unit suite still 79 passed/3 skipped,
ruff clean, app boots.

Next: Step 3 — build the waterfall enrichment service with stubbed
providers (mock mode when no API key is set).
