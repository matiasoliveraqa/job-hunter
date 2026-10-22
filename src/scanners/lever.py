"""
Lever ATS Job Board Scanner.
"""

from typing import List, Optional
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
        location_keywords: List[str],
        max_years_experience: Optional[int] = None,
    ) -> List[JobPosting]:
        url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
        postings: List[JobPosting] = []
        timeout = aiohttp.ClientTimeout(total=12, sock_connect=5, sock_read=8)
        try:
            async with session.get(url, timeout=timeout) as resp:
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
                        lists_text = " ".join(
                            f"{lst.get('text', '')} {lst.get('content', '')}"
                            for lst in (j.get("lists") or [])
                            if isinstance(lst, dict)
                        )
                        desc = (
                            f"{title} "
                            f"{j.get('descriptionPlain') or ''} "
                            f"{j.get('description') or ''} "
                            f"{lists_text}"
                        )
                        if not self.matches_experience(desc, max_years_experience):
                            continue

                        req_years = self.extract_required_years(desc)
                        postings.append(JobPosting(
                            ats=self.platform,
                            company=company_slug,
                            title=title,
                            location=loc.strip(),
                            url=j.get("hostedUrl") or f"https://jobs.lever.co/{company_slug}/{j.get('id')}",
                            required_years=req_years
                        ))
        except Exception:
            pass
        return postings
