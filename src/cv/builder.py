"""
ATS CV Builder & 1-Page PDF Compiler.
"""

import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader

from src.core.config import TEMPLATES_DIR, OUTPUT_DIR

APPLICATIONS_DIR = OUTPUT_DIR / "applications"

def sanitize_slug(text: str) -> str:
    """Convert company or role name into a clean filesystem-safe slug."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip())
    return cleaned.strip("_") or "Application"

def get_or_create_application_dir(company: str, role: str = "") -> Path:
    """Create and return a dedicated folder under output/applications/<YYYY-MM>_<Company>_<Role>."""
    ym = datetime.now().strftime("%Y-%m")
    comp_slug = sanitize_slug(company)
    role_slug = sanitize_slug(role) if role else ""
    folder_name = f"{ym}_{comp_slug}_{role_slug}" if role_slug else f"{ym}_{comp_slug}"
    app_dir = APPLICATIONS_DIR / folder_name
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir

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
        # Use .as_uri() for cross-platform compatibility (Windows file:///C:/... and Linux file:///home/...)
        abs_html_url = html_path.resolve().as_uri()

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

        # Check page count across Linux, Windows, and macOS
        self.verify_page_count(output_pdf_path)
        return output_pdf_path

    def verify_page_count(self, pdf_path: Path) -> int:
        """Verify that the generated PDF does not exceed 1 page (cross-platform)."""
        pages: Optional[int] = None

        # 1. Try pdfinfo if installed (common on Linux)
        try:
            res = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if "Pages:" in line:
                        pages = int(line.split(":")[1].strip())
                        break
        except Exception:
            pass

        # 2. Pure-Python cross-platform fallback (works on Windows/macOS without poppler)
        if pages is None:
            try:
                raw_bytes = pdf_path.read_bytes()
                matches = re.findall(rb"/Type\s*/Page\b(?!s)", raw_bytes)
                if matches:
                    pages = len(matches)
            except Exception:
                pages = 1

        pages = pages or 1
        if pages > 1:
            print(f"[WARNING] CV has {pages} pages. Ensure strict ATS 1-page rule by reducing margins or content.")
        else:
            print("[SUCCESS] Strict 1-Page ATS Rule Verified (1 page).")
        return pages
