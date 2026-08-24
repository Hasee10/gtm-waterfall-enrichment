"""Tests for CompanyService.get_or_create_by_domain.

Uses an in-memory SQLite engine (no Docker dependency), same pattern as the
waterfall service tests.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.database.session import Base
from src.modules.companies.service import CompanyService


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
async def test_creates_company_when_domain_unseen(db_session):
    service = CompanyService()
    company = await service.get_or_create_by_domain(db_session, domain="acme.com", name="Acme Inc")

    assert company["domain"] == "acme.com"
    assert company["name"] == "Acme Inc"
    assert company["id"] is not None


@pytest.mark.asyncio
async def test_returns_existing_company_for_same_domain(db_session):
    service = CompanyService()
    first = await service.get_or_create_by_domain(db_session, domain="acme.com", name="Acme Inc")
    second = await service.get_or_create_by_domain(db_session, domain="acme.com", name="A different name")

    assert second["id"] == first["id"]
    # The name from the first call wins — domain is the de-dup key, not name.
    assert second["name"] == "Acme Inc"
