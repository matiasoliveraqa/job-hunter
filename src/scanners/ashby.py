"""
Ashby ATS Job Board Scanner.
"""

from typing import List
import aiohttp
from src.scanners.base import BaseScanner
from src.core.models import JobPosting, ATSPlatform

class AshbyScanner(BaseScanner):
    def __init__(self):
        super().__init__(ATSPlatform.ASHBY)

    async def scan_company(
        self,
        session: aiohttp.ClientSession,
        company_slug: str,
        role_keywords: List[str],
        location_keywords: List[str]
    ) -> List[JobPosting]:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}"
        postings: List[JobPosting] = []
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                jobs = data.get("jobs", [])
                for j in jobs:
                    title = j.get("title", "")
                    loc = j.get("location") or ""
                    
                    if self.matches_keywords(title, role_keywords) and self.matches_location(title, loc, location_keywords):
                        job_url = j.get("jobUrl") or f"https://jobs.ashbyhq.com/{company_slug}/{j.get('id')}"
                        postings.append(JobPosting(
                            ats=self.platform,
                            company=company_slug,
                            title=title,
                            location=loc,
                            url=job_url
                        ))
        except Exception:
            pass
        return postings
