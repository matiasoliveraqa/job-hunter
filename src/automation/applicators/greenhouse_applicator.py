"""
Greenhouse ATS Form Applicator.
"""

import asyncio
from pathlib import Path
from typing import Optional
from src.automation.applicators.base import BaseApplicator

class GreenhouseApplicator(BaseApplicator):
    async def fill_form(self, cv_pdf_path: Optional[Path] = None) -> bool:
        print("[Greenhouse] Filling application fields...")

        # 1. Resume Upload
        if cv_pdf_path:
            await self.safe_upload("input[type='file']", cv_pdf_path, "CV PDF")

        # 2. First Name & Last Name (or Full Name)
        if await self.page.locator("input#first_name").count() > 0:
            await self.safe_fill("input#first_name", self.p_info.first_name, "First Name")
            await self.safe_fill("input#last_name", self.p_info.last_name, "Last Name")
        else:
            await self.safe_fill("input[name*='name' i]", self.p_info.full_name, "Full Name")

        # 3. Email & Phone
        await self.safe_fill("input#email, input[type='email']", self.p_info.email, "Email")
        await self.safe_fill("input#phone, input[type='tel']", self.p_info.phone, "Phone")

        # 4. Location
        await self.safe_fill("input#job_application_location, input[name*='location' i]", self.p_info.location, "Location")

        # 5. URLs
        for sel, val, lbl in [
            ("input[name*='linkedin' i], input[id*='linkedin' i]", self.p_info.linkedin_url, "LinkedIn"),
            ("input[name*='github' i], input[id*='github' i]", self.p_info.github_url, "GitHub"),
            ("input[name*='website' i], input[name*='portfolio' i], input[id*='portfolio' i]", self.p_info.portfolio_url, "Portfolio")
        ]:
            if val:
                await self.safe_fill(sel, val, lbl)

        # 6. Salary & Preferences
        await self.fill_common_preferences()

        return True
