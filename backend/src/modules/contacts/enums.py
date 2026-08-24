"""Contact-specific enums."""

from enum import StrEnum


class EnrichmentStatus(StrEnum):
    """Where a contact is in the waterfall enrichment lifecycle."""

    PENDING = "pending"
    ENRICHED = "enriched"
    FAILED = "failed"
