"""
Base Scanner Interface for Applicant Tracking Systems.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import aiohttp

from src.core.models import JobPosting, ATSPlatform
from src.scanners.constants import (
    COUNTRY_SYNONYMS,
    EXPERIENCE_PATTERNS,
    GENERIC_ROLE_WORDS,
    HYBRID_RE,
    LATAM_COUNTRIES_LIST,
    LATAM_KEYWORDS,
    LATAM_OR_GLOBAL_RE,
    LATAM_RE,
    NORTH_AMERICA_RE,
    ONSITE_RE,
    OTHER_REGIONS_RESTRICTED_RE,
    RESIDENCY_RESTRICTION_RE,
    RESTRICTED_LOCATION_RE,
    ROLE_ACRONYM_MAP,
    US_STATES_DELIMITED,
    US_VARIANTS,
)
from src.scanners.location_filter import (
    ScannerFilterMixin,
    build_home_only_re,
    build_home_region_re,
    expand_country_terms,
    format_company_name,
)

__all__ = [
    "BaseScanner",
    "format_company_name",
    "ScannerFilterMixin",
    "expand_country_terms",
    "build_home_region_re",
    "build_home_only_re",
    "EXPERIENCE_PATTERNS",
    "LATAM_OR_GLOBAL_RE",
    "ONSITE_RE",
    "HYBRID_RE",
    "US_STATES_DELIMITED",
    "US_VARIANTS",
    "RESTRICTED_LOCATION_RE",
    "RESIDENCY_RESTRICTION_RE",
    "LATAM_COUNTRIES_LIST",
    "LATAM_KEYWORDS",
    "LATAM_RE",
    "NORTH_AMERICA_RE",
    "OTHER_REGIONS_RESTRICTED_RE",
    "COUNTRY_SYNONYMS",
    "ROLE_ACRONYM_MAP",
    "GENERIC_ROLE_WORDS",
]


class BaseScanner(ScannerFilterMixin, ABC):
    """
    Abstract Base Class for ATS scanners.
    Incorporates location, experience, and role filters via ScannerFilterMixin.
    """

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
        home_terms: Optional[List[str]] = None,
        geo_scope: Optional[str] = None,
        custom_countries: Optional[List[str]] = None,
        work_modes: Optional[List[str]] = None,
    ) -> List[JobPosting]:
        """Scan a single company job board and return matching postings."""
        pass
