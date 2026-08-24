"""Tests for the waterfall enrichment service.

Uses an in-memory SQLite engine rather than the Postgres testcontainers fixtures
in conftest.py, so this stays a fast unit test with no Docker dependency — the
waterfall logic itself doesn't touch anything Postgres-specific.
"""

from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.database.session import Base
from src.modules.common.enums import FieldType
from src.modules.contacts.enums import EnrichmentStatus
from src.modules.contacts.models import Contact
from src.modules.enrichment_jobs.enums import JobStatus
from src.modules.waterfall_config.models import WaterfallConfig
from src.services.enrichment.waterfall import WaterfallEnrichmentService
from src.services.providers.base import ProviderResult


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def contact(db_session: AsyncSession):
    c = Contact(first_name="Jane", last_name="Doe")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    return c


class _FakeProvider:
    """A canned provider for deterministic waterfall tests."""

    def __init__(self, result: ProviderResult):
        self._result = result

    async def enrich(self, field_type, contact):
        return self._result


def _fake_registry(**providers):
    """Patch get_provider to serve fixed results by provider_name, independent of
    the real Hunter/Apollo mock-data generation."""
    return patch("src.services.enrichment.waterfall.get_provider", side_effect=lambda name: providers[name])


@pytest.mark.asyncio
async def test_first_provider_success_stops_the_waterfall(db_session, contact):
    db_session.add_all(
        [
            WaterfallConfig(field_type=FieldType.EMAIL, provider_name="hunter", priority_order=1, enabled=True),
            WaterfallConfig(field_type=FieldType.EMAIL, provider_name="apollo", priority_order=2, enabled=True),
        ]
    )
    await db_session.commit()

    with _fake_registry(
        hunter=_FakeProvider(ProviderResult(success=True, data={"email": "jane@acme.com"}, credits_used=1.0)),
        apollo=_FakeProvider(ProviderResult(success=True, data={"email": "should-not-be-used@x.com"})),
    ):
        service = WaterfallEnrichmentService()
        job = await service.enrich_field(db_session, contact, FieldType.EMAIL)
    await db_session.commit()

    assert job.provider_name == "hunter"
    assert job.status == JobStatus.SUCCESS
    assert contact.email == "jane@acme.com"
    assert contact.enrichment_status == EnrichmentStatus.ENRICHED


@pytest.mark.asyncio
async def test_falls_through_to_next_provider_on_miss(db_session, contact):
    db_session.add_all(
        [
            WaterfallConfig(field_type=FieldType.EMAIL, provider_name="hunter", priority_order=1, enabled=True),
            WaterfallConfig(field_type=FieldType.EMAIL, provider_name="apollo", priority_order=2, enabled=True),
        ]
    )
    await db_session.commit()

    with _fake_registry(
        hunter=_FakeProvider(ProviderResult(success=False, error="no match")),
        apollo=_FakeProvider(ProviderResult(success=True, data={"email": "jane@acme.com"}, credits_used=1.0)),
    ):
        service = WaterfallEnrichmentService()
        job = await service.enrich_field(db_session, contact, FieldType.EMAIL)
    await db_session.commit()

    assert job.provider_name == "apollo"
    assert job.status == JobStatus.SUCCESS
    assert contact.email == "jane@acme.com"


@pytest.mark.asyncio
async def test_all_providers_miss_marks_contact_failed(db_session, contact):
    db_session.add_all(
        [
            WaterfallConfig(field_type=FieldType.EMAIL, provider_name="hunter", priority_order=1, enabled=True),
            WaterfallConfig(field_type=FieldType.EMAIL, provider_name="apollo", priority_order=2, enabled=True),
        ]
    )
    await db_session.commit()

    with _fake_registry(
        hunter=_FakeProvider(ProviderResult(success=False, error="no match")),
        apollo=_FakeProvider(ProviderResult(success=False, error="no match")),
    ):
        service = WaterfallEnrichmentService()
        job = await service.enrich_field(db_session, contact, FieldType.EMAIL)
    await db_session.commit()

    assert job.provider_name == "apollo"
    assert job.status == JobStatus.FAIL
    assert contact.email is None
    assert contact.enrichment_status == EnrichmentStatus.FAILED


@pytest.mark.asyncio
async def test_disabled_config_is_skipped(db_session, contact):
    db_session.add_all(
        [
            WaterfallConfig(field_type=FieldType.EMAIL, provider_name="hunter", priority_order=1, enabled=False),
            WaterfallConfig(field_type=FieldType.EMAIL, provider_name="apollo", priority_order=2, enabled=True),
        ]
    )
    await db_session.commit()

    with _fake_registry(
        apollo=_FakeProvider(ProviderResult(success=True, data={"email": "jane@acme.com"}, credits_used=1.0)),
    ):
        service = WaterfallEnrichmentService()
        job = await service.enrich_field(db_session, contact, FieldType.EMAIL)

    assert job.provider_name == "apollo"


@pytest.mark.asyncio
async def test_no_enabled_configs_returns_none_and_marks_contact_failed(db_session, contact):
    """No WaterfallConfig rows for this field is treated the same as every
    provider missing: nothing to try means the email attempt failed."""
    service = WaterfallEnrichmentService()
    job = await service.enrich_field(db_session, contact, FieldType.EMAIL)

    assert job is None
    assert contact.email is None
    assert contact.enrichment_status == EnrichmentStatus.FAILED


@pytest.mark.asyncio
async def test_phone_miss_does_not_touch_contact_enrichment_status(db_session, contact):
    """Contact has no phone column, so a phone-field miss has nothing to mark failed."""
    db_session.add(WaterfallConfig(field_type=FieldType.PHONE, provider_name="apollo", priority_order=1, enabled=True))
    await db_session.commit()

    with _fake_registry(apollo=_FakeProvider(ProviderResult(success=False, error="no match"))):
        service = WaterfallEnrichmentService()
        await service.enrich_field(db_session, contact, FieldType.PHONE)

    assert contact.enrichment_status == EnrichmentStatus.PENDING
