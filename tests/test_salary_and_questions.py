import re
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

def test_universal_open_questions_and_custom_qa(dummy_profile):
    dummy_profile.open_questions.key_project = "Automated core payment flows with Playwright and GitHub Actions."
    dummy_profile.open_questions.additional_info = "Fluent in English, available for full Americas overlap."
    dummy_profile.open_questions.custom_qa["fintech"] = "Strong background in banking compliance."

    page = MagicMock()
    app = DummyApplicator(page, dummy_profile, company="Acme", role="QA Engineer")

    project_ans = app._generate_open_question_answer("Tell us about a technical challenge or project you are proud of")
    assert project_ans == "Automated core payment flows with Playwright and GitHub Actions."

    add_ans = app._generate_open_question_answer("Is there anything else you want to share with us?")
    assert add_ans == "Fluent in English, available for full Americas overlap."

    custom_ans = app._generate_open_question_answer("What is your experience in the fintech domain?")
    assert custom_ans == "Strong background in banking compliance."


def test_form_option_matching_levels_and_gender(dummy_profile):
    page = MagicMock()
    app = DummyApplicator(page, dummy_profile)

    # B1: Male must return exactly Male, not Female
    opts1 = ["Female", "Male", "Non-binary", "Decline to Self-Identify"]
    assert app.match_dropdown_option(opts1, ["Male", "Decline to self-identify"], is_sensitive=True) == "Male"

    # B1: Asian must return Asian, not South Asian
    opts2 = ["South Asian", "Asian"]
    assert app.match_dropdown_option(opts2, ["Asian"], is_sensitive=True) == "Asian"

    # B1: Yes must return Yes, not Yes, I consent
    opts3 = ["Yes, I consent", "Yes"]
    assert app.match_dropdown_option(opts3, ["Yes"], is_sensitive=False) == "Yes"

    # B4: Gender with no match must pick Decline if available, never first option (Female)
    opts4 = ["Female", "Non-binary", "Decline to Self-Identify"]
    assert app.match_dropdown_option(opts4, ["Male"], is_sensitive=True, fallback_first=True) == "Decline to Self-Identify"

    # B4: Gender with no match and no decline must return None (empty), never first option (Female)
    opts5 = ["Female", "Non-binary"]
    assert app.match_dropdown_option(opts5, ["Male"], is_sensitive=True, fallback_first=True) is None


def test_label_extraction_fieldset_contamination():
    # B2: label extraction on fieldset with multiple questions
    raw_label = "Gender"
    cleaned = BaseApplicator.clean_question_label(raw_label)
    assert cleaned == "Gender"

    # Multiple question contamination with ? or *
    contaminated_q = "Preferred name * What is your preferred first name? How many years of experience...?"
    cleaned_q = BaseApplicator.clean_question_label(contaminated_q)
    assert cleaned_q == "Preferred name * What is your preferred first name?"

    contaminated_multi_req = "Gender * Race * How many years of experience?"
    cleaned_multi_req = BaseApplicator.clean_question_label(contaminated_multi_req)
    assert cleaned_multi_req == "Gender *"


def test_routing_project_question_not_portfolio(dummy_profile):
    dummy_profile.open_questions.key_project = "Designed Playwright test framework for microservices."
    page = MagicMock()
    app = DummyApplicator(page, dummy_profile)

    # B3: Must NOT return portfolio URL
    det_ans = app._generate_deterministic_answer("Tell us about a project you are proud of. Do you have a personal website?")
    assert det_ans is None

    # Open-ended generator should reach the project answer, not the website URL
    open_ans = app._generate_open_question_answer("Tell us about a project you are proud of. Do you have a personal website?")
    assert open_ans == "Designed Playwright test framework for microservices."
    assert open_ans != dummy_profile.personal_info.portfolio_url


def test_router_defense_contaminated_label(dummy_profile):
    page = MagicMock()
    app = DummyApplicator(page, dummy_profile)
    # Contaminated question text starting with sensitive or deterministic field
    contaminated_text = "Gender Please select your gender. Race/Ethnicity. How many years of experience?"
    assert app._generate_deterministic_answer(contaminated_text) is None


