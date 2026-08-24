from fastapi import APIRouter

router = APIRouter(prefix="/v1")

# GTM domain routers (contacts, enrichment, scoring, CRM sync) get mounted here
# in later build steps. Intentionally empty for now.
