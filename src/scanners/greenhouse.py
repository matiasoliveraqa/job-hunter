"""
Greenhouse ATS Job Board Scanner.
"""

from typing import List, Optional
import aiohttp
from src.scanners.base import BaseScanner
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
    ) -> List[JobPosting]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs"
        postings: List[JobPosting] = []
        timeout = aiohttp.ClientTimeout(total=12, sock_connect=5, sock_read=8)
        try:
            async with session.get(url, timeout=timeout) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                jobs = data.get("jobs", [])
                for j in jobs:
                    title = j.get("title", "")
                    loc_obj = j.get("location", {})
                    loc_name = loc_obj.get("name") if isinstance(loc_obj, dict) else str(loc_obj) or ""

                    if self.matches_keywords(title, role_keywords) and self.matches_location(title, loc_name, location_keywords):
                        job_id = j.get("id")
                        desc_text = f"{title} {j.get('content') or ''}"

                        # If experience filter is set and content wasn't in list payload, fetch job detail
                        if max_years_experience is not None and not j.get("content") and job_id:
                            detail_url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs/{job_id}"
                            try:
                                async with session.get(detail_url, timeout=timeout) as d_resp:
                                    if d_resp.status == 200:
                                        d_data = await d_resp.json()
                                        desc_text = f"{title} {d_data.get('content') or ''}"
                            except Exception:
                                pass

                        if not self.matches_experience(desc_text, max_years_experience):
                            continue

                        req_years = self.extract_required_years(desc_text)
                        postings.append(JobPosting(
                            ats=self.platform,
                            company=company_slug,
                            title=title,
                            location=loc_name,
                            url=j.get("absolute_url") or f"https://job-boards.greenhouse.io/{company_slug}/jobs/{job_id}",
                            required_years=req_years
                        ))
        except Exception:
            pass
        return postings
