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
    r"\b("
    r"latam|latin\s+america|south\s+america|uruguay|montevideo|"
    r"worldwide|global|"
    r"anywhere(?!\s+in\s+(?:the\s+)?(us|u\.s\.|usa|united\s+states|uk|united\s+kingdom|canada|europe|eu|india|apac|brazil|brasil))"
    r")\b",
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

US_STATES_DELIMITED = (
    r",\s*(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|"
    r"MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|"
    r"SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b"
)

US_VARIANTS = r"(?:united\s+states|usa|us|u\.?\s?s\.?)"

# Non-LATAM country/city/region restrictions in location or title (e.g. "United States (Remote)", "Remote, US", "Anywhere in the US.")
RESTRICTED_LOCATION_RE = re.compile(
    r"(?:"
    r"\b(?:united\s+states|usa)\b|\bu\.s\.?(?!\w)|"
    rf"^\s*{US_VARIANTS}\s*$|"
    rf"^\s*{US_VARIANTS}\s*[-–,/|\)\]]|"
    rf"[-–,/|\(\[]\s*{US_VARIANTS}\s*(?:[-–,/|\)\]\.]|$)|"
    rf"\b(?:anywhere|everywhere|remote|based|located|resident)\s+in\s+(?:the\s+)?{US_VARIANTS}(?!\w)|"
    rf"\b(?:in|within)\s+(?:the\s+)?{US_VARIANTS}(?!\w)|"
    rf"\b(?:us|u\.?\s?s\.?|united\s+states)\s+(?:remote|only|based|resident|citizens?|nationwide)\b|"
    rf"\b(?:remote\s*[-–,/|]\s*{US_VARIANTS})(?!\w)|"
    r"\b(?:north\s+america|americas)\b|"
    + US_STATES_DELIMITED + r"|"
    r"\b(uk|united\s+kingdom|england|london|manchester|scotland|"
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
    r"new\s+york|texas|dallas|plano|austin|houston|seattle|washington|chicago|illinois|atlanta|maryland|boston|massachusetts|denver|colorado|miami|florida|alabama|birmingham|kentucky|ft\.?\s*knox)\b"
    r")",
    re.IGNORECASE,
)

