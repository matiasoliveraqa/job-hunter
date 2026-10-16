"""
Base Scanner Interface for Applicant Tracking Systems.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import aiohttp
from src.core.models import JobPosting, ATSPlatform

class BaseScanner(ABC):
    def __init__(self, platform: ATSPlatform):
        self.platform = platform

    @abstractmethod
    async def scan_company(
        self,
        session: aiohttp.ClientSession,
        company_slug: str,
        role_keywords: List[str],
        location_keywords: List[str]
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
