"""
Concurrent ATS Scanner Orchestrator.
Coordinates multi-platform scanning across thousands of company boards.
"""

import asyncio
import json
from pathlib import Path
from typing import List, Optional
import aiohttp

from src.core.models import JobPosting, CandidateProfile
from src.core.config import DATA_DIR, OUTPUT_DIR, get_exclusion_checker
from src.scanners.ashby import AshbyScanner
from src.scanners.greenhouse import GreenhouseScanner
from src.scanners.lever import LeverScanner

class ScannerOrchestrator:
    def __init__(self, profile: CandidateProfile):
        self.profile = profile
        self.exclusion_checker = get_exclusion_checker()
        self.scanners = {
            "ashby": AshbyScanner(),
            "greenhouse": GreenhouseScanner(),
            "lever": LeverScanner()
        }

    def _load_company_slugs(self, platform: str) -> List[str]:
        file_path = DATA_DIR / f"{platform}.json"
        if not file_path.exists():
            return []
        with open(file_path, "r", encoding="utf-8") as f:
            slugs = json.load(f)
        return [s for s in slugs if not self.exclusion_checker(s)]

    async def run(
        self,
        platforms: Optional[List[str]] = None,
        custom_roles: Optional[List[str]] = None,
        custom_locations: Optional[List[str]] = None,
        concurrency_limit: int = 200,
        max_years_experience: Optional[int] = None,
    ) -> List[JobPosting]:
        active_platforms = platforms or self.profile.ats_settings.enabled_platforms
        roles = custom_roles or self.profile.search_criteria.target_roles
        locations = custom_locations or self.profile.search_criteria.location_keywords
        max_years = (
            max_years_experience
            if max_years_experience is not None
            else self.profile.effective_max_years
        )

        # Use a semaphore so tasks do not start their HTTP timeout timer while waiting in the queue
        sem = asyncio.Semaphore(concurrency_limit)
        conn = aiohttp.TCPConnector(limit=concurrency_limit, ssl=False)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        all_postings: List[JobPosting] = []

        async def _bounded_scan(scanner, session, slug):
            async with sem:
                return await scanner.scan_company(
                    session,
                    slug,
                    roles,
                    locations,
                    max_years_experience=max_years,
                )

        async with aiohttp.ClientSession(connector=conn, headers=headers) as session:
            tasks = []
            for plat in active_platforms:
                plat_key = plat.lower()
                if plat_key in self.scanners:
                    scanner = self.scanners[plat_key]
                    slugs = self._load_company_slugs(plat_key)
                    for slug in slugs:
                        tasks.append(_bounded_scan(scanner, session, slug))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, list):
                    all_postings.extend(res)

        # Save results to output
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_file = OUTPUT_DIR / "scan_results.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump([p.model_dump() for p in all_postings], f, indent=2, ensure_ascii=False)

        return all_postings
