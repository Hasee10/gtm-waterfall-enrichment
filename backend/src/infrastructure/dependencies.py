from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .database.session import async_session

# Database. This API is intentionally fully open (no auth) for now — it is a
# self-hosted single-operator enrichment service, so there are no user-scoped
# dependencies here.
AsyncSessionDep = Annotated[AsyncSession, Depends(async_session)]
