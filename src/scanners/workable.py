"""
Workable ATS Job Board Scanner.
"""

from typing import List, Optional
import aiohttp
from src.scanners.base import BaseScanner, format_company_name
from src.core.models import JobPosting, ATSPlatform

class WorkableScanner(BaseScanner):
    def __init__(self):
        super().__init__(ATSPlatform.WORKABLE)

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
        url = f"https://apply.workable.com/api/v1/widget/accounts/{company_slug}"
        postings: List[JobPosting] = []
        timeout = aiohttp.ClientTimeout(total=12, sock_connect=5, sock_read=8)

        try:
            async with session.get(url, timeout=timeout) as resp:
                if resp.status == 404:
                    # Fallback to accounts v3 endpoint
                    v3_url = f"https://apply.workable.com/api/v3/accounts/{company_slug}/jobs"
                    async with session.post(v3_url, json={}, timeout=timeout) as v3_resp:
                        if v3_resp.status != 200:
                            return []
                        data = await v3_resp.json()
                        jobs = data.get("results") or []
                elif resp.status != 200:
                    return []
                else:
                    data = await resp.json()
                    jobs = data.get("jobs") or []

                for j in jobs:
                    title = j.get("title", "")
                    shortcode = j.get("shortcode") or str(j.get("id") or "")

                    # Extract location components
                    city = j.get("city") or (j.get("location") or {}).get("city") or ""
                    country = j.get("country") or (j.get("location") or {}).get("country") or ""
                    is_telecommuting = j.get("telecommuting") or (j.get("location") or {}).get("telecommuting") or False
                    workplace = (j.get("workplace") or "").lower()

                    loc_parts = [p for p in (city, country) if p]
                    loc = ", ".join(loc_parts)

                    if (is_telecommuting or workplace == "remote") and "remote" not in loc.lower():
                        loc = f"{loc} (Remote)".strip()

                    desc = f"{title} {j.get('description', '')} {j.get('requirements', '')} {j.get('benefits', '')}"

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
                        job_url = j.get("url") or f"https://apply.workable.com/{company_slug}/j/{shortcode}/"

                        postings.append(JobPosting(
                            ats=self.platform,
                            company=format_company_name(company_slug),
                            title=title,
                            location=loc,
                            url=job_url,
                            required_years=req_years,
                            work_mode=self.detect_work_mode(title, loc, desc),
                            has_captcha=True,
                        ))
        except Exception:
            pass

        return postings
