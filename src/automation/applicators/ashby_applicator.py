"""
Ashby ATS Form Applicator.
"""

import asyncio
from pathlib import Path
from typing import Optional
from src.automation.applicators.base import BaseApplicator

class AshbyApplicator(BaseApplicator):
    async def fill_form(self, cv_pdf_path: Optional[Path] = None) -> bool:
        print("[Ashby] Ensuring Application tab is active and filling fields...")

        # 0. Switch from 'Overview' tab to 'Application' tab if needed
        await self.ensure_application_tab_open()

        # 1. Resume Upload (target the main resume input, avoiding Ashby's 'Autofill from resume' banner if two exist)
        if cv_pdf_path:
            file_inputs = self.page.locator("input[type='file']")
            count = await file_inputs.count()
            if count > 1:
                try:
                    await file_inputs.nth(1).set_input_files(str(cv_pdf_path))
                    self.filled_fields["CV PDF"] = str(cv_pdf_path.resolve())
                    print(f"  [OK] Uploaded CV PDF: {cv_pdf_path.name}")
                    await asyncio.sleep(1.5)
                except Exception:
                    await self.safe_upload("input[type='file']", cv_pdf_path, "CV PDF")
            else:
                await self.safe_upload("input[type='file']", cv_pdf_path, "CV PDF")

        # 2. Smart Name Filling (handles both split First/Last Name and single Full Name)
        await self.fill_name_fields()

        # 3. Email & Phone
        await self.safe_fill("input[name='_systemfield_email'], input[type='email']", self.p_info.email, "Email")
        await self.safe_fill("input[name='phone'], input[type='tel']", self.p_info.phone, "Phone")

        # 4. Location Dropdown
        loc_inp = self.page.locator("input[placeholder*='Start typing' i]")
        if await loc_inp.count() > 0 and await loc_inp.first.is_visible():
            city = self.p_info.location.split(",")[0].strip() if self.p_info.location else ""
            await loc_inp.first.fill(city)
            await asyncio.sleep(1)
            opt = self.page.locator(f"[role='option']:has-text('{city}')")
            if await opt.count() > 0:
                await opt.first.click()
                self.filled_fields["Location"] = city
                print(f"  [OK] Selected location: {city}")
            else:
                await loc_inp.first.fill(self.p_info.location)
                self.filled_fields["Location"] = self.p_info.location

        # 5. URLs (LinkedIn, GitHub, Portfolio)
        for selector, val, label in [
            ("input:not([type='hidden'])[name*='LinkedIn' i], input:not([type='hidden'])[id*='LinkedIn' i], input[placeholder*='linkedin' i]", self.p_info.linkedin_url, "LinkedIn"),
            ("input:not([type='hidden'])[name*='GitHub' i], input:not([type='hidden'])[id*='GitHub' i], input[placeholder*='github' i]", self.p_info.github_url, "GitHub"),
            ("input:not([type='hidden'])[name*='Portfolio' i], input:not([type='hidden'])[id*='Portfolio' i], input:not([type='hidden'])[name*='website' i]", self.p_info.portfolio_url, "Portfolio")
        ]:
            if val:
                await self.safe_fill(selector, val, label)

        # Also search fields by neighboring label text for Ashby's custom questions
        if self.p_info.linkedin_url and "LinkedIn" not in self.filled_fields:
            li_input = self.page.locator("label:has-text('LinkedIn') ~ div input, div:has-text('LinkedIn') ~ div input")
            if await li_input.count() > 0 and await li_input.first.is_visible():
                await li_input.first.fill(self.p_info.linkedin_url)
                self.filled_fields["LinkedIn"] = self.p_info.linkedin_url
                print(f"  [OK] Filled LinkedIn: {self.p_info.linkedin_url}")

        if self.p_info.github_url and "GitHub" not in self.filled_fields:
            gh_input = self.page.locator("label:has-text('GitHub') ~ div input, div:has-text('Github') ~ div input, div:has-text('GitHub') ~ div input")
            if await gh_input.count() > 0 and await gh_input.first.is_visible():
                await gh_input.first.fill(self.p_info.github_url)
                self.filled_fields["GitHub"] = self.p_info.github_url
                print(f"  [OK] Filled GitHub: {self.p_info.github_url}")

        # 6. Sponsorship question
        req_spons = self.p_info.requires_us_visa_sponsorship.strip().lower()
        btn_text = "Yes" if req_spons == "yes" else "No"
        spons_btn = self.page.locator(f"div:has-text('visa sponsorship') button:has-text('{btn_text}')")
        if await spons_btn.count() > 0:
            try:
                await spons_btn.first.click()
                self.filled_fields["Visa Sponsorship"] = btn_text
                print(f"  [OK] Selected Sponsorship: {btn_text}")
            except Exception:
                pass

        # 7. Salary & Preferences
        await self.fill_common_preferences()

        return True
