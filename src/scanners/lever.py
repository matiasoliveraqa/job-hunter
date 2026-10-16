"""
Lever ATS Job Board Scanner.
"""

from typing import List
import aiohttp
from src.scanners.base import BaseScanner
from src.core.models import JobPosting, ATSPlatform

class LeverScanner(BaseScanner):
    def __init__(self):
        super().__init__(ATSPlatform.LEVER)

    async def scan_company(
        self,
        session: aiohttp.ClientSession,
        company_slug: str,
        role_keywords: List[str],
        location_keywords: List[str]
    ) -> List[JobPosting]:
        url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
        postings: List[JobPosting] = []
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    return []
                jobs = await resp.json()
                if not isinstance(jobs, list):
                    return []
                for j in jobs:
                    title = j.get("text", "")
                    cats = j.get("categories", {})
                    loc = (cats.get("location") or "") + " " + (cats.get("workplaceType") or "")
                    
                    if self.matches_keywords(title, role_keywords) and self.matches_location(title, loc, location_keywords):
                        postings.append(JobPosting(
                            ats=self.platform,
                            company=company_slug,
                            title=title,
                            location=loc.strip(),
                            url=j.get("hostedUrl") or f"https://jobs.lever.co/{company_slug}/{j.get('id')}"
                        ))
        except Exception:
            pass
        return postings
