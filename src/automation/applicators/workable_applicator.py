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

        # 1. Resume Upload (strictly targets Resume and excludes Cover Letter)
        if cv_pdf_path:
            uploaded = await self.safe_upload_resume(cv_pdf_path)
            if not uploaded:
                for sel in [
                    "[data-ui*='resume'] input[type='file']",
                    "div[data-ui='file-upload'] input[type='file']",
                    "div:has-text('Resume') input[type='file']",
                    "input[type='file']",
                ]:
                    loc = self.page.locator(sel)
                    if await loc.count() > 0:
                        await loc.first.set_input_files(str(cv_pdf_path.resolve()))
                        self.filled_fields["CV PDF"] = str(cv_pdf_path.resolve())
                        print(f"  [OK] Uploaded Resume via Workable fallback ({sel}): {cv_pdf_path.name}")
                        break

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

        # 7. Check and attempt to interact with Turnstile if present
        await self.handle_turnstile_if_present()

        return True

