"""
Lever ATS Form Applicator.
"""

from pathlib import Path
from typing import Optional
from src.automation.applicators.base import BaseApplicator

class LeverApplicator(BaseApplicator):
    async def fill_form(self, cv_pdf_path: Optional[Path] = None) -> bool:
        print("[Lever] Ensuring Application page is active and filling fields...")

        # 0. Navigate to /apply if URL was the job description overview
        await self.ensure_application_tab_open()

        # 1. Resume Upload
        if cv_pdf_path:
            await self.safe_upload("input[type='file']#resume-upload-input, input[type='file']", cv_pdf_path, "CV PDF")

        # 2. Smart Name Filling (handles both single Full Name and split First/Last Name)
        await self.fill_name_fields()

        # 3. Email & Phone
        await self.safe_fill("input[name='email'], input[type='email']", self.p_info.email, "Email")
        await self.fill_phone_field()

        # 4. Location & Company
        await self.safe_fill("#location-input, input[name*='location' i]", self.p_info.location, "Location")
        if self.p_info.current_company:
            await self.safe_fill("input[name='org']", self.p_info.current_company, "Current Company")

        # 5. URLs (Filtered to ignore hidden inputs)
        for sel, val, lbl in [
            ("input:not([type='hidden'])[name*='LinkedIn' i]", self.p_info.linkedin_url, "LinkedIn"),
            ("input:not([type='hidden'])[name*='GitHub' i]", self.p_info.github_url, "GitHub"),
            ("input:not([type='hidden'])[name*='Portfolio' i], input:not([type='hidden'])[name*='website' i]", self.p_info.portfolio_url, "Portfolio")
        ]:
            if val:
                await self.safe_fill(sel, val, lbl)

        # 6. Salary & Preferences
        await self.fill_common_preferences()

        return True
