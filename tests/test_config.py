"""
Tests for configuration, models, dual salaries, exclusions, and application script generation.
"""

from pathlib import Path
from src.core.config import load_candidate_profile, CONFIG_DIR
from src.core.models import CandidateProfile, PersonalInfo, CandidatePreferences
from src.cli import _save_application_artifacts

def test_load_candidate_profile():
    profile = load_candidate_profile()
    assert isinstance(profile, CandidateProfile)
    assert profile.personal_info.full_name != ""
    assert profile.personal_info.email != ""
    assert profile.effective_max_years == 6

def test_default_exclusions_are_empty():
    import importlib.util
    excl_example_path = CONFIG_DIR / "exclusions.example.py"
    spec = importlib.util.spec_from_file_location("exclusions_example", excl_example_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.EXCLUDED_COMPANIES == []
    assert mod.is_excluded_company("bairesdev") is False

def test_personal_info_properties():
    p = PersonalInfo(
        full_name="Matías Mieres",
        email="matias@example.com",
        phone="+598 99 123 456",
        location="Montevideo, Uruguay",
        linkedin_url="https://linkedin.com/in/matias",
        years_of_experience=6
    )
    assert p.first_name == "Matías"
    assert p.last_name == "Mieres"
    assert p.years_of_experience == 6

def test_dual_salary_preferences():
    prefs = CandidatePreferences(
        dependent_salary_usd=3000,
        contractor_salary_usd=4500,
        salary_period="monthly",
        notice_period="2 weeks"
    )
    # Default (not specified as contractor) -> dependent employee salary
    assert prefs.get_salary_value(is_contractor=False) == 3000
    assert prefs.get_formatted_salary(is_contractor=False) == "$3,000 USD / month"
    assert prefs.formatted_salary == "$3,000 USD / month"

    # Explicitly contractor -> contractor salary
    assert prefs.get_salary_value(is_contractor=True) == 4500
    assert prefs.get_formatted_salary(is_contractor=True) == "$4,500 USD / month"

def test_save_application_artifacts(tmp_path: Path):
    app_dir = tmp_path / "2026-10_Able_Senior_Software_Engineer"
    dummy_cv = app_dir / "CV_Able.pdf"
    app_dir.mkdir(parents=True, exist_ok=True)
    dummy_cv.write_bytes(b"%PDF-1.4 dummy")

    filled = {
        "First Name": "Matías",
        "Last Name": "Mieres",
        "Email": "matias@example.com",
        "Salary (Dependent Employee (Default))": "$3,000 USD / month",
    }
    url = "https://job-boards.greenhouse.io/able/jobs/8390834002"
    script_path = _save_application_artifacts(
        app_dir=app_dir,
        url=url,
        company="Able",
        role="Senior Software Engineer",
        cv_path=dummy_cv,
        filled_fields=filled,
    )
    assert script_path.exists()
    content = script_path.read_text(encoding="utf-8")
    assert url in content
    assert '"First Name": "Matías"' in content
    assert '"Last Name": "Mieres"' in content
    assert (app_dir / "application_info.json").exists()
