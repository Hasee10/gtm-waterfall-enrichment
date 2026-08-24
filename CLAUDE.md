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

Step 3 done: built the waterfall enrichment service with stubbed
providers, under src/services/ (not modules/ — this is orchestration
logic, not a vertical-slice domain resource). src/services/providers/
has base.py (BaseProvider ABC + ProviderResult dataclass), hunter.py
(HunterClient — real email-finder HTTP call implemented, since Hunter's
API is a single simple endpoint), apollo.py (ApolloClient — mock mode
covers email/phone/company; live mode is a deliberate TODO stub that
returns a clear miss rather than silently faking success, since
Apollo's free tier needs separate endpoints per lookup type that
weren't safe to build blind without a real key to verify against), and
registry.py (provider_name string -> client instance, so the waterfall
never imports a provider class directly). Both clients read
HUNTER_API_KEY/APOLLO_API_KEY from a new ProviderSettings class — unset
means mock mode, so the whole thing is testable with zero live keys.

src/services/enrichment/waterfall.py holds WaterfallEnrichmentService:
for one contact + field_type, it queries enabled WaterfallConfig rows
in priority order, tries each provider via the registry, logs every
attempt (hit or miss) as an EnrichmentJob, and stops at the first
success. On success it writes back onto Contact (email +
enrichment_status=ENRICHED); on total failure it sets
enrichment_status=FAILED, but only for the EMAIL field — phone/company
misses have no matching Contact column to update yet, which is a real
gap in the current data model (Contact has no phone field), not an
oversight to silently paper over. The service doesn't commit; same
convention as the rest of the codebase — the caller (a route, in step
4) owns the transaction.

Added 22 new unit tests: provider tests use synthetic contacts (no DB),
Hunter's live-mode HTTP call is tested via a mocked httpx.AsyncClient;
waterfall tests use an in-memory SQLite engine (not the Docker-gated
Postgres fixtures) with a patched provider registry for deterministic
success/fail/disabled-config scenarios. Full suite: 101 passed, 3
skipped, ruff clean, app boots.

Step 4 done: exposed the three endpoints, plus a companies module built
just far enough to support them (no company endpoints yet — company
resolution is internal-only, called by ContactService during import).

- src/modules/companies/: schemas.py, crud.py (FastCRUD), service.py
  (get_or_create_by_domain — domain is the de-dup key, so two contacts
  at the same company share one row).
- src/modules/contacts/: schemas.py (ContactRead/Create,
  ContactBulkImportResult + ContactImportError for row-level failures,
  ContactEnrichResult), crud.py, service.py, dependencies.py, routes.py.
- src/modules/enrichment_jobs/schemas.py: EnrichmentJobRead, for
  serializing the jobs list an enrich call returns.
- POST /api/v1/contacts/bulk: parses a CSV (first_name, last_name
  required; email, title, company_domain, company_name optional).
  Deliberately row-tolerant — a bad row (e.g. missing last_name) is
  collected into an errors list with its row number, not a reason to
  reject the whole file. Each row commits independently, so a
  company_domain repeated across rows resolves to the same Company
  within one batch.
- GET /api/v1/contacts/{id}: plain lookup, 404 via ResourceNotFoundError
  -> handle_exception's existing DomainError mapping (no new exception
  wiring needed).
- POST /api/v1/contacts/{id}/enrich: runs WaterfallEnrichmentService
  across all three FieldTypes (email/phone/company) against one
  contact, commits, and returns the updated contact + every
  EnrichmentJob logged.

Verified end-to-end against a throwaway SQLite db with a live uvicorn
server (not just imports): bulk-imported a 3-row CSV (2 created, 1
correctly rejected with "first_name and last_name are required" at row
4, company dedup confirmed — both Acme contacts got the same
company_id), GET by id returned the right contact, POST .../enrich ran
Hunter in mock mode and correctly set email + enrichment_status. Also
confirmed a genuinely-missing contact returns 404 against a live DB
(separately from a DB-unreachable 500, which is just this sandbox
having no working local Postgres — same known limitation as steps 1-2,
not a bug).

