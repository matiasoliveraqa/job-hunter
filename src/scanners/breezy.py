"""
Breezy HR ATS Job Board Scanner.
"""

from typing import List, Optional
import aiohttp
from src.scanners.base import BaseScanner, format_company_name
from src.core.models import JobPosting, ATSPlatform

class BreezyScanner(BaseScanner):
    def __init__(self):
        super().__init__(ATSPlatform.BREEZY)

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
        url = f"https://{company_slug}.breezy.hr/json"
        postings: List[JobPosting] = []
        timeout = aiohttp.ClientTimeout(total=12, sock_connect=5, sock_read=8)

        try:
            async with session.get(url, timeout=timeout) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                jobs = data if isinstance(data, list) else data.get("jobs", [])

                for j in jobs:
                    title = j.get("name") or j.get("title", "")
                    job_id = j.get("id") or j.get("friendly_id") or ""

                    loc_obj = j.get("location") or {}
                    if isinstance(loc_obj, dict):
                        loc_name = loc_obj.get("name") or ""
                        is_remote = loc_obj.get("is_remote", False)
                    else:
                        loc_name = str(loc_obj)
                        is_remote = False

                    if is_remote and "remote" not in loc_name.lower():
                        loc_name = f"{loc_name} (Remote)".strip()

                    desc = f"{title} {j.get('description', '')}"

                    if self.matches_keywords(title, role_keywords) and self.matches_location(
                        title,
                        loc_name,
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
                        job_url = j.get("url") or f"https://{company_slug}.breezy.hr/p/{job_id}"

                        postings.append(JobPosting(
                            ats=self.platform,
                            company=format_company_name(company_slug),
                            title=title,
                            location=loc_name,
                            url=job_url,
                            required_years=req_years
                        ))
        except Exception:
            pass

        return postings