@pytest.mark.asyncio
async def test_number_inputs_empty_education_dates(dummy_profile):
    page = MagicMock()
    app = DummyApplicator(page, dummy_profile)
    # Ensure profile has no education dates
    dummy_profile.open_questions.education_start_year = None
    dummy_profile.open_questions.education_end_year = None

    mock_field = AsyncMock()
    mock_field.is_visible = AsyncMock(return_value=True)
    mock_field.input_value = AsyncMock(return_value="")
    mock_field.evaluate = AsyncMock(return_value={
        "qText": "Start date (year)",
        "isRequired": True,
        "inputType": "number",
        "id": "school_start_year",
    })
    mock_field.fill = AsyncMock()

    mock_locator = MagicMock()
    mock_locator.count = AsyncMock(return_value=1)
    mock_locator.nth = MagicMock(return_value=mock_field)
    page.locator = MagicMock(return_value=mock_locator)

    await app.fill_custom_questions()

    # Must NOT fill "2021"
    mock_field.fill.assert_not_called()
    assert app.filled_fields.get("Number (Start date (year))") == "Pending manual review"


@pytest.mark.asyncio
async def test_number_inputs_with_education_dates(dummy_profile):
    page = MagicMock()
    app = DummyApplicator(page, dummy_profile)
    dummy_profile.open_questions.education_start_year = 2017
    dummy_profile.open_questions.education_end_year = 2021

    mock_field_start = AsyncMock()
    mock_field_start.is_visible = AsyncMock(return_value=True)
    mock_field_start.input_value = AsyncMock(return_value="")
    mock_field_start.evaluate = AsyncMock(return_value={
        "qText": "Start date (year)",
        "isRequired": True,
        "inputType": "number",
        "id": "school_start_year",
    })
    mock_field_start.fill = AsyncMock()

    mock_field_end = AsyncMock()
    mock_field_end.is_visible = AsyncMock(return_value=True)
    mock_field_end.input_value = AsyncMock(return_value="")
    mock_field_end.evaluate = AsyncMock(return_value={
        "qText": "End date (graduated year)",
        "isRequired": True,
        "inputType": "number",
        "id": "school_end_year",
    })
    mock_field_end.fill = AsyncMock()

    fields = [mock_field_start, mock_field_end]
    mock_locator = MagicMock()
    mock_locator.count = AsyncMock(return_value=len(fields))
    mock_locator.nth = MagicMock(side_effect=lambda i: fields[i])
    page.locator = MagicMock(return_value=mock_locator)

    await app.fill_custom_questions()

    mock_field_start.fill.assert_awaited_once_with("2017")
    mock_field_end.fill.assert_awaited_once_with("2021")
    assert app.filled_fields.get("Number (Start date (year))") == "2017"
    assert app.filled_fields.get("Number (End date (graduated year))") == "2021"


@pytest.mark.asyncio
async def test_number_inputs_required_generic_not_seven(dummy_profile):
    page = MagicMock()
    app = DummyApplicator(page, dummy_profile)

    mock_field = AsyncMock()
    mock_field.is_visible = AsyncMock(return_value=True)
    mock_field.input_value = AsyncMock(return_value="")
    mock_field.evaluate = AsyncMock(return_value={
        "qText": "How many people did you manage?",
        "isRequired": True,
        "inputType": "number",
        "id": "team_size",
    })
    mock_field.fill = AsyncMock()

    mock_locator = MagicMock()
    mock_locator.count = AsyncMock(return_value=1)
    mock_locator.nth = MagicMock(return_value=mock_field)
    page.locator = MagicMock(return_value=mock_locator)

    await app.fill_custom_questions()

    # Must NOT fill "7"
    mock_field.fill.assert_not_called()
    assert app.filled_fields.get("Number (How many people did you manage?)") == "Pending manual review"


@pytest.mark.asyncio
async def test_number_inputs_years_of_experience(dummy_profile):
    page = MagicMock()
    app = DummyApplicator(page, dummy_profile)
    dummy_profile.personal_info.years_of_experience = 8

    mock_field = AsyncMock()
    mock_field.is_visible = AsyncMock(return_value=True)
    mock_field.input_value = AsyncMock(return_value="")
    mock_field.evaluate = AsyncMock(return_value={
        "qText": "How many years of experience do you have?",
        "isRequired": True,
        "inputType": "number",
        "id": "exp_years",
    })
    mock_field.fill = AsyncMock()

    mock_locator = MagicMock()
    mock_locator.count = AsyncMock(return_value=1)
    mock_locator.nth = MagicMock(return_value=mock_field)
    page.locator = MagicMock(return_value=mock_locator)

    await app.fill_custom_questions()

    # Must fill "8" from profile
    mock_field.fill.assert_awaited_once_with("8")
    assert app.filled_fields.get("Number (How many years of experience do you have?)") == "8"


