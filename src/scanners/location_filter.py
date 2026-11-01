"""
Location, experience, and title filtering algorithms for job scanners.
"""

import re
import unicodedata
from typing import List, Optional

from src.scanners.constants import (
    COUNTRY_SYNONYMS,
    EXPERIENCE_PATTERNS,
    GENERIC_ROLE_WORDS,
    HYBRID_RE,
    LATAM_OR_GLOBAL_RE,
    LATAM_RE,
    NORTH_AMERICA_RE,
    ONSITE_RE,
    OTHER_REGIONS_RESTRICTED_RE,
    RESIDENCY_RESTRICTION_RE,
    RESTRICTED_LOCATION_RE,
    ROLE_ACRONYM_MAP,
)


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


def format_company_name(name: str) -> str:
    """Format company slug or raw name so each word starts with a capital letter."""
    if not name:
        return ""
    return re.sub(r"(^|[\s\-_]+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), name)


class ScannerFilterMixin:
    """Provides filtering and qualification methods for ATS job postings."""

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
                # If compound chip contains a domain term, check acronym regex
                for w in k_words:
                    if w in ROLE_ACRONYM_MAP and ROLE_ACRONYM_MAP[w].search(t_str):
                        return True
                # Check significant non-generic words
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
        onsite positions, hybrid positions outside candidate's home location, and restricted regions.
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
            if is_onsite and not is_home:
                return False
            if is_hybrid and not is_home:
                return False

        # 2. Custom Countries
        if clean_countries:
            country_patterns = [re.escape(c).replace(r"\ ", r"\s+") for c in clean_countries]
            custom_re = re.compile(r"\b(" + "|".join(country_patterns) + r")\b", re.IGNORECASE)
            if custom_re.search(combined):
                return True
            if not loc_str and desc_str and custom_re.search(desc_str):
                return True
            has_global_indicator = bool(re.search(r"\b(worldwide|global|anywhere)\b", loc_str, re.IGNORECASE))
            if has_global_indicator and not RESTRICTED_LOCATION_RE.search(loc_str):
                return True
            return False

        # 3. Geo Scope Resolution
        if geo_scope:
            if scope == "any":
                return "remote" in t_lower or "remote" in loc_lower or not (ONSITE_RE.search(t_str) or ONSITE_RE.search(loc_str))

            if scope == "latam":
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

        # 4. Legacy Keyword-based Resolution
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

    def has_residency_restriction(
        self,
        text: str,
        location_keywords: Optional[List[str]] = None,
        home_terms: Optional[List[str]] = None,
    ) -> bool:
        """Return True if the job description or form questions contain a US/EU/UK residency or clearance restriction."""
        if location_keywords and any(k.lower() in ("all", "any", "*") for k in location_keywords):
            return False
        if not text:
            return False
        clean_text = re.sub(r"<[^>]+>", " ", text)
        if not RESIDENCY_RESTRICTION_RE.search(clean_text):
            return False
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
