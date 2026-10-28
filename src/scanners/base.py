"""
Base Scanner Interface for Applicant Tracking Systems.
"""

import re
import unicodedata
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
    r"latam|latin\s+america|south\s+america|americas|"
    r"argentina|bolivia|brazil|brasil|chile|colombia|costa\s+rica|ecuador|el\s+salvador|guatemala|"
    r"honduras|mexico|m\u00e9xico|nicaragua|panama|panam\u00e1|paraguay|peru|per\u00fa|"
    r"dominican\s+republic|uruguay|venezuela|"
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

# Hybrid jobs are only acceptable if located in the candidate's own city or country
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
    rf"\b(?:remote\s*[-–,/|\s]\s*{US_VARIANTS})(?!\w)|"
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
    r"(?:"
    r"state\s+of\s+residence\s+within\s+the\s+united\s+states|"
    r"(?:must\s+(?:be\s+)?(?:reside|live|located|based)\s+in)\s+(?:the\s+)?(?:united\s+states|usa|uk|canada|europe|eu|brazil|brasil|india|north\s+america|\bu\.?\s?s\.?(?!\w))|"
    r"(?:candidates?|applicants?)\s+(?:who\s+)?(?:must\s+be\s+)?(?:reside|residing|live|living|located|based)\s+in\s+(?:the\s+)?(?:united\s+states|usa|uk|canada|europe|eu|brazil|brasil|india|north\s+america|\bu\.?\s?s\.?(?!\w))|"
    r"(?:role|position)\s+(?:requires\s+(?:you\s+to\s+be\s+)?(?:located|based|residing|living)\s+in|is\s+only\s+open\s+to\s+(?:candidates\s+in)?)\s+(?:the\s+)?(?:united\s+states|usa|uk|canada|europe|eu|brazil|brasil|\bu\.?\s?s\.?(?!\w))|"
    r"only\s+(?:hiring|open\s+to\s+candidates|able\s+to\s+hire|consider\s+candidates)\b|"
    r"residir\s+(?:en|no)\s+(?:brasil|brazil)|"
    r"contrato\s+clt|regime\s+clt|vaga\s+exclusiva\s+para\s+residentes|"
    r"requires?\s+on-site\s+availability|"
    r"required\s+clearance\s*:\s*(?:public\s+trust|secret|active\s+secret|top\s+secret)|"
    r"\bu\.?\s?s\.?(?!\w)\s+citizenship\s+(?:is\s+)?required|"
    r"\b(?:anywhere|everywhere)\s+in\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w))|"
    r"\b(?:united\s+states|\bu\.?\s?s\.?(?!\w))\s+(?:only|residents?\s+only|based\s+candidates\s+only|citizens?\s+only)\b|"
    r"\b(?:open|available)\s+(?:only\s+to|to)\s+(?:candidates\s+(?:based|located)\s+in\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w)))|"
    r"\b(?:remote\s+within\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w)))|"
    r"\b(?:remote\s*[-–,/|]\s*(?:anywhere\s+in\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w))|\(?us\s+only\)?))|"
    r"(?:location|workplace)\s*[:\s–-]+\s*(?:anywhere\s+in\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w))|(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w))\s+remote|remote\s*[,–-]\s*(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w)))|"
    r"(?:authorized|eligible|legally\s+(?:authorized|eligible|able))\s+to\s+work\s+in\s+(?:the\s+)?(?:united\s+states|usa|\bu\.?\s?s\.?(?!\w))|"
    r"work\s+in\s+the\s+us\s+without\s+sponsorship|"
    r"contingent\s+on\s+us\s+work\s+authorization|"
    r"\bu\.?\s?s\.?(?!\w)[-\s]based\s+(?:employees|candidates|applicants|workers|team|only)|"
    r"\bu\.?\s?s\.?(?!\w)\s+work\s+authorization"
    r")",
    re.IGNORECASE,
)

LATAM_COUNTRIES_LIST = [
    "argentina", "bolivia", "brazil", "brasil", "chile", "colombia", "costa rica", "ecuador",
    "el salvador", "guatemala", "honduras", "mexico", "méxico", "nicaragua", "panama", "panamá",
    "paraguay", "peru", "perú", "dominican republic", "uruguay", "venezuela"
]

