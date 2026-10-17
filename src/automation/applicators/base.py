"""
Base Form Applicator Interface.
"""

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from playwright.async_api import Page
from src.core.models import CandidateProfile

class BaseApplicator(ABC):
    def __init__(self, page: Page, profile: CandidateProfile):
        self.page = page
        self.profile = profile
        self.p_info = profile.personal_info
        self.prefs = profile.preferences

    @abstractmethod
    async def fill_form(self, cv_pdf_path: Optional[Path] = None) -> bool:
        """Fill all standard fields on the application page."""
        pass

    async def fill_common_preferences(self) -> None:
        """Fill compensation, notice period, and work authorization fields."""
        # 1. Salary / Compensation
        if self.prefs.desired_salary_usd:
            salary_inputs = self.page.locator(
                "input:not([type='hidden'])[name*='salary' i], "
                "input:not([type='hidden'])[id*='salary' i], "
                "input:not([type='hidden'])[name*='compensation' i], "
                "input:not([type='hidden'])[id*='compensation' i]"
            )
            if await salary_inputs.count() > 0 and await salary_inputs.first.is_visible():
                try:
                    inp = salary_inputs.first
                    input_type = await inp.get_attribute("type")
                    if input_type == "number":
                        await inp.fill(str(self.prefs.desired_salary_usd))
                    else:
                        await inp.fill(self.prefs.formatted_salary)
                    print(f"  [OK] Filled Desired Salary: {self.prefs.formatted_salary}")
                except Exception:
                    pass

        # 2. Notice period / Availability
        if self.prefs.notice_period:
            notice_inputs = self.page.locator(
                "input:not([type='hidden'])[name*='notice' i], "
                "input:not([type='hidden'])[id*='notice' i], "
                "input:not([type='hidden'])[name*='start_date' i], "
                "input:not([type='hidden'])[placeholder*='notice' i]"
            )
            if await notice_inputs.count() > 0 and await notice_inputs.first.is_visible():
                try:
                    await notice_inputs.first.fill(self.prefs.notice_period)
                    print(f"  [OK] Filled Notice Period: {self.prefs.notice_period}")
                except Exception:
                    pass

    async def safe_fill(self, selector: str, value: str, description: str = "") -> bool:
        """Safely fill an input if it exists and is visible."""
        if not value:
            return False
        try:
            loc = self.page.locator(selector)
            if await loc.count() > 0 and await loc.first.is_visible():
                await loc.first.fill(value)
                if description:
                    print(f"  [OK] Filled {description}")
                return True
        except Exception:
            pass
        return False

    async def safe_upload(self, selector: str, file_path: Path, description: str = "CV/Resume") -> bool:
        """Safely set files on a file input selector."""
        if not file_path or not file_path.exists():
            return False
        try:
            file_input = self.page.locator(selector)
            if await file_input.count() > 0:
                await file_input.first.set_input_files(str(file_path))
                print(f"  [OK] Uploaded {description}: {file_path.name}")
                await asyncio.sleep(1.5)
                return True
        except Exception as e:
            print(f"  [!] Upload failed for {description}: {e}")
        return False
