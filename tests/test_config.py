"""
Tests for configuration, models, dual salaries, exclusions, and application script generation.
"""

from pathlib import Path
from src.core.config import load_candidate_profile, CONFIG_DIR
from src.core.models import CandidateProfile, PersonalInfo, CandidatePreferences
from src.cli import _save_application_artifacts

def test_load_candidate_profile(monkeypatch):
    monkeypatch.setenv("JOBHUNTER_PROFILE", str(CONFIG_DIR / "profile.example.json"))
    profile = load_candidate_profile()
    assert isinstance(profile, CandidateProfile)
    assert profile.personal_info.full_name == ""
    assert profile.personal_info.email == ""
    assert profile.effective_max_years is None

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
        full_name="Alex Mercer",
        email="alex.mercer@example.com",
        phone="+598 99 123 456",
        location="Montevideo, Uruguay",
        linkedin_url="https://linkedin.com/in/alexmercer-dev",
        years_of_experience=6
    )
    assert p.first_name == "Alex"
    assert p.last_name == "Mercer"
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
        "First Name": "Alex",
        "Last Name": "Mercer",
        "Email": "alex.mercer@example.com",
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
    assert '"First Name": "Alex"' in content
    assert '"Last Name": "Mercer"' in content
    assert (app_dir / "application_info.json").exists()

def test_cv_role_and_filename_normalization():
    from src.cv.builder import normalize_cv_role_title, build_cv_filename

    assert normalize_cv_role_title("Lead QA Automation Engineer") == "QA Automation Engineer"
    assert normalize_cv_role_title("Senior SDET") == "QA Automation Engineer"
    assert normalize_cv_role_title("Lead QA Engineer") == "QA Engineer"
    assert normalize_cv_role_title("Senior QA Engineer") == "QA Engineer"
    assert normalize_cv_role_title("Lead Backend Engineer") == "Backend Engineer"
    assert normalize_cv_role_title("Principal Full Stack Engineer") == "Full Stack Engineer"
    assert normalize_cv_role_title("Lead DevOps Engineer", preferred_role="DevOps Engineer") == "DevOps Engineer"

    assert (
        build_cv_filename("Alex Mercer", "Lead QA Automation Engineer", "Stack AI")
        == "Alex_Mercer_QA_Automation_Engineer_Stack_AI.pdf"
    )
    assert (
        build_cv_filename("Jane Doe", "Lead QA Engineer", "Acme Corp")
        == "Jane_Doe_QA_Engineer_Acme_Corp.pdf"
    )
    assert (
        build_cv_filename("Alex Mercer", "Backend Engineer", "Stripe")
        == "Alex_Mercer_Backend_Engineer_Stripe.pdf"
    )

