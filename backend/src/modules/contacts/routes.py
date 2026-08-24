from fastapi import APIRouter, File, HTTPException, UploadFile

from ...infrastructure.dependencies import AsyncSessionDep
from ..common.utils.error_handler import handle_exception
from .dependencies import ContactServiceDep, WaterfallServiceDep
from .schemas import ContactBulkImportResult, ContactEnrichResult, ContactRead

router = APIRouter(tags=["Contacts"])


@router.post("/bulk", response_model=ContactBulkImportResult, summary="Bulk import contacts from a CSV file")
async def bulk_import_contacts(
    db: AsyncSessionDep,
    contact_service: ContactServiceDep,
    file: UploadFile = File(..., description="CSV with first_name,last_name,email,title,company_domain,company_name columns"),
) -> ContactBulkImportResult:
    try:
        content = await file.read()
        return await contact_service.bulk_create_from_csv(db, content)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.get("/{contact_id}", response_model=ContactRead, summary="Get a contact by ID")
async def get_contact(
    contact_id: int,
    db: AsyncSessionDep,
    contact_service: ContactServiceDep,
) -> dict:
    try:
        return await contact_service.get_by_id(db, contact_id)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.post("/{contact_id}/enrich", response_model=ContactEnrichResult, summary="Run the waterfall for a contact")
async def enrich_contact(
    contact_id: int,
    db: AsyncSessionDep,
    contact_service: ContactServiceDep,
    waterfall_service: WaterfallServiceDep,
) -> ContactEnrichResult:
    try:
        return await contact_service.enrich(db, contact_id, waterfall_service)
    except Exception as e:
        http_exception = handle_exception(e)
        if http_exception:
            raise http_exception
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
