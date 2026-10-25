"""
Greenhouse ATS Form Applicator.
"""

from pathlib import Path
from typing import Optional
from src.automation.applicators.base import BaseApplicator

class GreenhouseApplicator(BaseApplicator):
    async def fill_form(self, cv_pdf_path: Optional[Path] = None) -> bool:
        print("[Greenhouse] Ensuring Application tab is active and filling fields...")

        # 0. Switch to Application tab if separated
        await self.ensure_application_tab_open()

        # 1. Resume Upload
        if cv_pdf_path:
            await self.safe_upload("input[type='file']#resume, input[type='file']", cv_pdf_path, "CV PDF")

        # 2. First Name & Last Name (smart detection prevents putting Full Name into First Name)
        await self.fill_name_fields()

        # 3. Email & Phone
        await self.safe_fill("input#email, input[name='email' i], input[type='email']", self.p_info.email, "Email")
        await self.fill_phone_field()

        # 4. Location
        await self.safe_fill("input#job_application_location, input#candidate-location, input[name*='location' i]", self.p_info.location, "Location")

        # 5. URLs
        for sel, val, lbl in [
            ("input[name*='linkedin' i], input[id*='linkedin' i], input[aria-label*='LinkedIn' i]", self.p_info.linkedin_url, "LinkedIn"),
            ("input[name*='github' i], input[id*='github' i], input[aria-label*='GitHub' i]", self.p_info.github_url, "GitHub"),
            ("input[name*='website' i], input[name*='portfolio' i], input[id*='portfolio' i], input[aria-label*='Portfolio' i], input[aria-label*='Website' i]", self.p_info.portfolio_url, "Portfolio")
        ]:
            if val:
                await self.safe_fill(sel, val, lbl)

        # 6. Salary & Preferences
        await self.fill_common_preferences()

        return True
