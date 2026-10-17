"""
Tests for configuration and models.
"""

from src.core.config import load_candidate_profile
from src.core.models import CandidateProfile, PersonalInfo

def test_load_candidate_profile():
    profile = load_candidate_profile()
    assert isinstance(profile, CandidateProfile)
    assert profile.personal_info.full_name != ""
    assert profile.personal_info.email != ""

def test_personal_info_properties():
    p = PersonalInfo(
        full_name="Alex Mercer",
        email="alex@example.com",
        phone="+1 555 1234",
        location="Montevideo, Uruguay",
        linkedin_url="https://linkedin.com/in/alex"
    )
    assert p.first_name == "Alex"
    assert p.last_name == "Mercer"

def test_candidate_preferences():
    from src.core.models import CandidatePreferences
    prefs = CandidatePreferences(
        desired_salary_usd=3500,
        salary_period="monthly",
        notice_period="2 weeks"
    )
    assert prefs.formatted_salary == "$3,500 USD / month"
    assert prefs.notice_period == "2 weeks"
