"""Tests for ContactService: CSV bulk import, lookup, and the enrich endpoint's
service layer. Uses an in-memory SQLite engine — no Docker dependency.
"""

from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.database.session import Base
from src.modules.common.enums import FieldType
from src.modules.common.exceptions import ResourceNotFoundError, ValidationError
from src.modules.contacts.enums import EnrichmentStatus
from src.modules.contacts.service import ContactService
from src.modules.waterfall_config.models import WaterfallConfig
from src.services.enrichment.waterfall import WaterfallEnrichmentService
from src.services.providers.base import ProviderResult

SAMPLE_CSV = (
    "first_name,last_name,email,title,company_domain,company_name\n"
    "Jane,Doe,,VP Sales,acme.com,Acme Inc\n"
    "Bob,Builder,,CTO,acme.com,\n"  # same domain as Jane — should share a company
    "John,,Smith,Manager,,\n"  # missing last_name — should be reported, not raised
)


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_bulk_import_creates_contacts_and_reports_bad_rows(db_session):
    service = ContactService()
    result = await service.bulk_create_from_csv(db_session, SAMPLE_CSV.encode("utf-8"))

    assert result.created == 2
    assert result.failed == 1
    assert result.errors[0].row == 4  # header is row 1, so John's row is row 4
    assert "first_name and last_name" in result.errors[0].error
    assert {c.first_name for c in result.contacts} == {"Jane", "Bob"}


@pytest.mark.asyncio
async def test_bulk_import_dedupes_company_by_domain(db_session):
    service = ContactService()
    result = await service.bulk_create_from_csv(db_session, SAMPLE_CSV.encode("utf-8"))

    jane, bob = result.contacts
    assert jane.company_id == bob.company_id


@pytest.mark.asyncio
async def test_bulk_import_rejects_missing_required_columns(db_session):
    service = ContactService()
    bad_csv = b"name,email\nJane,jane@acme.com\n"

    with pytest.raises(ValidationError):
        await service.bulk_create_from_csv(db_session, bad_csv)


@pytest.mark.asyncio
async def test_get_by_id_returns_contact(db_session):
    service = ContactService()
    imported = await service.bulk_create_from_csv(db_session, SAMPLE_CSV.encode("utf-8"))
    contact_id = imported.contacts[0].id

    fetched = await service.get_by_id(db_session, contact_id)
    assert fetched["id"] == contact_id


@pytest.mark.asyncio
async def test_get_by_id_raises_for_missing_contact(db_session):
    service = ContactService()
    with pytest.raises(ResourceNotFoundError):
        await service.get_by_id(db_session, 999)


@pytest.mark.asyncio
async def test_enrich_raises_for_missing_contact(db_session):
    service = ContactService()
    with pytest.raises(ResourceNotFoundError):
        await service.enrich(db_session, 999, WaterfallEnrichmentService())


class _FakeProvider:
    def __init__(self, result: ProviderResult):
        self._result = result

    async def enrich(self, field_type, contact):
        return self._result


@pytest.mark.asyncio
async def test_enrich_runs_waterfall_and_updates_contact(db_session):
    service = ContactService()
    imported = await service.bulk_create_from_csv(db_session, SAMPLE_CSV.encode("utf-8"))
    contact_id = imported.contacts[0].id

    db_session.add(WaterfallConfig(field_type=FieldType.EMAIL, provider_name="hunter", priority_order=1, enabled=True))
    await db_session.commit()

    hunter_result = ProviderResult(success=True, data={"email": "jane@acme.com"}, credits_used=1.0)
    with patch(
        "src.services.enrichment.waterfall.get_provider",
        side_effect=lambda name: _FakeProvider(hunter_result),
    ):
        outcome = await service.enrich(db_session, contact_id, WaterfallEnrichmentService())

    assert outcome.contact.email == "jane@acme.com"
    assert outcome.contact.enrichment_status == EnrichmentStatus.ENRICHED
    assert len(outcome.jobs) == 1
    assert outcome.jobs[0].provider_name == "hunter"


@pytest.mark.asyncio
async def test_enrich_with_no_waterfall_config_returns_no_jobs(db_session):
    """No WaterfallConfig rows at all for any field — enrich shouldn't error,
    just come back empty (email attempt still marks the contact failed)."""
    service = ContactService()
    imported = await service.bulk_create_from_csv(db_session, SAMPLE_CSV.encode("utf-8"))
    contact_id = imported.contacts[0].id

    outcome = await service.enrich(db_session, contact_id, WaterfallEnrichmentService())

    assert outcome.jobs == []
    assert outcome.contact.enrichment_status == EnrichmentStatus.FAILED
