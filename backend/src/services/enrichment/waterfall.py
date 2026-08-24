"""The waterfall enrichment service.

For one contact field, this tries each enabled provider in WaterfallConfig's
priority order until one succeeds — that's the "waterfall": cheap/free
providers first, more expensive ones only as fallback. Every attempt (hit or
miss) is logged as an EnrichmentJob, which is what makes cost-per-field and
provider hit-rate reportable later instead of just a final pass/fail.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...modules.common.enums import FieldType
from ...modules.contacts.enums import EnrichmentStatus
from ...modules.contacts.models import Contact
from ...modules.enrichment_jobs.enums import JobStatus
from ...modules.enrichment_jobs.models import EnrichmentJob
from ...modules.waterfall_config.models import WaterfallConfig
from ..providers.registry import get_provider


class WaterfallEnrichmentService:
    """Runs the provider waterfall for a single contact field."""

    async def enrich_field(self, db: AsyncSession, contact: Contact, field_type: FieldType) -> EnrichmentJob | None:
        """Try enabled providers for field_type in priority order.

        Returns the EnrichmentJob for whichever attempt was last made (a success,
        or the final miss if every provider failed). Does not commit — the caller
        owns the transaction boundary, same as everywhere else in this codebase.
        """
        result = await db.execute(
            select(WaterfallConfig)
            .where(WaterfallConfig.field_type == field_type, WaterfallConfig.enabled.is_(True))
            .order_by(WaterfallConfig.priority_order)
        )
        configs = result.scalars().all()

        last_job: EnrichmentJob | None = None
        for config in configs:
            provider = get_provider(config.provider_name)
            outcome = await provider.enrich(field_type, contact)

            job = EnrichmentJob(
                contact_id=contact.id,
                field_type=field_type,
                provider_name=config.provider_name,
                status=JobStatus.SUCCESS if outcome.success else JobStatus.FAIL,
                credits_used=outcome.credits_used,
                result_json=outcome.data if outcome.success else {"error": outcome.error},
            )
            db.add(job)
            last_job = job

            if outcome.success:
                self._apply_result(contact, field_type, outcome.data)
                return job

        # Every provider missed. Only EMAIL currently drives Contact.enrichment_status —
        # the data model has no phone column and company fields live on Company, not
        # Contact, so a phone/company miss has nothing on Contact to mark as failed.
        if field_type == FieldType.EMAIL:
            contact.enrichment_status = EnrichmentStatus.FAILED

        return last_job

    def _apply_result(self, contact: Contact, field_type: FieldType, data: dict) -> None:
        """Write a successful provider result onto the contact it was found for."""
        if field_type == FieldType.EMAIL and data.get("email"):
            contact.email = data["email"]
            contact.enrichment_status = EnrichmentStatus.ENRICHED
        # Phone and company results are logged on the EnrichmentJob but have no
        # matching Contact column yet, so there's nothing further to reconcile.
