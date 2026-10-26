"""
Greenhouse ATS Job Board Scanner.
"""

from typing import List, Optional
import aiohttp
from src.scanners.base import BaseScanner, format_company_name
from src.core.models import JobPosting, ATSPlatform

class GreenhouseScanner(BaseScanner):
    def __init__(self):
        super().__init__(ATSPlatform.GREENHOUSE)

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
        url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs?content=true"
        postings: List[JobPosting] = []
        timeout = aiohttp.ClientTimeout(total=12, sock_connect=5, sock_read=8)
        try:
            async with session.get(url, timeout=timeout) as resp:
                if resp.status in (406, 429):
                    raise aiohttp.ClientResponseError(
                        resp.request_info,
                        resp.history,
                        status=resp.status,
                        message=f"Rate limit / WAF block (HTTP {resp.status})",
                    )
                if resp.status != 200:
                    return []
                data = await resp.json()
                jobs = data.get("jobs", [])
                for j in jobs:
                    title = j.get("title", "")
                    loc_obj = j.get("location", {})
                    loc_name = loc_obj.get("name") if isinstance(loc_obj, dict) else str(loc_obj) or ""

                    desc_text = f"{title} {j.get('content') or ''}"
                    if self.matches_keywords(title, role_keywords) and self.matches_location(
                        title,
                        loc_name,
                        location_keywords,
                        description=desc_text,
                        home_terms=home_terms,
                        geo_scope=geo_scope,
                        custom_countries=custom_countries,
                        work_modes=work_modes,
                    ):
                        job_id = j.get("id")

                        if self.has_residency_restriction(desc_text, location_keywords, home_terms=home_terms):
                            continue
                        if not self.matches_experience(desc_text, max_years_experience):
                            continue

                        req_years = self.extract_required_years(desc_text)
                        abs_url = j.get("absolute_url") or ""
                        if "greenhouse.io" in abs_url:
                            job_url = abs_url
                        elif job_id:
                            job_url = f"https://job-boards.greenhouse.io/{company_slug}/jobs/{job_id}"
                        else:
                            job_url = abs_url

                        postings.append(JobPosting(
                            ats=self.platform,
                            company=format_company_name(company_slug),
                            title=title,
                            location=loc_name,
                            url=job_url,
                            required_years=req_years
                        ))
        except aiohttp.ClientResponseError as e:
            if e.status in (406, 429):
                raise
        except Exception:
            pass
        return postings
