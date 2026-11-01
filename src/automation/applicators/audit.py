"""
Application page auditing, captcha detection, and tab navigation mixin.
"""

import asyncio
from typing import Optional, Dict, List, Any
from urllib.parse import urlparse


class AuditMixin:
    """Methods for opening application tabs, detecting challenges, and auditing required fields."""

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
            ats_domains = [
                "greenhouse.io", "lever.co", "ashbyhq.com",
                "workable.com", "breezy.hr", "recruitee.com",
                "bamboohr.com", "bamboohr.co.uk",
            ]
            is_on_ats = any(d in url_lower for d in ats_domains)

            if not is_on_ats:
                iframe_selectors = [
                    "iframe#grnhse_iframe",
                    "iframe[name='grnhse_iframe']",
                    "iframe[src*='boards.greenhouse.io']",
                    "iframe[src*='job-boards.greenhouse.io']",
                    "iframe[src*='jobs.lever.co']",
                    "iframe[src*='jobs.ashbyhq.com']",
                    "iframe[src*='workable.com']",
                    "iframe[src*='breezy.hr']",
                    "iframe[src*='recruitee.com']",
                    "iframe[src*='bamboohr.com']",
                ]
                for ifr_sel in iframe_selectors:
                    ifr = self.page.locator(ifr_sel)
                    if await ifr.count() > 0:
                        src = await ifr.first.get_attribute("src")
                        if src and (src.startswith("http://") or src.startswith("https://") or src.startswith("//")):
                            full_src = ("https:" + src) if src.startswith("//") else src
                            parsed_host = urlparse(full_src).netloc.lower()
                            if any(d in parsed_host for d in ats_domains):
                                print(f"  [OK] Found embedded ATS form iframe ({full_src[:65]}...). Navigating directly to form...")
                                await self.page.goto(full_src, wait_until="domcontentloaded")
                                await asyncio.sleep(2)
                                return

                for f in self.page.frames:
                    if f != self.page.main_frame:
                        f_url = f.url or ""
                        parsed_host = urlparse(f_url).netloc.lower()
                        if any(d in parsed_host for d in ats_domains):
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

            # 2. Ashby / Greenhouse / Generic / BambooHR: look for 'Application' tab or 'Apply' button
            tab_selectors = [
                "[role='tab']:has-text('Application')",
                "a:has-text('Application')",
                "button:has-text('Application')",
                "a:has-text('Apply for This Job')",
                "button:has-text('Apply for This Job')",
                "a:has-text('Apply for this Job')",
                "button:has-text('Apply for this Job')",
                "a:has-text('Apply for this job')",
                "button:has-text('Apply for this job')",
                "a:has-text('Apply Now')",
                "button:has-text('Apply Now')",
                "a:has-text('Apply to Position')",
                "button:has-text('Apply to Position')",
                "a:has-text('Apply for Position')",
                "button:has-text('Apply for Position')",
                "a:has-text('Postularme')",
                "button:has-text('Postularme')",
                "button:has-text('Apply')",
            ]
            combined_tab_selector = ", ".join(tab_selectors)
            try:
                await self.page.wait_for_selector(combined_tab_selector, timeout=6000, state="visible")
            except Exception:
                pass

            for sel in tab_selectors:
                loc = self.page.locator(sel)
                if await loc.count() > 0 and await loc.first.is_visible():
                    await loc.first.click()
                    print(f"  [OK] Switched to Application form view ({sel})")
                    try:
                        await self.page.wait_for_selector(
                            "input[type='file'], input[type='email'], input#first_name, input#firstName, input[name*='name' i]",
                            timeout=8000,
                            state="visible",
                        )
                    except Exception:
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

    async def handle_turnstile_if_present(self) -> bool:
        """
        Detects Cloudflare Turnstile iframe and clicks the challenge checkbox if visible.
        """
        try:
            cf_frames = [
                f for f in self.page.frames
                if "challenges.cloudflare.com" in f.url or "turnstile" in f.url
            ]
            for frame in cf_frames:
                checkbox = frame.locator("input[type='checkbox'], #challenge-stage input, .ctp-checkbox-label, div#cf-stage")
                if await checkbox.count() > 0 and await checkbox.first.is_visible():
                    await checkbox.first.click()
                    return True
        except Exception:
            pass
        return False

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
                if hasattr(self, "show_hud_status"):
                    await self.show_hud_status(msg, status="warning")
                print(f"  [AUDIT] {count} required field(s) pending: {', '.join(missing_fields)}")
            else:
                if hasattr(self, "show_hud_status"):
                    await self.show_hud_status("All required fields completed", status="success", auto_hide_ms=4000)
                print("  [AUDIT] All required fields (*) have been completed.")
            return missing_fields
        except Exception as e:
            print(f"  [AUDIT] Error during audit: {e}")
            return []
