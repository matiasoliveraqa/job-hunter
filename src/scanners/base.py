"""
Base Scanner Interface for Applicant Tracking Systems.
"""

import re
from abc import ABC, abstractmethod
from typing import List, Optional
import aiohttp
from src.core.models import JobPosting, ATSPlatform

# Regex patterns to extract minimum required years of experience from job descriptions
EXPERIENCE_PATTERNS = [
    re.compile(
        r"\b(\d{1,2})\s*(?:\+|\s*(?:to|-|–)\s*\d{1,2})?\s*(?:years?|yrs?|años?)\b"
        r"(?:\s+of)?\s+(?:[a-z\-]+\s+){0,4}?(?:experience|experiencia)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:minimum|at\s+least|mínimo|al\s+menos)\s+(?:of\s+)?(\d{1,2})\+?\s*(?:years?|yrs?|años?)"
        r"(?:\s+of\s+(?:[a-z\-]+\s+){0,3}?experience)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:experience|experiencia)\s*(?:of|:)?\s*(\d{1,2})\s*(?:\+|\s*(?:to|-|–)\s*\d{1,2})?\s*(?:years?|yrs?|años?)",
        re.IGNORECASE,
    ),
]

class BaseScanner(ABC):
    def __init__(self, platform: ATSPlatform):
        self.platform = platform

    @abstractmethod
    async def scan_company(
        self,
        session: aiohttp.ClientSession,
        company_slug: str,
        role_keywords: List[str],
        location_keywords: List[str],
        max_years_experience: Optional[int] = None,
    ) -> List[JobPosting]:
        """Scan a single company job board and return matching postings."""
        pass

    def matches_keywords(self, title: str, keywords: List[str]) -> bool:
        """Check if job title matches any of the target keywords."""
        if not keywords:
            return True
        t_lower = title.lower()
        return any(k.lower() in t_lower for k in keywords)

    def matches_location(self, title: str, location: str, loc_keywords: List[str]) -> bool:
        """Check if location or title matches target location criteria."""
        if not loc_keywords:
            return True
        loc_lower = (location or "").lower()
        t_lower = title.lower()

        # If title explicitly mentions remote
        if "remote" in t_lower:
            return True

        return any(k.lower() in loc_lower for k in loc_keywords)

    def extract_required_years(self, text: str) -> Optional[int]:
        """
        Extract the required years of experience from a job title or description.
        Returns the highest minimum years requirement found (if any, between 1 and 20).
        """
        if not text:
            return None
        clean_text = re.sub(r"<[^>]+>", " ", text)
        found_years: List[int] = []
        for pattern in EXPERIENCE_PATTERNS:
            for match in pattern.finditer(clean_text):
                try:
                    yrs = int(match.group(1))
                    # Filter out company age mentions (e.g. "25 years in the market")
                    if 1 <= yrs <= 18:
                        found_years.append(yrs)
                except ValueError:
                    continue
        return max(found_years) if found_years else None

    def matches_experience(self, text: str, max_years: Optional[int]) -> bool:
        """
        Return True if the job's required years of experience is <= max_years.
        If max_years is None or the posting doesn't specify years, returns True.
        """
        if max_years is None:
            return True
        req_years = self.extract_required_years(text)
        if req_years is not None and req_years > max_years:
            return False
        return True
