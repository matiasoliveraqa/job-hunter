import pytest
from unittest.mock import AsyncMock, MagicMock
from src.core.models import CandidateProfile, PersonalInfo, SearchCriteria, CandidatePreferences, OpenQuestionTemplates
from src.automation.applicators.base import BaseApplicator

class DummyApplicator(BaseApplicator):
    async def fill_form(self, cv_pdf_path=None):
        return True

@pytest.fixture
def dummy_profile():
    return CandidateProfile(
        personal_info=PersonalInfo(
            full_name="Alex Mercer",
            email="alex.mercer@example.com",
            phone="+598 99 123 456",
            location="Montevideo, Uruguay",
            years_of_experience=7,
            current_company="Acme Corp",
            linkedin_url="https://www.linkedin.com/in/alex-mercer-qa/",
            github_url="https://github.com/alex-mercer",
            portfolio_url="https://alex-mercer.dev",
        ),
        search_criteria=SearchCriteria(roles=["QA Engineer"]),
        preferences=CandidatePreferences(
            dependent_salary_usd=3500,
            contractor_salary_usd=4500,
            desired_salary_usd=3000,
            salary_period="monthly",
            notice_period="2 weeks",
            english_level="B2 Upper Intermediate",
        ),
        open_questions=OpenQuestionTemplates(
            motivation="Default motivation text",
            experience_summary="Default experience text",
            education_level="Bachelor in IT",
            timezone_overlap="UTC-3",
        )
    )

@pytest.mark.asyncio
async def test_salary_higher_than_preference_annual(dummy_profile):
    page = MagicMock()
    page.inner_text = AsyncMock(return_value="The compensation range is $120,000 - $140,000 / year USD.")
    app = DummyApplicator(page, dummy_profile, company="Acme", role="QA Engineer")

    num, s_str, label = await app.get_effective_salary(is_contractor=False)
    assert num == 140000
    assert "/ year" in s_str
    assert "Ajustado al maximo" in label

@pytest.mark.asyncio
async def test_salary_higher_than_preference_monthly(dummy_profile):
    page = MagicMock()
    page.inner_text = AsyncMock(return_value="We offer $4,000 to $6,000 per month for this role.")
    app = DummyApplicator(page, dummy_profile, company="Acme", role="QA Engineer")

    num, s_str, label = await app.get_effective_salary(is_contractor=False)
    assert num == 6000
    assert "$6,000 USD / month" == s_str
    assert "Ajustado al maximo" in label

@pytest.mark.asyncio
async def test_salary_higher_than_preference_hourly(dummy_profile):
    page = MagicMock()
    page.inner_text = AsyncMock(return_value="Hourly rate between $45 - $60 / hour.")
    app = DummyApplicator(page, dummy_profile, company="Acme", role="QA Engineer")

    num, s_str, label = await app.get_effective_salary(is_contractor=False)
    assert num == 60
    assert "$60 USD / hour" == s_str
    assert "Ajustado al maximo" in label

@pytest.mark.asyncio
async def test_salary_lower_than_preference_ignored(dummy_profile):
    page = MagicMock()
    # 2,000/mo is lower than candidate's 3,500/mo preference
    page.inner_text = AsyncMock(return_value="Offering $1,500 - $2,000 / month.")
    app = DummyApplicator(page, dummy_profile, company="Acme", role="QA Engineer")

    num, s_str, label = await app.get_effective_salary(is_contractor=False)
    # Ignored posted salary, keeps preference
    assert num == 3500
    assert "$3,500 USD / month" == s_str
    assert "Ajustado" not in label

def test_deterministic_vs_open_questions(dummy_profile):
    page = MagicMock()
    app = DummyApplicator(page, dummy_profile, company="Hone", role="Quality Engineer II")

    # Factual fields
    assert app._generate_deterministic_answer("LinkedIn profile") == "https://www.linkedin.com/in/alex-mercer-qa/"
    assert app._generate_deterministic_answer("How many years of experience?") == "7"
    assert app._generate_deterministic_answer("Notice period") == "2 weeks"
    assert app._generate_deterministic_answer("Level of education") == "Bachelor in IT"

    # Open-ended questions should NOT be captured by deterministic generator
    assert app._generate_deterministic_answer("Why Hone? Tell us what you know about us") is None
    assert app._generate_deterministic_answer("Why this role? Describe why you fit") is None

    # Fallback differentiates company vs role
    company_ans = app._generate_open_question_answer("Why Hone? Tell us what you know about what we do")
    role_ans = app._generate_open_question_answer("Why this role? Tell us why you are a fit")
    assert company_ans != role_ans
    assert "Hone" in company_ans

def test_parse_phone_info(dummy_profile):
    page = MagicMock()
    app = DummyApplicator(page, dummy_profile)
    info = app._parse_phone_info()
    assert info["country"] == "Uruguay"
    assert info["dial_code"] == "+598"
    assert info["code_digits"] == "598"
    assert info["iso2"] == "UY"
    assert info["national_number"] == "99123456"

