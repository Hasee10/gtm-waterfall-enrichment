"""Tests for the HubSpot CRM client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.modules.contacts.models import Contact
from src.services.crm.hubspot import HubSpotClient


@pytest.fixture
def contact():
    return Contact(first_name="Jane", last_name="Doe", email="jane@acme.com", title="VP Sales")


def test_mock_mode_when_no_token():
    assert HubSpotClient(token=None).is_mock is True


def test_live_mode_when_token_set():
    assert HubSpotClient(token="test-token").is_mock is False


@pytest.mark.asyncio
async def test_mock_push_returns_fake_external_id(contact):
    contact.id = 42  # normally set by the DB; faked here since this contact is never persisted
    client = HubSpotClient(token=None)

    result = await client.push_contact(contact)

    assert result.success is True
    assert result.external_id == "mock-hubspot-42"


@pytest.mark.asyncio
async def test_live_push_success(contact):
    client = HubSpotClient(token="test-token")

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "hs-123"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
        result = await client.push_contact(contact)

    assert result.success is True
    assert result.external_id == "hs-123"


@pytest.mark.asyncio
async def test_live_push_missing_id_in_response(contact):
    client = HubSpotClient(token="test-token")

    mock_response = MagicMock()
    mock_response.json.return_value = {}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
        result = await client.push_contact(contact)

    assert result.success is False
    assert "missing contact id" in result.error


@pytest.mark.asyncio
async def test_live_push_http_error(contact):
    client = HubSpotClient(token="test-token")

    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.ConnectTimeout("timed out"))):
        result = await client.push_contact(contact)

    assert result.success is False
