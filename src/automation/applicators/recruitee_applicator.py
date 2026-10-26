"""
Recruitee ATS Form Applicator.
"""

from pathlib import Path
from typing import Optional
from src.automation.applicators.base import BaseApplicator

class RecruiteeApplicator(BaseApplicator):
    async def fill_form(self, cv_pdf_path: Optional[Path] = None) -> bool:
        print("[Recruitee] Ensuring Application page is active and filling fields...")

        # 0. Ensure application tab / page is active
        await self.ensure_application_tab_open()

        # 1. Resume Upload
        if cv_pdf_path:
            await self.safe_upload(
                "input[type='file'][name*='cv' i], input[type='file'][name*='resume' i], input[type='file']",
                cv_pdf_path,
                "CV PDF",
            )

        # 2. Smart Name Filling
        await self.fill_name_fields()

        # 3. Email & Phone
        await self.safe_fill("input[name*='email' i], input[type='email']", self.p_info.email, "Email")
        await self.fill_phone_field()

        # 4. Location
        await self.safe_fill(
            "input[name*='city' i], input[name*='location' i], input[name*='address' i]",
            self.p_info.location,
            "Location",
        )

        # 5. Social & Portfolio URLs
        for sel, val, lbl in [
            ("input:not([type='hidden'])[name*='linkedin' i]", self.p_info.linkedin_url, "LinkedIn"),
            ("input:not([type='hidden'])[name*='github' i]", self.p_info.github_url, "GitHub"),
            ("input:not([type='hidden'])[name*='website' i], input:not([type='hidden'])[name*='portfolio' i]", self.p_info.portfolio_url, "Portfolio"),
        ]:
            if val:
                await self.safe_fill(sel, val, lbl)

        # 6. Salary & Preferences
        await self.fill_common_preferences()

        return True
