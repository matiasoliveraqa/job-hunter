"""
Custom questions, dropdowns, radio groups, and comboboxes mixin.
"""

import re
import asyncio
from typing import Optional, List


class CustomQuestionsMixin:
    """Methods for filling employer custom questions, comboboxes, selects, and radio groups."""

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

    async def fill_custom_questions(self, salary_str: str = "", salary_num: Optional[int] = None) -> None:
        """Inspect visible empty textareas, text inputs, selects, radio groups, and comboboxes."""
        try:
            # 1. Textareas, text inputs, and number inputs
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

                # Number inputs
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

                # B. Deterministic whitelist field (never call LLM)
                is_det_only = self.is_deterministic_field(q_text, field_meta=meta)

                # C. Open-ended employer questions via agent
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

                # D. Fallback to static templates if LLM is unavailable
                if not answer and not is_det_only:
                    answer = self._generate_open_question_answer(q_text, salary_str=salary_str, salary_num=salary_num, is_required=is_required)

                # E. Strict mandatory fallback if required and still empty
                if not answer and is_required and not is_det_only:
                    answer = self._generate_required_fallback(q_text)

                if answer:
                    await el.fill(answer)
                    await self.show_hud_status(f"Completado: '{short_q}'", status="success", auto_hide_ms=2500)
                    self.filled_fields[f"Question ({short_q})"] = answer
                    print(f"  [OK] Answered '{short_q}'{' (*)' if is_required else ''}")

            # 2. Standard HTML <select> dropdowns
            await self._fill_standard_selects()

            # 3. Radio button groups
            await self._fill_radio_groups()

            # 4. Consent and privacy checkboxes
            await self._fill_consent_checkboxes()

            # 5. React-Select / ARIA combobox dropdowns
            combos = self.page.locator("input[role='combobox'], input.select__input")
            c_count = await combos.count()
            for i in range(c_count):
                cb = combos.nth(i)
                if not await cb.is_visible():
                    continue

                meta = await cb.evaluate(
                    """(node) => {
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
                        description="Location (City)",
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
                            description="School",
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

                # 1. Deterministic check: Numeric years of experience ranges
                candidate_years = getattr(self.p_info, "years_of_experience", None)
                if candidate_years is not None and re.search(r"\b(years?\s+of\s+experience|years?\s+in\s+|años\s+de\s+experiencia)\b", q_text, re.IGNORECASE):
                    matched_exp = self.match_experience_range(candidate_years, option_labels)
                    if matched_exp:
                        picked_label = matched_exp

                # 2. Deterministic check: Standard compliance and profile dropdown/radio choices
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

                # 3. AI / LLM selection for open-ended custom radio questions
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

                # 4. Apply check on matching radio element
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
