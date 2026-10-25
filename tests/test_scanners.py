"""
Tests for scanner matching and experience filtering logic.
"""

from src.scanners.ashby import AshbyScanner

def test_keyword_matching():
    scanner = AshbyScanner()
    assert scanner.matches_keywords("Senior Software Engineer", ["software", "python"]) is True
    assert scanner.matches_keywords("Data Analyst", ["software", "python"]) is False
    assert scanner.matches_keywords("QA Automation Lead", ["qa automation"]) is True
    assert scanner.matches_keywords("Senior Automation QA Engineer", ["QA Automation Engineer"]) is True
    assert scanner.matches_keywords("Lead QA", ["QA"]) is True
    assert scanner.matches_keywords("Software Quality Assurance Engineer", ["Quality Engineer"]) is True

def test_location_matching():
    scanner = AshbyScanner()
    assert scanner.matches_location("Backend Dev", "Remote - LATAM", ["remote", "latam"]) is True
    assert scanner.matches_location("QA Engineer", "South America (Remote)", ["remote", "latam"]) is True
    assert scanner.matches_location("QA Engineer", "Remote (US & LATAM)", ["remote", "latam"]) is True
    assert scanner.matches_location("QA Engineer", "United States (Remote)", ["remote", "latam"]) is False
    assert scanner.matches_location("Remote Frontend Engineer", "New York Office", ["latam", "remote"]) is False
    assert scanner.matches_location("Staff Engineer", "Berlin, Germany Office", ["latam", "worldwide"]) is False
    assert scanner.matches_location("Senior QA Engineer", "São Paulo, Brazil onsite", ["remote", "latam"]) is False
    assert scanner.matches_location("QA Engineer", "Draper, UT (Hybrid)", ["remote", "latam"]) is False
    assert scanner.matches_location("QA Engineer", "Montevideo, Uruguay (Hybrid)", ["remote", "latam"]) is True

def test_residency_restriction():
    scanner = AshbyScanner()
    assert scanner.has_residency_restriction("What is your state of residence within the United States?") is True
    assert scanner.has_residency_restriction("Candidates must reside in the US to be considered.") is True
    assert scanner.has_residency_restriction("Open to remote candidates across Latin America.") is False
    assert scanner.has_residency_restriction("Vaga exclusiva para residentes no Brasil (Contrato CLT)") is True
    assert scanner.has_residency_restriction("This role requires on-site availability in São Paulo.") is True

def test_applicator_custom_questions():
    from src.core.config import load_candidate_profile
    from src.automation.applicators.greenhouse_applicator import GreenhouseApplicator
    profile = load_candidate_profile()
    app = GreenhouseApplicator(None, profile)
    assert app._generate_open_question_answer("Why Hone? Tell us what you know about what we do and how that aligns with your career path.") is not None
    assert app._generate_open_question_answer("Level of education * Indicate your highest level of education completed.") is not None
    assert app._desired_dropdown_choice("Remote work * Does your current home setup allow you to work remotely?") == ["Yes"]
    assert app._desired_dropdown_choice("Are you legally authorized to work in the United States?") == ["No"]
    assert app._desired_dropdown_choice("Will you now or in the future require employer sponsorship for a work visa?") == ["No"]

def test_experience_extraction_and_filtering():
    scanner = AshbyScanner()
    assert scanner.extract_required_years("We require 10+ years of experience in backend systems.") == 10
    assert scanner.matches_experience("We require 10+ years of experience in backend systems.", max_years=7) is False

    assert scanner.extract_required_years("Minimum of 8 years of professional software experience.") == 8
    assert scanner.matches_experience("Minimum of 8 years of professional software experience.", max_years=7) is False

    assert scanner.extract_required_years("5+ years of experience with React and TypeScript.") == 5
    assert scanner.matches_experience("5+ years of experience with React and TypeScript.", max_years=7) is True

    assert scanner.extract_required_years("6-9 years of experience building web apps.") == 6
    assert scanner.matches_experience("6-9 years of experience building web apps.", max_years=7) is True

    assert scanner.extract_required_years("Looking for a passionate Full Stack Engineer.") is None
    assert scanner.matches_experience("Looking for a passionate Full Stack Engineer.", max_years=7) is True

    # Required vs preferred
    mixed_text = "Required: 2+ years of QA experience. Preferred: 8+ years of test architecture experience."
    assert scanner.extract_required_years(mixed_text) == 2
    assert scanner.matches_experience(mixed_text, max_years=7) is True

def test_captcha_model_and_filtering():
    from src.core.models import JobPosting, ATSPlatform

    jp1 = JobPosting(
        ats=ATSPlatform.ASHBY,
        company="test-ashby",
        title="QA Engineer",
        location="Remote",
        url="https://jobs.ashbyhq.com/test-ashby/123",
        has_captcha=False,
    )
    jp2 = JobPosting(
        ats=ATSPlatform.LEVER,
        company="test-lever",
        title="QA Automation Engineer",
        location="Remote",
        url="https://jobs.lever.co/test-lever/456",
        has_captcha=True,
    )
    assert jp1.has_captcha is False
    assert jp2.has_captcha is True

    # When allow_captcha is False (default), jp2 is excluded
    allow_captcha = False
    filtered = [p for p in [jp1, jp2] if (allow_captcha or not p.has_captcha)]
    assert filtered == [jp1]

    # When allow_captcha is True, both are kept
    allow_captcha = True
    filtered_all = [p for p in [jp1, jp2] if (allow_captcha or not p.has_captcha)]
    assert filtered_all == [jp1, jp2]



