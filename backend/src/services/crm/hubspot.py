"""HubSpot CRM client (free tier: https://developers.hubspot.com/docs/api/crm/contacts).

Pushes a single contact as a new HubSpot CRM contact via a private app token.
Create-only for now — there's no stored HubSpot contact id on the Contact
model yet (out of scope for this build step), so repeated pushes for the same
contact will create duplicate CRM records rather than update one. Wiring an
upsert (search-by-email-then-update, or storing the returned id) is a
follow-up once this is actually exercised against a real HubSpot account.
"""

import httpx

from ...infrastructure.config.settings import settings
from ...infrastructure.logging import get_logger
from ...modules.contacts.models import Contact
from .base import BaseCRMClient, CRMSyncResult

logger = get_logger()

HUBSPOT_CONTACTS_URL = "https://api.hubapi.com/crm/v3/objects/contacts"


class HubSpotClient(BaseCRMClient):
    """Pushes a contact into HubSpot's free-tier CRM as a new contact record."""

    name = "hubspot"

    def __init__(self, token: str | None = None) -> None:
        self._token = token if token is not None else settings.HUBSPOT_PRIVATE_APP_TOKEN

    @property
    def is_mock(self) -> bool:
        return not self._token

    async def push_contact(self, contact: Contact) -> CRMSyncResult:
        if self.is_mock:
            return self._mock_result(contact)
        return await self._call_api(contact)

    def _mock_result(self, contact: Contact) -> CRMSyncResult:
        return CRMSyncResult(success=True, external_id=f"mock-hubspot-{contact.id}")

    async def _call_api(self, contact: Contact) -> CRMSyncResult:
        properties = {"firstname": contact.first_name, "lastname": contact.last_name}
        if contact.email:
            properties["email"] = contact.email
        if contact.title:
            properties["jobtitle"] = contact.title

        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(HUBSPOT_CONTACTS_URL, json={"properties": properties}, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(f"HubSpot contact push failed: {exc}")
            return CRMSyncResult(success=False, error=str(exc))

        external_id = response.json().get("id")
        if not external_id:
            return CRMSyncResult(success=False, error="HubSpot response missing contact id")

        return CRMSyncResult(success=True, external_id=external_id)
