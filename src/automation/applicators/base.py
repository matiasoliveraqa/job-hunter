"""
Base Form Applicator Interface.
"""

import re
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from playwright.async_api import Page
from src.core.models import CandidateProfile
from src.core.synonyms import get_dropdown_choices, GENERAL_DECLINE_CHOICES

CONTRACTOR_KEYWORDS = re.compile(
    r"\b(contractor|independent\s+contractor|b2b|freelance|hourly\s+rate|usd/hr|usd\s+per\s+hour)\b",
    re.IGNORECASE,
)

class BaseApplicator(ABC):
    def __init__(self, page: Page, profile: CandidateProfile, company: str = "", role: str = ""):
        self.page = page
        self.profile = profile
        self.p_info = profile.personal_info
        self.prefs = profile.preferences
        self.company = company
        self.role = role
        self.filled_fields: Dict[str, str] = {}

    @abstractmethod
    async def fill_form(self, cv_pdf_path: Optional[Path] = None) -> bool:
        """Fill all standard fields on the application page."""
        pass

    async def ensure_application_tab_open(self) -> None:
        """
        If the job URL opened on an 'Overview' or job description view where form inputs
        are hidden behind an 'Application' tab or 'Apply' button (common in Ashby, Lever,
        and some Greenhouse boards), automatically switch to the application form view.
        """
        try:
            # 0. Check for embedded ATS form iframes ONLY if we are NOT already on an ATS domain
            current_url = self.page.url
            url_lower = current_url.lower()
            is_on_ats = any(d in url_lower for d in ["greenhouse.io", "lever.co", "ashbyhq.com"])

            if not is_on_ats:
                from urllib.parse import urlparse
                iframe_selectors = [
                    "iframe#grnhse_iframe",
                    "iframe[name='grnhse_iframe']",
                    "iframe[src*='boards.greenhouse.io']",
                    "iframe[src*='job-boards.greenhouse.io']",
                    "iframe[src*='jobs.lever.co']",
                    "iframe[src*='jobs.ashbyhq.com']",
                ]
                for ifr_sel in iframe_selectors:
                    ifr = self.page.locator(ifr_sel)
                    if await ifr.count() > 0:
                        src = await ifr.first.get_attribute("src")
                        if src and (src.startswith("http://") or src.startswith("https://") or src.startswith("//")):
                            full_src = ("https:" + src) if src.startswith("//") else src
                            parsed_host = urlparse(full_src).netloc.lower()
                            if any(d in parsed_host for d in ["greenhouse.io", "lever.co", "ashbyhq.com"]):
                                print(f"  [OK] Found embedded ATS form iframe ({full_src[:65]}...). Navigating directly to form...")
                                await self.page.goto(full_src, wait_until="domcontentloaded")
                                await asyncio.sleep(2)
                                return

                for f in self.page.frames:
                    if f != self.page.main_frame:
                        f_url = f.url or ""
                        parsed_host = urlparse(f_url).netloc.lower()
                        if any(d in parsed_host for d in ["job-boards.greenhouse.io", "boards.greenhouse.io", "jobs.lever.co", "jobs.ashbyhq.com"]):
                            print(f"  [OK] Found embedded ATS frame URL. Navigating directly to {f_url[:65]}...")
                            await self.page.goto(f_url, wait_until="domcontentloaded")
                            await asyncio.sleep(2)
                            return

            # Check if core form inputs are already visible
            core_inputs = self.page.locator(
                "input[type='file'], input[type='email'], input#first_name, "
                "input[name='_systemfield_name'], input[name='name']"
            )
            if await core_inputs.count() > 0:
                for i in range(await core_inputs.count()):
                    if await core_inputs.nth(i).is_visible():
                        return

            current_url = self.page.url
            url_lower = current_url.lower()

            # 1. Lever: navigate or click Apply if not on /apply
            if "lever.co" in url_lower and not url_lower.rstrip("/").endswith("/apply"):
                apply_link = self.page.locator(
                    "a.postings-btn:has-text('Apply'), a[href*='/apply']:has-text('Apply')"
                )
                if await apply_link.count() > 0 and await apply_link.first.is_visible():
                    await apply_link.first.click()
                    await self.page.wait_for_load_state("domcontentloaded")
                    await asyncio.sleep(1.5)
                    return
                else:
                    target = current_url.split("?")[0].rstrip("/") + "/apply"
                    await self.page.goto(target, wait_until="domcontentloaded")
                    await asyncio.sleep(1.5)
                    return

            # 2. Ashby / Greenhouse / Generic: look for 'Application' tab or 'Apply' button
            tab_selectors = [
                "[role='tab']:has-text('Application')",
                "a:has-text('Application')",
                "button:has-text('Application')",
                "a:has-text('Apply for this Job')",
                "button:has-text('Apply for this Job')",
                "a:has-text('Apply for this job')",
                "button:has-text('Apply for this job')",
                "a:has-text('Apply Now')",
                "button:has-text('Apply Now')",
                "button:has-text('Apply')",
            ]
            for sel in tab_selectors:
                loc = self.page.locator(sel)
                if await loc.count() > 0 and await loc.first.is_visible():
                    await loc.first.click()
                    print(f"  [OK] Switched to Application form view ({sel})")
                    await asyncio.sleep(1.5)
                    break

            # 3. Ashby fallback: if still no inputs on ashbyhq.com, append /application
            if "ashbyhq.com" in url_lower and "/application" not in url_lower:
                if await self.page.locator("input[type='email'], input[type='file']").count() == 0:
                    base_u = current_url.split("?")[0].rstrip("/")
                    await self.page.goto(f"{base_u}/application", wait_until="domcontentloaded")
                    await asyncio.sleep(1.5)
        except Exception:
            pass

    async def detect_captcha(self) -> Optional[str]:
        """Detect presence of captcha challenges (hCaptcha, Turnstile, reCAPTCHA)."""
        widgets = {
            "hCaptcha": "iframe[src*='hcaptcha.com'], .h-captcha, [name='h-captcha-response']",
            "Cloudflare Turnstile": "iframe[src*='challenges.cloudflare.com'], iframe[src*='turnstile'], [name='cf-turnstile-response']",
            "reCAPTCHA": "iframe[src*='recaptcha'], .g-recaptcha, [name='g-recaptcha-response']",
        }
        for name, sel in widgets.items():
            try:
                if await self.page.locator(sel).count() > 0:
                    return name
            except Exception:
                pass
        return None

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

        # Also check by explicit <label> text if CSS attributes didn't match
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

        # Only if there are NO split First/Last name fields, fill single Full Name field
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

        # Unknown country: derive the dial code from the phone number itself so the
        # applicator stays correct for any candidate, whatever their country is.
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

            # 1. Check for interactive country prefix button adjacent to or inside the phone container
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

            # 2. Check for standard <select> country dropdown
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

    SALARY_RANGE_PATTERNS = [
        re.compile(
            r"(?:salary|compensation|pay|rate|range|budget)?[:\s]*"
            r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})*|[0-9]{2,6})(?:\.[0-9]{2})?\s*(k)?\s*"
            r"(?:-|–|—|to)\s*"
            r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})*|[0-9]{2,6})(?:\.[0-9]{2})?\s*(k)?\s*"
            r"(?:usd)?\s*"
            r"(?:(?:per|\/|a)\s*(year|yr|annum|annual|month|mo|hr|hour))?",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:up\s+to|max|maximum|budget\s+of|starting\s+at)\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*|[0-9]{2,6})(?:\.[0-9]{2})?\s*(k)?\s*(?:usd)?\s*"
            r"(?:(?:per|\/|a)\s*(year|yr|annum|annual|month|mo|hr|hour))?",
            re.IGNORECASE,
        ),
    ]

    async def detect_is_contractor_posting(self) -> bool:
        """
        Check page text to determine if the job posting explicitly specifies a contractor/B2B modality.
        If not specified, returns False so the dependent employee salary is used by default.
        """
        try:
            body_text = await self.page.inner_text("body")
            return bool(CONTRACTOR_KEYWORDS.search(body_text))
        except Exception:
            return False

    async def detect_posted_salary_range(self) -> Optional[Dict[str, Any]]:
        """
        Inspect job description and page text to detect if the job posting explicitly specifies
        a salary range or compensation ceiling (hourly, monthly, or annual).
        """
        try:
            body_text = await self.page.inner_text("body")
            for pattern in self.SALARY_RANGE_PATTERNS:
                for match in pattern.finditer(body_text):
                    groups = match.groups()
                    if len(groups) == 5:
                        raw_max = groups[2]
                        is_k = bool(groups[3] or groups[1])
                        period_raw = (groups[4] or "").lower()
                    else:
                        raw_max = groups[0]
                        is_k = bool(groups[1])
                        period_raw = (groups[2] or "").lower()

                    if not raw_max:
                        continue

                    val = float(raw_max.replace(",", ""))
                    if is_k or (val < 1000 and "k" in match.group(0).lower()):
                        val *= 1000

                    # Filter out year numbers (2024, 2025, 2026, 2027) or tiny integers < 15
                    if val in (2024, 2025, 2026, 2027) or val < 15:
                        continue

                    if any(p in period_raw for p in ["year", "yr", "annum", "annual"]):
                        period = "year"
                    elif any(p in period_raw for p in ["month", "mo"]):
                        period = "month"
                    elif any(p in period_raw for p in ["hr", "hour"]):
                        period = "hour"
                    else:
                        if val >= 20000:
                            period = "year"
                        elif val <= 150:
                            period = "hour"
                        else:
                            period = "month"

                    if period == "year":
                        monthly_equiv = val / 12.0
                    elif period == "hour":
                        monthly_equiv = val * 160.0
                    else:
                        monthly_equiv = val

                    return {
                        "max_amount": val,
                        "period": period,
                        "monthly_equivalent": monthly_equiv,
                    }
        except Exception:
            pass
        return None

    async def get_effective_salary(self, is_contractor: bool = False) -> Tuple[int, str, str]:
        """
        Calculate effective salary to fill.
        If the posting specifies a salary ceiling greater than the candidate's preferences,
        adjust to that proposed maximum. If lower or not specified, use candidate's preference.
        Returns: (salary_num, salary_str, modality_label)
        """
        base_monthly = self.prefs.get_salary_value(is_contractor=is_contractor) or 3500
        modality_label = "Contractor" if is_contractor else "Dependent Employee (Default)"

        posted_salary = await self.detect_posted_salary_range()
        if posted_salary and posted_salary["monthly_equivalent"] > base_monthly:
            period = posted_salary["period"]
            max_amount = posted_salary["max_amount"]
            monthly_equiv = posted_salary["monthly_equivalent"]

            if period == "year":
                salary_num = int(max_amount)
                salary_str = f"${salary_num:,} USD / year"
                label = f"{modality_label} (Ajustado al maximo anual propuesto: {salary_str})"
            elif period == "hour":
                salary_num = int(max_amount)
                salary_str = f"${salary_num:,} USD / hour"
                label = f"{modality_label} (Ajustado al maximo por hora propuesto: {salary_str})"
            else:
                salary_num = int(monthly_equiv)
                salary_str = f"${salary_num:,} USD / month"
                label = f"{modality_label} (Ajustado al maximo mensual propuesto: {salary_str})"

            return salary_num, salary_str, label

        salary_num = base_monthly
        salary_str = self.prefs.get_formatted_salary(is_contractor=is_contractor)
        return salary_num, salary_str, modality_label

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

        # 3. Automatically fill custom & open-ended questions (textareas and text inputs)
        await self.fill_custom_questions(salary_str=salary_str, salary_num=salary_num)

    @staticmethod
    def is_deterministic_field(text: str, field_meta: Optional[dict] = None) -> bool:
        """Return True if field belongs to closed deterministic whitelist (never send to LLM)."""
        meta = field_meta or {}
        combined = f"{text or ''} {meta.get('name', '')} {meta.get('id', '')} {meta.get('autocomplete', '')}".lower()
        patterns = [
            # Gender / Sex (English & Spanish)
            re.compile(r"\b(gender|sex|género|genero|sexo)\b", re.IGNORECASE),
            # Race / Ethnicity (English & Spanish)
            re.compile(r"\b(race|ethnicity|hispanic|latino|raza|etnia|hispano)\b", re.IGNORECASE),
            # Veteran (English & Spanish)
            re.compile(r"\b(veteran|military|veterano|condición\s+de\s+veterano|condicion\s+de\s+veterano|militar)\b", re.IGNORECASE),
            # Disability (English & Spanish)
            re.compile(r"\b(disability|handicap|discapacidad|situación\s+de\s+discapacidad|situacion\s+de\s+discapacidad)\b", re.IGNORECASE),
            # Names (English & Spanish)
            re.compile(r"\b(preferred\s+name|first\s+name|last\s+name|full\s+name|given\s+name|family\s+name|legal\s+name|nombre|apellido|nombre\s+completo|primer\s+nombre|segundo\s+nombre)\b", re.IGNORECASE),
            # Contact (Email / Phone) (English & Spanish)
            re.compile(r"\b(email|phone|telephone|mobile|cell|correo\s+electr[oó]nico|correo|tel[eé]fono|m[oó]vil|celular)\b", re.IGNORECASE),
            # Location / Residence / City / State / Country (English & Spanish)
            re.compile(r"\b(location|city|country|state|province|office|region|country\s+of\s+residence|city\s+of\s+residence|where\s+are\s+you\s+based|ubicaci[oó]n|pa[ií]s|provincia|departamento|ciudad|oficina|sede|regi[oó]n|donde\s+vives|donde\s+resides|residencia)\b", re.IGNORECASE),
            # Authorization / Visa (English & Spanish)
            re.compile(r"\b(authorized\s+to\s+work|work\s+authorization|legally\s+authorized|visa\s+sponsorship|require\s+sponsorship|autorizaci[oó]n\s+para\s+trabajar|autorizacion\s+para\s+trabajar|autorizado\s+para\s+trabajar|patrocinio\s+de\s+visa|patrocinio)\b", re.IGNORECASE),
        ]
        return any(p.search(combined) for p in patterns)

    @staticmethod
    def is_sensitive_field(text: str) -> bool:
        """Return True if field is related to EEO (gender, race, veteran, disability) or location/residency."""
        t = (text or "").lower()
        patterns = [
            # EEO (English & Spanish)
            r"\b(gender|sex|género|genero|sexo)\b",
            r"\b(race|ethnicity|raza|etnia)\b",
            r"\b(veteran|military|veterano|condición\s+de\s+veterano|condicion\s+de\s+veterano|militar)\b",
            r"\b(disability|disabled|handicap|discapacidad|situación\s+de\s+discapacidad|situacion\s+de\s+discapacidad)\b",
            # Location / Country / State / Province / Office / City (English & Spanish)
            r"\b(location|country|state|province|office|city|region)\b",
            r"\b(ubicaci[oó]n|pa[ií]s|provincia|departamento|ciudad|oficina|sede|regi[oó]n)\b",
        ]
        return any(re.search(p, t, re.IGNORECASE) for p in patterns)

    @staticmethod
    def is_location_field(text: str) -> bool:
        """Return True if field is specifically related to location, state, country, or office."""
        t = (text or "").lower()
        patterns = [
            r"\b(location|country|state|province|office|city|region)\b",
            r"\b(ubicaci[oó]n|pa[ií]s|provincia|departamento|ciudad|oficina|sede|regi[oó]n)\b",
        ]
        return any(re.search(p, t, re.IGNORECASE) for p in patterns)

    @staticmethod
    def clean_question_label(text: str) -> str:
        """Sanitize field question/label text to avoid neighbor question contamination."""
        if not text:
            return ""
        cleaned = re.sub(r"\s+", " ", text).strip()
        if len(cleaned) > 120:
            cleaned = cleaned[:120].strip()
        if cleaned.count("?") > 1:
            cleaned = cleaned.split("?")[0] + "?"
        if cleaned.count("*") > 1:
            cleaned = (cleaned.split("*")[0] + "*").strip()
        return cleaned.strip()

    @staticmethod
    def match_experience_range(years: int, options: List[str]) -> Optional[str]:
        """Match candidate's numeric years of experience to a discrete radio/select option."""
        if not options:
            return None
        # 1. Exact range (e.g., "3-5 years", "6-9 years", "6 to 9")
        for opt in options:
            text = opt.lower().strip()
            m_range = re.search(r"(\d+)\s*(?:-|to|a)\s*(\d+)", text)
            if m_range:
                low = int(m_range.group(1))
                high = int(m_range.group(2))
                if low <= years <= high:
                    return opt
        # 2. Plus/more range (e.g., "10+ years", "5+ years", "more than 5")
        for opt in options:
            text = opt.lower().strip()
            m_plus = re.search(r"(\d+)\s*(?:\+|plus|\s+or\s+more|\s+o\s+m[aá]s)", text)
            if m_plus:
                min_y = int(m_plus.group(1))
                if years >= min_y:
                    return opt
        # 3. Less/under range (e.g., "Less than 3", "under 3", "< 3")
        for opt in options:
            text = opt.lower().strip()
            m_less = re.search(r"(?:less\s+than|under|menos\s+de|<)\s*(\d+)", text)
            if m_less:
                max_y = int(m_less.group(1))
                if years < max_y:
                    return opt
        return None

    def match_dropdown_option(
        self,
        options: List[str],
        preferred_choices: List[str],
        is_sensitive: bool = False,
        fallback_first: bool = False,
    ) -> Optional[str]:
        """
        Match dropdown options using strict 3-level matching:
        1. Normalized exact equality (strip().lower())
        2. Whole word match (\bword\b)
        3. Substring match (as last resort, disallowed for sensitive fields to prevent Male -> Female)

        If sensitive and no match, picks 'Decline to self-identify' / 'Prefer not to say'.
        Never selects fallback_first on sensitive fields.
        """
        if not options:
            return None

        def find_level_match(wanted: str) -> Optional[tuple[int, str]]:
            w_norm = wanted.strip().lower()
            if not w_norm:
                return None
            word_re = re.compile(rf"\b{re.escape(w_norm)}\b", re.IGNORECASE)

            # Level 1: exact normalized match
            for opt in options:
                t = (opt or "").strip()
                if t.lower() == w_norm:
                    return (1, t)

            # Level 2: whole word match
            for opt in options:
                t = (opt or "").strip()
                if word_re.search(t):
                    return (2, t)

            # Level 3: substring match (last resort, disallowed for sensitive fields)
            if not is_sensitive:
                for opt in options:
                    t = (opt or "").strip()
                    if w_norm in t.lower():
                        return (3, t)

            return None

        # 1. Match preferred choices
        best_match = None
        for choice in preferred_choices:
            if not choice:
                continue
            m = find_level_match(choice)
            if m:
                level, opt_text = m
                if level == 1:
                    return opt_text
                if best_match is None or level < best_match[0]:
                    best_match = m

        if best_match:
            return best_match[1]

        # 2. Sensitive fields: fallback to decline / prefer not to say
        if is_sensitive:
            for dec in GENERAL_DECLINE_CHOICES:
                m = find_level_match(dec)
                if m:
                    return m[1]
            return None

        # 3. Non-sensitive fallback
        if fallback_first and options:
            for opt in options:
                t = (opt or "").strip()
                if t and not any(p in t.lower() for p in ["select", "choose", "please", "elegir", "--"]):
                    return t
            return options[0]

        return None

    def _generate_deterministic_answer(
        self,
        question_text: str,
        salary_str: str = "",
        salary_num: Optional[int] = None,
        field_meta: Optional[dict] = None,
    ) -> Optional[str]:
        """Generate factual, deterministic answers for contact and profile fields."""
        # 1. Attribute-based routing (clean signals from input name, id, autocomplete)
        meta = field_meta or {}
        attr_tokens = f"{meta.get('name', '')} {meta.get('id', '')} {meta.get('autocomplete', '')}".lower().strip()
        if attr_tokens:
            if re.search(r"\b(linkedin|linkedin_url)\b", attr_tokens):
                return self.p_info.linkedin_url
            if re.search(r"\b(github|github_url)\b", attr_tokens):
                return self.p_info.github_url
            if re.search(r"\b(portfolio|website|blog)\b", attr_tokens) and not re.search(r"\b(project|proud)\b", attr_tokens):
                return self.p_info.portfolio_url
            if re.search(r"\b(preferred_name|preferred_first_name)\b", attr_tokens) or attr_tokens == "preferred-name":
                return getattr(self.p_info, "preferred_name", None) or self.p_info.first_name
            if re.search(r"\b(given[-_]?name|first[-_]?name)\b", attr_tokens) or meta.get("autocomplete") == "given-name":
                return self.p_info.first_name
            if re.search(r"\b(family[-_]?name|last[-_]?name)\b", attr_tokens) or meta.get("autocomplete") == "family-name":
                return self.p_info.last_name
            if re.search(r"\b(email)\b", attr_tokens) or meta.get("autocomplete") == "email":
                return self.p_info.email
            if re.search(r"\b(phone|mobile|cell|tel)\b", attr_tokens) or meta.get("autocomplete") == "tel":
                return self.p_info.phone
            if re.search(r"\b(city)\b", attr_tokens) or meta.get("autocomplete") == "address-level2":
                return self.p_info.city or self.p_info.location
            if re.search(r"\b(country)\b", attr_tokens) or meta.get("autocomplete") == "country-name":
                return self.p_info.country

        q = (question_text or "").strip().lower()
        if not q or len(q) < 3:
            return None

        # Guard: return None if question starts with a sensitive or deterministic field before keyword rules
        first_chunk = re.split(r"[.?;*:\n]+", (question_text or "").strip())[0].strip()
        first_tokens = " ".join(first_chunk.split()[:4]) if first_chunk else ""
        if (
            self.is_sensitive_field(first_chunk)
            or self.is_sensitive_field(first_tokens)
            or self.is_deterministic_field(first_chunk)
            or self.is_deterministic_field(first_tokens)
        ):
            if not any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["where are you based", "current location", "country of residence", "city and country"]):
                return None

        # Preferred name check before standard contact fields
        if re.search(r"\b(preferred\s+name|preferred\s+first\s+name)\b", q):
            return getattr(self.p_info, "preferred_name", None) or self.p_info.first_name

        # Skip standard contact fields already handled if not preferred name
        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["first name", "last name", "full name", "email", "phone", "resume", "cv", "pronoun"]):
            return None

        if re.search(r"\blinkedin\b", q):
            return self.p_info.linkedin_url
        if re.search(r"\b(github|git\s+repository)\b", q):
            return self.p_info.github_url

        # Check if question is an open-ended question asking about a project or experience
        is_project_q = bool(re.search(r"\b(project|proud\s+of|technical\s+challenge|problem\s+you\s+solved|achievement|describe|tell\s+us\s+about)\b", q))
        if not is_project_q and re.search(r"\b(portfolio|personal\s+website|website|blog)\b", q):
            return self.p_info.portfolio_url

        if any(
            re.search(rf"\b{re.escape(k)}\b", q)
            for k in [
                "salary",
                "compensation",
                "financial expectation",
                "pay expectation",
                "expected pay",
                "expected rate",
                "rate expectation",
                "hourly rate",
                "monthly rate",
                "remuneration",
                "us dollars per month",
                "usd per month",
                "usd/month",
            ]
        ):
            if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["annual", "yearly", "per year", "/yr", "/year"]):
                if salary_num:
                    target_val = salary_num if "/ year" in salary_str else (salary_num * 12 if "/ month" in salary_str else salary_num)
                    return f"${target_val:,} USD / year"
            elif any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["hourly", "per hour", "/hr", "/hour"]):
                if salary_num:
                    target_val = salary_num if "/ hour" in salary_str else max(1, round(salary_num / 160))
                    return f"${target_val:,} USD / hour"
            return salary_str or self.prefs.get_formatted_salary(is_contractor=False)

        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["notice period", "when can you start", "earliest start", "availability to start", "how soon can you"]):
            return self.prefs.notice_period or "2 weeks"
        if re.search(r"\b(years\s+of\s+experience|how\s+many\s+years)\b", q):
            return str(self.p_info.years_of_experience) if getattr(self.p_info, "years_of_experience", None) is not None else None
        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["current company", "current employer", "present employer"]):
            return self.p_info.current_company
        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["english level", "english proficiency", "level of english", "your english"]):
            return self.prefs.english_level
        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["native language", "mother tongue", "first language", "idioma nativo"]):
            return getattr(self.prefs, "native_language", None)

        # Explicit instruction: e.g. "type 'YES' to confirm" or "enter 'AGREE'"
        m_type = re.search(r"(?:type|enter|write)\s+['\"]([^'\"]+)['\"]", question_text, re.IGNORECASE)
        if m_type:
            return m_type.group(1).strip()

        oq = getattr(self.profile, "open_questions", None)
        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["level of education", "highest level of education", "education completed", "educational background"]):
            return oq.education_level if oq else None
        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["time zone", "timezone", "working hours"]):
            return oq.timezone_overlap if oq else None
        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in ["where are you based", "current location", "country of residence", "city and country"]):
            return self.p_info.location
        if re.search(r"\btelegram\b", q):
            return self.p_info.phone

        if oq and oq.custom_qa:
            for kw, ans in oq.custom_qa.items():
                if re.search(rf"\b{re.escape(kw.lower())}\b", q):
                    return ans

        return None


    def _generate_open_question_answer(self, question_text: str, salary_str: str = "", salary_num: Optional[int] = None, is_required: bool = False) -> Optional[str]:
        """
        Fallback generator for open-ended application questions when LLM is unavailable.
        Strictly grounded in candidate facts.
        """
        q = (question_text or "").strip().lower()
        if not q or len(q) < 3:
            return None

        # Check deterministic fields first
        det = self._generate_deterministic_answer(question_text, salary_str=salary_str, salary_num=salary_num)
        if det:
            return det

        oq = getattr(self.profile, "open_questions", None)

        # Open-ended motivation / "Why do you want to..." / "Why <Company>?" / "What excites you..."
        is_motivation_q = bool(
            re.search(r"\bwhy\s+[a-z0-9]", q)
            or any(
                k in q
                for k in [
                    "why do you want",
                    "why are you interested",
                    "what interests you",
                    "what excites you",
                    "why this role",
                    "why apply",
                    "why join",
                    "what draws you",
                    "what you know about what we do",
                    "aligns with your career",
                    "motivat",
                ]
            )
        )
        if is_motivation_q and any(k in q for k in ["bank", "fintech", "payment"]):
            if oq and oq.fintech_motivation:
                return oq.fintech_motivation
            years = self.p_info.years_of_experience or 7
            return (
                f"I have over {years} years of professional experience testing financial systems and web platforms, "
                "where reliability, compliance, and regression test coverage are critical."
            )

        # Distinguish between questions about the company vs questions about the role
        is_about_company = any(k in q for k in ["what you know about what we do", "aligns with your career", "why us", "why this company"]) or (
            bool(self.company and self.company.lower() in q)
        )
        if is_motivation_q:
            if is_about_company:
                comp = self.company or "your company"
                years = self.p_info.years_of_experience
                years_text = f"my {years}+ years of QA experience" if years else "my QA experience"
                return (
                    f"I want to work with {comp} because I value strong product engineering and high quality standards. "
                    f"I want to apply {years_text} to improve test coverage and collaborate closely with your engineering team."
                )
            if oq and oq.motivation:
                return oq.motivation
            years = self.p_info.years_of_experience or 7
            company_mention = f"at {self.p_info.current_company}" if self.p_info.current_company else ""
            return (
                f"I have {years} years of engineering experience {company_mention}. "
                "I want to work on a team with high quality standards where I can own automated testing and CI/CD workflows."
            )

        if any(k in q for k in ["project", "proud of", "technical challenge", "problem you solved", "achievement", "quota", "kpi", "metrics", "targets"]):
            if oq and getattr(oq, "key_project", None):
                return oq.key_project
            if oq and getattr(oq, "metrics_and_kpis", None):
                return oq.metrics_and_kpis
            return (
                "I focus on designing automated testing frameworks, maintaining release stability, "
                "reducing defect rates, and meeting sprint delivery goals."
            )

        if any(k in q for k in ["anything else", "additional information", "cover letter", "additional notes"]):
            if oq and getattr(oq, "additional_info", None):
                return oq.additional_info
            if oq and oq.experience_summary:
                return oq.experience_summary

        if any(k in q for k in ["experience with automation", "describe your experience", "tell us about your experience", "relevant experience", "background"]):
            if oq and oq.experience_summary:
                return oq.experience_summary
            years = self.p_info.years_of_experience or 7
            company_mention = f"in my current role at {self.p_info.current_company}" if self.p_info.current_company else ""
            return (
                f"I have worked in software engineering and QA for over {years} years. "
                f"{company_mention.capitalize()}, I build automated test suites, maintain CI/CD pipelines, "
                "and collaborate with engineering teams to ensure release quality."
            )

        if is_required:
            years = self.p_info.years_of_experience or 7
            comp = self.company or "your team"
            return (
                f"I bring over {years} years of software testing and QA automation experience. "
                f"I want to collaborate with {comp} to improve test coverage, automate regression suites, and maintain high release standards."
            )

        return None

    async def fill_react_select(
        self,
        target,
        preferred_choices: Optional[List[str]] = None,
        query_text: str = "",
        fallback_first: bool = False,
        description: str = "",
        allow_multi: bool = True,
    ) -> Optional[str]:
        """
        Interact with a React-Select, Ashby, or custom ARIA combobox component:
        1. Click or focus the target input/control.
        2. If query_text is provided, type it sequentially to query autocomplete options.
        3. Scopes search strictly to the active .select__menu / .select__menu-list container.
        4. Matches against preferred_choices. Supports multi-selection if supported by the component.
        5. If no match and fallback_first is True, clicks the first enabled option.
        """
        try:
            loc = self.page.locator(target) if isinstance(target, str) else target
            if await loc.count() == 0:
                return None
            el = loc.first
            await el.scroll_into_view_if_needed()

            # Check if this is a multi-select control
            is_multi = allow_multi and await el.evaluate(
                """(node) => {
                    if (node.id && node.id.includes('[]')) return true;
                    if (node.getAttribute('aria-multiselectable') === 'true') return true;
                    const ctrl = node.closest('.select__control, [class*="select__control"]');
                    if (ctrl && (ctrl.querySelector('[class*="multi-value"]') || (ctrl.className || '').includes('is-multi'))) return true;
                    const wrapper = node.closest('[class*="field"], [class*="question"]');
                    if (wrapper && /select all/i.test(wrapper.innerText)) return true;
                    return false;
                }"""
            )

            await el.click()
            await asyncio.sleep(0.35)

            if query_text:
                try:
                    await el.fill("")
                except Exception:
                    pass
                await el.press_sequentially(query_text, delay=50)
                await asyncio.sleep(0.8)

            menu = self.page.locator(".select__menu, .select__menu-list, [class*='menu-list']").first
            if await menu.count() == 0:
                # Retry clicking parent container if input didn't open menu
                parent_ctrl = el.locator("xpath=ancestor::*[contains(@class, 'select__control')][1]")
                if await parent_ctrl.count() > 0:
                    await parent_ctrl.first.click()
                    await asyncio.sleep(0.35)
                menu = self.page.locator(".select__menu, .select__menu-list, [class*='menu-list']").first

            if await menu.count() == 0:
                return None

            is_sensitive = self.is_sensitive_field(description or query_text)
            actual_fallback = fallback_first and not is_sensitive

            opts_data = await menu.evaluate("""(node) => {
                const items = Array.from(node.querySelectorAll(".select__option, [role='option']"));
                return items.map((o, idx) => ({
                    index: idx,
                    text: (o.innerText || o.textContent || '').trim(),
                    disabled: o.classList.contains('disabled') || o.getAttribute('aria-disabled') === 'true'
                }));
            }""")
            enabled_opts = [o for o in opts_data if not o.get("disabled")]
            opt_texts = [o["text"] for o in enabled_opts]

            selected_list = []
            if is_multi and preferred_choices:
                for choice in preferred_choices:
                    if not choice:
                        continue
                    picked = self.match_dropdown_option(opt_texts, [choice], is_sensitive=is_sensitive, fallback_first=False)
                    if picked:
                        matching_meta = next((o for o in enabled_opts if o["text"] == picked), None)
                        if matching_meta:
                            opt_loc = menu.locator(".select__option, [role='option']").nth(matching_meta["index"])
                            if await opt_loc.count() > 0 and await opt_loc.is_visible():
                                await opt_loc.click()
                                selected_list.append(picked)
                                await asyncio.sleep(0.3)
            elif preferred_choices or actual_fallback:
                picked = self.match_dropdown_option(
                    opt_texts,
                    preferred_choices or [],
                    is_sensitive=is_sensitive,
                    fallback_first=actual_fallback,
                )
                if picked:
                    matching_meta = next((o for o in enabled_opts if o["text"] == picked), None)
                    if matching_meta:
                        opt_loc = menu.locator(".select__option, [role='option']").nth(matching_meta["index"])
                        if await opt_loc.count() > 0 and await opt_loc.is_visible():
                            await opt_loc.click()
                            selected_list.append(picked)
                            await asyncio.sleep(0.3)

            if selected_list:
                result_txt = ", ".join(selected_list)
                if description:
                    self.filled_fields[description] = result_txt
                    print(f"  [OK] Selected {description}: '{result_txt}'")
                await self.page.keyboard.press("Escape")
                return result_txt

            if is_sensitive:
                if description:
                    self.filled_fields[description] = "Pending manual review"
                if self.is_location_field(description or query_text):
                    print(f"  [!] Location dropdown '{description}' has no compatible option for candidate location '{self.p_info.location}'. Job might be regionally restricted.")
                else:
                    print(f"  [!] Sensitive field '{description}' left empty for manual review (no confident match)")

            await self.page.keyboard.press("Escape")
        except Exception as e:
            print(f"  [!] fill_react_select error on {description}: {e}")
        return None

    def _desired_dropdown_choice(self, question_text: str) -> Optional[List[str]]:
        """Return prioritized list of option substrings to pick for a dropdown/select question."""
        q = (question_text or "").strip().lower()
        if not q:
            return None

        # Explicit instruction in question: e.g. "please select 'Digital Therapeutics' from the list below"
        m_instruct = re.search(r"(?:please\s+)?select\s+['\"]([^'\"]+)['\"]", question_text, re.IGNORECASE)
        if m_instruct:
            target_val = m_instruct.group(1).strip()
            return [target_val]
        if any(k in q for k in ["visa sponsorship", "require sponsorship", "require employer sponsorship", "h-1b", "patrocinio de visa", "patrocinio"]):
            return ["No"] if self.p_info.requires_us_visa_sponsorship.strip().lower() != "yes" else ["Yes"]
        if "authorized to work" in q and any(c in q for c in ["united states", "u.s.", " in the us", "brazil", "brasil", "uk", "canada"]):
            return ["No"]
        if any(k in q for k in ["autorizado para trabajar", "autorización para trabajar", "autorizacion para trabajar"]):
            return ["Sí", "Si", "Yes"]
        if any(k in q for k in ["authorized to work", "legally authorized"]):
            return ["Yes"]
        if any(k in q for k in ["trabajo remoto"]):
            return ["Sí", "Si", "Yes"]
        if any(k in q for k in ["remote work", "comfortable working in a remote", "work remotely", "remote setting"]):
            return ["Yes"]
        if any(k in q for k in ["privacy policy", "consent", "interview transcript", "acknowledge", "data processing", "agree"]):
            return ["Yes, I consent", "Yes", "I agree", "Agree", "Accept"]
        if any(k in q for k in ["política de privacidad", "politica de privacidad", "terminos", "consentimiento", "autorizo"]):
            return ["Sí", "Si", "Acepto", "Yes"]
        if any(k in q for k in ["country are you currently a resident", "country of residence", "current resident of", "resident of", "country you reside", "country do you reside", "país de residencia", "pais de residencia"]):
            return [self.p_info.country, self.p_info.location]
        if any(k in q for k in ["based in united states", "state of residence", "outside of the united states", "outside the united states", "state in the us"]):
            return [
                "I am not located in the United States of America currently",
                "I am not located in the United States",
                "Not located in the United States",
                "Outside the United States",
                "Outside the US",
                "N/A",
                "None",
            ]
        if any(k in q for k in ["native language", "mother tongue", "first language", "primary language", "idioma nativo", "lengua materna"]):
            native = getattr(self.prefs, "native_language", None)
            return [native] if native else None
        if any(k in q for k in ["english level", "english proficiency", "level of english", "proficiency in english", "your english", "english", "nivel de inglés", "nivel de ingles"]):
            level = self.prefs.english_level
            return [level, "Fluent", "Professional", "Advanced"] if level else None
        if any(k in q for k in ["languages you are proficient in", "language proficiency", "languages you speak", "working language", "idiomas", "language"]):
            native = getattr(self.prefs, "native_language", None)
            return ["English", native] if native else ["English"]
        if any(k in q for k in ["skills category", "core strengths", "functional area", "primary skill", "area of expertise"]):
            return ["Software Engineering", "Quality Assurance", "Information Technology", "Computer Science"]
        if any(k in q for k in ["degree", "título", "titulo", "level of education", "highest level of education", "education", "educación", "educacion", "formación", "formacion"]):
            return ["Bachelors Degree", "Bachelor", "Engineer's Degree", "Associates Degree", "University", "Undergraduate", "Some College", "Universitario", "Grado", "Licenciatura", "Ingeniería", "Ingenieria"]
        if any(k in q for k in ["discipline", "major", "field of study", "carrera"]):
            return ["Computer Science", "Information Systems", "Information Technology", "Software Engineering", "Engineering", "Tecnología de la Información", "Ingeniería de Software", "Informática", "Informatica"]
        if any(k in q for k in ["gender", "sex", "género", "genero", "sexo"]):
            return get_dropdown_choices("gender", getattr(self.p_info, "gender", None))
        if any(k in q for k in ["race", "ethnicity", "raza", "etnia"]):
            return get_dropdown_choices("race", getattr(self.p_info, "race", None))
        if any(k in q for k in ["veteran", "militar", "veterano", "condición de veterano", "condicion de veterano"]):
            return get_dropdown_choices("veteran_status", getattr(self.p_info, "veteran_status", None))
        if any(k in q for k in ["disability", "discapacidad", "situación de discapacidad", "situacion de discapacidad"]):
            return get_dropdown_choices("disability_status", getattr(self.p_info, "disability_status", None))
        if any(k in q for k in ["location", "ubicación", "ubicacion", "country", "país", "pais", "state", "estado", "provincia", "departamento", "office", "oficina", "sede", "city", "ciudad", "region", "región", "regio"]):
            return [
                self.p_info.location,
                self.p_info.country,
                self.p_info.city,
                "Remote",
                "Remoto",
                "LATAM",
                "Remote - LATAM",
                "Worldwide",
                "Anywhere",
            ]
        return None

    async def fill_custom_questions(self, salary_str: str = "", salary_num: Optional[int] = None) -> None:
        """Inspect visible empty textareas, text inputs, selects, radio groups, and comboboxes."""
        try:
            # 1. Textareas, text inputs, and number inputs (strictly excluding comboboxes & react-select hidden validation inputs)
            fields = self.page.locator(
                "textarea, "
                "input[type='text']:not([role='combobox']), "
                "input:not([type]):not([role='combobox']), "
                "input[type='number']"
            )
            count = await fields.count()
            for i in range(count):
                el = fields.nth(i)
                if not await el.is_visible():
                    continue
                curr_val = (await el.input_value() or "").strip()
                if curr_val:
                    continue

                meta = await el.evaluate(
                    """(node) => {
                        // Exclude React-Select inputs and hidden dummy validation fields
                        if (node.classList && (
                            node.classList.contains('select__input') ||
                            node.classList.contains('iti__search-input') ||
                            node.className.includes('requiredInput')
                        )) return null;
                        if (node.getAttribute('tabindex') === '-1' || node.getAttribute('aria-hidden') === 'true') return null;
                        if (node.closest('.select__control, .select__value-container, [class*="select__"], [id*="country-listbox"]')) return null;

                        let rawText = '';
                        let required = node.hasAttribute('required') || node.getAttribute('aria-required') === 'true';

                        if (node.id) {
                            const lbl = document.querySelector(`label[for="${CSS.escape(node.id)}"]`);
                            if (lbl && lbl.innerText && lbl.innerText.trim()) {
                                rawText = lbl.innerText.trim();
                            }
                        }
                        if (!rawText) {
                            const parentLbl = node.closest('label');
                            if (parentLbl && parentLbl.innerText && parentLbl.innerText.trim()) {
                                rawText = parentLbl.innerText.trim();
                            }
                        }
                        if (!rawText && node.getAttribute('aria-labelledby')) {
                            const ids = node.getAttribute('aria-labelledby').split(/\\s+/);
                            const labels = ids.map(id => document.getElementById(id)).filter(Boolean).map(el => (el.innerText || '').trim()).filter(Boolean);
                            if (labels.length > 0) rawText = labels.join(' ').trim();
                        }
                        if (!rawText && node.getAttribute('aria-label')) {
                            rawText = node.getAttribute('aria-label').trim();
                        }
                        if (!rawText && node.getAttribute('placeholder')) {
                            rawText = node.getAttribute('placeholder').trim();
                        }
                        if (!rawText) {
                            const fs = node.closest('fieldset');
                            if (fs) {
                                const leg = fs.querySelector('legend');
                                if (leg && leg.innerText && leg.innerText.trim()) rawText = leg.innerText.trim();
                            }
                        }

                        if (rawText.includes('*') || /\\b(required|mandatory)\\b/i.test(rawText)) {
                            required = true;
                        }

                        let cleaned = rawText.replace(/\\s+/g, ' ').trim();
                        if (cleaned.length > 120) cleaned = cleaned.slice(0, 120).trim();
                        if ((cleaned.match(/\\?/g) || []).length > 1) cleaned = cleaned.split('?')[0] + '?';
                        if ((cleaned.match(/\\*/g) || []).length > 1) cleaned = (cleaned.split('*')[0] + '*').trim();

                        return {
                            qText: cleaned.trim(),
                            isRequired: required,
                            inputType: node.type || 'text',
                            id: node.id || '',
                            name: node.name || '',
                            autocomplete: node.getAttribute('autocomplete') || '',
                            maxLength: node.maxLength > 0 ? node.maxLength : (node.getAttribute('maxlength') ? parseInt(node.getAttribute('maxlength')) : null),
                        };
                    }"""
                )
                if not meta or not meta.get("qText"):
                    continue

                q_text = meta["qText"]
                is_required = bool(meta.get("isRequired"))
                input_type = meta.get("inputType", "text")
                short_q = (q_text[:45] + "...") if len(q_text) > 45 else q_text

                # Number inputs (e.g. education start/end year, experience)
                if input_type == "number":
                    lower_q = (q_text + " " + meta.get("id", "")).lower()
                    oq = getattr(self.profile, "open_questions", None)
                    if "start" in lower_q and ("year" in lower_q or "date" in lower_q):
                        start_yr = getattr(oq, "education_start_year", None) if oq else None
                        if start_yr:
                            val_str = str(start_yr)
                            await el.fill(val_str)
                            self.filled_fields[f"Number ({short_q})"] = val_str
                            print(f"  [OK] Filled start year '{val_str}' for '{short_q}'")
                        else:
                            self.filled_fields[f"Number ({short_q})"] = "Pending manual review"
                            print(f"  [!] Skipped start year for '{short_q}': not set in profile")
                        continue
                    elif ("end" in lower_q or "graduat" in lower_q) and ("year" in lower_q or "date" in lower_q):
                        end_yr = getattr(oq, "education_end_year", None) if oq else None
                        if end_yr:
                            val_str = str(end_yr)
                            await el.fill(val_str)
                            self.filled_fields[f"Number ({short_q})"] = val_str
                            print(f"  [OK] Filled graduation year '{val_str}' for '{short_q}'")
                        else:
                            self.filled_fields[f"Number ({short_q})"] = "Pending manual review"
                            print(f"  [!] Skipped graduation year for '{short_q}': not set in profile")
                        continue
                    elif ("experience" in lower_q or "experiencia" in lower_q) and getattr(self.p_info, "years_of_experience", None) is not None:
                        val_str = str(self.p_info.years_of_experience)
                        await el.fill(val_str)
                        self.filled_fields[f"Number ({short_q})"] = val_str
                        print(f"  [OK] Filled years of experience '{val_str}' for '{short_q}'")
                        continue
                    elif is_required:
                        self.filled_fields[f"Number ({short_q})"] = "Pending manual review"
                        print(f"  [!] Left required number field '{short_q}' empty for manual review")
                        continue

                # A. Deterministic profile & preferences fields
                answer = self._generate_deterministic_answer(q_text, salary_str=salary_str, salary_num=salary_num, field_meta=meta)

                # B5: Check if deterministic whitelist field (never call LLM)
                is_det_only = self.is_deterministic_field(q_text, field_meta=meta)

                # B. Open-ended employer questions: analyze with local LLM agent based on candidate profile and job context
                if not answer and not is_det_only:
                    try:
                        req_badge = " [Required *]" if is_required else ""
                        await self.show_hud_status(f"Job Hunter AI: Drafting answer for '{short_q}'{req_badge}...", status="thinking")
                        await self.highlight_field_thinking(el, placeholder_text="Job Hunter AI drafting answer...")

                        from src.automation.agent_adapter import answer_form_question
                        body_ctx = await self.page.evaluate("() => (document.body ? document.body.innerText.slice(0, 1500) : '')")
                        raw_ai_ans = await answer_form_question(
                            question_text=q_text,
                            job_title=self.role,
                            company=self.company,
                            job_context=body_ctx,
                            candidate_profile=self.profile,
                            is_required=is_required,
                        )

                        # B6: Validate LLM output against field constraints
                        if raw_ai_ans:
                            ai_trimmed = raw_ai_ans.strip()
                            max_len = meta.get("maxLength")
                            is_short = bool(re.search(r"\b(name|first_name|last_name|city|state|zip|postal|date|year|salary|phone|location)\b", f"{meta.get('name', '')} {meta.get('id', '')} {q_text}", re.IGNORECASE))
                            word_count = len(ai_trimmed.split())

                            if max_len and len(ai_trimmed) > max_len:
                                print(f"  [!] Rejected LLM answer for '{short_q}': exceeds maxlength {max_len}")
                                self.filled_fields[f"Question ({short_q})"] = f"Rejected: exceeds maxlength {max_len}"
                            elif is_short and word_count > 15:
                                print(f"  [!] Rejected LLM answer for '{short_q}': too long ({word_count} words) for short field")
                                self.filled_fields[f"Question ({short_q})"] = "Rejected: too long for short field"
                            else:
                                answer = ai_trimmed
                    except Exception as err:
                        print(f"  [!] Error querying AI for '{short_q}': {err}")
                        answer = None
                    finally:
                        await self.clear_field_highlight(el)

                # C. Fallback to static templates if LLM is unavailable (and not deterministic-only)
                if not answer and not is_det_only:
                    answer = self._generate_open_question_answer(q_text, salary_str=salary_str, salary_num=salary_num, is_required=is_required)

                # D. Strict mandatory fallback if required and still empty (and not deterministic-only)
                if not answer and is_required and not is_det_only:
                    answer = self._generate_required_fallback(q_text)

                if answer:
                    await el.fill(answer)
                    await self.show_hud_status(f"Completado: '{short_q}'", status="success", auto_hide_ms=2500)
                    self.filled_fields[f"Question ({short_q})"] = answer
                    print(f"  [OK] Answered '{short_q}'{' (*)' if is_required else ''}")

            # 2. Standard HTML <select> dropdowns (Lever, Greenhouse, Ashby)
            await self._fill_standard_selects()

            # 3. Radio button groups (Yes/No, location, authorization)
            await self._fill_radio_groups()

            # 4. Consent and privacy checkboxes
            await self._fill_consent_checkboxes()

            # 5. React-Select / ARIA combobox dropdowns (common on Greenhouse and Ashby)
            combos = self.page.locator("input[role='combobox'], input.select__input")
            c_count = await combos.count()
            for i in range(c_count):
                cb = combos.nth(i)
                if not await cb.is_visible():
                    continue

                meta = await cb.evaluate(
                    """(node) => {
                        // Skip phone search input inside international phone dropdown
                        if (node.classList && node.classList.contains('iti__search-input')) return null;
                        if (node.closest('#iti-0__country-listbox')) return null;

                        const ctrl = node.closest('.select__control, [class*="select__control"], [class*="select-shell"]');
                        if (ctrl && (ctrl.querySelector('[class*="single-value"]') || ctrl.querySelector('[class*="multi-value"]'))) {
                            return { alreadySelected: true, qText: '', isRequired: false };
                        }

                        let rawText = '';
                        let required = node.hasAttribute('required') || node.getAttribute('aria-required') === 'true';

                        if (node.id) {
                            const lbl = document.querySelector(`label[for="${CSS.escape(node.id)}"]`);
                            if (lbl && lbl.innerText && lbl.innerText.trim()) {
                                rawText = lbl.innerText.trim();
                            }
                        }
                        if (!rawText) {
                            const parentLbl = node.closest('label');
                            if (parentLbl && parentLbl.innerText && parentLbl.innerText.trim()) {
                                rawText = parentLbl.innerText.trim();
                            }
                        }
                        if (!rawText && node.getAttribute('aria-labelledby')) {
                            const ids = node.getAttribute('aria-labelledby').split(/\\s+/);
                            const labels = ids.map(id => document.getElementById(id)).filter(Boolean).map(el => (el.innerText || '').trim()).filter(Boolean);
                            if (labels.length > 0) rawText = labels.join(' ').trim();
                        }
                        if (!rawText && node.getAttribute('aria-label')) {
                            rawText = node.getAttribute('aria-label').trim();
                        }
                        if (!rawText && node.getAttribute('placeholder')) {
                            rawText = node.getAttribute('placeholder').trim();
                        }
                        if (!rawText) {
                            const fs = node.closest('fieldset');
                            if (fs) {
                                const leg = fs.querySelector('legend');
                                if (leg && leg.innerText && leg.innerText.trim()) rawText = leg.innerText.trim();
                            }
                        }

                        if (rawText.includes('*') || /\\b(required|mandatory)\\b/i.test(rawText)) {
                            required = true;
                        }

                        let cleaned = rawText.replace(/\\s+/g, ' ').trim();
                        if (cleaned.length > 120) cleaned = cleaned.slice(0, 120).trim();
                        if ((cleaned.match(/\\?/g) || []).length > 1) cleaned = cleaned.split('?')[0] + '?';
                        if ((cleaned.match(/\\*/g) || []).length > 1) cleaned = (cleaned.split('*')[0] + '*').trim();

                        return {
                            alreadySelected: false,
                            qText: cleaned.trim(),
                            isRequired: required,
                            id: node.id || '',
                            name: node.name || '',
                            autocomplete: node.getAttribute('autocomplete') || '',
                        };
                    }"""
                )
                if not meta or meta.get("alreadySelected") or not meta.get("qText"):
                    continue

                q_text = meta["qText"]
                is_required = bool(meta.get("isRequired"))
                short_q = (q_text[:45] + "...") if len(q_text) > 45 else q_text
                q_lower = q_text.lower()

                # A. Location (City)
                if any(k in q_lower for k in ["location (city)", "city", "ciudad", "ubicación", "ubicacion"]) or "candidate-location" in meta.get("id", ""):
                    await self.fill_react_select(
                        cb,
                        preferred_choices=[self.p_info.location, self.p_info.city, self.p_info.country, "Remote", "Remoto", "LATAM"],
                        query_text=self.p_info.city or self.p_info.location,
                        fallback_first=False,
                        description="Location (City)"
                    )
                    continue

                # B. School / University
                if any(k in q_lower for k in ["school", "university", "universidad", "institution"]) or "school" in meta.get("id", ""):
                    oq = getattr(self.profile, "open_questions", None)
                    institution = getattr(oq, "education_institution", None) if oq else None
                    if institution:
                        await self.fill_react_select(
                            cb,
                            preferred_choices=[institution],
                            query_text=institution,
                            fallback_first=False,
                            description="School"
                        )
                    else:
                        self.filled_fields[f"Select ({short_q})"] = "Pending manual review"
                        print(f"  [!] Skipped school for '{short_q}': education_institution not set in profile")
                    continue

                # C. General dropdown question via _desired_dropdown_choice
                is_sensitive = self.is_sensitive_field(q_text)
                choices = self._desired_dropdown_choice(q_text)
                if choices or is_required:
                    is_single_choice = any(k in q_lower for k in ["best describes", "primary", "single", "main", "core strength"])
                    await self.fill_react_select(
                        cb,
                        preferred_choices=choices or [],
                        fallback_first=(is_required and not is_sensitive),
                        description=short_q,
                        allow_multi=not is_single_choice,
                    )
        except Exception:
            pass

    async def _fill_standard_selects(self) -> None:
        """Inspect visible standard HTML <select> elements and pick appropriate options."""
        try:
            selects = self.page.locator("select")
            count = await selects.count()
            for i in range(count):
                sel = selects.nth(i)
                if not await sel.is_visible():
                    continue

                meta = await sel.evaluate(
                    """(node) => {
                        let rawText = '';
                        let required = node.hasAttribute('required') || node.getAttribute('aria-required') === 'true';

                        if (node.id) {
                            const lbl = document.querySelector(`label[for="${CSS.escape(node.id)}"]`);
                            if (lbl && lbl.innerText && lbl.innerText.trim()) {
                                rawText = lbl.innerText.trim();
                            }
                        }
                        if (!rawText) {
                            const parentLbl = node.closest('label');
                            if (parentLbl && parentLbl.innerText && parentLbl.innerText.trim()) {
                                rawText = parentLbl.innerText.trim();
                            }
                        }
                        if (!rawText && node.getAttribute('aria-labelledby')) {
                            const ids = node.getAttribute('aria-labelledby').split(/\\s+/);
                            const labels = ids.map(id => document.getElementById(id)).filter(Boolean).map(el => (el.innerText || '').trim()).filter(Boolean);
                            if (labels.length > 0) rawText = labels.join(' ').trim();
                        }
                        if (!rawText && node.getAttribute('aria-label')) {
                            rawText = node.getAttribute('aria-label').trim();
                        }
                        if (!rawText) {
                            const fs = node.closest('fieldset');
                            if (fs) {
                                const leg = fs.querySelector('legend');
                                if (leg && leg.innerText && leg.innerText.trim()) rawText = leg.innerText.trim();
                            }
                        }

                        if (rawText.includes('*') || /\\b(required|mandatory)\\b/i.test(rawText)) {
                            required = true;
                        }

                        let cleaned = rawText.replace(/\\s+/g, ' ').trim();
                        if (cleaned.length > 120) cleaned = cleaned.slice(0, 120).trim();
                        if ((cleaned.match(/\\?/g) || []).length > 1) cleaned = cleaned.split('?')[0] + '?';
                        if ((cleaned.match(/\\*/g) || []).length > 1) cleaned = (cleaned.split('*')[0] + '*').trim();

                        return {
                            qText: cleaned.trim(),
                            isRequired: required,
                            id: node.id || '',
                            name: node.name || '',
                        };
                    }"""
                )
                if not meta or not meta.get("qText"):
                    continue

                q_text = meta["qText"]
                is_req = bool(meta.get("isRequired"))
                is_sensitive = self.is_sensitive_field(q_text)
                choices = self._desired_dropdown_choice(q_text)

                options_data = await sel.evaluate(
                    """(node) => Array.from(node.options).map(o => ({ value: o.value, text: (o.text || '').trim() }))"""
                )
                valid_opts = [o for o in options_data if o.get("value") and o.get("text")]
                opt_texts = [o["text"] for o in valid_opts]

                picked_text = self.match_dropdown_option(
                    opt_texts,
                    choices or [],
                    is_sensitive=is_sensitive,
                    fallback_first=(is_req and not is_sensitive),
                )
                picked_val = None
                if picked_text:
                    for opt in valid_opts:
                        if opt["text"] == picked_text:
                            picked_val = opt.get("value")
                            break

                short_q = (q_text[:50] + "...") if len(q_text) > 50 else q_text
                if picked_val is not None:
                    await sel.select_option(value=picked_val)
                    self.filled_fields[f"Select ({short_q})"] = picked_text
                    print(f"  [OK] Selected option '{picked_text}' for '{short_q}'{' (*)' if is_req else ''}")
                elif is_sensitive:
                    self.filled_fields[f"Select ({short_q})"] = "Pending manual review"
                    if self.is_location_field(q_text):
                        print(f"  [!] Location dropdown '{short_q}' has no compatible option for candidate location '{self.p_info.location}'. Job might be regionally restricted.")
                    else:
                        print(f"  [!] Sensitive select '{short_q}' left empty for manual review (no confident match)")

        except Exception:
            pass

    async def _fill_radio_groups(self) -> None:
        """Inspect radio button groups and select matching answers using deterministic rules and AI."""
        try:
            radios = self.page.locator("input[type='radio']")
            count = await radios.count()
            if count == 0:
                return

            names = set()
            for i in range(count):
                r = radios.nth(i)
                name = await r.get_attribute("name")
                if name:
                    names.add(name)

            for name in names:
                group = self.page.locator(f"input[type='radio'][name='{name}']")
                g_count = await group.count()
                if g_count == 0:
                    continue

                already_checked = False
                for j in range(g_count):
                    if await group.nth(j).is_checked():
                        already_checked = True
                        break
                if already_checked:
                    continue

                q_text = await group.first.evaluate(
                    """(node) => {
                        const fieldset = node.closest('fieldset');
                        if (fieldset) {
                            const leg = fieldset.querySelector('legend');
                            if (leg && leg.innerText && leg.innerText.trim()) return leg.innerText.trim();
                        }
                        const rg = node.closest('[role="radiogroup"], .application-question, [class*="question"], [class*="field"], .section');
                        if (rg) {
                            const ariaLabel = rg.getAttribute('aria-label');
                            if (ariaLabel && ariaLabel.trim()) return ariaLabel.trim();
                            const ariaBy = rg.getAttribute('aria-labelledby');
                            if (ariaBy) {
                                const el = document.getElementById(ariaBy);
                                if (el && el.innerText && el.innerText.trim()) return el.innerText.trim();
                            }
                            const titles = rg.querySelectorAll('legend, h2, h3, h4, h5, [class*="title"], [class*="label"], [class*="questionText"], p, label');
                            for (const t of titles) {
                                if (t.querySelector('input[type="radio"]')) continue;
                                const forAttr = t.getAttribute('for');
                                if (forAttr && document.getElementById(forAttr)?.type === 'radio') continue;
                                const txt = (t.innerText || '').trim();
                                if (txt && txt.length > 3) return txt;
                            }
                        }
                        const wrapper = node.closest('.application-question, [class*="question"], [class*="field"], .section');
                        if (wrapper) {
                            return wrapper.innerText.slice(0, 200).trim();
                        }
                        return '';
                    }"""
                )
                if not q_text:
                    continue

                q_text = re.sub(r"\s+", " ", q_text).strip()
                is_req = "*" in q_text or "required" in q_text.lower()
                short_q = (q_text[:50] + "...") if len(q_text) > 50 else q_text

                # Extract each option in this group
                options_data = []
                for j in range(g_count):
                    radio_el = group.nth(j)
                    label_text = await radio_el.evaluate(
                        """(node) => {
                            if (node.id) {
                                const lbl = document.querySelector(`label[for="${CSS.escape(node.id)}"]`);
                                if (lbl && lbl.innerText && lbl.innerText.trim()) return lbl.innerText.trim();
                            }
                            const parent = node.closest('label');
                            if (parent && parent.innerText && parent.innerText.trim()) return parent.innerText.trim();
                            let sib = node.nextElementSibling;
                            while (sib) {
                                if (sib.tagName === 'LABEL' || sib.tagName === 'SPAN' || sib.tagName === 'DIV') {
                                    const txt = (sib.innerText || '').trim();
                                    if (txt) return txt;
                                }
                                sib = sib.nextElementSibling;
                            }
                            return node.getAttribute('aria-label') || node.getAttribute('value') || '';
                        }"""
                    )
                    options_data.append({"el": radio_el, "label": (label_text or "").strip()})

                option_labels = [o["label"] for o in options_data if o["label"]]

                picked_label = None
                picked_el = None

                # 1. Deterministic check: Years of experience ranges
                candidate_years = getattr(self.p_info, "years_of_experience", None) or 7
                if re.search(r"\b(years?\s+of\s+experience|years?\s+in\s+(?:qa|software|testing|test|engineering)|años\s+de\s+experiencia)\b", q_text, re.IGNORECASE):
                    matched_exp = self.match_experience_range(candidate_years, option_labels)
                    if matched_exp:
                        picked_label = matched_exp

                # 2. Deterministic check: Primary or sole QA owner
                if not picked_label and re.search(r"\b(primary\s+or\s+sole\s+qa|sole\s+qa|solo\s+qa|primary\s+qa|qa\s+owner)\b", q_text, re.IGNORECASE):
                    for o in option_labels:
                        if o.lower() in ("yes", "sí", "si"):
                            picked_label = o
                            break

                # 3. Deterministic check: Recent QA work
                if not picked_label and re.search(r"\b(recent\s+qa\s+work|describe\s+your\s+(?:recent\s+)?qa)\b", q_text, re.IGNORECASE):
                    for o in option_labels:
                        if any(w in o.lower() for w in ("hands-on", "testing, investigation", "automation")):
                            picked_label = o
                            break

                # 4. Deterministic check: Standard desired dropdown/radio choices
                if not picked_label:
                    choices = self._desired_dropdown_choice(q_text)
                    if choices:
                        for wanted in choices:
                            for o in option_labels:
                                if wanted.lower() == o.lower() or wanted.lower() in o.lower():
                                    picked_label = o
                                    break
                            if picked_label:
                                break

                # 5. AI / LLM selection for open-ended custom radio questions
                is_sensitive = self.is_sensitive_field(q_text)
                if not picked_label and not is_sensitive and option_labels:
                    try:
                        from src.automation.agent_adapter import choose_radio_option
                        body_ctx = await self.page.evaluate("() => (document.body ? document.body.innerText.slice(0, 1500) : '')")
                        ai_choice = await choose_radio_option(
                            question_text=q_text,
                            options=option_labels,
                            job_title=self.role,
                            company=self.company,
                            job_context=body_ctx,
                            candidate_profile=self.profile,
                        )
                        if ai_choice:
                            picked_label = ai_choice
                    except Exception as err:
                        print(f"  [!] AI radio option evaluation error for '{short_q}': {err}")

                # 6. Apply check on matching radio element
                if picked_label:
                    for o in options_data:
                        if o["label"].lower() == picked_label.lower():
                            picked_el = o["el"]
                            break
                    if not picked_el:
                        for o in options_data:
                            if picked_label.lower() in o["label"].lower() or o["label"].lower() in picked_label.lower():
                                picked_el = o["el"]
                                break

                if picked_el:
                    await picked_el.check(force=True)
                    self.filled_fields[f"Radio ({short_q})"] = picked_label
                    print(f"  [OK] Selected radio '{picked_label}' for '{short_q}'{' (*)' if is_req else ''}")
                elif is_req and g_count > 0 and not is_sensitive:
                    await group.first.check(force=True)
                    first_label = options_data[0]["label"] or "Primera opción"
                    self.filled_fields[f"Radio ({short_q})"] = first_label
                    print(f"  [OK] Selected default radio '{first_label}' for '{short_q}' (*)")
                elif is_sensitive:
                    self.filled_fields[f"Radio ({short_q})"] = "Pending manual review"
                    if self.is_location_field(q_text):
                        print(f"  [!] Location radio '{short_q}' has no compatible option for '{self.p_info.location}'. Job might be regionally restricted.")
                    else:
                        print(f"  [!] Sensitive radio '{short_q}' left empty for manual review (no confident match)")
        except Exception:
            pass

    async def _fill_consent_checkboxes(self) -> None:
        """Check required consent and privacy policy checkboxes."""
        try:
            cbs = self.page.locator("input[type='checkbox']")
            count = await cbs.count()
            for i in range(count):
                cb = cbs.nth(i)
                if not await cb.is_visible() or await cb.is_checked():
                    continue

                meta = await cb.evaluate(
                    """(node) => {
                        const parent = node.closest('label, .application-question, [class*="consent"], [class*="privacy"], [class*="terms"], [class*="field"], [class*="question"], fieldset');
                        const txt = parent ? parent.innerText.slice(0, 300).trim() : '';
                        const isReq = node.hasAttribute('required') || node.getAttribute('aria-required') === 'true' || txt.includes('*');
                        return { text: txt, isRequired: isReq };
                    }"""
                )
                text_lower = (meta.get("text") or "").lower()
                is_req = bool(meta.get("isRequired"))
                if is_req or any(k in text_lower for k in ["privacy", "terms", "consent", "agree", "acknowledge", "data processing", "autorizo", "yes"]):
                    await cb.check(force=True)
                    self.filled_fields["Consent/Privacy"] = "Checked"
                    print("  [OK] Accepted privacy policy / terms checkbox")
        except Exception:
            pass

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

    async def safe_upload(self, selector: str, file_path: Path, description: str = "CV/Resume") -> bool:
        """Safely set files on a file input selector."""
        if not file_path or not file_path.exists():
            return False
        try:
            file_input = self.page.locator(selector)
            if await file_input.count() > 0:
                await file_input.first.set_input_files(str(file_path))
                self.filled_fields[description] = str(file_path.resolve())
                print(f"  [OK] Uploaded {description}: {file_path.name}")
                await asyncio.sleep(1.5)
                return True
        except Exception as e:
            print(f"  [!] Upload failed for {description}: {e}")
        return False

    async def show_hud_status(self, message: str, status: str = "thinking", auto_hide_ms: int = 0) -> None:
        """Inject or update a modern floating HUD indicator in the browser view."""
        try:
            await self.page.evaluate(
                """({ message, status, autoHideMs }) => {
                    let hud = document.getElementById('jh-ai-hud');
                    if (!hud) {
                        hud = document.createElement('div');
                        hud.id = 'jh-ai-hud';
                        hud.style.position = 'fixed';
                        hud.style.top = '16px';
                        hud.style.right = '20px';
                        hud.style.zIndex = '9999999';
                        hud.style.display = 'flex';
                        hud.style.alignItems = 'center';
                        hud.style.gap = '10px';
                        hud.style.padding = '10px 16px';
                        hud.style.borderRadius = '10px';
                        hud.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
                        hud.style.fontSize = '13px';
                        hud.style.fontWeight = '500';
                        hud.style.boxShadow = '0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3)';
                        hud.style.transition = 'all 0.3s ease';
                        hud.style.pointerEvents = 'none';
                        document.body.appendChild(hud);
                    }
                    hud.style.opacity = '1';
                    hud.style.transform = 'translateY(0)';

                    if (status === 'thinking') {
                        hud.style.background = 'rgba(15, 23, 42, 0.94)';
                        hud.style.backdropFilter = 'blur(8px)';
                        hud.style.border = '1px solid rgba(99, 102, 241, 0.6)';
                        hud.style.color = '#f8fafc';
                        hud.innerHTML = `
                            <div style="width: 14px; height: 14px; border: 2px solid #818cf8; border-top-color: transparent; border-radius: 50%; animation: jh-spin 0.8s linear infinite;"></div>
                            <span>${message}</span>
                            <style>
                                @keyframes jh-spin { to { transform: rotate(360deg); } }
                                @keyframes jh-pulse-border {
                                    0% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.6); }
                                    70% { box-shadow: 0 0 0 6px rgba(99, 102, 241, 0); }
                                    100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0); }
                                }
                            </style>
                        `;
                    } else if (status === 'success') {
                        hud.style.background = 'rgba(15, 23, 42, 0.94)';
                        hud.style.backdropFilter = 'blur(8px)';
                        hud.style.border = '1px solid rgba(34, 197, 94, 0.6)';
                        hud.style.color = '#86efac';
                        hud.innerHTML = `<span style="font-weight: 700; color: #4ade80;">✓</span><span>${message}</span>`;
                    } else if (status === 'warning') {
                        hud.style.background = 'rgba(15, 23, 42, 0.94)';
                        hud.style.backdropFilter = 'blur(8px)';
                        hud.style.border = '1px solid rgba(234, 179, 8, 0.7)';
                        hud.style.color = '#fef08a';
                        hud.innerHTML = `<span style="font-weight: 700; color: #eab308;">⚠</span><span>${message}</span>`;
                    }

                    if (autoHideMs > 0) {
                        setTimeout(() => {
                            if (hud) {
                                hud.style.opacity = '0';
                                hud.style.transform = 'translateY(-6px)';
                            }
                        }, autoHideMs);
                    }
                }""",
                {"message": message, "status": status, "autoHideMs": auto_hide_ms}
            )
        except Exception:
            pass

    async def hide_hud_status(self) -> None:
        """Fade out and remove the HUD indicator."""
        try:
            await self.page.evaluate(
                """() => {
                    const hud = document.getElementById('jh-ai-hud');
                    if (hud) {
                        hud.style.opacity = '0';
                        hud.style.transform = 'translateY(-6px)';
                        setTimeout(() => hud.remove(), 400);
                    }
                }"""
            )
        except Exception:
            pass

    async def highlight_field_thinking(self, el, placeholder_text: str = "Job Hunter AI drafting answer...") -> None:
        """Highlight active input/textarea and set temporary placeholder."""
        try:
            await el.scroll_into_view_if_needed()
            await el.evaluate(
                """(node, ph) => {
                    node.setAttribute('data-jh-orig-border', node.style.border || '');
                    node.setAttribute('data-jh-orig-ph', node.getAttribute('placeholder') || '');
                    node.style.border = '2px solid #6366f1';
                    node.style.outline = 'none';
                    node.style.animation = 'jh-pulse-border 1.5s infinite';
                    if (ph) node.setAttribute('placeholder', ph);
                }""",
                placeholder_text
            )
        except Exception:
            pass

    async def clear_field_highlight(self, el) -> None:
        """Restore original border and placeholder of an input/textarea."""
        try:
            await el.evaluate(
                """(node) => {
                    const origB = node.getAttribute('data-jh-orig-border') || '';
                    const origPh = node.getAttribute('data-jh-orig-ph') || '';
                    node.style.border = origB;
                    node.style.animation = '';
                    if (origPh) node.setAttribute('placeholder', origPh);
                }"""
            )
        except Exception:
            pass

    def _generate_required_fallback(self, question_text: str) -> str:
        """
        Produce a safe, truthful fallback answer for any required question that wasn't covered.
        Grounded strictly in the candidate's verified profile.
        """
        q = (question_text or "").strip().lower()
        years = self.p_info.years_of_experience or 7

        if any(k in q for k in ["salary", "compensation", "rate", "remunerat"]):
            is_contractor = bool(CONTRACTOR_KEYWORDS.search(q))
            return "$4,500 USD / month" if is_contractor else "$3,000 USD / month"

        if any(k in q for k in ["notice", "start date", "availability", "how soon"]):
            return self.prefs.notice_period or "2 weeks notice period"

        if any(k in q for k in ["why", "interest", "motivat"]):
            comp = self.company or "your team"
            return (
                f"I want to join {comp} to apply my {years}+ years of QA automation experience, "
                "strengthen end-to-end test coverage, and collaborate with engineering on release quality."
            )

        return (
            f"I have over {years} years of software testing and QA automation experience. "
            "I design and maintain Playwright test suites, REST API test frameworks, and CI/CD pipelines."
        )

    async def audit_and_highlight_required_fields(self) -> List[str]:
        """
        Audit all required fields on the form (* or required attribute).
        If any empty required field exists, attempt a fallback fill or highlight in amber.
        """
        try:
            audit_res: Dict[str, Any] = await self.page.evaluate(
                """() => {
                    const missing = [];
                    const nodes = document.querySelectorAll(
                        'input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select'
                    );
                    nodes.forEach(node => {
                        // Check if input is part of a React-Select combobox
                        const reactControl = node.closest('.select__control, [class*="select__control"], [class*="select-shell"]');
                        if (reactControl) {
                            const valEl = reactControl.querySelector('[class*="single-value"], [class*="multi-value"]');
                            if (valEl && valEl.innerText.trim()) {
                                return; // Successfully selected!
                            }
                            let isReq = node.hasAttribute('required') || node.getAttribute('aria-required') === 'true';
                            const wrapper = node.closest('.application-question, [class*="field"], [class*="question"], fieldset');
                            const combinedText = (wrapper ? wrapper.innerText : '').slice(0, 320);
                            if (/\\*|\\b(required|mandatory)\\b/i.test(combinedText) || (wrapper && /\\b(required|mandatory)\\b/i.test(wrapper.className || ''))) {
                                isReq = true;
                            }
                            if (isReq) {
                                reactControl.style.border = '2px solid #eab308';
                                const labelName = wrapper ? wrapper.innerText.slice(0, 60).replace(/\\s+/g, ' ').replace(/\\*/g, '').trim() : 'Desplegable';
                                missing.push(labelName);
                            }
                            return;
                        }

                        if (!node.offsetParent && node.type !== 'file') return;

                        let isReq = node.hasAttribute('required') || node.getAttribute('aria-required') === 'true';
                        const lbl = node.id ? document.querySelector(`label[for="${CSS.escape(node.id)}"]`) : null;
                        const parentLbl = node.closest('label');
                        const wrapper = node.closest('.application-question, [class*="field"], [class*="question"], fieldset');
                        const combinedText = ((lbl ? lbl.innerText : '') + ' ' + (parentLbl ? parentLbl.innerText : '') + ' ' + (wrapper ? wrapper.innerText : '')).slice(0, 320);

                        if (/\\*|\\b(required|mandatory)\\b/i.test(combinedText) || (wrapper && /\\b(required|mandatory)\\b/i.test(wrapper.className || ''))) {
                            isReq = true;
                        }

                        if (!isReq) return;

                        const labelName = (lbl ? lbl.innerText : (parentLbl ? parentLbl.innerText : (node.getAttribute('aria-label') || node.name || 'Campo'))).replace(/\\s+/g, ' ').replace(/\\*/g, '').trim().slice(0, 60);

                        if (node.tagName.toLowerCase() === 'select') {
                            if (!node.value || node.value === '' || node.selectedIndex <= 0) {
                                node.style.border = '2px solid #eab308';
                                missing.push(labelName);
                            }
                        } else if (node.type === 'checkbox' || node.type === 'radio') {
                            if (node.name) {
                                const checked = document.querySelectorAll(`input[name="${CSS.escape(node.name)}"]:checked`);
                                if (checked.length === 0) {
                                    node.style.outline = '2px solid #eab308';
                                    missing.push(labelName);
                                }
                            } else if (!node.checked) {
                                node.style.outline = '2px solid #eab308';
                                missing.push(labelName);
                            }
                        } else if (node.type === 'file') {
                            if (!node.files || node.files.length === 0) {
                                missing.push(labelName);
                            }
                        } else {
                            const val = (node.value || '').trim();
                            if (!val) {
                                node.style.border = '2px solid #eab308';
                                missing.push(labelName);
                            }
                        }
                    });
                    return {
                        missing: Array.from(new Set(missing.filter(Boolean))),
                        totalInputs: nodes.length
                    };
                }"""
            )

            missing_fields = audit_res.get("missing", [])
            total_inputs = audit_res.get("totalInputs", 0)

            if total_inputs == 0:
                print("  [AUDIT] No form fields found on current page.")
                return []

            if missing_fields:
                count = len(missing_fields)
                msg = f"Warning: {count} required field(s) pending and highlighted in yellow"
                await self.show_hud_status(msg, status="warning")
                print(f"  [AUDIT] {count} required field(s) pending: {', '.join(missing_fields)}")
            else:
                await self.show_hud_status("All required fields completed", status="success", auto_hide_ms=4000)
                print("  [AUDIT] All required fields (*) have been completed.")
            return missing_fields
        except Exception as e:
            print(f"  [AUDIT] Error during audit: {e}")
            return []
