from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...infrastructure.database.models import TimestampMixin
from ...infrastructure.database.session import Base
from .enums import EnrichmentStatus

if TYPE_CHECKING:
    from ..companies.models import Company
    from ..enrichment_jobs.models import EnrichmentJob


class Contact(Base, TimestampMixin):
    """A raw contact, enriched via the waterfall and scored against the ICP."""

    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(
        "id",
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), index=True, default=None)
    title: Mapped[str | None] = mapped_column(String(150), default=None)

    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id"),
        index=True,
        default=None,
    )

    # native_enum=False stores this as a plain VARCHAR + CHECK constraint instead of
    # a native Postgres enum type, so adding a new status later is a column-level
    # migration rather than an ALTER TYPE.
    enrichment_status: Mapped[EnrichmentStatus] = mapped_column(
        SQLEnum(EnrichmentStatus, native_enum=False, length=20),
        default=EnrichmentStatus.PENDING,
    )
    icp_score: Mapped[float | None] = mapped_column(Float, default=None)

    company: Mapped["Company | None"] = relationship("Company", back_populates="contacts", lazy="selectin", init=False)
    enrichment_jobs: Mapped[list["EnrichmentJob"]] = relationship(
        "EnrichmentJob", back_populates="contact", lazy="selectin", default_factory=list, init=False
    )

    def __repr__(self) -> str:
        return f"{self.first_name} {self.last_name} <{self.email}>"
