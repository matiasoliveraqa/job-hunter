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

# Explicit LATAM / Global keywords that override regional restrictions in location strings
LATAM_OR_GLOBAL_RE = re.compile(
    r"\b(latam|latin\s+america|south\s+america|uruguay|worldwide|global|anywhere|americas)\b",
    re.IGNORECASE,
)

# Reject explicit on-site and in-office jobs immediately
ONSITE_RE = re.compile(
    r"\b(onsite|on-site|in-office|presencial|office-based)\b",
    re.IGNORECASE,
)

# Hybrid jobs are only acceptable if located in the candidate's residence (Uruguay)
HYBRID_RE = re.compile(
    r"\b(hybrid|híbrido)\b",
    re.IGNORECASE,
)

# Non-LATAM country/city/region restrictions in location or title (e.g. "United States (Remote)", "Remote, US", "UK (Remote)")
RESTRICTED_LOCATION_RE = re.compile(
    r"\b(united\s+states|u\.s\.a?\.?|usa|us\s+remote|remote\s*[-–,/|]\s*us|remote\s+in\s+(?:the\s+)?us|remote\s+us|"
    r"uk|united\s+kingdom|england|london|manchester|scotland|"
    r"canada|toronto|ottawa|montreal|vancouver|british\s+columbia|"
    r"europe|european\s+union|eu\s+remote|emea|cet|"
    r"germany|berlin|munich|france|paris|spain|madrid|barcelona|italy|rome|ireland|dublin|"
    r"netherlands|amsterdam|belgium|sweden|stockholm|switzerland|zurich|denmark|copenhagen|"
    r"poland|warsaw|serbia|belgrade|cyprus|romania|bulgaria|georgia|ukraine|kyiv|czech|prague|armenia|"
    r"finland|espoo|helsinki|norway|oslo|austria|vienna|hungary|budapest|israel|tel\s+aviv|"
    r"china|guangdong|beijing|shanghai|shenzhen|hong\s+kong|"
    r"india|ind-remote|bengaluru|bangalore|hyderabad|pune|mumbai|"
    r"philippines|manila|apac|vietnam|japan|tokyo|singapore|taiwan|south\s+korea|korea|pangyo|malaysia|kuala\s+lumpur|australia|sydney|melbourne|new\s+zealand|auckland|"
    r"california|san\s+francisco|san\s+mateo|santa\s+clara|marina\s+del\s+rey|los\s+angeles|los\s+gatos|"
    r"new\s+york|texas|dallas|plano|austin|houston|seattle|washington|chicago|illinois|atlanta|maryland|boston|massachusetts|denver|colorado|miami|florida|alabama|birmingham|kentucky|ft\.?\s*knox)\b",
    re.IGNORECASE,
)

# Phrases inside the job description or application form questions that restrict the role to specific residents/citizens
RESIDENCY_RESTRICTION_RE = re.compile(
    r"(state\s+of\s+residence\s+within\s+the\s+united\s+states|"
    r"must\s+(?:reside|live|be\s+located|be\s+based)\s+in\s+(?:the\s+)?(?:united\s+states|u\.s\.|usa|us|uk|canada|europe|eu|brazil|brasil|india)\b|"
    r"only\s+(?:hiring|open\s+to\s+candidates)\s+in\s+(?:the\s+)?(?:united\s+states|u\.s\.|usa|us|brazil|brasil)\b|"
    r"candidates\s+must\s+be\s+(?:located|based|residing)\s+in\s+(?:the\s+)?(?:united\s+states|u\.s\.|usa|us|brazil|brasil)\b|"
    r"residir\s+(?:en|no)\s+(?:brasil|brazil)|"
    r"contrato\s+clt|regime\s+clt|vaga\s+exclusiva\s+para\s+residentes|"
    r"requires?\s+on-site\s+availability|"
    r"required\s+clearance\s*:\s*(?:public\s+trust|secret|active\s+secret|top\s+secret)|"
    r"u\.?s\.?\s+citizenship\s+(?:is\s+)?required)",
    re.IGNORECASE,
)

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
        t_lower = (title or "").lower()
        for k in keywords:
            k_lower = (k or "").lower().strip()
            if not k_lower:
                continue
            if k_lower in t_lower:
                return True
            k_words = [w for w in re.split(r"[\s/_\-]+", k_lower) if w]
            if len(k_words) > 1 and all(w in t_lower for w in k_words):
                return True
            if len(k_words) == 1 and re.search(r"\b" + re.escape(k_words[0]) + r"\b", t_lower):
                return True
        return False

    def matches_location(self, title: str, location: str, loc_keywords: List[str]) -> bool:
        """
        Check if location or title matches target location criteria while rejecting
        onsite positions, hybrid positions outside Uruguay, and restricted regions.
        """
        combined = f"{title or ''} {location or ''}".strip()
        loc_lower = (location or "").lower()
        t_lower = (title or "").lower()

        # Reject explicit onsite or in-office jobs immediately
        if ONSITE_RE.search(combined):
            return False

        # Reject hybrid jobs unless located in Uruguay
        if HYBRID_RE.search(combined) and not re.search(r"\b(uruguay|montevideo)\b", combined, re.IGNORECASE):
            return False

        if loc_keywords:
            if RESTRICTED_LOCATION_RE.search(combined) and not LATAM_OR_GLOBAL_RE.search(combined):
                return False

            if LATAM_OR_GLOBAL_RE.search(combined):
                return True

            return any(k.lower() in loc_lower or k.lower() in t_lower for k in loc_keywords)

        return "remote" in t_lower or "remote" in loc_lower

    def has_residency_restriction(self, text: str) -> bool:
        """Return True if the job description or form questions contain a US/EU/UK residency or clearance restriction."""
        if not text:
            return False
        clean_text = re.sub(r"<[^>]+>", " ", text)
        return bool(RESIDENCY_RESTRICTION_RE.search(clean_text))

    def extract_required_years(self, text: str) -> Optional[int]:
        """
        Extract the minimum required years of experience from a job title or description.
        Distinguishes required experience from preferred/bonus mentions.
        """
        if not text:
            return None
        clean_text = re.sub(r"<[^>]+>", " ", text)
        required_years: List[int] = []
        preferred_years: List[int] = []

        chunks = re.split(r"[\n\r.;•]+", clean_text)
        for chunk in chunks:
            chunk_lower = chunk.lower()
            is_preferred = any(
                k in chunk_lower
                for k in ["preferred", "nice to have", "plus", "bonus", "desirable", "preferable"]
            )
            for pattern in EXPERIENCE_PATTERNS:
                for match in pattern.finditer(chunk):
                    try:
                        yrs = int(match.group(1))
                        if 1 <= yrs <= 18:
                            if is_preferred:
                                preferred_years.append(yrs)
                            else:
                                required_years.append(yrs)
                    except ValueError:
                        continue

        if required_years:
            return min(required_years)
        if preferred_years:
            return min(preferred_years)
        return None

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