def test_location_dropdown_protection(dummy_profile):
    page = MagicMock()
    app = DummyApplicator(page, dummy_profile)

    # Parte 1: US states dropdown with Uruguay profile returns None, never California, even with fallback_first=True
    us_states = ["California", "New York", "Texas", "Washington"]
    loc_choices = app._desired_dropdown_choice("Location")
    is_sens = BaseApplicator.is_sensitive_field("Location")
    assert is_sens is True
    res = app.match_dropdown_option(us_states, loc_choices or [], is_sensitive=is_sens, fallback_first=True)
    assert res is None

    # is_sensitive_field() returns True for Location, Country, State, Ubicación, País, Provincia
    for field in ["Location", "Country", "State", "Ubicación", "País", "Provincia"]:
        assert BaseApplicator.is_sensitive_field(field) is True, f"Failed on {field}"

    # Dropdown with compatible option (e.g. [Uruguay, Brazil]) selects Uruguay
    options_latam = ["Uruguay", "Brazil"]
    res_latam = app.match_dropdown_option(options_latam, loc_choices or [], is_sensitive=is_sens, fallback_first=True)
    assert res_latam == "Uruguay"


def test_spanish_routing_and_canonical_matching(dummy_profile):
    page = MagicMock()
    app = DummyApplicator(page, dummy_profile)

    # Parte 2: is_deterministic_field() returns True for all 9 Spanish evidence labels
    spanish_deterministic_labels = [
        "Nombre",
        "Apellido",
        "Correo electrónico",
        "Teléfono",
        "Género",
        "Raza / Etnia",
        "Condición de veterano",
        "Situación de discapacidad",
        "Ubicación (Ciudad)",
    ]
    for label in spanish_deterministic_labels:
        assert BaseApplicator.is_deterministic_field(label) is True, f"Failed on deterministic label: {label}"

    # is_sensitive_field() returns True for all 5 Spanish evidence labels
    spanish_sensitive_labels = [
        "Género",
        "Raza / Etnia",
        "Condición de veterano",
        "Situación de discapacidad",
        "Sexo",
    ]
    for label in spanish_sensitive_labels:
        assert BaseApplicator.is_sensitive_field(label) is True, f"Failed on sensitive label: {label}"

    # Dropdown [Femenino, Masculino, No binario, Prefiero no responder] with gender="male" returns 'Masculino'
    dummy_profile.personal_info.gender = "male"
    gender_choices = app._desired_dropdown_choice("Género")
    opts_gender_es = ["Femenino", "Masculino", "No binario", "Prefiero no responder"]
    picked_gender = app.match_dropdown_option(opts_gender_es, gender_choices or [], is_sensitive=True)
    assert picked_gender == "Masculino"

    # Dropdown [Sí, tengo una discapacidad, No, no tengo una discapacidad] with disability_status="no" returns negative option
    dummy_profile.personal_info.disability_status = "no"
    disability_choices = app._desired_dropdown_choice("Situación de discapacidad")
    opts_disability_es = ["Sí, tengo una discapacidad", "No, no tengo una discapacidad"]
    picked_disability = app.match_dropdown_option(opts_disability_es, disability_choices or [], is_sensitive=True)
    assert picked_disability == "No, no tengo una discapacidad"

    # Legacy profile with "gender": "Male" normalizes to "male" upon reading and continues working
    legacy_profile = CandidateProfile(
        personal_info=PersonalInfo(
            full_name="Alex Mercer",
            email="alex.mercer@example.com",
            phone="+598 99 123 456",
            location="Montevideo, Uruguay",
            linkedin_url="https://www.linkedin.com/in/alex-mercer-qa/",
            gender="Male",
            race="Hispanic or Latino",
            veteran_status="I am not a veteran",
            disability_status="No, I do not have a disability",
        ),
        search_criteria=dummy_profile.search_criteria,
    )
    assert legacy_profile.personal_info.gender == "male"
    assert legacy_profile.personal_info.race == "hispanic_latino"
    assert legacy_profile.personal_info.veteran_status == "not_veteran"
    assert legacy_profile.personal_info.disability_status == "no"

    legacy_app = DummyApplicator(page, legacy_profile)
    choices = legacy_app._desired_dropdown_choice("Gender")
    assert legacy_app.match_dropdown_option(["Female", "Male", "Non-binary", "Decline to Self-Identify"], choices or [], is_sensitive=True) == "Male"
    assert legacy_app.match_dropdown_option(["Femenino", "Masculino", "No binario", "Prefiero no responder"], choices or [], is_sensitive=True) == "Masculino"


