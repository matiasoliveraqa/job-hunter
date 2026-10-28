"""
BambooHR ATS Form Applicator.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from src.automation.applicators.base import BaseApplicator


class BambooHRApplicator(BaseApplicator):
    async def fill_form(self, cv_pdf_path: Optional[Path] = None) -> bool:
        print("[BambooHR] Ensuring Application page is active and filling fields...")

        # 0. Ensure application tab / page is active
        await self.ensure_application_tab_open()

        # Wait up to 10 seconds for BambooHR form elements to be present in DOM
        try:
            await self.page.wait_for_selector(
                "input#firstName, input[name='firstName'], input[name*='first' i], input[type='file'], input[name*='email' i]",
                timeout=10000,
                state="visible",
            )
        except Exception:
            pass

        # 1. Resume Upload (strictly targets Resume and excludes Cover Letter)
        if cv_pdf_path:
            await self.safe_upload_resume(cv_pdf_path)

        # 2. Smart Name Filling (firstName and lastName)
        await self.fill_name_fields()

        # 3. Email & Phone
        await self.safe_fill("input[name*='email' i], input[type='email']", self.p_info.email, "Email")
        await self.fill_phone_field()

        # 4. Country Selection (generic from candidate profile)
        country_to_select = self.p_info.country
        if country_to_select:
            await self._select_bamboohr_country(country_to_select)

        # 5. Address, City, State / Province, ZIP (generic from candidate profile)
        await self._fill_bamboohr_location()

        # 6. Date Available
        await self._fill_bamboohr_date_available()

        # 7. Desired Pay
        is_contractor = await self.detect_is_contractor_posting()
        _salary_num, salary_str, modality = await self.get_effective_salary(is_contractor=is_contractor)
        await self.safe_fill(
            "input#desiredPay, input[name='desiredPay'], input[name*='desired' i]",
            salary_str,
            f"Desired Pay ({modality})",
        )

        # 8. Social & Portfolio URLs
        for sel, val, lbl in [
            ("input#linkedinUrl, input:not([type='hidden'])[name*='linkedin' i]", self.p_info.linkedin_url, "LinkedIn"),
            ("input#websiteUrl, input:not([type='hidden'])[name*='website' i], input:not([type='hidden'])[name*='portfolio' i]", self.p_info.portfolio_url, "Portfolio"),
            ("input:not([type='hidden'])[name*='github' i]", self.p_info.github_url, "GitHub"),
        ]:
            if val:
                await self.safe_fill(sel, val, lbl)

        # 9. Additional custom questions & preferences
        await self.fill_common_preferences()

        return True

    async def _select_bamboohr_country(self, target_country: Optional[str] = None) -> None:
        """Select country in BambooHR's custom Fabric dropdown."""
        country_to_select = target_country or self.p_info.country
        if not country_to_select:
            return

        try:
            country_toggle = self.page.locator("button.fab-SelectToggle[aria-label*='Country' i]")
            if await country_toggle.count() == 0 or not await country_toggle.first.is_visible():
                # Fallback by label container
                c_lbl = self.page.locator("label:has-text('Country')")
                if await c_lbl.count() > 0:
                    country_toggle = c_lbl.first.locator("xpath=../..//button[contains(@class, 'fab-SelectToggle')]")

            if await country_toggle.count() > 0 and await country_toggle.first.is_visible():
                current_text = (await country_toggle.first.text_content() or "").strip()
                if country_to_select.lower() in current_text.lower():
                    return

                await country_toggle.first.click()
                await asyncio.sleep(0.3)

                # Search box inside opened dropdown menu
                search_inps = self.page.locator(
                    "[role='menu'] input, .fab-Menu input, input[type='search'], input[placeholder*='Search' i]"
                )
                if await search_inps.count() > 0 and await search_inps.first.is_visible():
                    await search_inps.first.fill(country_to_select)
                    await asyncio.sleep(0.3)

                # Option selector
                country_opt = self.page.locator(
                    f"[role='menuitem']:has-text('{country_to_select}'), "
                    f"[role='option']:has-text('{country_to_select}'), "
                    f"li:has-text('{country_to_select}'), "
                    f"button:has-text('{country_to_select}')"
                ).first

                if await country_opt.count() > 0 and await country_opt.is_visible():
                    await country_opt.click()
                    self.filled_fields["Country"] = country_to_select
                    print(f"  [OK] Selected Country: {country_to_select}")
                    # Allow BambooHR SPA to dynamically re-render State/Province fields
                    await asyncio.sleep(0.8)
        except Exception as e:
            print(f"  [!] BambooHR country selection failed: {e}")

    async def _fill_bamboohr_location(self) -> None:
        """Fill address, city, province/state, and zip fields generically."""
        city_val = self.p_info.city
        addr_val = self.p_info.resolved_address
        state_val = self.p_info.resolved_state
        postal_val = self.p_info.resolved_postal_code

        # Address / Street
        if addr_val:
            await self.safe_fill(
                "input[name='streetAddress.value'], input[name*='street' i], input[name='address.value']",
                addr_val,
                "Address",
            )

        # City
        if city_val:
            await self.safe_fill(
                "input[name='city.value'], input[name*='city' i]",
                city_val,
                "City",
            )

        # Province / State / Department (Text input or dropdown)
        if state_val:
            # 1. Text input: BambooHR renders input[name='state.value'] with label Province or State
            await self.safe_fill(
                "input[name='state.value'], input[name*='province' i], input[name*='state' i]",
                state_val,
                "Province / State",
            )

            # 2. Select dropdown (if rendered as dropdown for US/Canada or other countries)
            state_toggle = self.page.locator(
                "button.fab-SelectToggle[aria-label*='State' i], "
                "button.fab-SelectToggle[aria-label*='Province' i], "
                "button.fab-SelectToggle[aria-label*='Provincia' i]"
            )
            if await state_toggle.count() > 0 and await state_toggle.first.is_visible():
                current_txt = (await state_toggle.first.text_content() or "").strip()
                if state_val.lower() not in current_txt.lower() and "-select-" in current_txt.lower():
                    await state_toggle.first.click()
                    await asyncio.sleep(0.3)
                    search_inp = self.page.locator("[role='menu'] input, .fab-Menu input, input[type='search']")
                    if await search_inp.count() > 0 and await search_inp.first.is_visible():
                        await search_inp.first.fill(state_val)
                        await asyncio.sleep(0.3)
                    opt = self.page.locator(
                        f"[role='menuitem']:has-text('{state_val}'), [role='option']:has-text('{state_val}'), li:has-text('{state_val}')"
                    ).first
                    if await opt.count() > 0 and await opt.is_visible():
                        await opt.click()
                        self.filled_fields["Province / State"] = state_val
                        await asyncio.sleep(0.3)

        # ZIP / Postal Code
        if postal_val:
            await self.safe_fill(
                "input[name='zip.value'], input[name*='zip' i], input[name*='postal' i]",
                postal_val,
                "ZIP / Postal Code",
            )

    async def _fill_bamboohr_date_available(self) -> None:
        """Fill Date Available input based on notice period."""
        try:
            target_dt = datetime.now() + timedelta(days=14)
            date_inp = None

            # Look up input via 'Date Available' label
            date_lbl = self.page.locator("label:has-text('Date Available')")
            if await date_lbl.count() > 0:
                for_id = await date_lbl.first.get_attribute("for")
                if for_id:
                    candidate = self.page.locator(f"#{for_id}")
                    if await candidate.count() > 0 and await candidate.first.is_visible():
                        date_inp = candidate.first

            # Fallback selector
            if not date_inp:
                fallback = self.page.locator(
                    "input[name*='available' i], input[placeholder*='dd/mm' i], input[placeholder*='mm/dd' i]"
                )
                if await fallback.count() > 0 and await fallback.first.is_visible():
                    date_inp = fallback.first

            if date_inp:
                ph = (await date_inp.get_attribute("placeholder") or "").lower()
                dt_str = target_dt.strftime("%d/%m/%Y") if ("dd/mm" in ph or "dd-mm" in ph) else target_dt.strftime("%m/%d/%Y")
                await date_inp.fill(dt_str)
                self.filled_fields["Date Available"] = dt_str
                print(f"  [OK] Filled Date Available: {dt_str}")
        except Exception as e:
            print(f"  [!] BambooHR Date Available fill failed: {e}")
