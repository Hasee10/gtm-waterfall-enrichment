from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...infrastructure.database.session import Base
from ..common.enums import FieldType
from .enums import JobStatus

if TYPE_CHECKING:
    from ..contacts.models import Contact


class EnrichmentJob(Base):
    """One attempt to fill a single contact field via a single provider.

    This is the audit trail the waterfall runs on: every attempt is logged here
    (which provider, whether it hit, what it cost) regardless of whether it
    succeeded, so cost-per-field and provider hit-rate can be reported on later.
    """

    __tablename__ = "enrichment_jobs"

    id: Mapped[int] = mapped_column(
        "id",
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )

    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), index=True)
    field_type: Mapped[FieldType] = mapped_column(SQLEnum(FieldType, native_enum=False, length=20))
    provider_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[JobStatus] = mapped_column(SQLEnum(JobStatus, native_enum=False, length=10))

    # Float, not int: providers bill in fractional units (e.g. $0.01/lookup), and
    # this is meant to answer "what did this contact cost to enrich", not just
    # "how many discrete credits were spent".
    credits_used: Mapped[float] = mapped_column(Float, default=0.0)
    result_json: Mapped[dict | None] = mapped_column(JSON, default=None)

    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
        init=False,
    )

    contact: Mapped["Contact"] = relationship("Contact", back_populates="enrichment_jobs", lazy="selectin", init=False)

    def __repr__(self) -> str:
        return f"{self.field_type}/{self.provider_name} -> {self.status}"
