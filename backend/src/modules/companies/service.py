from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .crud import crud_companies
from .schemas import CompanyCreate, CompanyRead


class CompanyService:
    """Companies are resolved by domain during CSV import and contact
    enrichment. There's no direct company CRUD endpoint yet — this
    lookup-or-create is only ever called internally, by ContactService.
    """

    async def get_or_create_by_domain(self, db: AsyncSession, domain: str, name: str) -> dict[str, Any]:
        """Domain is the de-dup key: two contacts at the same company share one row."""
        existing = await crud_companies.get(db=db, domain=domain, schema_to_select=CompanyRead)
        if existing:
            return existing

        created = await crud_companies.create(
            db=db, object=CompanyCreate(domain=domain, name=name), schema_to_select=CompanyRead
        )
        return created
