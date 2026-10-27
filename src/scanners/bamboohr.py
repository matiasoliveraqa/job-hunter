"""
BambooHR ATS Job Board Scanner.
"""

from typing import List, Optional
import aiohttp
from src.scanners.base import BaseScanner, format_company_name
from src.core.models import JobPosting, ATSPlatform

class BambooHRScanner(BaseScanner):
    def __init__(self):
        super().__init__(ATSPlatform.BAMBOOHR)

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
        url = f"https://{company_slug}.bamboohr.com/careers/list"
        postings: List[JobPosting] = []
        timeout = aiohttp.ClientTimeout(total=12, sock_connect=5, sock_read=8)

        try:
            async with session.get(url, timeout=timeout) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                jobs = data.get("result", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

                for j in jobs:
                    title = j.get("jobOpeningName") or j.get("title") or ""
                    job_id = str(j.get("id") or "")

                    loc_obj = j.get("location") or {}
                    ats_loc_obj = j.get("atsLocation") or {}
                    parts = []
                    if isinstance(loc_obj, dict):
                        parts.extend([loc_obj.get("city"), loc_obj.get("state"), loc_obj.get("country")])
                    elif loc_obj:
                        parts.append(str(loc_obj))
                    if isinstance(ats_loc_obj, dict):
                        for k in ["city", "state", "province", "country"]:
                            val = ats_loc_obj.get(k)
                            if val and val not in parts:
                                parts.append(val)
                    loc = ", ".join(p for p in parts if p)

                    is_remote = (
                        bool(j.get("isRemote"))
                        or bool(j.get("is_remote"))
                        or str(j.get("locationType", "")) in ("1", "remote")
                    )
                    if is_remote and "remote" not in loc.lower():
                        loc = f"{loc} (Remote)".strip() if loc else "Remote"

                    desc = f"{title} {j.get('description', '')}"

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
                        job_url = j.get("url") or f"https://{company_slug}.bamboohr.com/careers/{job_id}"

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
