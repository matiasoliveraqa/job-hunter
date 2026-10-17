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

    @abstractmethod
    async def fill_form(self, cv_pdf_path: Optional[Path] = None) -> bool:
        """Fill all standard fields on the application page."""
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
