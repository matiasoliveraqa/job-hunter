"""
Concurrent ATS Scanner Orchestrator.
Coordinates multi-platform scanning across thousands of company boards.
"""

import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import aiohttp

from src.core.models import JobPosting, CandidateProfile, ATSPlatform
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
        concurrency_limit: int = 50
    ) -> List[JobPosting]:
        active_platforms = platforms or self.profile.ats_settings.enabled_platforms
        roles = custom_roles or self.profile.search_criteria.target_roles
        locations = custom_locations or self.profile.search_criteria.location_keywords

        conn = aiohttp.TCPConnector(limit=concurrency_limit, ssl=False)
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

        all_postings: List[JobPosting] = []

        async with aiohttp.ClientSession(connector=conn, headers=headers) as session:
            tasks = []
            for plat in active_platforms:
                plat_key = plat.lower()
                if plat_key in self.scanners:
                    scanner = self.scanners[plat_key]
                    slugs = self._load_company_slugs(plat_key)
                    for slug in slugs:
                        tasks.append(scanner.scan_company(session, slug, roles, locations))

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
