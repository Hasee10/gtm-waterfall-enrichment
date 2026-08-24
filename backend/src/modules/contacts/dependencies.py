from typing import Annotated

from fastapi import Depends

from ...services.enrichment.waterfall import WaterfallEnrichmentService
from ...services.scoring.icp import ICPScoringService
from .service import ContactService


def get_contact_service() -> ContactService:
    return ContactService()


def get_waterfall_service() -> WaterfallEnrichmentService:
    return WaterfallEnrichmentService()


def get_icp_scoring_service() -> ICPScoringService:
    return ICPScoringService()


ContactServiceDep = Annotated[ContactService, Depends(get_contact_service)]
WaterfallServiceDep = Annotated[WaterfallEnrichmentService, Depends(get_waterfall_service)]
ICPScoringServiceDep = Annotated[ICPScoringService, Depends(get_icp_scoring_service)]