10 new unit tests for CompanyService/ContactService (in-memory SQLite,
patched provider registry — no Docker). Full suite: 111 passed, 3
skipped, ruff clean, app boots.

Step 5 done: ICP scoring, config-driven via a new ICPConfig table
(src/modules/icp_config/models.py) — same non-hardcoded reasoning as
WaterfallConfig: tightening or loosening the ICP definition should be a
DB update, not a deploy. No CRUD endpoint for ICPConfig yet either
(consistent with WaterfallConfig) — it's seeded directly for now.

Four criteria, each independently optional (None/empty = not
configured, skipped entirely rather than counted as a miss, so an
incomplete profile doesn't drag every score toward zero):
target_industries (comma-separated, matched against Company.industry),
employee_count_min/max (inclusive range against
Company.employee_count), target_revenue_ranges (comma-separated,
matched against Company.revenue_range), title_keywords
(comma-separated, case-insensitive substring match against
Contact.title). Each has its own weight; final score is normalized to
0-100 over only the criteria actually configured (earned/possible *
100), so a 2-of-4-configured profile isn't unfairly capped.

Scoring logic itself lives in src/services/scoring/icp.py
(ICPScoringService — services/, not modules/, same reasoning as
waterfall living in services/enrichment: this is orchestration across
Contact+Company+ICPConfig, not one vertical-slice CRUD resource).
Wired into ContactService.score() and exposed as POST
/api/v1/contacts/{id}/score, which persists the score onto Contact and
returns the full per-criterion breakdown (not just the number) so a
caller can see why a contact scored the way it did.

Added the migration (b8207c2e3983, chained onto the step-2 migration)
the same way as before: autogenerate, then upgrade/downgrade/upgrade
against a throwaway SQLite db to confirm it's clean. Verified the score
endpoint end-to-end with a live uvicorn server too — seeded an
ICPConfig, imported a contact via CSV, scored them, got back a
correctly partial 50.0 (title keyword matched, industry didn't since
the company had none set).

13 new unit tests: pure-Python scoring tests (no DB) covering full
match, no-criteria, partial-match normalization, unconfigured-criterion
exclusion, no-company, open-ended employee range, and case-insensitive
title matching; plus service-layer tests for the missing-contact and
missing-config error paths and for persistence. Full suite: 121 passed,
3 skipped, ruff clean, app boots.

Step 6 done: HubSpot sync service, stubbed until a token is provided —
same mock-mode pattern as Hunter/Apollo. src/services/crm/base.py has
BaseCRMClient (mirrors BaseProvider) + CRMSyncResult; src/services/crm/
hubspot.py has HubSpotClient, reading HUBSPOT_PRIVATE_APP_TOKEN from a
new CRMSettings class. Live mode does a real POST to HubSpot's
crm/v3/objects/contacts (implemented properly, like Hunter — it's a
single simple endpoint, safe to build without a live token to verify
against). Wired into ContactService.sync_to_crm().

Deliberately NOT wired to a route yet — step 6 in the build order only
asked for "the sync service," not an endpoint (unlike step 4, which
named its three routes explicitly). Two real gaps, flagged rather than
silently papered over: (1) create-only — there's no hubspot_contact_id
column on Contact, so repeated syncs for the same contact will create
duplicate CRM records rather than update one; (2) there's no
"qualified leads only" gate (e.g. icp_score above a threshold) before
pushing — the project's own framing (README-level: "Syncs qualified
leads to HubSpot") implies that gate should exist before this is
exposed as an endpoint. Both are natural fits for whichever future step
adds the actual /sync-crm route.

8 new unit tests (mock mode, live mode via mocked httpx, HTTP-error
handling, missing-contact and missing-response-id paths). Full suite:
129 passed, 3 skipped, ruff clean, app boots. No new migration — no
schema changes this step.

Next: Step 7 — write README with architecture diagram description
(Trigger → Waterfall Enrichment → Scoring → CRM Sync) and setup
instructions.
