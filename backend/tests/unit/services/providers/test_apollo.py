"""Tests for the Apollo.io client."""

import pytest

from src.modules.common.enums import FieldType
from src.modules.companies.models import Company
from src.modules.contacts.models import Contact
from src.services.providers.apollo import ApolloClient


@pytest.fixture
def contact_with_company():
    company = Company(domain="acme.com", name="Acme Inc")
    contact = Contact(first_name="Jane", last_name="Doe")
    contact.company = company
    return contact


def test_mock_mode_when_no_api_key():
    assert ApolloClient(api_key=None).is_mock is True


def test_live_mode_when_api_key_set():
    assert ApolloClient(api_key="test-key").is_mock is False


@pytest.mark.asyncio
async def test_mock_email_lookup(contact_with_company):
    client = ApolloClient(api_key=None)
    result = await client.enrich(FieldType.EMAIL, contact_with_company)

    assert result.success is True
    assert result.data["email"] == "jane.doe@acme.com"
    assert result.credits_used == 0.0


@pytest.mark.asyncio
async def test_mock_phone_lookup(contact_with_company):
    client = ApolloClient(api_key=None)
    result = await client.enrich(FieldType.PHONE, contact_with_company)

    assert result.success is True
    assert "phone" in result.data


@pytest.mark.asyncio
async def test_mock_company_lookup(contact_with_company):
    client = ApolloClient(api_key=None)
    result = await client.enrich(FieldType.COMPANY, contact_with_company)

    assert result.success is True
    assert result.data["industry"] == "Software"
    assert result.data["employee_count"] == 50


@pytest.mark.asyncio
async def test_supports_all_three_field_types(contact_with_company):
    client = ApolloClient(api_key=None)
    for field_type in (FieldType.EMAIL, FieldType.PHONE, FieldType.COMPANY):
        result = await client.enrich(field_type, contact_with_company)
        assert result.success is True


@pytest.mark.asyncio
async def test_live_mode_is_a_clear_miss_not_a_silent_mock(contact_with_company):
    """Live mode isn't implemented yet — it must fail loudly, not fake success."""
    client = ApolloClient(api_key="test-key")
    result = await client.enrich(FieldType.EMAIL, contact_with_company)

    assert result.success is False
    assert "not yet implemented" in result.error
