"""
Tests for scanner matching logic.
"""

from src.scanners.ashby import AshbyScanner
from src.core.models import ATSPlatform

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
