"""Initialize all modules and models to ensure SQLAlchemy registration."""

from .companies.models import Company
from .contacts.models import Contact
from .enrichment_jobs.models import EnrichmentJob
from .icp_config.models import ICPConfig
from .waterfall_config.models import WaterfallConfig

__all__ = [
    "Company",
    "Contact",
    "EnrichmentJob",
    "ICPConfig",
    "WaterfallConfig",
]
