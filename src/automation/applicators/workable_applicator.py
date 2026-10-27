"""
Workable ATS Form Applicator.
"""

from pathlib import Path
from typing import Optional
from src.automation.applicators.base import BaseApplicator

class WorkableApplicator(BaseApplicator):
    async def fill_form(self, cv_pdf_path: Optional[Path] = None) -> bool:
        print("[Workable] Ensuring Application page is active and filling fields...")

        # 0. Ensure application tab / section is open
        await self.ensure_application_tab_open()

        # 1. Resume Upload
        if cv_pdf_path:
            await self.safe_upload(
                "input[type='file'][data-ui='resume'], input[data-ui='file-input'], input[type='file']",
                cv_pdf_path,
                "CV PDF",
            )

        # 2. Smart Name Filling (first/last or full name)
        await self.fill_name_fields()

        # 3. Email & Phone
        await self.safe_fill("input[name='email'], input[type='email']", self.p_info.email, "Email")
        await self.fill_phone_field()

        # 4. Location & Current Company
        await self.safe_fill(
            "input[name='address'], input[name*='location' i], input[name='city']",
            self.p_info.location,
            "Location",
        )
        if self.p_info.current_company:
            await self.safe_fill("input[name='company'], input[name='headline']", self.p_info.current_company, "Current Company")

        # 5. Social & Portfolio URLs
        for sel, val, lbl in [
            ("input:not([type='hidden'])[name*='linkedin' i], input[placeholder*='linkedin' i]", self.p_info.linkedin_url, "LinkedIn"),
            ("input:not([type='hidden'])[name*='github' i], input[placeholder*='github' i]", self.p_info.github_url, "GitHub"),
            ("input:not([type='hidden'])[name*='portfolio' i], input:not([type='hidden'])[name*='website' i], input[placeholder*='website' i]", self.p_info.portfolio_url, "Portfolio"),
        ]:
            if val:
                await self.safe_fill(sel, val, lbl)

        # 6. Salary & Preferences
        await self.fill_common_preferences()

        return True
