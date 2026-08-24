"""Tests for ICPScoringService."""

import pytest

from src.modules.companies.models import Company
from src.modules.contacts.models import Contact
from src.modules.icp_config.models import ICPConfig
from src.services.scoring.icp import ICPScoringService


def _config(**overrides) -> ICPConfig:
    defaults = dict(
        target_industries=None,
        industry_weight=25.0,
        employee_count_min=None,
        employee_count_max=None,
        employee_count_weight=25.0,
        target_revenue_ranges=None,
        revenue_range_weight=25.0,
        title_keywords=None,
        title_weight=25.0,
    )
    defaults.update(overrides)
    return ICPConfig(**defaults)


def _contact(title=None, company=None) -> Contact:
    contact = Contact(first_name="Jane", last_name="Doe", title=title)
    contact.company = company
    return contact


def test_all_criteria_match_scores_100():
    company = Company(domain="acme.com", name="Acme", industry="Software", employee_count=50, revenue_range="$1M-$10M")
    contact = _contact(title="VP of Sales", company=company)
    config = _config(
        target_industries="Software",
        employee_count_min=10,
        employee_count_max=200,
        target_revenue_ranges="$1M-$10M",
        title_keywords="VP,Director",
    )

    result = ICPScoringService().score(contact, config)

    assert result.score == 100.0
    assert all(c.matched for c in result.breakdown)
    assert len(result.breakdown) == 4


def test_no_criteria_configured_scores_zero_with_empty_breakdown():
    contact = _contact()
    config = _config()

    result = ICPScoringService().score(contact, config)

    assert result.score == 0.0
    assert result.breakdown == []


def test_partial_match_scores_proportionally():
    company = Company(domain="acme.com", name="Acme", industry="Retail", employee_count=50, revenue_range=None)
    contact = _contact(title="VP of Sales", company=company)
    config = _config(
        target_industries="Software",  # miss
        employee_count_min=10,
        employee_count_max=200,  # hit
        title_keywords="VP",  # hit
    )

    result = ICPScoringService().score(contact, config)

    # 2 of 3 configured criteria hit -> 200/300 * 100
    assert result.score == pytest.approx(66.67, abs=0.01)
    matched_criteria = {c.criterion for c in result.breakdown if c.matched}
    assert matched_criteria == {"employee_count", "title"}


def test_unconfigured_criterion_is_excluded_not_penalized():
    """revenue_range isn't set on the config, so it shouldn't drag the score
    down even though the contact's company has no revenue_range value either."""
    company = Company(domain="acme.com", name="Acme", industry="Software", employee_count=None, revenue_range=None)
    contact = _contact(title="VP", company=company)
    config = _config(target_industries="Software", title_keywords="VP")

    result = ICPScoringService().score(contact, config)

    assert result.score == 100.0
    assert len(result.breakdown) == 2


def test_contact_with_no_company_fails_company_criteria():
    contact = _contact(title="VP", company=None)
    config = _config(target_industries="Software", title_keywords="VP")

    result = ICPScoringService().score(contact, config)

    industry_result = next(c for c in result.breakdown if c.criterion == "industry")
    assert industry_result.matched is False


def test_employee_count_open_ended_range():
    """Only a min is configured — no max means no upper bound."""
    company = Company(domain="acme.com", name="Acme", employee_count=10_000)
    contact = _contact(company=company)
    config = _config(employee_count_min=100)

    result = ICPScoringService().score(contact, config)

    assert result.breakdown[0].matched is True


def test_title_keyword_match_is_case_insensitive_substring():
    contact = _contact(title="Head of Growth")
    config = _config(title_keywords="head,director")

    result = ICPScoringService().score(contact, config)

    assert result.breakdown[0].matched is True
