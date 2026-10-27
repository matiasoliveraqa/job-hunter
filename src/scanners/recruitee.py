"""
Recruitee ATS Job Board Scanner.
"""

from typing import List, Optional
import aiohttp
from src.scanners.base import BaseScanner, format_company_name
from src.core.models import JobPosting, ATSPlatform

class RecruiteeScanner(BaseScanner):
    def __init__(self):
        super().__init__(ATSPlatform.RECRUITEE)

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
        url = f"https://{company_slug}.recruitee.com/api/offers/"
        postings: List[JobPosting] = []
        timeout = aiohttp.ClientTimeout(total=12, sock_connect=5, sock_read=8)

        try:
            async with session.get(url, timeout=timeout) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                offers = data.get("offers", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

                for o in offers:
                    title = o.get("title", "")
                    slug = o.get("slug") or str(o.get("id") or "")

                    loc = o.get("location") or ""
                    country_code = o.get("country_code") or ""
                    if country_code and country_code.lower() not in loc.lower():
                        loc = f"{loc}, {country_code}".strip(", ")

                    is_remote = o.get("remote", False)
                    if is_remote and "remote" not in loc.lower():
                        loc = f"{loc} (Remote)".strip()

                    desc = f"{title} {o.get('description', '')} {o.get('requirements', '')}"

                    if self.matches_keywords(title, role_keywords) and self.matches_location(
                        title,
                        loc,
                        location_keywords,
                        description=desc,
                        home_terms=home_terms,
                        geo_scope=geo_scope,
                        custom_countries=custom_countries,
                        work_modes=work_modes,
                    ):
                        if self.has_residency_restriction(desc, location_keywords, home_terms=home_terms):
                            continue
                        if not self.matches_experience(desc, max_years_experience):
                            continue

                        req_years = self.extract_required_years(desc)
                        job_url = o.get("careers_url") or f"https://{company_slug}.recruitee.com/o/{slug}"

                        postings.append(JobPosting(
                            ats=self.platform,
                            company=format_company_name(company_slug),
                            title=title,
                            location=loc,
                            url=job_url,
                            required_years=req_years,
                            work_mode=self.detect_work_mode(title, loc, desc),
                        ))
        except Exception:
            pass

        return postings
