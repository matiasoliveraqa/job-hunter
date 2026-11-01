"""
Resume and document upload mixin for application forms.
"""

import asyncio
from pathlib import Path
from typing import Optional


class FileUploaderMixin:
    """Methods for uploading candidate CV/Resume and documents safely."""

    async def safe_upload_resume(self, file_path: Path) -> bool:
        """
        Safely upload candidate's CV/Resume PDF to the application form.
        Strictly targets inputs designated for Resume/CV and excludes Cover Letter inputs.
        """
        if not file_path or not file_path.exists():
            return False

        try:
            # 1. First check explicit selectors that strictly specify Resume/CV
            explicit_selectors = [
                "[data-ui*='resume' i] input[type='file']",
                "div[data-ui='file-upload'] input[type='file']",
                "div:has(> label:has-text('Resume')) input[type='file']",
                "div:has(label:has-text('Resume')) input[type='file']",
                "section:has-text('Resume') input[type='file']",
                "div[data-fabric-component='Flex']:has-text('Resume') input[type='file']",
                "div:has(> p:has-text('Resume')) input[type='file']",
                "input[type='file'][name*='resume' i]",
                "input[type='file'][id*='resume' i]",
                "input[type='file'][data-qa*='resume' i]",
                "input[type='file'][aria-label*='resume' i]",
                "input[type='file'][name*='cv' i]",
                "input[type='file'][id*='cv' i]",
                "input[type='file'][aria-label*='cv' i]",
                "input[type='file']#resume-upload-input",
                "input[type='file']#resume",
                "[data-testid*='resume' i] input[type='file']",
            ]
            for sel in explicit_selectors:
                loc = self.page.locator(sel)
                if await loc.count() > 0:
                    await loc.first.set_input_files(str(file_path.resolve()))
                    self.filled_fields["CV PDF"] = str(file_path.resolve())
                    print(f"  [OK] Uploaded Resume via explicit selector ({sel}): {file_path.name}")
                    await asyncio.sleep(1.5)
                    return True

            # 2. Inspect all file inputs on the page to identify Resume and reject Cover Letter
            file_inputs = await self.page.locator("input[type='file']").all()
            if not file_inputs:
                return False

            if len(file_inputs) == 1:
                is_strict_cover = await file_inputs[0].evaluate(r'''el => {
                    const attrs = `${el.name || ''} ${el.id || ''} ${el.getAttribute('aria-label') || ''} ${el.getAttribute('data-ui') || ''}`.toLowerCase();
                    let curr = el;
                    let depth = 0;
                    let localText = '';
                    while (curr && curr !== document.body && depth < 3) {
                        const tag = (curr.tagName || '').toLowerCase();
                        if (tag === 'form' || tag === 'main' || tag === 'body') break;
                        localText += ' ' + (curr.innerText || '').toLowerCase();
                        curr = curr.parentElement;
                        depth++;
                    }
                    const combined = (attrs + ' ' + localText).toLowerCase();
                    const hasCover = /cover[\s_-]?letter|carta de presentaci/i.test(combined);
                    const hasResume = /resume|curriculum|cv\b|hoja de vida/i.test(combined);
                    return hasCover && !hasResume;
                }''')
                if not is_strict_cover:
                    await file_inputs[0].set_input_files(str(file_path.resolve()))
                    self.filled_fields["CV PDF"] = str(file_path.resolve())
                    print(f"  [OK] Uploaded Resume to single file input: {file_path.name}")
                    await asyncio.sleep(1.5)
                    return True

            # Multiple file inputs: score each input based on immediate field context
            scored_inputs = []
            for inp in file_inputs:
                score = await inp.evaluate(r'''el => {
                    const attrs = `${el.name || ''} ${el.id || ''} ${el.getAttribute('aria-label') || ''} ${el.getAttribute('data-ui') || ''} ${el.getAttribute('data-qa') || ''}`.toLowerCase();
                    let curr = el;
                    let depth = 0;
                    let localText = '';
                    while (curr && curr !== document.body && depth < 3) {
                        const tag = (curr.tagName || '').toLowerCase();
                        if (tag === 'form' || tag === 'main' || tag === 'body') break;
                        localText += ' ' + (curr.innerText || '').toLowerCase();
                        curr = curr.parentElement;
                        depth++;
                    }
                    const combined = (attrs + ' ' + localText).toLowerCase();
                    const hasResume = /resume|curriculum|cv\b|hoja de vida/i.test(combined);
                    const hasCover = /cover[\s_-]?letter|carta de presentaci/i.test(combined);

                    if (hasResume && !hasCover) return 50;
                    if (hasCover && !hasResume) return -100;
                    if (hasResume && hasCover) {
                        if (/resume|curriculum|cv/i.test(attrs)) return 30;
                        if (/cover/i.test(attrs)) return -50;
                        return 10;
                    }
                    return 0;
                }''')
                scored_inputs.append((score, inp))

            scored_inputs.sort(key=lambda x: x[0], reverse=True)
            if scored_inputs and scored_inputs[0][0] > 0:
                best_input = scored_inputs[0][1]
                await best_input.set_input_files(str(file_path.resolve()))
                self.filled_fields["CV PDF"] = str(file_path.resolve())
                print(f"  [OK] Uploaded Resume to contextual Resume input: {file_path.name}")
                await asyncio.sleep(1.5)
                return True

            for score, inp in scored_inputs:
                if score >= 0:
                    await inp.set_input_files(str(file_path.resolve()))
                    self.filled_fields["CV PDF"] = str(file_path.resolve())
                    print(f"  [OK] Uploaded Resume to non-cover file input: {file_path.name}")
                    await asyncio.sleep(1.5)
                    return True

        except Exception as e:
            print(f"  [!] Failed to upload Resume: {e}")

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
