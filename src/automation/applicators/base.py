"""
Base Form Applicator Interface.
"""

import re
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict
from playwright.async_api import Page
from src.core.models import CandidateProfile

CONTRACTOR_KEYWORDS = re.compile(
    r"\b(contractor|independent\s+contractor|b2b|freelance|hourly\s+rate|usd/hr|usd\s+per\s+hour)\b",
    re.IGNORECASE,
)

class BaseApplicator(ABC):
    def __init__(self, page: Page, profile: CandidateProfile):
        self.page = page
        self.profile = profile
        self.p_info = profile.personal_info
        self.prefs = profile.preferences
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

    async def fill_common_preferences(self) -> None:
        """Fill compensation (contractor vs dependent employee), notice period, and work authorization."""
        is_contractor = await self.detect_is_contractor_posting()
        salary_num = self.prefs.get_salary_value(is_contractor=is_contractor)
        salary_str = self.prefs.get_formatted_salary(is_contractor=is_contractor)
        modality_label = "Contractor" if is_contractor else "Dependent Employee (Default)"

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
