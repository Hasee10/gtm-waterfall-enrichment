"""ICP (Ideal Customer Profile) scoring.

Weights and thresholds come from ICPConfig (DB-backed), not hardcoded Python
constants — same reasoning as WaterfallConfig: tightening or loosening the ICP
definition should be a data change, not a deploy. The score is normalized to
0-100 over only the criteria that are actually configured, so a config that
only sets two of the four criteria isn't penalized on the other two.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...modules.contacts.models import Contact
from ...modules.icp_config.models import ICPConfig


@dataclass
class ICPCriterionResult:
    criterion: str
    matched: bool
    weight: float


@dataclass
class ICPScoreResult:
    score: float
    breakdown: list[ICPCriterionResult] = field(default_factory=list)


def _split_csv_lower(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip().lower() for v in value.split(",") if v.strip()]


class ICPScoringService:
    """Scores one contact against the currently active ICPConfig."""

    async def get_active_config(self, db: AsyncSession) -> ICPConfig | None:
        """The first enabled config, by id. Supporting multiple named ICP
        profiles at once is out of scope for now — one active profile at a
        time, same as how WaterfallConfig is queried per field_type."""
        result = await db.execute(select(ICPConfig).where(ICPConfig.enabled.is_(True)).order_by(ICPConfig.id))
        return result.scalars().first()

    def score(self, contact: Contact, config: ICPConfig) -> ICPScoreResult:
        breakdown: list[ICPCriterionResult] = []

        self._score_industry(contact, config, breakdown)
        self._score_employee_count(contact, config, breakdown)
        self._score_revenue_range(contact, config, breakdown)
        self._score_title(contact, config, breakdown)

        possible = sum(c.weight for c in breakdown)
        earned = sum(c.weight for c in breakdown if c.matched)
        normalized_score = round((earned / possible) * 100, 2) if possible > 0 else 0.0

        return ICPScoreResult(score=normalized_score, breakdown=breakdown)

    def _score_industry(self, contact: Contact, config: ICPConfig, breakdown: list[ICPCriterionResult]) -> None:
        targets = _split_csv_lower(config.target_industries)
        if not targets:
            return
        industry = (contact.company.industry or "").strip().lower() if contact.company else ""
        breakdown.append(ICPCriterionResult(criterion="industry", matched=industry in targets, weight=config.industry_weight))

    def _score_employee_count(self, contact: Contact, config: ICPConfig, breakdown: list[ICPCriterionResult]) -> None:
        if config.employee_count_min is None and config.employee_count_max is None:
            return
        count = contact.company.employee_count if contact.company else None
        lower = config.employee_count_min if config.employee_count_min is not None else float("-inf")
        upper = config.employee_count_max if config.employee_count_max is not None else float("inf")
        matched = count is not None and lower <= count <= upper
        breakdown.append(ICPCriterionResult(criterion="employee_count", matched=matched, weight=config.employee_count_weight))

    def _score_revenue_range(self, contact: Contact, config: ICPConfig, breakdown: list[ICPCriterionResult]) -> None:
        targets = _split_csv_lower(config.target_revenue_ranges)
        if not targets:
            return
        revenue = (contact.company.revenue_range or "").strip().lower() if contact.company else ""
        breakdown.append(
            ICPCriterionResult(criterion="revenue_range", matched=revenue in targets, weight=config.revenue_range_weight)
        )

    def _score_title(self, contact: Contact, config: ICPConfig, breakdown: list[ICPCriterionResult]) -> None:
        keywords = _split_csv_lower(config.title_keywords)
        if not keywords:
            return
        title = (contact.title or "").lower()
        matched = any(keyword in title for keyword in keywords)
        breakdown.append(ICPCriterionResult(criterion="title", matched=matched, weight=config.title_weight))