LATAM_KEYWORDS = [
    "latam", r"latin\s+america", r"south\s+america"
] + [re.escape(c).replace(r"\ ", r"\s+") for c in LATAM_COUNTRIES_LIST]

LATAM_RE = re.compile(r"\b(" + "|".join(LATAM_KEYWORDS) + r")\b", re.IGNORECASE)

NORTH_AMERICA_RE = re.compile(
    r"\b(united\s+states|usa|u\.s\.?|us|canada|toronto|vancouver|montreal|north\s+america)\b",
    re.IGNORECASE
)

OTHER_REGIONS_RESTRICTED_RE = re.compile(
    r"\b(uk|united\s+kingdom|england|london|manchester|scotland|"
    r"europe|european\s+union|eu\s+remote|emea|cet|"
    r"germany|berlin|munich|france|paris|spain|madrid|barcelona|italy|rome|ireland|dublin|"
    r"netherlands|amsterdam|belgium|sweden|stockholm|switzerland|zurich|denmark|copenhagen|"
    r"poland|warsaw|serbia|belgrade|cyprus|romania|bulgaria|georgia|ukraine|kyiv|czech|prague|armenia|"
    r"finland|espoo|helsinki|norway|oslo|austria|vienna|hungary|budapest|israel|tel\s+aviv|"
    r"china|guangdong|beijing|shanghai|shenzhen|hong\s+kong|"
    r"india|ind-remote|bengaluru|bangalore|hyderabad|pune|mumbai|"
    r"philippines|manila|apac|vietnam|japan|tokyo|singapore|taiwan|south\s+korea|korea|pangyo|malaysia|kuala\s+lumpur|australia|sydney|melbourne|new\s+zealand|auckland)\b",
    re.IGNORECASE,
)

COUNTRY_SYNONYMS = {
    "alemania": ["alemania", "germany", "deutschland", "berlin", "munich"],
    "germany": ["alemania", "germany", "deutschland", "berlin", "munich"],
    "japon": ["japon", "japón", "japan", "tokyo"],
    "japón": ["japon", "japón", "japan", "tokyo"],
    "japan": ["japon", "japón", "japan", "tokyo"],
    "espana": ["españa", "espana", "spain", "madrid", "barcelona"],
    "españa": ["españa", "espana", "spain", "madrid", "barcelona"],
    "spain": ["españa", "espana", "spain", "madrid", "barcelona"],
    "estados unidos": ["estados unidos", "united states", "usa", "us"],
    "united states": ["estados unidos", "united states", "usa", "us"],
    "reino unido": ["reino unido", "united kingdom", "uk", "great britain", "england", "london"],
    "united kingdom": ["reino unido", "united kingdom", "uk", "great britain", "england", "london"],
    "paises bajos": ["paises bajos", "países bajos", "netherlands", "holland", "amsterdam"],
    "países bajos": ["paises bajos", "países bajos", "netherlands", "holland", "amsterdam"],
    "netherlands": ["paises bajos", "países bajos", "netherlands", "holland", "amsterdam"],
    "brasil": ["brasil", "brazil", "sao paulo", "rio"],
    "brazil": ["brasil", "brazil", "sao paulo", "rio"],
    "mexico": ["mexico", "méxico"],
    "méxico": ["mexico", "méxico"],
    "canada": ["canada", "canadá", "toronto", "vancouver", "montreal"],
    "canadá": ["canada", "canadá", "toronto", "vancouver", "montreal"],
    "italia": ["italia", "italy", "rome", "milan"],
    "italy": ["italia", "italy", "rome", "milan"],
    "francia": ["francia", "france", "paris"],
    "france": ["francia", "france", "paris"],
    "suecia": ["suecia", "sweden", "stockholm"],
    "sweden": ["suecia", "sweden", "stockholm"],
    "suiza": ["suiza", "switzerland", "zurich", "geneva"],
    "switzerland": ["suiza", "switzerland", "zurich", "geneva"],
    "irlanda": ["irlanda", "ireland", "dublin"],
    "ireland": ["irlanda", "ireland", "dublin"],
    "polonia": ["polonia", "poland", "warsaw"],
    "poland": ["polonia", "poland", "warsaw"],
    "portugal": ["portugal", "lisbon", "porto"],
    "noruega": ["noruega", "norway", "oslo"],
    "norway": ["noruega", "norway", "oslo"],
    "dinamarca": ["dinamarca", "denmark", "copenhagen"],
    "denmark": ["dinamarca", "denmark", "copenhagen"],
    "finlandia": ["finlandia", "finland", "helsinki"],
    "finland": ["finlandia", "finland", "helsinki"],
    "belgica": ["bélgica", "belgica", "belgium", "brussels"],
    "bélgica": ["bélgica", "belgica", "belgium", "brussels"],
    "belgium": ["bélgica", "belgica", "belgium", "brussels"],
    "austria": ["austria", "vienna"],
    "republica checa": ["república checa", "republica checa", "czech republic", "czechia", "prague"],
    "república checa": ["república checa", "republica checa", "czech republic", "czechia", "prague"],
    "czech republic": ["república checa", "republica checa", "czech republic", "czechia", "prague"],
    "corea del sur": ["corea del sur", "south korea", "korea", "seoul"],
    "south korea": ["corea del sur", "south korea", "korea", "seoul"],
    "emiratos arabes unidos": ["emiratos árabes unidos", "emiratos arabes unidos", "united arab emirates", "uae", "dubai", "abu dhabi"],
    "emiratos árabes unidos": ["emiratos árabes unidos", "emiratos arabes unidos", "united arab emirates", "uae", "dubai", "abu dhabi"],
    "united arab emirates": ["emiratos árabes unidos", "emiratos arabes unidos", "united arab emirates", "uae", "dubai", "abu dhabi"],
    "nueva zelanda": ["nueva zelanda", "new zealand", "auckland"],
    "new zealand": ["nueva zelanda", "new zealand", "auckland"],
    "sudafrica": ["sudáfrica", "sudafrica", "south africa", "cape town", "johannesburg"],
    "sudáfrica": ["sudáfrica", "sudafrica", "south africa", "cape town", "johannesburg"],
    "south africa": ["sudáfrica", "sudafrica", "south africa", "cape town", "johannesburg"],
    "singapur": ["singapur", "singapore"],
    "singapore": ["singapur", "singapore"],
    "filipinas": ["filipinas", "philippines", "manila"],
    "philippines": ["filipinas", "philippines", "manila"],
    "ucrania": ["ucrania", "ukraine", "kyiv"],
    "ukraine": ["ucrania", "ukraine", "kyiv"],
    "peru": ["perú", "peru", "lima"],
    "perú": ["perú", "peru", "lima"],
    "uruguay": ["uruguay", "montevideo"],
    "argentina": ["argentina", "buenos aires"],
    "chile": ["chile", "santiago"],
    "colombia": ["colombia", "bogota", "bogotá", "medellin", "medellín"],
}

