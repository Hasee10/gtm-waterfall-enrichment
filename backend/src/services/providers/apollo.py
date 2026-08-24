"""Apollo.io client (free tier lookup) — the broader fallback provider.

Unlike Hunter (email only), Apollo's free tier can return email, phone, and
firmographic data, so it covers whatever Hunter misses in the email waterfall
and is the only provider currently configured for phone/company lookups.
"""

from ...infrastructure.config.settings import settings
from ...infrastructure.logging import get_logger
from ...modules.common.enums import FieldType
from ...modules.contacts.models import Contact
from .base import BaseProvider, ProviderResult

logger = get_logger()


class ApolloClient(BaseProvider):
    """Looks up email, phone, or company data from Apollo's free tier."""

    name = "apollo"
    supported_fields = {FieldType.EMAIL, FieldType.PHONE, FieldType.COMPANY}

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else settings.APOLLO_API_KEY

    @property
    def is_mock(self) -> bool:
        return not self._api_key

    async def enrich(self, field_type: FieldType, contact: Contact) -> ProviderResult:
        if field_type not in self.supported_fields:
            return self._unsupported_field_result(field_type)

        if self.is_mock:
            return self._mock_result(field_type, contact)

        return await self._call_api(field_type, contact)

    def _mock_result(self, field_type: FieldType, contact: Contact) -> ProviderResult:
        if field_type == FieldType.EMAIL:
            domain = contact.company.domain if contact.company else "example.com"
            fake_email = f"{contact.first_name}.{contact.last_name}@{domain}".lower()
            return ProviderResult(success=True, data={"email": fake_email}, credits_used=0.0)

        if field_type == FieldType.PHONE:
            return ProviderResult(success=True, data={"phone": "+1-555-0100"}, credits_used=0.0)

        # FieldType.COMPANY
        return ProviderResult(
            success=True,
            data={"industry": "Software", "employee_count": 50, "revenue_range": "$1M-$10M"},
            credits_used=0.0,
        )

    async def _call_api(self, field_type: FieldType, contact: Contact) -> ProviderResult:
        # TODO: wire Apollo's people-search (email/phone) and organization-enrichment
        # (company) endpoints once a real API key is available to verify against.
        # Apollo's free tier uses separate endpoints per lookup type, unlike Hunter's
        # single email-finder call, so this needs a live key to build against safely.
        # Deliberately a miss, not a silent fallback to mock data: with a real key
        # configured, faking a success here would hide that live mode isn't wired up.
        logger.warning("Apollo live mode requested but not yet implemented")
        return ProviderResult(success=False, credits_used=0.0, error="Apollo live mode not yet implemented")
