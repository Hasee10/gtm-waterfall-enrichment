from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ...infrastructure.database.session import Base


class ICPConfig(Base):
    """Configurable ICP (Ideal Customer Profile) scoring weights.

    Each criterion is optional — None/empty means "not configured," and the
    scoring service skips it entirely rather than counting it as a miss, so an
    incomplete profile doesn't drag every contact's score toward zero. Weights
    are config-driven (this table), not hardcoded in Python, same reasoning as
    WaterfallConfig: tightening or loosening the ICP definition is a DB update,
    not a deploy. There is no CRUD endpoint for this yet — like
    WaterfallConfig, it's seeded directly for now.
    """

    __tablename__ = "icp_configs"

    id: Mapped[int] = mapped_column(
        "id",
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )

    enabled: Mapped[bool] = mapped_column(default=True)

    # Comma-separated, case-insensitive match against Company.industry.
    target_industries: Mapped[str | None] = mapped_column(String(500), default=None)
    industry_weight: Mapped[float] = mapped_column(Float, default=25.0)

    # Inclusive range match against Company.employee_count.
    employee_count_min: Mapped[int | None] = mapped_column(Integer, default=None)
    employee_count_max: Mapped[int | None] = mapped_column(Integer, default=None)
    employee_count_weight: Mapped[float] = mapped_column(Float, default=25.0)

    # Comma-separated, case-insensitive match against Company.revenue_range.
    target_revenue_ranges: Mapped[str | None] = mapped_column(String(500), default=None)
    revenue_range_weight: Mapped[float] = mapped_column(Float, default=25.0)

    # Comma-separated seniority keywords, matched as a substring of Contact.title.
    title_keywords: Mapped[str | None] = mapped_column(String(500), default=None)
    title_weight: Mapped[float] = mapped_column(Float, default=25.0)

    def __repr__(self) -> str:
        return f"ICPConfig(id={self.id}, enabled={self.enabled})"