def expand_country_terms(countries: Optional[List[str]]) -> List[str]:
    """Expands country names into bilingual search terms."""
    if not countries:
        return []
    result = set()
    for c in countries:
        if not c or not c.strip():
            continue
        cleaned = c.strip().lower()
        result.add(cleaned)
        if cleaned in COUNTRY_SYNONYMS:
            result.update(COUNTRY_SYNONYMS[cleaned])
        else:
            unaccented = unicodedata.normalize("NFKD", cleaned).encode("ascii", "ignore").decode("utf-8")
            if unaccented in COUNTRY_SYNONYMS:
                result.update(COUNTRY_SYNONYMS[unaccented])
    return list(result)

def build_home_region_re(home_terms: Optional[List[str]] = None) -> re.Pattern:
    """Regex matching candidate's region: LATAM terms plus candidate city/country from profile."""
    terms = ["latam", r"latin\s+america", r"south\s+america"]
    for t in home_terms or []:
        t = (t or "").strip()
        if t:
            escaped = re.escape(t.lower()).replace(r"\ ", r"\s+")
            if escaped not in terms:
                terms.append(escaped)
    return re.compile(r"\b(" + "|".join(terms) + r")\b", re.IGNORECASE)


def build_home_only_re(home_terms: Optional[List[str]] = None) -> re.Pattern:
    """Regex matching only the candidate's own city/country declared in profile."""
    terms = [re.escape((t or "").strip().lower()).replace(r"\ ", r"\s+") for t in (home_terms or []) if (t or "").strip()]
    if not terms:
        return re.compile(r"(?!x)x")
    return re.compile(r"\b(" + "|".join(terms) + r")\b", re.IGNORECASE)


