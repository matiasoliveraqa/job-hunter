"""
Concurrent ATS Scanner Orchestrator.
Coordinates multi-platform scanning across thousands of company boards.
"""

import asyncio
import json
from pathlib import Path
from typing import List, Optional, Callable, Any
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
        slugs: List[str] = []
        file_path = DATA_DIR / f"{platform}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    slugs.extend(data)
                elif isinstance(data, dict) and platform in data:
                    slugs.extend(data[platform])

        gaming_path = DATA_DIR / "gaming_studios.json"
        if gaming_path.exists():
            try:
                with open(gaming_path, "r", encoding="utf-8") as f:
                    gaming_data = json.load(f)
                    if isinstance(gaming_data, dict) and platform in gaming_data:
                        slugs.extend(gaming_data[platform])
            except Exception:
                pass

        unique_slugs = list(dict.fromkeys(slugs))
        return [s for s in unique_slugs if not self.exclusion_checker(s)]

    async def run(
        self,
        platforms: Optional[List[str]] = None,
        custom_roles: Optional[List[str]] = None,
        custom_locations: Optional[List[str]] = None,
        concurrency_limit: int = 200,
        max_years_experience: Optional[int] = None,
        allow_captcha: bool = False,
        on_match: Optional[Callable[[JobPosting], Any]] = None,
        on_progress: Optional[Callable[[int, int, str, str], Any]] = None,
        on_error: Optional[Callable[[str, str, str], Any]] = None,
    ) -> List[JobPosting]:
        active_platforms = platforms or self.profile.ats_settings.enabled_platforms
        roles = custom_roles or self.profile.search_criteria.target_roles
        locations = custom_locations or self.profile.search_criteria.location_keywords
        max_years = (
            max_years_experience
            if max_years_experience is not None
            else self.profile.effective_max_years
        )

        items = []
        for plat in active_platforms:
            plat_key = plat.lower()
            if plat_key in self.scanners:
                scanner = self.scanners[plat_key]
                slugs = self._load_company_slugs(plat_key)
                for slug in slugs:
                    items.append((scanner, plat_key, slug))

        total_tasks = len(items)
        checked_count = 0
        all_postings: List[JobPosting] = []

        # Use a semaphore so tasks do not start their HTTP timeout timer while waiting in the queue
        sem = asyncio.Semaphore(concurrency_limit)
        # Greenhouse WAF (Signal Sciences) enforces strict IP rate limits. Limit Greenhouse to 5 concurrent requests with slight pacing.
        greenhouse_sem = asyncio.Semaphore(min(concurrency_limit, 5))
        conn = aiohttp.TCPConnector(limit=concurrency_limit)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }

        async def _bounded_scan(scanner, session, plat_key, slug):
            nonlocal checked_count
            plat_sem = greenhouse_sem if plat_key == "greenhouse" else sem
            try:
                async with plat_sem:
                    if plat_key == "greenhouse":
                        await asyncio.sleep(0.15)
                    postings = await scanner.scan_company(
                        session,
                        slug,
                        roles,
                        locations,
                        max_years_experience=max_years,
                    )
                    if not allow_captcha:
                        postings = [p for p in postings if not p.has_captcha]

                    checked_count += 1
                    if on_progress:
                        try:
                            on_progress(checked_count, total_tasks, plat_key, slug)
                        except Exception:
                            pass
                    if postings:
                        all_postings.extend(postings)
                        try:
                            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                            out_file = OUTPUT_DIR / "scan_results.json"
                            with open(out_file, "w", encoding="utf-8") as f:
                                json.dump([p.model_dump() for p in all_postings], f, indent=2, ensure_ascii=False)
                        except Exception:
                            pass
                        if on_match:
                            for p in postings:
                                try:
                                    on_match(p)
                                except Exception:
                                    pass
                    return postings
            except Exception as e:
                checked_count += 1
                if on_error:
                    try:
                        on_error(plat_key, slug, str(e))
                    except Exception:
                        pass
                return []

        async with aiohttp.ClientSession(connector=conn, headers=headers) as session:
            tasks = [_bounded_scan(sc, session, pk, sl) for sc, pk, sl in items]
            await asyncio.gather(*tasks, return_exceptions=True)

        # Allow underlying SSL transports to close cleanly on Windows ProactorEventLoop
        await asyncio.sleep(0.1)

        # Save results to output
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_file = OUTPUT_DIR / "scan_results.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump([p.model_dump() for p in all_postings], f, indent=2, ensure_ascii=False)

        return all_postings
