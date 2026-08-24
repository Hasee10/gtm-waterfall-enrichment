from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...infrastructure.database.models import TimestampMixin
from ...infrastructure.database.session import Base

if TYPE_CHECKING:
    from ..contacts.models import Contact


class Company(Base, TimestampMixin):
    """A target company. Enrichment waterfalls fill in industry/size/revenue so
    ICP scoring has something to weigh a contact's employer against.
    """

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(
        "id",
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )

    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    industry: Mapped[str | None] = mapped_column(String(100), default=None)
    employee_count: Mapped[int | None] = mapped_column(Integer, default=None)
    revenue_range: Mapped[str | None] = mapped_column(String(50), default=None)

    contacts: Mapped[list["Contact"]] = relationship(
        "Contact", back_populates="company", lazy="selectin", default_factory=list, init=False
    )

    def __repr__(self) -> str:
        return f"{self.name} ({self.domain})"