ROLE_ACRONYM_MAP = {
    "qa": re.compile(r"\b(qa|quality\s+assurance)\b", re.IGNORECASE),
    "quality assurance": re.compile(r"\b(qa|quality\s+assurance)\b", re.IGNORECASE),
    "qc": re.compile(r"\b(qc|quality\s+control)\b", re.IGNORECASE),
    "quality control": re.compile(r"\b(qc|quality\s+control)\b", re.IGNORECASE),
    "qe": re.compile(r"\b(qe|quality\s+engineer(?:ing)?)\b", re.IGNORECASE),
    "quality engineer": re.compile(r"\b(qe|quality\s+engineer(?:ing)?)\b", re.IGNORECASE),
    "quality engineering": re.compile(r"\b(qe|quality\s+engineer(?:ing)?)\b", re.IGNORECASE),
    "qia": re.compile(r"\b(qia|quality\s+(?:ai|ia)|(?:ai|ia)\s+(?:qa|quality))\b", re.IGNORECASE),
    "quality ai": re.compile(r"\b(qia|quality\s+(?:ai|ia)|(?:ai|ia)\s+(?:qa|quality))\b", re.IGNORECASE),
    "quality ia": re.compile(r"\b(qia|quality\s+(?:ai|ia)|(?:ai|ia)\s+(?:qa|quality))\b", re.IGNORECASE),
    "ai qa": re.compile(r"\b(qia|quality\s+(?:ai|ia)|(?:ai|ia)\s+(?:qa|quality))\b", re.IGNORECASE),
    "sdet": re.compile(r"\b(sdet|software\s+(?:development\s+)?engineer\s+in\s+test)\b", re.IGNORECASE),
    "software engineer in test": re.compile(r"\b(sdet|software\s+(?:development\s+)?engineer\s+in\s+test)\b", re.IGNORECASE),
    "software development engineer in test": re.compile(r"\b(sdet|software\s+(?:development\s+)?engineer\s+in\s+test)\b", re.IGNORECASE),
    "test": re.compile(r"\b(tests?|testers?|testing)\b", re.IGNORECASE),
    "tester": re.compile(r"\b(tests?|testers?|testing)\b", re.IGNORECASE),
    "testing": re.compile(r"\b(tests?|testers?|testing)\b", re.IGNORECASE),
    "automation": re.compile(r"\b(automation|automated)\b", re.IGNORECASE),
    "quality": re.compile(r"\bquality\b", re.IGNORECASE),
}

