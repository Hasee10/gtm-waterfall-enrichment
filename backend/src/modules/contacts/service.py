import csv
import io
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...services.crm.base import BaseCRMClient, CRMSyncResult
from ...services.enrichment.waterfall import WaterfallEnrichmentService
from ...services.scoring.icp import ICPScoringService
from ..common.enums import FieldType
from ..common.exceptions import ResourceNotFoundError, ValidationError
from ..companies.service import CompanyService
from ..enrichment_jobs.schemas import EnrichmentJobRead
from .crud import crud_contacts
from .models import Contact
from .schemas import (
    ContactBulkImportResult,
    ContactEnrichResult,
    ContactImportError,
    ContactRead,
    ContactScoreResult,
    ICPCriterionScoreRead,
)

REQUIRED_CSV_COLUMNS = {"first_name", "last_name"}


class ContactService:
    """Bulk CSV import is intentionally row-tolerant: one malformed row
    shouldn't sink an otherwise-good batch of a few hundred leads, so
    per-row failures are collected and reported rather than aborting the
    whole import.
    """

    def __init__(self, company_service: CompanyService | None = None) -> None:
        self._company_service = company_service or CompanyService()

    async def bulk_create_from_csv(self, db: AsyncSession, csv_bytes: bytes) -> ContactBulkImportResult:
        try:
            text = csv_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValidationError(f"CSV must be UTF-8 encoded: {exc}") from exc

        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None or not REQUIRED_CSV_COLUMNS.issubset(set(reader.fieldnames)):
            raise ValidationError(f"CSV must include columns: {', '.join(sorted(REQUIRED_CSV_COLUMNS))}")

        created: list[Contact] = []
        errors: list[ContactImportError] = []

        # Row 1 is the header, so the first data row is row 2 — matches what a
        # caller sees if they open the file in a spreadsheet.
        for row_number, row in enumerate(reader, start=2):
            try:
                contact = await self._create_one(db, row)
                created.append(contact)
            except Exception as exc:
                errors.append(ContactImportError(row=row_number, error=str(exc)))

        return ContactBulkImportResult(
            created=len(created),
            failed=len(errors),
            errors=errors,
            contacts=[ContactRead.model_validate(c) for c in created],
        )

    async def _create_one(self, db: AsyncSession, row: dict[str, str | None]) -> Contact:
        first_name = (row.get("first_name") or "").strip()
        last_name = (row.get("last_name") or "").strip()
        if not first_name or not last_name:
            raise ValidationError("first_name and last_name are required")

        company_id = None
        domain = (row.get("company_domain") or "").strip()
        if domain:
            name = (row.get("company_name") or "").strip() or domain
            company = await self._company_service.get_or_create_by_domain(db, domain=domain, name=name)
            company_id = company["id"]

        contact = Contact(
            first_name=first_name,
            last_name=last_name,
            email=(row.get("email") or "").strip() or None,
            title=(row.get("title") or "").strip() or None,
            company_id=company_id,
        )
        db.add(contact)
        await db.commit()
        await db.refresh(contact)
        return contact

    async def get_by_id(self, db: AsyncSession, contact_id: int) -> dict[str, Any]:
        contact = await crud_contacts.get(db=db, id=contact_id, schema_to_select=ContactRead)
        if not contact:
            raise ResourceNotFoundError(f"Contact {contact_id} not found")
        return contact

    async def enrich(
        self, db: AsyncSession, contact_id: int, waterfall_service: WaterfallEnrichmentService
    ) -> ContactEnrichResult:
        """Runs the waterfall for every field type against one contact.

        Only EMAIL currently has a Contact column to write back onto, but PHONE
        and COMPANY attempts are still logged as EnrichmentJobs — see
        WaterfallEnrichmentService for why.
        """
        contact = await db.get(Contact, contact_id)
        if not contact:
            raise ResourceNotFoundError(f"Contact {contact_id} not found")

        jobs = []
        for field_type in (FieldType.EMAIL, FieldType.PHONE, FieldType.COMPANY):
            job = await waterfall_service.enrich_field(db, contact, field_type)
            if job is not None:
                jobs.append(job)

        await db.commit()
        await db.refresh(contact)

        return ContactEnrichResult(
            contact=ContactRead.model_validate(contact),
            jobs=[EnrichmentJobRead.model_validate(job) for job in jobs],
        )

    async def score(self, db: AsyncSession, contact_id: int, scoring_service: ICPScoringService) -> ContactScoreResult:
        """Scores one contact against the active ICPConfig and persists the result."""
        contact = await db.get(Contact, contact_id)
        if not contact:
            raise ResourceNotFoundError(f"Contact {contact_id} not found")

        config = await scoring_service.get_active_config(db)
        if config is None:
            raise ValidationError("No active ICPConfig found — seed one before scoring contacts")

        result = scoring_service.score(contact, config)
        contact.icp_score = result.score

        await db.commit()
        await db.refresh(contact)

        return ContactScoreResult(
            contact=ContactRead.model_validate(contact),
            breakdown=[
                ICPCriterionScoreRead(criterion=c.criterion, matched=c.matched, weight=c.weight) for c in result.breakdown
            ],
        )

    async def sync_to_crm(self, db: AsyncSession, contact_id: int, crm_client: BaseCRMClient) -> CRMSyncResult:
        """Pushes one contact into the CRM.

        Not wired to a route yet — this is the sync service itself, ready for a
        future step to gate it behind "qualified leads only" (e.g. icp_score
        above a threshold) and expose it as an endpoint.
        """
        contact = await db.get(Contact, contact_id)
        if not contact:
            raise ResourceNotFoundError(f"Contact {contact_id} not found")

        return await crm_client.push_contact(contact)
