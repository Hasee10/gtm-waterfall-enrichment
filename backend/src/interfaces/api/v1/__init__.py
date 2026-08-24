from fastapi import APIRouter

from ....modules.contacts.routes import router as contacts_router

router = APIRouter(prefix="/v1")
router.include_router(contacts_router, prefix="/contacts")

# Scoring and CRM sync routers get mounted here in later build steps.