GENERIC_ROLE_WORDS = {
    "engineer", "engineering", "senior", "sr", "junior", "jr", "lead", "staff",
    "principal", "manager", "analyst", "specialist", "developer", "software",
    "architect", "intern", "director", "vp", "head", "in", "and", "of", "for",
    "to", "ii", "iii", "iv", "mid", "tech", "level", "team", "group", "associate",
    "consultant", "expert",
}


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
        home_terms: Optional[List[str]] = None,
        geo_scope: Optional[str] = None,
        custom_countries: Optional[List[str]] = None,
        work_modes: Optional[List[str]] = None,
    ) -> List[JobPosting]:
        """Scan a single company job board and return matching postings."""
        pass

    def matches_keywords(self, title: str, keywords: List[str]) -> bool:
        """
        Check if job title matches target keywords, acronym expansions, or loose words.
        Supports single words, compound phrases, and acronym variants (QA, QC, QE, QIA, SDET).
        """
        if not keywords:
            return True
        t_str = (title or "").strip()
        t_lower = t_str.lower()
        for k in keywords:
            k_clean = (k or "").strip()
            if not k_clean:
                continue
            k_lower = k_clean.lower()

            # 1. Direct acronym expansions (e.g. QA, QC, QE, QIA, SDET, Quality Engineer, etc.)
            if k_lower in ROLE_ACRONYM_MAP:
                if ROLE_ACRONYM_MAP[k_lower].search(t_str):
                    return True

            # 2. Substring match
            if k_lower in t_lower:
                return True

            # 3. Tokenized matching (single words and compound phrases)
            k_words = [w for w in re.split(r"[\s/_\-]+", k_lower) if w]
            if len(k_words) == 1:
                w0 = k_words[0]
                if w0 in ROLE_ACRONYM_MAP and ROLE_ACRONYM_MAP[w0].search(t_str):
                    return True
                if re.search(r"\b" + re.escape(w0) + r"\b", t_lower):
                    return True
            elif len(k_words) > 1:
                # If compound chip contains a domain term (e.g. 'QA Automation', 'Test Engineer', 'Senior QA'),
                # check if any constituent matches a role acronym regex
                for w in k_words:
                    if w in ROLE_ACRONYM_MAP and ROLE_ACRONYM_MAP[w].search(t_str):
                        return True
                # Check significant non-generic words without requiring rigid multi-word exactness
                significant_words = [w for w in k_words if w not in GENERIC_ROLE_WORDS]
                if significant_words:
                    if all(w in t_lower for w in significant_words):
                        return True
                else:
                    if all(w in t_lower for w in k_words):
                        return True

        return False

    def detect_work_mode(self, title: str, location: str, description: str = "") -> str:
        """
        Detect whether a vacancy is remote, hybrid, or onsite based on title and location.
        Returns 'hybrid', 'onsite', or 'remote'.
        """
        t_str = (title or "").strip()
        loc_str = (location or "").strip()
        combined = f"{t_str} {loc_str}".strip()

        if HYBRID_RE.search(t_str) or HYBRID_RE.search(loc_str):
            return "hybrid"

        has_remote = bool(
            re.search(r"\b(remote|remoto)\b", combined, re.IGNORECASE)
            or re.search(r"\b(worldwide|global|anywhere)\b", loc_str, re.IGNORECASE)
        )
        is_explicit_onsite = bool(ONSITE_RE.search(t_str) or ONSITE_RE.search(loc_str))

        if is_explicit_onsite or (bool(loc_str) and not has_remote):
            return "onsite"

        return "remote"

    def matches_location(
        self,
        title: str,
        location: str,
        loc_keywords: List[str],
        description: str = "",
        home_terms: Optional[List[str]] = None,
        geo_scope: Optional[str] = None,
        custom_countries: Optional[List[str]] = None,
        work_modes: Optional[List[str]] = None,
    ) -> bool:
        """
        Check if location or title matches target location criteria while rejecting
        onsite positions, hybrid positions outside the candidate's home location, and restricted regions.
        """
        home_re = build_home_region_re(home_terms)
        home_only_re = build_home_only_re(home_terms)
        loc_str = (location or "").strip()
        t_str = (title or "").strip()
        desc_str = (description or "").strip()
        combined = f"{t_str} {loc_str}".strip()
        loc_lower = loc_str.lower()
        t_lower = t_str.lower()

        has_remote_indicator = bool(
            re.search(r"\b(remote|remoto)\b", combined, re.IGNORECASE)
            or re.search(r"\b(worldwide|global|anywhere)\b", loc_str, re.IGNORECASE)
        )
        is_explicit_onsite = bool(ONSITE_RE.search(t_str) or ONSITE_RE.search(loc_str))
        is_hybrid = bool(HYBRID_RE.search(t_str) or HYBRID_RE.search(loc_str))
        is_onsite = is_explicit_onsite or (bool(loc_str) and not has_remote_indicator and not is_hybrid)
        is_home = bool(home_only_re.search(combined))
        scope = (geo_scope or "").lower().strip()
        clean_countries = expand_country_terms(custom_countries) if custom_countries else []

        # 1. Work Mode Filtering (remote, hybrid, onsite)
        if work_modes is not None:
            modes = [m.lower().strip() for m in work_modes if m and m.strip()]
            if is_onsite:
                if "onsite" not in modes:
                    return False
                # If custom_countries is specified, only accept onsite in those specific countries
                if clean_countries:
                    country_patterns = [re.escape(c).replace(r"\ ", r"\s+") for c in clean_countries]
                    c_re = re.compile(r"\b(" + "|".join(country_patterns) + r")\b", re.IGNORECASE)
                    if not c_re.search(combined):
                        return False
                elif scope != "global" and not is_home:
                    if scope == "latam" and not LATAM_RE.search(combined):
                        return False
                    elif scope == "latam_na" and not (LATAM_RE.search(combined) or NORTH_AMERICA_RE.search(combined)):
                        return False
                    elif not scope:
                        return False

            if is_hybrid:
                if "hybrid" not in modes:
                    return False
                # If custom_countries is specified, only accept hybrid in those specific countries
                if clean_countries:
                    country_patterns = [re.escape(c).replace(r"\ ", r"\s+") for c in clean_countries]
                    c_re = re.compile(r"\b(" + "|".join(country_patterns) + r")\b", re.IGNORECASE)
                    if not c_re.search(combined):
                        return False
                elif scope != "global" and not is_home:
                    if scope == "latam" and not LATAM_RE.search(combined):
                        return False
                    elif scope == "latam_na" and not (LATAM_RE.search(combined) or NORTH_AMERICA_RE.search(combined)):
                        return False
                    elif not scope:
                        return False

            if not is_onsite and not is_hybrid:
                if "remote" not in modes:
                    return False
        else:
            # Legacy default: reject onsite unless local home, allow local hybrid, allow remote
            if is_onsite and not is_home:
                return False
            if is_hybrid and not is_home:
                return False

        # 2. Custom Countries (if user selected specific country tags)
        if clean_countries:
            country_patterns = [re.escape(c).replace(r"\ ", r"\s+") for c in clean_countries]
            custom_re = re.compile(r"\b(" + "|".join(country_patterns) + r")\b", re.IGNORECASE)
            if custom_re.search(combined):
                return True
            if not loc_str and desc_str and custom_re.search(desc_str):
                return True
            # Accept unconstrained global remote jobs (only if location field specifies global/worldwide)
            has_global_indicator = bool(re.search(r"\b(worldwide|global|anywhere)\b", loc_str, re.IGNORECASE))
            if has_global_indicator and not RESTRICTED_LOCATION_RE.search(loc_str):
                return True
            return False

        # 3. Geo Scope Resolution (when explicit geo_scope is specified)
        if geo_scope:
            if scope == "any":
                return "remote" in t_lower or "remote" in loc_lower or not (ONSITE_RE.search(t_str) or ONSITE_RE.search(loc_str))

            if scope == "latam":
                has_remote_indicator = bool(
                    re.search(r"\b(remote|remoto)\b", combined, re.IGNORECASE)
                    or re.search(r"\b(worldwide|global|anywhere|americas)\b", loc_str, re.IGNORECASE)
                )
                is_distributed_latam = bool(re.search(r"^\s*(?:latam|latin\s+america|south\s+america|americas)\s*$", loc_str, re.IGNORECASE))
                # For remote roles, reject physical non-local onsite
                if loc_str and not is_home and not has_remote_indicator and not is_distributed_latam and not (is_onsite and work_modes and "onsite" in work_modes):
                    return False

                if not loc_str:
                    if desc_str:
                        if self.has_residency_restriction(desc_str, loc_keywords, home_terms=home_terms):
                            return False
                        return bool(LATAM_RE.search(f"{t_str} {desc_str}")) or bool(re.search(r"\b(remote|remoto|worldwide|global|anywhere|americas)\b", f"{t_str} {desc_str}", re.IGNORECASE))
                    return bool(LATAM_RE.search(t_str)) or "remote" in t_lower

                if RESTRICTED_LOCATION_RE.search(loc_str) or RESTRICTED_LOCATION_RE.search(t_str):
                    if not LATAM_RE.search(combined):
                        return False

                if self.has_residency_restriction(desc_str, loc_keywords, home_terms=home_terms):
                    return False

                return bool(LATAM_RE.search(combined)) or is_home or has_remote_indicator

            if scope == "latam_na":
                has_remote_indicator = bool(
                    re.search(r"\b(remote|remoto)\b", combined, re.IGNORECASE)
                    or re.search(r"\b(worldwide|global|anywhere|americas)\b", loc_str, re.IGNORECASE)
                )
                is_distributed_latam = bool(re.search(r"^\s*(?:latam|latin\s+america|south\s+america|americas)\s*$", loc_str, re.IGNORECASE))
                if loc_str and not is_home and not has_remote_indicator and not is_distributed_latam and not (is_onsite and work_modes and "onsite" in work_modes):
                    return False

                if not loc_str:
                    if desc_str:
                        if self.has_residency_restriction(desc_str, loc_keywords, home_terms=home_terms):
                            return False
                        return bool(LATAM_RE.search(desc_str) or NORTH_AMERICA_RE.search(desc_str) or "remote" in desc_str.lower())
                    return bool(LATAM_RE.search(t_str) or NORTH_AMERICA_RE.search(t_str) or "remote" in t_lower)

                if OTHER_REGIONS_RESTRICTED_RE.search(loc_str) or OTHER_REGIONS_RESTRICTED_RE.search(t_str):
                    if not LATAM_RE.search(combined):
                        return False

                if self.has_residency_restriction(desc_str, loc_keywords, home_terms=home_terms):
                    return False

                is_na = bool(NORTH_AMERICA_RE.search(combined))
                is_latam = bool(LATAM_RE.search(combined))
                return is_latam or is_na or is_home or has_remote_indicator

            if scope == "global":
                has_remote_indicator = bool(
                    re.search(r"\b(remote|remoto)\b", combined, re.IGNORECASE)
                    or re.search(r"\b(worldwide|global|anywhere)\b", loc_str, re.IGNORECASE)
                )
                if loc_str and not is_home and not has_remote_indicator and not (is_onsite and work_modes and "onsite" in work_modes):
                    return False

                if not loc_str:
                    if desc_str and self.has_residency_restriction(desc_str, loc_keywords, home_terms=home_terms):
                        return False
                    return True

                if self.has_residency_restriction(desc_str, loc_keywords, home_terms=home_terms):
                    return False

                return True

        # 4. Legacy Keyword-based Resolution (matches existing tests and profile defaults)
        if loc_keywords:
            if any(k.lower() in ("all", "any", "*") for k in loc_keywords):
                return "remote" in t_lower or "remote" in loc_lower or not (ONSITE_RE.search(t_str) or ONSITE_RE.search(loc_str))

            if not loc_str:
                if desc_str:
                    if self.has_residency_restriction(desc_str, loc_keywords, home_terms=home_terms):
                        return False
                    if (RESTRICTED_LOCATION_RE.search(desc_str) or ONSITE_RE.search(desc_str)) and not home_re.search(desc_str):
                        return False
                    if LATAM_OR_GLOBAL_RE.search(desc_str) or LATAM_OR_GLOBAL_RE.search(t_str):
                        wants_global = any(k.lower() in ("remote", "worldwide", "global", "anywhere") for k in loc_keywords)
                        if not wants_global:
                            return bool(home_re.search(f"{t_str} {desc_str}"))
                        return True
                    if any(k.lower() in desc_str.lower() or k.lower() in t_lower for k in loc_keywords):
                        return True
                else:
                    if RESTRICTED_LOCATION_RE.search(t_str) and not home_re.search(t_str):
                        return False
                    if LATAM_OR_GLOBAL_RE.search(t_str):
                        wants_global = any(k.lower() in ("remote", "worldwide", "global", "anywhere") for k in loc_keywords)
                        if not wants_global:
                            return bool(home_re.search(t_str))
                        return True
                    if any(k.lower() in t_lower for k in loc_keywords):
                        return True
                return False

            has_remote_indicator = bool(re.search(r"\b(remote|remoto|worldwide|global|anywhere)\b", combined, re.IGNORECASE))
            is_distributed_latam = bool(re.search(r"^\s*(?:latam|latin\s+america|south\s+america)\s*$", loc_str, re.IGNORECASE))
            if loc_str and not is_home and not has_remote_indicator and not is_distributed_latam:
                return False

            is_restricted = bool(RESTRICTED_LOCATION_RE.search(loc_str) or RESTRICTED_LOCATION_RE.search(t_str))
            if is_restricted:
                if not home_re.search(combined):
                    return False
                return True

            if LATAM_OR_GLOBAL_RE.search(combined):
                wants_global = any(k.lower() in ("remote", "worldwide", "global", "anywhere") for k in loc_keywords)
                if not wants_global:
                    return bool(home_re.search(combined))
                return True

            return any(k.lower() in loc_lower or k.lower() in t_lower for k in loc_keywords)

        return "remote" in t_lower or "remote" in loc_lower


    def has_residency_restriction(self, text: str, location_keywords: Optional[List[str]] = None, home_terms: Optional[List[str]] = None) -> bool:
        """Return True if the job description or form questions contain a US/EU/UK residency or clearance restriction."""
        if location_keywords and any(k.lower() in ("all", "any", "*") for k in location_keywords):
            return False
        if not text:
            return False
        clean_text = re.sub(r"<[^>]+>", " ", text)
        if not RESIDENCY_RESTRICTION_RE.search(clean_text):
            return False
        # Do not treat as restricted if the candidate's region is explicitly supported
        if build_home_region_re(home_terms).search(clean_text):
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

