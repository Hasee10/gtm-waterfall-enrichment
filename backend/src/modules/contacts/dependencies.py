from typing import Annotated

from fastapi import Depends

from ...services.enrichment.waterfall import WaterfallEnrichmentService
from .service import ContactService


def get_contact_service() -> ContactService:
    return ContactService()


def get_waterfall_service() -> WaterfallEnrichmentService:
    return WaterfallEnrichmentService()


ContactServiceDep = Annotated[ContactService, Depends(get_contact_service)]
WaterfallServiceDep = Annotated[WaterfallEnrichmentService, Depends(get_waterfall_service)]
