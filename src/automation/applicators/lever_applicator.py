"""
Lever ATS Form Applicator.
"""

import asyncio
from pathlib import Path
from typing import Optional
from src.automation.applicators.base import BaseApplicator

class LeverApplicator(BaseApplicator):
    async def fill_form(self, cv_pdf_path: Optional[Path] = None) -> bool:
        print("[Lever] Filling application fields...")

        # 1. Resume Upload
        if cv_pdf_path:
            await self.safe_upload("input[type='file']#resume-upload-input, input[type='file']", cv_pdf_path, "CV PDF")

        # 2. Name, Email, Phone
        await self.safe_fill("input[name='name']", self.p_info.full_name, "Full Name")
        await self.safe_fill("input[name='email']", self.p_info.email, "Email")
        await self.safe_fill("input[name='phone']", self.p_info.phone, "Phone")

        # 3. Location & Company
        await self.safe_fill("#location-input, input[name*='location' i]", self.p_info.location, "Location")
        if self.p_info.current_company:
            await self.safe_fill("input[name='org']", self.p_info.current_company, "Current Company")

        # 4. URLs (Filtered to ignore hidden inputs)
        for sel, val, lbl in [
            ("input:not([type='hidden'])[name*='LinkedIn' i]", self.p_info.linkedin_url, "LinkedIn"),
            ("input:not([type='hidden'])[name*='GitHub' i]", self.p_info.github_url, "GitHub"),
            ("input:not([type='hidden'])[name*='Portfolio' i], input:not([type='hidden'])[name*='website' i]", self.p_info.portfolio_url, "Portfolio")
        ]:
            if val:
                await self.safe_fill(sel, val, lbl)

        # 5. Salary & Preferences
        await self.fill_common_preferences()

        return True
