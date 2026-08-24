from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ...infrastructure.database.session import Base
from ..common.enums import FieldType


class WaterfallConfig(Base):
    """Defines, per field, which providers to try and in what order.

    This is what makes the waterfall configurable without a code change: to
    reorder providers or turn one off, update a row here rather than the
    enrichment service. priority_order is ascending — 1 is tried first.
    """

    __tablename__ = "waterfall_configs"
    __table_args__ = (UniqueConstraint("field_type", "provider_name", name="uq_waterfall_config_field_provider"),)

    id: Mapped[int] = mapped_column(
        "id",
        autoincrement=True,
        nullable=False,
        unique=True,
        primary_key=True,
        init=False,
    )

    field_type: Mapped[FieldType] = mapped_column(SQLEnum(FieldType, native_enum=False, length=20), index=True)
    provider_name: Mapped[str] = mapped_column(String(100))
    priority_order: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(default=True)

    def __repr__(self) -> str:
        return f"{self.field_type}[{self.priority_order}] {self.provider_name}"
