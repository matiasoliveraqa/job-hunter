"""
Ashby ATS Job Board Scanner.
"""

from typing import List, Optional
import aiohttp
from src.scanners.base import BaseScanner, format_company_name
from src.core.models import JobPosting, ATSPlatform

class AshbyScanner(BaseScanner):
    def __init__(self):
        super().__init__(ATSPlatform.ASHBY)

    async def scan_company(
        self,
        session: aiohttp.ClientSession,
        company_slug: str,
        role_keywords: List[str],
        location_keywords: List[str],
        max_years_experience: Optional[int] = None,
    ) -> List[JobPosting]:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}"
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
                    loc = j.get("location") or ""
                    addr_country = ((j.get("address") or {}).get("postalAddress") or {}).get("addressCountry") or ""
                    if addr_country and addr_country.lower() not in loc.lower():
                        loc = f"{loc}, {addr_country}".strip(", ")
                    if j.get("isRemote") is False and not any(r in loc.lower() for r in ("remote", "worldwide", "global", "uruguay", "montevideo")):
                        continue

                    if j.get("isRemote") and "remote" not in loc.lower():
                        loc = f"{loc} (Remote)".strip()

                    desc = (
                        f"{title} "
                        f"{j.get('descriptionPlain') or ''} "
                        f"{j.get('descriptionHtml') or ''}"
                    )
                    if self.matches_keywords(title, role_keywords) and self.matches_location(title, loc, location_keywords, description=desc):
                        if self.has_residency_restriction(desc, location_keywords):
                            continue
                        if not self.matches_experience(desc, max_years_experience):
                            continue

                        req_years = self.extract_required_years(desc)
                        job_url = j.get("jobUrl") or f"https://jobs.ashbyhq.com/{company_slug}/{j.get('id')}"
                        postings.append(JobPosting(
                            ats=self.platform,
                            company=format_company_name(company_slug),
                            title=title,
                            location=loc,
                            url=job_url,
                            required_years=req_years
                        ))
        except Exception:
            pass
        return postings
