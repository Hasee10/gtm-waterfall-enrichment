"""Enums shared across GTM domain modules."""

from enum import StrEnum


class FieldType(StrEnum):
    """The contact field a waterfall enrichment attempt is trying to fill.

    Shared between EnrichmentJob and WaterfallConfig: WaterfallConfig defines the
    provider order to try per field, and EnrichmentJob logs which field a given
    attempt was for.
    """

    EMAIL = "email"
    PHONE = "phone"
    COMPANY = "company"
