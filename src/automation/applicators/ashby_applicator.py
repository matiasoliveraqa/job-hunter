"""
Ashby ATS Form Applicator.
"""

import asyncio
from pathlib import Path
from typing import Optional
from src.automation.applicators.base import BaseApplicator

class AshbyApplicator(BaseApplicator):
    async def fill_form(self, cv_pdf_path: Optional[Path] = None) -> bool:
        print("[Ashby] Filling application fields...")

        # 1. Resume
        if cv_pdf_path:
            await self.safe_upload("input[type='file']", cv_pdf_path, "CV PDF")

        # 2. Standard Personal Fields
        await self.safe_fill("input[name='_systemfield_name'], input[name='name']", self.p_info.full_name, "Full Name")
        await self.safe_fill("input[name='_systemfield_email'], input[type='email']", self.p_info.email, "Email")
        await self.safe_fill("input[name='phone'], input[type='tel']", self.p_info.phone, "Phone")

        # 3. Location Dropdown
        loc_inp = self.page.locator("input[placeholder*='Start typing' i]")
        if await loc_inp.count() > 0 and await loc_inp.first.is_visible():
            city = self.p_info.location.split(",")[0].strip() if self.p_info.location else ""
            await loc_inp.first.fill(city)
            await asyncio.sleep(1)
            opt = self.page.locator(f"[role='option']:has-text('{city}')")
            if await opt.count() > 0:
                await opt.first.click()
                print(f"  [✓] Selected location: {city}")
            else:
                await loc_inp.first.fill(self.p_info.location)

        # 4. URLs (LinkedIn, GitHub, Portfolio)
        for selector, val, label in [
            ("input:not([type='hidden'])[name*='LinkedIn' i], input:not([type='hidden'])[id*='LinkedIn' i]", self.p_info.linkedin_url, "LinkedIn"),
            ("input:not([type='hidden'])[name*='GitHub' i], input:not([type='hidden'])[id*='GitHub' i]", self.p_info.github_url, "GitHub"),
            ("input:not([type='hidden'])[name*='Portfolio' i], input:not([type='hidden'])[id*='Portfolio' i], input:not([type='hidden'])[name*='website' i]", self.p_info.portfolio_url, "Portfolio")
        ]:
            if val:
                await self.safe_fill(selector, val, label)

        # Also search fields by neighboring label text for Ashby's custom questions
        if self.p_info.github_url:
            gh_input = self.page.locator("div:has-text('Github') ~ div input, div:has-text('GitHub') ~ div input")
            if await gh_input.count() > 0:
                await gh_input.first.fill(self.p_info.github_url)

        # 5. Sponsorship question
        req_spons = self.p_info.requires_us_visa_sponsorship.strip().lower()
        btn_text = "Yes" if req_spons == "yes" else "No"
        spons_btn = self.page.locator(f"div:has-text('visa sponsorship') button:has-text('{btn_text}')")
        if await spons_btn.count() > 0:
            try:
                await spons_btn.first.click()
                print(f"  [✓] Selected Sponsorship: {btn_text}")
            except Exception:
                pass

        return True