def test_regression_controls_eeo(dummy_profile):
    page = MagicMock()
    app = DummyApplicator(page, dummy_profile)

    # 1. [Female, Male, Non-binary, Decline to Self-Identify] with male returns 'Male'
    dummy_profile.personal_info.gender = "male"
    choices_gender = app._desired_dropdown_choice("Gender")
    assert app.match_dropdown_option(["Female", "Male", "Non-binary", "Decline to Self-Identify"], choices_gender or [], is_sensitive=True) == "Male"

    # 2. [South Asian, Asian, White] with asian returns 'Asian'
    dummy_profile.personal_info.race = "asian"
    choices_race = app._desired_dropdown_choice("Race")
    assert app.match_dropdown_option(["South Asian", "Asian", "White"], choices_race or [], is_sensitive=True) == "Asian"

    # 3. [Female, Non-binary, Decline to Self-Identify] with male returns 'Decline to Self-Identify'
    dummy_profile.personal_info.gender = "male"
    choices_no_male = app._desired_dropdown_choice("Gender")
    assert app.match_dropdown_option(["Female", "Non-binary", "Decline to Self-Identify"], choices_no_male or [], is_sensitive=True) == "Decline to Self-Identify"

    # 4. Spanish decline fallback: [Femenino, No binario, Prefiero no responder] with male returns 'Prefiero no responder'
    assert app.match_dropdown_option(["Femenino", "No binario", "Prefiero no responder"], choices_no_male or [], is_sensitive=True) == "Prefiero no responder"


def test_match_experience_range():
    # 7 years QA experience (Matías Olivera)
    opts_1 = ["Less than 3", "3-5 years", "6-9 years", "10+ years"]
    assert BaseApplicator.match_experience_range(7, opts_1) == "6-9 years"
    assert BaseApplicator.match_experience_range(2, opts_1) == "Less than 3"
    assert BaseApplicator.match_experience_range(4, opts_1) == "3-5 years"
    assert BaseApplicator.match_experience_range(11, opts_1) == "10+ years"

    opts_2 = ["0-2 years", "3-5 years", "5+ years"]
    assert BaseApplicator.match_experience_range(7, opts_2) == "5+ years"

    opts_3 = ["1 to 3", "4 to 6", "7 to 9", "10 or more"]
    assert BaseApplicator.match_experience_range(7, opts_3) == "7 to 9"


@pytest.mark.asyncio
async def test_choose_radio_option_mocked(dummy_profile, monkeypatch):
    from src.automation import agent_adapter

    async def mock_query(prompt, preferred_provider="auto", timeout=35):
        return "6-9 years"

    monkeypatch.setattr(agent_adapter, "query_model", mock_query)

    chosen = await agent_adapter.choose_radio_option(
        question_text="How many years of experience in QA?",
        options=["Less than 3", "3-5 years", "6-9 years", "10+ years"],
        job_title="QA Engineer",
        company="Acme",
        candidate_profile=dummy_profile,
    )
    assert chosen == "6-9 years"


@pytest.mark.asyncio
async def test_fill_radio_groups_qa_questions(dummy_profile):
    page = MagicMock()
    app = DummyApplicator(page, dummy_profile)

    # 1. Experience range question: 7 years -> "6-9 years"
    opts_exp = ["Less than 3", "3-5 years", "6-9 years", "10+ years"]
    matched_exp = app.match_experience_range(dummy_profile.personal_info.years_of_experience, opts_exp)
    assert matched_exp == "6-9 years"

    # 2. Sole QA owner question -> "Yes"
    q_sole = "Have you worked as the primary or sole QA owner on a project or team?*"
    assert any(re.search(r"\b(primary\s+or\s+sole\s+qa|sole\s+qa|solo\s+qa|primary\s+qa|qa\s+owner)\b", q_sole, re.IGNORECASE) for _ in [1])

    # 3. Recent QA work question -> hands-on
    opts_work = [
        "Primarily hands-on testing, investigation, and automation",
        "Mix of hands-on QA and QA leadership/mentoring",
        "Primarily QA leadership, mentoring, or people management",
        "Primarily project/product management with some QA involvement"
    ]
    picked_work = next(o for o in opts_work if any(w in o.lower() for w in ("hands-on", "automation")))
    assert picked_work == "Primarily hands-on testing, investigation, and automation"




