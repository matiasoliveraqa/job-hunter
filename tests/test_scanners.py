"""
Tests for scanner matching and experience filtering logic.
"""

from src.scanners.ashby import AshbyScanner

def test_keyword_matching():
    scanner = AshbyScanner()
    assert scanner.matches_keywords("Senior Software Engineer", ["software", "python"]) is True
    assert scanner.matches_keywords("Data Analyst", ["software", "python"]) is False
    assert scanner.matches_keywords("QA Automation Lead", ["qa automation"]) is True

def test_location_matching():
    scanner = AshbyScanner()
    assert scanner.matches_location("Backend Dev", "Remote - LATAM", ["remote", "latam"]) is True
    assert scanner.matches_location("Remote Frontend Engineer", "New York Office", ["latam"]) is True
    assert scanner.matches_location("Staff Engineer", "Berlin, Germany Office", ["latam", "worldwide"]) is False

def test_experience_extraction_and_filtering():
    scanner = AshbyScanner()
    # Candidate has 6 years of experience
    assert scanner.extract_required_years("We require 10+ years of experience in backend systems.") == 10
    assert scanner.matches_experience("We require 10+ years of experience in backend systems.", max_years=6) is False

    assert scanner.extract_required_years("Minimum of 8 years of professional software experience.") == 8
    assert scanner.matches_experience("Minimum of 8 years of professional software experience.", max_years=6) is False

    assert scanner.extract_required_years("5+ years of experience with React and TypeScript.") == 5
    assert scanner.matches_experience("5+ years of experience with React and TypeScript.", max_years=6) is True

    # Range 6-9 years -> minimum is 6 -> allowed for candidate with 6 years
    assert scanner.extract_required_years("6-9 years of experience building web apps.") == 6
    assert scanner.matches_experience("6-9 years of experience building web apps.", max_years=6) is True

    # No years mentioned -> allowed
    assert scanner.extract_required_years("Looking for a passionate Full Stack Engineer.") is None
    assert scanner.matches_experience("Looking for a passionate Full Stack Engineer.", max_years=6) is True
