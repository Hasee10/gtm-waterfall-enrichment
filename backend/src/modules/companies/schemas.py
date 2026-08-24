from typing import Annotated

from pydantic import BaseModel, Field

from ..common.schemas import TimestampSchema


class CompanyBase(BaseModel):
    """Base company schema with common attributes."""

    domain: Annotated[str, Field(description="Company website domain, used as the de-dup key", examples=["acme.com"])]
    name: Annotated[str, Field(description="Company name", examples=["Acme Inc"])]


class CompanyRead(TimestampSchema, CompanyBase):
    """Schema for reading company data."""

    id: int
    industry: str | None = None
    employee_count: int | None = None
    revenue_range: str | None = None


class CompanyCreate(CompanyBase):
    """Schema for creating a new company."""

    pass
