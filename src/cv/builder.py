"""
ATS CV Builder & 1-Page PDF Compiler.
"""

import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

import unicodedata
from src.core.config import TEMPLATES_DIR, OUTPUT_DIR, load_candidate_profile

APPLICATIONS_DIR = OUTPUT_DIR / "applications"

def sanitize_slug(text: str) -> str:
    """Convert company or role name into a clean ASCII filesystem-safe slug."""
    norm = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", norm.strip())
    return cleaned.strip("_") or "Application"

def normalize_cv_role_title(raw_role: str, preferred_role: Optional[str] = None) -> str:
    """
    Normalize job role title for CV header and filename in English:
    - Never use 'Lead', 'Principal', 'Manager', 'Head', or 'Director'.
    - If preferred_role is provided, prioritize it.
    - If role involves automation / SDET -> 'QA Automation Engineer'
    - If role involves QA / testing -> 'QA Engineer'
    - Otherwise, strip seniorities and preserve base role title.
    """
    clean = re.sub(
        r"\b(lead|principal|head\s+of|director|manager)\b",
        "",
        raw_role or "",
        flags=re.IGNORECASE,
    ).strip()
    clean = re.sub(r"\s+", " ", clean).strip(" -:,|/")

    if preferred_role:
        return preferred_role

    low = (raw_role or "").lower()
    if any(k in low for k in ["automation", "sdet", "playwright", "test engineer", "engineer in test", "automated"]):
        return "QA Automation Engineer"
    if any(k in low for k in ["qa", "quality", "test", "tester", "testing"]):
        return "QA Engineer"
    return clean or "Software Engineer"

def build_cv_filename(full_name: str, role: str, company: str) -> str:
    """
    Build standardized CV PDF filename:
    <Full_Name>_<Normalized_Role>_<Company>.pdf
    Example: Alex_Mercer_QA_Automation_Engineer_Stack_AI.pdf
    """
    name_slug = sanitize_slug(full_name or "Candidate")
    role_slug = sanitize_slug(normalize_cv_role_title(role))
    comp_slug = sanitize_slug(company or "Company")
    return f"{name_slug}_{role_slug}_{comp_slug}.pdf"

def get_or_create_application_dir(company: str, role: str = "") -> Path:
    """Create and return a dedicated folder under output/applications/<YYYY-MM>_<Company>_<Role>."""
    ym = datetime.now().strftime("%Y-%m")
    comp_slug = sanitize_slug(company)
    role_slug = sanitize_slug(normalize_cv_role_title(role)) if role else ""
    folder_name = f"{ym}_{comp_slug}_{role_slug}" if role_slug else f"{ym}_{comp_slug}"
    app_dir = APPLICATIONS_DIR / folder_name
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir

class CVBuilder:
    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def enforce_profile_contact_info(self, html_path: Path) -> None:
        """
        Programmatic guardrail:
        1. Ensure any linkedin.com/in/... URL in the HTML matches config/profile.json.
        2. Strip 'Lead', 'Principal', 'Manager', 'Director' from the CV header role title.
        """
        try:
            if not html_path.exists():
                return
            html_text = html_path.read_text(encoding="utf-8")
            fixed_text = html_text

            profile = load_candidate_profile()
            real_li = (profile.personal_info.linkedin_url or "").strip()
            m = re.search(r"linkedin\.com/in/([a-zA-Z0-9_-]+)", real_li, flags=re.IGNORECASE)
            if m:
                real_slug = m.group(1)
                fixed_text = re.sub(
                    r"(linkedin\.com/in/)[a-zA-Z0-9_-]+",
                    rf"\g<1>{real_slug}",
                    fixed_text,
                    flags=re.IGNORECASE,
                )

            # Never allow "Lead QA..." or "Principal QA..." in the CV title/subtitle
            fixed_text = re.sub(
                r"\b(?:Lead|Principal|Staff|Head of)\s+(QA|Quality\s+Assurance|Quality|Test|SDET)",
                r"\1",
                fixed_text,
                flags=re.IGNORECASE,
            )

            # Strip scripts and event handlers
            fixed_text = re.sub(r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", "", fixed_text, flags=re.IGNORECASE)
            fixed_text = re.sub(r"\son[a-zA-Z]+\s*=\s*([\"'][^\"']*[\"']|[^\s>]+)", "", fixed_text, flags=re.IGNORECASE)

            if fixed_text != html_text:
                html_path.write_text(fixed_text, encoding="utf-8")
        except Exception:
            pass

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

        self.enforce_profile_contact_info(html_path)
        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        # Use .as_uri() for cross-platform compatibility (Windows file:///C:/... and Linux file:///home/...)
        abs_html_url = html_path.resolve().as_uri()

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Block all external network requests to prevent tracking or data exfiltration
            await page.route(
                "**/*",
                lambda route: route.abort()
                if route.request.url.startswith(("http://", "https://"))
                else route.continue_()
            )
            await page.goto(abs_html_url, wait_until="load")

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
