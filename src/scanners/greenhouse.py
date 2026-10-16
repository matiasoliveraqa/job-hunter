"""
Greenhouse ATS Job Board Scanner.
"""

from typing import List
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
        location_keywords: List[str]
    ) -> List[JobPosting]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs"
        postings: List[JobPosting] = []
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                jobs = data.get("jobs", [])
                for j in jobs:
                    title = j.get("title", "")
                    loc_obj = j.get("location", {})
                    loc_name = loc_obj.get("name") if isinstance(loc_obj, dict) else str(loc_obj) or ""
                    
                    if self.matches_keywords(title, role_keywords) and self.matches_location(title, loc_name, location_keywords):
                        postings.append(JobPosting(
                            ats=self.platform,
                            company=company_slug,
                            title=title,
                            location=loc_name,
                            url=j.get("absolute_url") or f"https://job-boards.greenhouse.io/{company_slug}/jobs/{j.get('id')}"
                        ))
        except Exception:
            pass
        return postings
