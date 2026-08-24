"""Tests for the Hunter.io email-finder client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.modules.common.enums import FieldType
from src.modules.companies.models import Company
from src.modules.contacts.models import Contact
from src.services.providers.hunter import HunterClient


@pytest.fixture
def contact_with_company():
    company = Company(domain="acme.com", name="Acme Inc")
    contact = Contact(first_name="Jane", last_name="Doe")
    contact.company = company
    return contact


def test_mock_mode_when_no_api_key():
    client = HunterClient(api_key=None)
    assert client.is_mock is True


def test_live_mode_when_api_key_set():
    client = HunterClient(api_key="test-key")
    assert client.is_mock is False


@pytest.mark.asyncio
async def test_mock_result_returns_fake_email(contact_with_company):
    client = HunterClient(api_key=None)
    result = await client.enrich(FieldType.EMAIL, contact_with_company)

    assert result.success is True
    assert result.data["email"] == "jane.doe@acme.com"
    assert result.credits_used == 0.0


@pytest.mark.asyncio
async def test_mock_result_falls_back_to_example_domain_without_company():
    client = HunterClient(api_key=None)
    contact = Contact(first_name="Jane", last_name="Doe")

    result = await client.enrich(FieldType.EMAIL, contact)

    assert result.success is True
    assert result.data["email"] == "jane.doe@example.com"


@pytest.mark.asyncio
async def test_unsupported_field_type_returns_failure(contact_with_company):
    client = HunterClient(api_key=None)
    result = await client.enrich(FieldType.PHONE, contact_with_company)

    assert result.success is False
    assert "does not support" in result.error


@pytest.mark.asyncio
async def test_live_mode_without_company_domain_fails_fast():
    client = HunterClient(api_key="test-key")
    contact = Contact(first_name="Jane", last_name="Doe")

    result = await client.enrich(FieldType.EMAIL, contact)

    assert result.success is False
    assert "domain" in result.error


@pytest.mark.asyncio
async def test_live_mode_success(contact_with_company):
    client = HunterClient(api_key="test-key")

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"email": "jane.doe@acme.com"}}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_response)):
        result = await client.enrich(FieldType.EMAIL, contact_with_company)

    assert result.success is True
    assert result.data["email"] == "jane.doe@acme.com"
    assert result.credits_used == 1.0


@pytest.mark.asyncio
async def test_live_mode_no_email_found(contact_with_company):
    client = HunterClient(api_key="test-key")

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"email": None}}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_response)):
        result = await client.enrich(FieldType.EMAIL, contact_with_company)

    assert result.success is False
    assert result.credits_used == 1.0


@pytest.mark.asyncio
async def test_live_mode_http_error(contact_with_company):
    client = HunterClient(api_key="test-key")

    with patch(
        "httpx.AsyncClient.get",
        new=AsyncMock(side_effect=httpx.ConnectTimeout("timed out")),
    ):
        result = await client.enrich(FieldType.EMAIL, contact_with_company)

    assert result.success is False
    assert result.credits_used == 0.0
