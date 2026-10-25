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

        country = "Uruguay"
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

        dial_code, code_digits, iso2 = dial_codes.get(country.lower(), ("+598", "598", "UY"))

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

    def _generate_deterministic_answer(self, question_text: str, salary_str: str = "", salary_num: Optional[int] = None) -> Optional[str]:
        """Generate factual, deterministic answers for contact and profile fields."""
        q = (question_text or "").strip().lower()
        if not q or len(q) < 3:
            return None

        # Skip standard contact fields already handled
        if any(k in q for k in ["first name", "last name", "full name", "email", "phone", "resume", "cv", "pronoun"]):
            return None

        if any(k in q for k in ["linkedin"]):
            return self.p_info.linkedin_url
        if any(k in q for k in ["github", "git repository"]):
            return self.p_info.github_url
        if any(k in q for k in ["portfolio", "personal website", "website", "blog"]):
            return self.p_info.portfolio_url
        if any(
            k in q
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
            if any(k in q for k in ["annual", "yearly", "per year", "/yr", "/year"]):
                if salary_num:
                    target_val = salary_num if "/ year" in salary_str else (salary_num * 12 if "/ month" in salary_str else salary_num)
                    return f"${target_val:,} USD / year"
            elif any(k in q for k in ["hourly", "per hour", "/hr", "/hour"]):
                if salary_num:
                    target_val = salary_num if "/ hour" in salary_str else max(1, round(salary_num / 160))
                    return f"${target_val:,} USD / hour"
            return salary_str or self.prefs.get_formatted_salary(is_contractor=False)

        if any(k in q for k in ["notice period", "when can you start", "earliest start", "availability to start", "how soon can you"]):
            return self.prefs.notice_period or "2 weeks"
        if any(k in q for k in ["years of experience", "how many years"]):
            return str(self.p_info.years_of_experience or 7)
        if any(k in q for k in ["current company", "current employer", "present employer"]):
            return self.p_info.current_company
        if any(k in q for k in ["english level", "english proficiency", "level of english", "your english"]):
            return self.prefs.english_level or "B2 Upper Intermediate"

        oq = getattr(self.profile, "open_questions", None)
        if any(k in q for k in ["level of education", "highest level of education", "education completed", "educational background"]):
            if oq and oq.education_level:
                return oq.education_level
            return "Bachelor's Degree in Information Technology (UTEC, in progress)"
        if any(k in q for k in ["time zone", "timezone", "working hours"]):
            if oq and oq.timezone_overlap:
                return oq.timezone_overlap
            return "UTC-3 (Montevideo, Uruguay), with full overlap with US and Americas workdays."
        if any(k in q for k in ["where are you based", "current location", "country of residence", "city and country"]):
            return self.p_info.location
        if any(k in q for k in ["telegram"]):
            return self.p_info.phone

        if oq and oq.custom_qa:
            for kw, ans in oq.custom_qa.items():
                if kw.lower() in q:
                    return ans

        return None

    def _generate_open_question_answer(self, question_text: str, salary_str: str = "", salary_num: Optional[int] = None) -> Optional[str]:
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

        if any(k in q for k in ["quota", "kpi", "metrics", "targets in your most recent role"]):
            if oq and oq.metrics_and_kpis:
                return oq.metrics_and_kpis
            return (
                "My key metrics focus on test coverage, release stability, reducing defect rates, "
                "and meeting sprint delivery goals."
            )

        if any(k in q for k in ["experience with automation", "describe your experience", "tell us about your experience", "relevant experience", "background", "cover letter", "anything else", "additional information"]):
            if oq and oq.experience_summary:
                return oq.experience_summary
            years = self.p_info.years_of_experience or 7
            company_mention = f"in my current role at {self.p_info.current_company}" if self.p_info.current_company else ""
            return (
                f"I have worked in software engineering and QA for over {years} years. "
                f"{company_mention.capitalize()}, I build automated test suites, maintain CI/CD pipelines, "
                "and collaborate with engineering teams to ensure release quality."
            )

        return None

    def _desired_dropdown_choice(self, question_text: str) -> Optional[List[str]]:
        """Return prioritized list of option substrings to pick for a dropdown/select question."""
        q = (question_text or "").strip().lower()
        if not q:
            return None
        if any(k in q for k in ["visa sponsorship", "require sponsorship", "require employer sponsorship", "h-1b"]):
            return ["No"] if self.p_info.requires_us_visa_sponsorship.strip().lower() != "yes" else ["Yes"]
        if "authorized to work" in q and any(c in q for c in ["united states", "u.s.", " in the us", "brazil", "brasil", "uk", "canada"]):
            return ["No"]
        if any(k in q for k in ["authorized to work", "legally authorized"]):
            return ["Yes"]
        if any(k in q for k in ["remote work", "comfortable working in a remote", "work remotely", "remote setting"]):
            return ["Yes"]
        if any(k in q for k in ["privacy policy", "consent", "interview transcript", "acknowledge", "data processing", "agree"]):
            return ["Yes, I consent", "Yes", "I agree", "Agree", "Accept"]
        if any(k in q for k in ["english"]):
            return ["B2", "Upper Intermediate", "Fluent", "Advanced", "Professional", "Intermediate"]
        if any(k in q for k in ["level of education", "highest level of education", "education"]):
            return ["Bachelor", "University", "Undergraduate", "Some College", "Associate"]
        if any(k in q for k in ["gender", "sex"]):
            chosen = getattr(self.p_info, "gender", None)
            return [chosen, "Decline to self-identify", "Prefer not to say"] if chosen else ["Decline to self-identify", "Prefer not to say"]
        if any(k in q for k in ["race", "ethnicity"]):
            chosen = getattr(self.p_info, "race", None)
            return [chosen, "Decline to self-identify", "Prefer not to say"] if chosen else ["Decline to self-identify", "Prefer not to say"]
        if any(k in q for k in ["veteran"]):
            chosen = getattr(self.p_info, "veteran_status", None)
            return [chosen, "I am not a veteran", "I am not a protected veteran", "Not a veteran", "No", "Decline to self-identify"] if chosen else ["Decline to self-identify", "I am not a veteran"]
        if any(k in q for k in ["disability"]):
            chosen = getattr(self.p_info, "disability_status", None)
            return [chosen, "No, I do not have a disability", "No", "Decline to self-identify", "I do not wish to answer"] if chosen else ["Decline to self-identify", "No, I do not have a disability"]
        return None

    async def fill_custom_questions(self, salary_str: str = "", salary_num: Optional[int] = None) -> None:
        """Inspect visible empty textareas, text inputs, selects, radio groups, and comboboxes."""
        try:
            # 1. Textareas and text inputs (excluding React-Select comboboxes)
            fields = self.page.locator("textarea, input[type='text']:not([role='combobox']), input:not([type]):not([role='combobox'])")
            count = await fields.count()
            for i in range(count):
                el = fields.nth(i)
                if not await el.is_visible():
                    continue
                curr_val = (await el.input_value() or "").strip()
                if curr_val:
                    continue

                q_text = await el.evaluate(
                    """(node) => {
                        if (node.classList && node.classList.contains('select__input')) return '';
                        const parts = [];
                        if (node.id) {
                            const lbl = document.querySelector(`label[for="${CSS.escape(node.id)}"]`);
                            if (lbl) parts.push(lbl.innerText);
                        }
                        const parentLbl = node.closest('label');
                        if (parentLbl) parts.push(parentLbl.innerText);
                        const fieldWrapper = node.closest('[class*="field"], [class*="question"], .application-question, fieldset');
                        if (fieldWrapper) {
                            parts.push(fieldWrapper.innerText.slice(0, 320));
                        }
                        if (node.getAttribute('aria-label')) parts.push(node.getAttribute('aria-label'));
                        if (node.getAttribute('placeholder')) parts.push(node.getAttribute('placeholder'));
                        return parts.join(' ').replace(/\\s+/g, ' ').trim();
                    }"""
                )
                if not q_text:
                    continue

                # A. Deterministic profile & preferences fields
                answer = self._generate_deterministic_answer(q_text, salary_str=salary_str, salary_num=salary_num)

                # B. Open-ended employer questions: analyze with local LLM agent based on candidate profile and job context
                if not answer:
                    try:
                        from src.automation.agent_adapter import answer_form_question
                        body_ctx = await self.page.evaluate("() => (document.body ? document.body.innerText.slice(0, 1500) : '')")
                        answer = await answer_form_question(
                            question_text=q_text,
                            job_title=self.role,
                            company=self.company,
                            job_context=body_ctx,
                            candidate_profile=self.profile,
                        )
                    except Exception:
                        answer = None

                # C. Fallback to static templates if LLM is unavailable
                if not answer:
                    answer = self._generate_open_question_answer(q_text, salary_str=salary_str, salary_num=salary_num)

                if answer:
                    await el.fill(answer)
                    short_q = (q_text[:55] + "...") if len(q_text) > 55 else q_text
                    self.filled_fields[f"Question ({short_q})"] = answer
                    print(f"  [OK] Answered '{short_q}'")

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
                        const ctrl = node.closest('.select__control, [class*="select__control"], [class*="select-shell"]');
                        if (ctrl && ctrl.querySelector('[class*="single-value"]')) {
                            return { alreadySelected: true, qText: '' };
                        }
                        const parts = [];
                        if (node.id) {
                            const lbl = document.querySelector(`label[for="${CSS.escape(node.id)}"]`);
                            if (lbl) parts.push(lbl.innerText);
                        }
                        const wrapper = node.closest('[class*="field"], [class*="question"], .application-question, .select, fieldset');
                        if (wrapper) parts.push(wrapper.innerText.slice(0, 320));
                        if (node.getAttribute('aria-label')) parts.push(node.getAttribute('aria-label'));
                        return { alreadySelected: false, qText: parts.join(' ').replace(/\\s+/g, ' ').trim() };
                    }"""
                )
                if meta.get("alreadySelected") or not meta.get("qText"):
                    continue
                q_text = meta["qText"]
                choices = self._desired_dropdown_choice(q_text)
                if not choices:
                    continue
                try:
                    await cb.click()
                    await asyncio.sleep(0.35)
                    options = self.page.locator("[role='option'], .select__option")
                    opt_count = await options.count()
                    picked = None
                    for wanted in choices:
                        for j in range(opt_count):
                            opt_el = options.nth(j)
                            if not await opt_el.is_visible():
                                continue
                            opt_txt = (await opt_el.inner_text() or "").strip()
                            if wanted.lower() == opt_txt.lower() or wanted.lower() in opt_txt.lower():
                                await opt_el.click()
                                picked = opt_txt
                                break
                        if picked:
                            break
                    if picked:
                        short_q = (q_text[:55] + "...") if len(q_text) > 55 else q_text
                        self.filled_fields[f"Dropdown ({short_q})"] = picked
                        print(f"  [OK] Selected '{picked}' for '{short_q}'")
                    else:
                        await self.page.keyboard.press("Escape")
                except Exception:
                    pass
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

                q_text = await sel.evaluate(
                    """(node) => {
                        const parts = [];
                        if (node.id) {
                            const lbl = document.querySelector(`label[for="${CSS.escape(node.id)}"]`);
                            if (lbl) parts.push(lbl.innerText);
                        }
                        const parent = node.closest('.application-question, [class*="field"], [class*="question"], label');
                        if (parent) parts.push(parent.innerText.slice(0, 240));
                        return parts.join(' ').replace(/\\s+/g, ' ').trim();
                    }"""
                )
                if not q_text:
                    continue

                choices = self._desired_dropdown_choice(q_text)
                if not choices:
                    continue

                options_data = await sel.evaluate(
                    """(node) => Array.from(node.options).map(o => ({ value: o.value, text: o.text }))"""
                )
                picked_val = None
                picked_text = None
                for wanted in choices:
                    for opt in options_data:
                        t = (opt.get("text") or "").strip()
                        if wanted.lower() == t.lower() or wanted.lower() in t.lower():
                            picked_val = opt.get("value")
                            picked_text = t
                            break
                    if picked_val is not None:
                        break

                if picked_val is not None:
                    await sel.select_option(value=picked_val)
                    short_q = (q_text[:50] + "...") if len(q_text) > 50 else q_text
                    self.filled_fields[f"Select ({short_q})"] = picked_text
                    print(f"  [OK] Selected option '{picked_text}' for '{short_q}'")
        except Exception:
            pass

    async def _fill_radio_groups(self) -> None:
        """Inspect radio button groups and select matching answers."""
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
                        const wrapper = node.closest('.application-question, [class*="question"], fieldset, [class*="field"], .section');
                        if (wrapper) {
                            const lbl = wrapper.querySelector('.application-label, legend, label, h3, h4, [class*="label"]');
                            if (lbl) return lbl.innerText.trim();
                            return wrapper.innerText.slice(0, 200).trim();
                        }
                        return '';
                    }"""
                )
                if not q_text:
                    continue

                choices = self._desired_dropdown_choice(q_text)
                if not choices:
                    continue

                picked = None
                for wanted in choices:
                    for j in range(g_count):
                        radio_el = group.nth(j)
                        label_text = await radio_el.evaluate(
                            """(node) => {
                                if (node.id) {
                                    const lbl = document.querySelector(`label[for="${CSS.escape(node.id)}"]`);
                                    if (lbl) return lbl.innerText.trim();
                                }
                                const parent = node.closest('label');
                                if (parent) return parent.innerText.trim();
                                const sibling = node.nextElementSibling;
                                if (sibling && sibling.tagName === 'LABEL') return sibling.innerText.trim();
                                return node.getAttribute('value') || '';
                            }"""
                        )
                        if wanted.lower() == label_text.lower() or wanted.lower() in label_text.lower():
                            await radio_el.check(force=True)
                            picked = label_text
                            break
                    if picked:
                        break

                if picked:
                    short_q = (q_text[:50] + "...") if len(q_text) > 50 else q_text
                    self.filled_fields[f"Radio ({short_q})"] = picked
                    print(f"  [OK] Selected radio '{picked}' for '{short_q}'")
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

                text = await cb.evaluate(
                    """(node) => {
                        const parent = node.closest('label, .application-question, [class*="consent"], [class*="privacy"], [class*="terms"]');
                        return parent ? parent.innerText.slice(0, 200).trim() : '';
                    }"""
                )
                text_lower = text.lower()
                if any(k in text_lower for k in ["privacy", "terms", "consent", "agree", "acknowledge", "data processing", "autorizo"]):
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
