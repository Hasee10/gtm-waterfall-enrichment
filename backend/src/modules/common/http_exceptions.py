"""Shared HTTP exceptions.

Re-exports the FastCRUD HTTP exception set so the rest of the app has one
import site for API-layer errors. This previously lived under
``infrastructure/auth/`` but nothing here is auth-specific — the auth stack
was removed when this project was stripped down from the boilerplate.
"""

from fastapi.exceptions import HTTPException
from fastcrud.exceptions.http_exceptions import (
    BadRequestException,
    DuplicateValueException,
    ForbiddenException,
    NotFoundException,
    RateLimitException,
    UnauthorizedException,
    UnprocessableEntityException,
)

__all__ = [
    "BadRequestException",
    "NotFoundException",
    "ForbiddenException",
    "UnauthorizedException",
    "UnprocessableEntityException",
    "DuplicateValueException",
    "RateLimitException",
    "HTTPException",
]