# Phrases inside the job description or application form questions that restrict the role to specific residents/citizens
RESIDENCY_RESTRICTION_RE = re.compile(
    r"(state\s+of\s+residence\s+within\s+the\s+united\s+states|"
    r"(?:must\s+)?(?:reside|live|be\s+located|be\s+based)\s+in\s+(?:the\s+)?(?:united\s+states|usa|uk|canada|europe|eu|brazil|brasil|india|\bu\.?\s?s\.?(?!\w))|"
    r"only\s+(?:hiring|open\s+to\s+candidates|able\s+to\s+hire)\s+in\s+(?:the\s+)?(?:united\s+states|usa|brazil|brasil|\bu\.?\s?s\.?(?!\w))|"
    r"candidates\s+must\s+be\s+(?:located|based|residing)\s+in\s+(?:the\s+)?(?:united\s+states|usa|brazil|brasil|\bu\.?\s?s\.?(?!\w))|"
    r"residir\s+(?:en|no)\s+(?:brasil|brazil)|"
    r"contrato\s+clt|regime\s+clt|vaga\s+exclusiva\s+para\s+residentes|"
    r"requires?\s+on-site\s+availability|"
    r"required\s+clearance\s*:\s*(?:public\s+trust|secret|active\s+secret|top\s+secret)|"
    r"\bu\.?\s?s\.?(?!\w)\s+citizenship\s+(?:is\s+)?required|"
    r"\b(?:anywhere|everywhere)\s+in\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w))|"
    r"\b(?:united\s+states|\bu\.?\s?s\.?(?!\w))\s+(?:only|residents?\s+only|based\s+candidates\s+only|citizens?\s+only)\b|"
    r"\b(?:open|available)\s+(?:only\s+to|to)\s+(?:candidates\s+(?:based|located)\s+in\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w)))|"
    r"\b(?:position|role)\s+is\s+(?:only\s+)?(?:open\s+to|available\s+to)\s+(?:candidates\s+in\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w)))|"
    r"\b(?:located|based|residing)\s+(?:within|in)\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w))|"
    r"\b(?:remote\s+within\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w)))|"
    r"\b(?:remote\s*[-–,/|]\s*(?:anywhere\s+in\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w))))|"
    r"(?:location|workplace)\s*[:\s–-]+\s*(?:anywhere\s+in\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w))|(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w))\s+remote|remote\s*[,–-]\s*(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w)))|"
    r"(?:authorized|eligible|legally\s+(?:authorized|eligible|able))\s+to\s+work\s+in\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w))|"
    r"\bu\.?\s?s\.?(?!\w)[-\s]based\s+(?:employees|candidates|applicants|workers|team|only)|"
    r"(?:reside|residing|located|based)\s+in\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w))|"
    r"\bu\.?\s?s\.?(?!\w)\s+work\s+authorization|"
    r"based\s+in\s+north\s+america)",
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

    def matches_location(self, title: str, location: str, loc_keywords: List[str], description: str = "") -> bool:
        """
        Check if location or title matches target location criteria while rejecting
        onsite positions, hybrid positions outside Uruguay, and restricted regions.
        """
        loc_str = (location or "").strip()
        t_str = (title or "").strip()
        desc_str = (description or "").strip()
        combined = f"{t_str} {loc_str}".strip()
        loc_lower = loc_str.lower()
        t_lower = t_str.lower()

        # Reject explicit onsite or in-office jobs immediately
        if ONSITE_RE.search(t_str) or ONSITE_RE.search(loc_str):
            return False

        # Reject hybrid jobs unless located in Uruguay
        if (HYBRID_RE.search(t_str) or HYBRID_RE.search(loc_str)) and not re.search(r"\b(uruguay|montevideo)\b", combined, re.IGNORECASE):
            return False

        if loc_keywords:
            # If the user chose "any", accept any remote job without discarding restricted regions
            if any(k.lower() in ("all", "any", "*") for k in loc_keywords):
                return "remote" in t_lower or "remote" in loc_lower or not (ONSITE_RE.search(t_str) or ONSITE_RE.search(loc_str))

            # When location is empty, evaluate based on description and title
            if not loc_str:
                if desc_str:
                    if self.has_residency_restriction(desc_str, loc_keywords):
                        return False
                    if (RESTRICTED_LOCATION_RE.search(desc_str) or ONSITE_RE.search(desc_str)) and not re.search(r"\b(latam|latin\s+america|south\s+america|uruguay|montevideo)\b", desc_str, re.IGNORECASE):
                        return False
                    if LATAM_OR_GLOBAL_RE.search(desc_str) or LATAM_OR_GLOBAL_RE.search(t_str):
                        wants_global = any(k.lower() in ("remote", "worldwide", "global", "anywhere") for k in loc_keywords)
                        if not wants_global:
                            return bool(re.search(r"\b(latam|latin\s+america|south\s+america|uruguay|montevideo)\b", f"{t_str} {desc_str}", re.IGNORECASE))
                        return True
                    if any(k.lower() in desc_str.lower() or k.lower() in t_lower for k in loc_keywords):
                        return True
                else:
                    if RESTRICTED_LOCATION_RE.search(t_str) and not re.search(r"\b(latam|latin\s+america|south\s+america|uruguay|montevideo)\b", t_str, re.IGNORECASE):
                        return False
                    if LATAM_OR_GLOBAL_RE.search(t_str):
                        wants_global = any(k.lower() in ("remote", "worldwide", "global", "anywhere") for k in loc_keywords)
                        if not wants_global:
                            return bool(re.search(r"\b(latam|latin\s+america|south\s+america|uruguay|montevideo)\b", t_str, re.IGNORECASE))
                        return True
                    if any(k.lower() in t_lower for k in loc_keywords):
                        return True
                return False

            # Reject physical on-site locations outside Uruguay if neither location nor title mentions remote/worldwide
            is_uruguay = bool(re.search(r"\b(uruguay|montevideo)\b", combined, re.IGNORECASE))
            has_remote_indicator = bool(re.search(r"\b(remote|remoto|worldwide|global|anywhere)\b", combined, re.IGNORECASE))
            is_distributed_latam = bool(re.search(r"^\s*(?:latam|latin\s+america|south\s+america)\s*$", loc_str, re.IGNORECASE))
            if loc_str and not is_uruguay and not has_remote_indicator and not is_distributed_latam:
                return False

            # Evaluate restricted locations on location and title separately so anchors (^, $) work
            is_restricted = bool(RESTRICTED_LOCATION_RE.search(loc_str) or RESTRICTED_LOCATION_RE.search(t_str))
            if is_restricted:
                # When a restricted location (US/UK/EU/India/etc.) matches, strictly reject
                # unless the posting explicitly includes LATAM / Uruguay in the title/location
                if not re.search(r"\b(latam|latin\s+america|south\s+america|uruguay|montevideo)\b", combined, re.IGNORECASE):
                    return False
                return True

            if LATAM_OR_GLOBAL_RE.search(combined):
                wants_global = any(k.lower() in ("remote", "worldwide", "global", "anywhere") for k in loc_keywords)
                if not wants_global:
                    return bool(re.search(r"\b(latam|latin\s+america|south\s+america|uruguay|montevideo)\b", combined, re.IGNORECASE))
                return True

            return any(k.lower() in loc_lower or k.lower() in t_lower for k in loc_keywords)

        return "remote" in t_lower or "remote" in loc_lower


    def has_residency_restriction(self, text: str, location_keywords: Optional[List[str]] = None) -> bool:
        """Return True if the job description or form questions contain a US/EU/UK residency or clearance restriction."""
        if location_keywords and any(k.lower() in ("all", "any", "*") for k in location_keywords):
            return False
        if not text:
            return False
        clean_text = re.sub(r"<[^>]+>", " ", text)
        if not RESIDENCY_RESTRICTION_RE.search(clean_text):
            return False
        # Do not treat as restricted if LATAM or Uruguay is explicitly supported
        if re.search(r"\b(latam|latin\s+america|south\s+america|uruguay|montevideo)\b", clean_text, re.IGNORECASE):
            return False
        return True

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


def format_company_name(name: str) -> str:
    """Format company slug or raw name so each word starts with a capital letter."""
    if not name:
        return ""
    return re.sub(r"(^|[\s\-_]+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), name)

