"""Shared interface for waterfall enrichment providers.

Every provider (Hunter, Apollo, ...) implements this same interface, so the
waterfall service can try them interchangeably in priority order without
knowing anything provider-specific. Adding a new provider later means adding a
new class here and a WaterfallConfig row — the waterfall logic itself never
changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from ...modules.common.enums import FieldType
from ...modules.contacts.models import Contact


@dataclass
class ProviderResult:
    """The outcome of one provider call for one contact field.

    credits_used tracks cost regardless of outcome — a miss still consumes
    provider quota on most free tiers, and this is what lets the waterfall
    report cost-per-field later instead of just success/fail counts.
    """

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    credits_used: float = 0.0
    error: str | None = None


class BaseProvider(ABC):
    """Base class every enrichment provider client implements."""

    name: ClassVar[str]
    supported_fields: ClassVar[set[FieldType]]

    @property
    @abstractmethod
    def is_mock(self) -> bool:
        """Whether this client is running without a live API key."""
        raise NotImplementedError

    @abstractmethod
    async def enrich(self, field_type: FieldType, contact: Contact) -> ProviderResult:
        """Attempt to fill one field for one contact."""
        raise NotImplementedError

    def _unsupported_field_result(self, field_type: FieldType) -> ProviderResult:
        return ProviderResult(success=False, error=f"{self.name} does not support field_type={field_type}")
