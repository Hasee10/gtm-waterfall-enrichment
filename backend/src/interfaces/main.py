from ..infrastructure.app_factory import create_application
from ..infrastructure.config.settings import get_settings
from ..interfaces.api import router

settings = get_settings()

app = create_application(
    router=router,
    settings=settings,
    title="GTM Waterfall Enrichment",
    summary="Self-hosted lead enrichment waterfall + CRM sync engine",
    description="""
    # GTM Waterfall Enrichment

    An open-source alternative to Clay:

    * Ingest raw contacts (CSV upload or manual entry)
    * Waterfall enrichment across free-tier providers, with per-provider cost logging
    * Configurable ICP scoring
    * Sync of qualified leads to HubSpot

    Note: this API is intentionally unauthenticated. It is meant to run
    self-hosted behind your own network boundary, not exposed publicly.
    """,
    version="0.1.0",
    license_info={
        "name": "MIT",
        "identifier": "MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "healthy"}
