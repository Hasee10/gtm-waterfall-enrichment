from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from ..common.schemas import TimestampSchema
from ..enrichment_jobs.schemas import EnrichmentJobRead
from .enums import EnrichmentStatus


class ContactBase(BaseModel):
    """Base contact schema with common attributes."""

    first_name: Annotated[str, Field(min_length=1, max_length=100, examples=["Jane"])]
    last_name: Annotated[str, Field(min_length=1, max_length=100, examples=["Doe"])]
    email: str | None = None
    title: str | None = None


class ContactRead(TimestampSchema, ContactBase):
    """Schema for reading contact data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int | None = None
    enrichment_status: EnrichmentStatus
    icp_score: float | None = None


class ContactCreate(ContactBase):
    """One row of a bulk CSV import. company_domain resolves (or creates) the
    Company this contact belongs to; company_name is only used the first time
    a domain is seen.
    """

    company_domain: str | None = None
    company_name: str | None = None


class ContactImportError(BaseModel):
    """A single CSV row that failed to import, with its 1-based row number
    (header counts as row 1) so a caller can find and fix it in their sheet.
    """

    row: int
    error: str


class ContactBulkImportResult(BaseModel):
    """Bulk import is row-tolerant: a bad row is reported here, not a reason to
    reject the whole file.
    """

    created: int
    failed: int
    errors: list[ContactImportError]
    contacts: list[ContactRead]


class ContactEnrichResult(BaseModel):
    """The contact after a waterfall run, plus every provider attempt it took."""

    contact: ContactRead
    jobs: list[EnrichmentJobRead]
