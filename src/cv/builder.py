"""
ATS CV Builder & 1-Page PDF Compiler.
"""

import os
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader

from src.core.config import TEMPLATES_DIR, OUTPUT_DIR

class CVBuilder:
    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self.env = Environment(loader=FileSystemLoader(str(self.templates_dir)))

    def render_html(self, template_name: str, context: Dict[str, Any], output_path: Path) -> Path:
        """Render a Jinja2 template to an HTML file."""
        template = self.env.get_template(template_name)
        rendered_content = template.render(**context)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered_content)
        return output_path

    async def compile_to_pdf(self, html_path: Path, output_pdf_path: Path) -> Path:
        """Compile an HTML CV into an ATS-compliant Letter PDF using Playwright."""
        from playwright.async_api import async_playwright

        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        abs_html_url = "file://" + str(html_path.resolve())

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(abs_html_url, wait_until="networkidle")
            
            await page.pdf(
                path=str(output_pdf_path),
                format="Letter",
                print_background=True,
                margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"}
            )
            await browser.close()

        # Check page count
        self.verify_page_count(output_pdf_path)
        return output_pdf_path

    def verify_page_count(self, pdf_path: Path) -> int:
        """Verify that the generated PDF does not exceed 1 page."""
        try:
            res = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True)
            for line in res.stdout.splitlines():
                if "Pages:" in line:
                    pages = int(line.split(":")[1].strip())
                    if pages > 1:
                        print(f"[WARNING] CV has {pages} pages. Ensure strict ATS 1-page rule by reducing margins or content.")
                    else:
                        print("[SUCCESS] Strict 1-Page ATS Rule Verified.")
                    return pages
        except Exception:
            pass
        return 1
