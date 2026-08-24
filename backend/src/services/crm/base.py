"""Shared interface for CRM sync clients.

Mirrors the enrichment provider pattern (BaseProvider/ProviderResult): one
shared interface so a caller doesn't need to know which CRM it's pushing to,
and adding a second CRM target later doesn't touch the calling code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from ...modules.contacts.models import Contact


@dataclass
class CRMSyncResult:
    """The outcome of pushing one contact into a CRM."""

    success: bool
    external_id: str | None = None
    error: str | None = None


class BaseCRMClient(ABC):
    """Base class every CRM sync client implements."""

    name: ClassVar[str]

    @property
    @abstractmethod
    def is_mock(self) -> bool:
        """Whether this client is running without a live API token."""
        raise NotImplementedError

    @abstractmethod
    async def push_contact(self, contact: Contact) -> CRMSyncResult:
        """Create or update this contact in the CRM."""
        raise NotImplementedError
