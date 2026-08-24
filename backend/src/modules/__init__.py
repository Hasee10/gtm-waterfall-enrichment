"""Initialize all modules and models to ensure SQLAlchemy registration.

GTM domain models (Company, Contact, EnrichmentJob, WaterfallConfig) get
imported here in the next build step so Alembic autogenerate can see them.
"""

__all__: list[str] = []
