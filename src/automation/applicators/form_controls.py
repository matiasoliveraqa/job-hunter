"""
Personal, phone, name, and preference form controls mixin.
"""

import re
import asyncio
from typing import Dict


class FormControlsMixin:
    """Methods for filling name fields, international phones, common preferences, and safe typing."""

    async def fill_name_fields(self) -> bool:
        """
        Smartly detect whether the application form splits Name into First Name + Last Name
        or uses a single Full Name field. Prevents putting full_name into First Name while
        leaving Last Name empty.
        """
        first_selectors = (
            "input#first_name, "
            "input[name='first_name' i], "
            "input[name='firstName' i], "
            "input[name*='first_name' i], "
            "input[name*='firstname' i], "
            "input[id*='first_name' i], "
            "input[id*='firstname' i], "
            "input[autocomplete='given-name'], "
            "input[aria-label*='First Name' i], "
            "input[placeholder*='First name' i]"
        )
        last_selectors = (
            "input#last_name, "
            "input[name='last_name' i], "
            "input[name='lastName' i], "
            "input[name*='last_name' i], "
            "input[name*='lastname' i], "
            "input[id*='last_name' i], "
            "input[id*='lastname' i], "
            "input[autocomplete='family-name'], "
            "input[aria-label*='Last Name' i], "
            "input[placeholder*='Last name' i]"
        )

        filled_first = await self.safe_fill(first_selectors, self.p_info.first_name, "First Name")
        filled_last = await self.safe_fill(last_selectors, self.p_info.last_name, "Last Name")

        if not filled_first:
            try:
                lbl_first = self.page.get_by_label(re.compile(r"^\s*(first\s*name|given\s*name|nombre)\b", re.I))
                if await lbl_first.count() > 0 and await lbl_first.first.is_visible():
                    await lbl_first.first.fill(self.p_info.first_name)
                    self.filled_fields["First Name"] = self.p_info.first_name
                    print(f"  [OK] Filled First Name: {self.p_info.first_name}")
                    filled_first = True
            except Exception:
                pass

        if not filled_last:
            try:
                lbl_last = self.page.get_by_label(re.compile(r"^\s*(last\s*name|surname|family\s*name|apellido)\b", re.I))
                if await lbl_last.count() > 0 and await lbl_last.first.is_visible():
                    await lbl_last.first.fill(self.p_info.last_name)
                    self.filled_fields["Last Name"] = self.p_info.last_name
                    print(f"  [OK] Filled Last Name: {self.p_info.last_name}")
                    filled_last = True
            except Exception:
                pass

        if filled_first or filled_last:
            return True

        full_selectors = (
            "input[name='_systemfield_name'], "
            "input[name='name'], "
            "input[id='name'], "
            "input[autocomplete='name'], "
            "input[aria-label*='Full Name' i], "
            "input[placeholder*='Full name' i]"
        )
        if await self.safe_fill(full_selectors, self.p_info.full_name, "Full Name"):
            return True

        try:
            lbl_full = self.page.get_by_label(re.compile(r"^\s*(full\s*name|your\s*name|name)\b", re.I))
            if await lbl_full.count() > 0 and await lbl_full.first.is_visible():
                await lbl_full.first.fill(self.p_info.full_name)
                self.filled_fields["Full Name"] = self.p_info.full_name
                print(f"  [OK] Filled Full Name: {self.p_info.full_name}")
                return True
        except Exception:
            pass

        return False

    def _parse_phone_info(self) -> Dict[str, str]:
        phone_str = (self.p_info.phone or "").strip()
        location_str = (self.p_info.location or "").strip()

        country = ""
        if location_str and "," in location_str:
            country = location_str.split(",")[-1].strip()
        elif location_str:
            country = location_str.strip()

        dial_codes = {
            "uruguay": ("+598", "598", "UY"),
            "argentina": ("+54", "54", "AR"),
            "chile": ("+56", "56", "CL"),
            "colombia": ("+57", "57", "CO"),
            "mexico": ("+52", "52", "MX"),
            "peru": ("+51", "51", "PE"),
            "brazil": ("+55", "55", "BR"),
            "brasil": ("+55", "55", "BR"),
            "united states": ("+1", "1", "US"),
            "usa": ("+1", "1", "US"),
            "spain": ("+34", "34", "ES"),
            "espana": ("+34", "34", "ES"),
        }

        fallback = ("", "", "")
        m_dial = re.match(r"\+(\d{1,3})", phone_str)
        if m_dial:
            fallback = (f"+{m_dial.group(1)}", m_dial.group(1), "")
        dial_code, code_digits, iso2 = dial_codes.get(country.lower(), fallback)

        digits_only = re.sub(r"\D", "", phone_str)
        if digits_only.startswith(code_digits):
            national_number = digits_only[len(code_digits):]
        else:
            national_number = digits_only

        return {
            "full_phone": phone_str,
            "country": country,
            "dial_code": dial_code,
            "code_digits": code_digits,
            "iso2": iso2,
            "national_number": national_number or digits_only,
        }

    async def fill_phone_field(self) -> bool:
        """
        Fill the phone number field and handle international country prefix selectors
        (e.g. dropdowns, button popovers, or standard inputs), matching candidate's country.
        """
        try:
            phone_inputs = self.page.locator(
                "input[type='tel'], input#phone, input[name='phone' i], input[id*='phone' i], input[placeholder*='phone' i]"
            )
            if await phone_inputs.count() == 0:
                return False

            tel_inp = phone_inputs.first
            if not await tel_inp.is_visible():
                return False

            phone_info = self._parse_phone_info()
            country_name = phone_info["country"]
            dial_code = phone_info["dial_code"]
            national_num = phone_info["national_number"]
            full_phone = phone_info["full_phone"]

            country_selected = False

            # 1. Interactive country prefix button
            prefix_btn = None
            parent = tel_inp.locator("xpath=ancestor::*[contains(@class, 'phone') or contains(@class, 'field') or contains(@class, 'container') or self::fieldset or self::div][1]")
            if await parent.count() > 0:
                btns = parent.locator("button:has-text('+'), button[class*='country'], button[class*='phone'], [aria-haspopup='listbox'], .iti__selected-flag")
                if await btns.count() > 0 and await btns.first.is_visible():
                    prefix_btn = btns.first

            if not prefix_btn:
                near_btns = self.page.locator("button:has-text('+'):visible")
                if await near_btns.count() > 0:
                    prefix_btn = near_btns.first

            if prefix_btn:
                btn_text = (await prefix_btn.inner_text() or "").strip()
                if dial_code in btn_text:
                    country_selected = True
                else:
                    try:
                        await prefix_btn.click()
                        await asyncio.sleep(0.35)

                        search_inp = self.page.locator(
                            "input[placeholder*='search' i]:visible, [role='searchbox']:visible, input[type='search']:visible, .iti__search-input:visible"
                        )
                        if await search_inp.count() > 0 and await search_inp.first.is_visible():
                            await search_inp.first.fill(country_name)
                            await asyncio.sleep(0.3)

                        opt = self.page.locator(
                            f"[role='option']:has-text('{country_name}'):visible, li:has-text('{country_name}'):visible, button:has-text('{country_name}'):visible, div:has-text('{country_name}'):visible"
                        )
                        if await opt.count() > 0:
                            await opt.last.click()
                            await asyncio.sleep(0.3)
                            country_selected = True
                            print(f"  [OK] Selected phone country prefix: {country_name} ({dial_code})")
                        else:
                            opt_code = self.page.locator(
                                f"[role='option']:has-text('{dial_code}'):visible, li:has-text('{dial_code}'):visible, button:has-text('{dial_code}'):visible"
                            )
                            if await opt_code.count() > 0:
                                await opt_code.last.click()
                                await asyncio.sleep(0.3)
                                country_selected = True
                                print(f"  [OK] Selected phone country prefix: {dial_code}")
                            else:
                                await self.page.keyboard.press("Escape")
                    except Exception:
                        pass

            # 2. Standard select country dropdown
            if not country_selected:
                country_selects = self.page.locator(
                    "select[name*='country' i], select[id*='country' i], select[aria-label*='country' i]"
                )
                if await country_selects.count() > 0:
                    cs = country_selects.first
                    if await cs.is_visible():
                        for val in [country_name, dial_code, phone_info["iso2"]]:
                            try:
                                await cs.select_option(label=val)
                                country_selected = True
                                print(f"  [OK] Selected phone country from dropdown: {val}")
                                break
                            except Exception:
                                pass

            # 3. Fill the phone input
            num_to_fill = national_num if country_selected else full_phone
            await tel_inp.fill(num_to_fill)
            self.filled_fields["Phone"] = f"{dial_code} {national_num}" if country_selected else full_phone
            print(f"  [OK] Filled Phone: {self.filled_fields['Phone']}")
            return True
        except Exception:
            return False

    async def fill_common_preferences(self) -> None:
        """Fill compensation (contractor vs dependent employee), notice period, and work authorization."""
        is_contractor = await self.detect_is_contractor_posting()
        salary_num, salary_str, modality_label = await self.get_effective_salary(is_contractor=is_contractor)

        # 1. Salary / Compensation
        if salary_num:
            salary_inputs = self.page.locator(
                "input:not([type='hidden'])[name*='salary' i], "
                "input:not([type='hidden'])[id*='salary' i], "
                "input:not([type='hidden'])[name*='compensation' i], "
                "input:not([type='hidden'])[id*='compensation' i], "
                "input:not([type='hidden'])[placeholder*='salary' i], "
                "input:not([type='hidden'])[placeholder*='compensation' i]"
            )
            if await salary_inputs.count() > 0 and await salary_inputs.first.is_visible():
                try:
                    inp = salary_inputs.first
                    input_type = await inp.get_attribute("type")
                    inp_text = await inp.evaluate("""(node) => {
                        const parts = [node.name || '', node.id || '', node.placeholder || ''];
                        const lbl = node.id ? document.querySelector(`label[for="${CSS.escape(node.id)}"]`) : null;
                        if (lbl) parts.push(lbl.innerText);
                        const parentLbl = node.closest('label');
                        if (parentLbl) parts.push(parentLbl.innerText);
                        return parts.join(' ').toLowerCase();
                    }""")

                    if any(k in inp_text for k in ["annual", "yearly", "per year", "/yr", "/year"]):
                        target_val = salary_num if "/ year" in salary_str else (salary_num * 12 if "/ month" in salary_str else salary_num)
                        val_to_fill = str(target_val) if input_type == "number" else f"${target_val:,} USD / year"
                    elif any(k in inp_text for k in ["hourly", "per hour", "/hr", "/hour"]):
                        target_val = salary_num if "/ hour" in salary_str else max(1, round(salary_num / 160))
                        val_to_fill = str(target_val) if input_type == "number" else f"${target_val:,} USD / hour"
                    else:
                        val_to_fill = str(salary_num) if input_type == "number" else salary_str

                    await inp.fill(val_to_fill)
                    self.filled_fields[f"Salary ({modality_label})"] = val_to_fill
                    print(f"  [OK] Filled Desired Salary ({modality_label}): {val_to_fill}")
                except Exception:
                    pass

        # 2. Notice period / Availability
        if self.prefs.notice_period:
            notice_inputs = self.page.locator(
                "input:not([type='hidden'])[name*='notice' i], "
                "input:not([type='hidden'])[id*='notice' i], "
                "input:not([type='hidden'])[name*='start_date' i], "
                "input:not([type='hidden'])[placeholder*='notice' i]"
            )
            if await notice_inputs.count() > 0 and await notice_inputs.first.is_visible():
                try:
                    await notice_inputs.first.fill(self.prefs.notice_period)
                    self.filled_fields["Notice Period"] = self.prefs.notice_period
                    print(f"  [OK] Filled Notice Period: {self.prefs.notice_period}")
                except Exception:
                    pass

        # 3. Date Available / Start Date
        date_inputs = self.page.locator(
            "input:not([type='hidden'])[name*='available' i], "
            "input:not([type='hidden'])[id*='available' i], "
            "input:not([type='hidden'])[name*='start_date' i], "
            "input:not([type='hidden'])[placeholder*='dd/mm' i], "
            "input:not([type='hidden'])[placeholder*='mm/dd' i]"
        )
        if await date_inputs.count() > 0 and await date_inputs.first.is_visible():
            try:
                inp = date_inputs.first
                ph = (await inp.get_attribute("placeholder") or "").lower()
                from datetime import datetime, timedelta
                target_dt = datetime.now() + timedelta(days=14)
                dt_str = target_dt.strftime("%d/%m/%Y") if ("dd/mm" in ph or "dd-mm" in ph) else target_dt.strftime("%m/%d/%Y")
                await inp.fill(dt_str)
                self.filled_fields["Date Available"] = dt_str
                print(f"  [OK] Filled Date Available: {dt_str}")
            except Exception:
                pass

        # 4. Fill custom questions
        if hasattr(self, "fill_custom_questions"):
            await self.fill_custom_questions(salary_str=salary_str, salary_num=salary_num)

    async def safe_fill(self, selector: str, value: str, description: str = "") -> bool:
        """Safely fill an input if it exists and is visible."""
        if not value:
            return False
        try:
            loc = self.page.locator(selector)
            count = await loc.count()
            for i in range(count):
                el = loc.nth(i)
                if await el.is_visible():
                    await el.fill(value)
                    if description:
                        self.filled_fields[description] = value
                        print(f"  [OK] Filled {description}: {value}")
                    return True
        except Exception:
            pass
        return False
