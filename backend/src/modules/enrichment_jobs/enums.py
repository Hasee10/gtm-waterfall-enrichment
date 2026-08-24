"""Enrichment job-specific enums."""

from enum import StrEnum


class JobStatus(StrEnum):
    """Outcome of a single waterfall attempt against one provider."""

    SUCCESS = "success"
    FAIL = "fail"
