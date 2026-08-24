"""Hunter.io email-finder client (free tier: https://hunter.io/api/email-finder)."""

import httpx

from ...infrastructure.config.settings import settings
from ...infrastructure.logging import get_logger
from ...modules.common.enums import FieldType
from ...modules.contacts.models import Contact
from .base import BaseProvider, ProviderResult

logger = get_logger()

HUNTER_EMAIL_FINDER_URL = "https://api.hunter.io/v2/email-finder"


class HunterClient(BaseProvider):
    """Finds a contact's email from their name + company domain."""

    name = "hunter"
    supported_fields = {FieldType.EMAIL}

    def __init__(self, api_key: str | None = None) -> None:
        # Allow an explicit key (tests), otherwise fall back to settings so the
        # waterfall's default registry always reflects the current environment.
        self._api_key = api_key if api_key is not None else settings.HUNTER_API_KEY

    @property
    def is_mock(self) -> bool:
        return not self._api_key

    async def enrich(self, field_type: FieldType, contact: Contact) -> ProviderResult:
        if field_type not in self.supported_fields:
            return self._unsupported_field_result(field_type)

        if self.is_mock:
            return self._mock_result(contact)

        return await self._call_api(contact)

    def _mock_result(self, contact: Contact) -> ProviderResult:
        domain = contact.company.domain if contact.company else "example.com"
        fake_email = f"{contact.first_name}.{contact.last_name}@{domain}".lower()
        return ProviderResult(success=True, data={"email": fake_email}, credits_used=0.0)

    async def _call_api(self, contact: Contact) -> ProviderResult:
        if not contact.company or not contact.company.domain:
            return ProviderResult(success=False, error="no company domain to search against")

        params = {
            "domain": contact.company.domain,
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "api_key": self._api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(HUNTER_EMAIL_FINDER_URL, params=params)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(f"Hunter email-finder call failed: {exc}")
            return ProviderResult(success=False, credits_used=0.0, error=str(exc))

        email = response.json().get("data", {}).get("email")
        if not email:
            return ProviderResult(success=False, credits_used=1.0, error="Hunter found no matching email")

        return ProviderResult(success=True, data={"email": email}, credits_used=1.0)
