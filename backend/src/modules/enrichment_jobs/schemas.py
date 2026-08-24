from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ..common.enums import FieldType
from .enums import JobStatus


class EnrichmentJobRead(BaseModel):
    """One logged waterfall attempt, returned to the caller after an enrich run."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    contact_id: int
    field_type: FieldType
    provider_name: str
    status: JobStatus
    credits_used: float
    result_json: dict | None = None
    attempted_at: datetime
