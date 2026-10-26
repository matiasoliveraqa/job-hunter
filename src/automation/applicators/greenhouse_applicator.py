"""
Greenhouse ATS Form Applicator.
"""

import asyncio
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

        # 4. Location (City)
        await self.fill_location_field()

        # 5. Education block
        await self.fill_education_fields()

        # 6. URLs
        for sel, val, lbl in [
            ("input[name*='linkedin' i], input[id*='linkedin' i], input[aria-label*='LinkedIn' i]", self.p_info.linkedin_url, "LinkedIn"),
            ("input[name*='github' i], input[id*='github' i], input[aria-label*='GitHub' i]", self.p_info.github_url, "GitHub"),
            ("input[name*='website' i], input[name*='portfolio' i], input[id*='portfolio' i], input[aria-label*='Portfolio' i], input[aria-label*='Website' i]", self.p_info.portfolio_url, "Portfolio")
        ]:
            if val:
                await self.safe_fill(sel, val, lbl)

        # 7. Salary, Preferences, Custom Questions & Dropdowns
        await self.fill_common_preferences()

        return True

    async def fill_location_field(self) -> bool:
        """Fill Location (City) on Greenhouse forms (React-Select autocomplete or plain text/Places)."""
        city_query = self.p_info.city or self.p_info.location
        full_loc = self.p_info.location or self.p_info.city

        # Modern Greenhouse React-Select combobox (#candidate-location)
        loc_cb = self.page.locator("#candidate-location, input[id*='candidate-location' i]")
        if await loc_cb.count() > 0 and await loc_cb.first.is_visible():
            chosen = await self.fill_react_select(
                loc_cb.first,
                preferred_choices=[full_loc, city_query, self.p_info.country],
                query_text=city_query,
                fallback_first=True,
                description="Location (City)"
            )
            if chosen:
                return True

        # Fallback: standard input or Google Places autocomplete
        loc_inputs = self.page.locator("input#job_application_location, input[name*='location' i], input[aria-label*='Location' i]")
        if await loc_inputs.count() > 0 and await loc_inputs.first.is_visible():
            inp = loc_inputs.first
            await inp.fill(full_loc)
            await asyncio.sleep(0.5)
            sugg = self.page.locator(".pac-container .pac-item, [role='option']")
            if city_query:
                narrowed = self.page.locator("[role='option']").filter(has_text=city_query)
                if await narrowed.count() > 0:
                    sugg = narrowed
            if await sugg.count() > 0:
                await sugg.first.click()
            self.filled_fields["Location (City)"] = full_loc
            print(f"  [OK] Filled Location (City): {full_loc}")
            return True

        return False

    async def fill_education_fields(self) -> None:
        """Fill Education block (School, Degree, Discipline, Start/End Years) on Greenhouse."""
        # 1. School (remote search combobox)
        school_cb = self.page.locator("#school--0, input[id^='school' i]")
        if await school_cb.count() > 0 and await school_cb.first.is_visible():
            oq = getattr(self.profile, "open_questions", None)
            institution = getattr(oq, "education_institution", None) if oq else None
            if institution:
                await self.fill_react_select(
                    school_cb.first,
                    preferred_choices=[institution],
                    query_text=institution,
                    fallback_first=False,
                    description="Education School"
                )
            else:
                self.filled_fields["Education School"] = "Pending manual review"
                print("  [!] Skipped school: education_institution not set in profile")

        # 2. Degree
        deg_cb = self.page.locator("#degree--0, input[id^='degree' i]")
        if await deg_cb.count() > 0 and await deg_cb.first.is_visible():
            await self.fill_react_select(
                deg_cb.first,
                preferred_choices=["Bachelors Degree", "Bachelor", "Engineer's Degree", "Associates Degree"],
                fallback_first=True,
                description="Education Degree"
            )

        # 3. Discipline
        disc_cb = self.page.locator("#discipline--0, input[id^='discipline' i]")
        if await disc_cb.count() > 0 and await disc_cb.first.is_visible():
            await self.fill_react_select(
                disc_cb.first,
                preferred_choices=["Computer Science", "Information Systems", "Information Technology", "Software Engineering", "Engineering"],
                fallback_first=True,
                description="Education Discipline"
            )

        # 4. Start date year
        start_yr = self.page.locator("#start-year--0, input[id*='start-year' i], input[id*='start_year' i], input[name*='start_date' i]")
        if await start_yr.count() > 0 and await start_yr.first.is_visible():
            await start_yr.first.fill("2021")
            self.filled_fields["Education Start Year"] = "2021"
            print("  [OK] Filled Education Start Year: 2021")

        # 5. End date year
        end_yr = self.page.locator("#end-year--0, input[id*='end-year' i], input[id*='end_year' i], input[name*='end_date' i]")
        if await end_yr.count() > 0 and await end_yr.first.is_visible():
            await end_yr.first.fill("2024")
            self.filled_fields["Education End Year"] = "2024"
            print("  [OK] Filled Education End Year: 2024")
