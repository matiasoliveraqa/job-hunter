"""
Job Hunter Command Line Interface.
"""

import re
import sys
import json
import shutil
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from urllib.parse import urlparse

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.core.config import load_candidate_profile, CONFIG_DIR, OUTPUT_DIR, PROJECT_ROOT
from src.scanners.orchestrator import ScannerOrchestrator
from src.automation.browser import launch_stealth_browser
from src.automation.applicators.ashby_applicator import AshbyApplicator
from src.automation.applicators.greenhouse_applicator import GreenhouseApplicator
from src.automation.applicators.lever_applicator import LeverApplicator
from src.automation.applicators.workable_applicator import WorkableApplicator
from src.automation.applicators.breezy_applicator import BreezyApplicator
from src.automation.applicators.recruitee_applicator import RecruiteeApplicator
from src.automation.applicators.bamboohr_applicator import BambooHRApplicator
from src.cv.builder import (
    CVBuilder,
    get_or_create_application_dir,
    sanitize_slug,
    build_cv_filename,
    normalize_cv_role_title,
    APPLICATIONS_DIR,
)

# Ensure UTF-8 output across Windows (cp1252), Linux, and macOS terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()

def _infer_company_from_url(url: str) -> str:
    """Extract company name/slug from an Ashby, Greenhouse, or Lever URL."""
    try:
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if parts:
            if parts[0].lower() in ("boards", "jobs", "v1", "posting-api") and len(parts) > 1:
                return parts[1]
            return parts[0]
    except Exception:
        pass
    return "Company"

def _save_application_artifacts(
    app_dir: Path,
    url: str,
    company: str,
    role: str,
    cv_path: Optional[Path],
    filled_fields: Dict[str, str],
) -> Path:
    """
    Save both application_info.json and a standalone executable script open_application.py
    inside the company's application folder containing the application URL and all filled fields.
    Works across Windows, Linux, and macOS.
    """
    app_dir.mkdir(parents=True, exist_ok=True)
    cv_name = cv_path.name if cv_path and cv_path.exists() else ""
    cv_str = str(cv_path.resolve()) if cv_path and cv_path.exists() else ""

    info_payload = {
        "company": company,
        "role": role,
        "application_url": url,
        "tailored_cv_pdf": cv_str,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "completed_fields": filled_fields,
    }
    info_path = app_dir / "application_info.json"
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info_payload, f, indent=2, ensure_ascii=False)

    fields_repr = json.dumps(filled_fields, indent=4, ensure_ascii=False)
    script_content = f'''#!/usr/bin/env python3
"""
Auto-generated Application Execution Script (Windows / Linux / macOS)
Company: {company}
Role: {role or "Target Role"}
Application URL: {url}
"""

import sys
from pathlib import Path

# Resolve project root dynamically across Windows, Linux, and macOS
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
if not (PROJECT_ROOT / "src" / "cli.py").exists():
    PROJECT_ROOT = Path({repr(str(PROJECT_ROOT.resolve()))})

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Direct link to the job posting / application
APPLICATION_URL = {repr(url)}

# Tailored 1-Page ATS CV used for this application (resolved relative to this folder)
TAILORED_CV_PDF = str(SCRIPT_DIR / {repr(cv_name)}) if {repr(cv_name)} else ""

# Summary of fields pre-filled by Job Hunter on this application form
COMPLETED_FIELDS = {fields_repr}

if __name__ == "__main__":
    from src.cli import main
    sys.argv = [
        "job-hunter",
        "apply",
        "--url", APPLICATION_URL,
        "--company", {repr(company)},
    ]
    if TAILORED_CV_PDF and Path(TAILORED_CV_PDF).exists():
        sys.argv.extend(["--cv", TAILORED_CV_PDF])
    main()
'''
    script_path = app_dir / "open_application.py"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    return script_path

def init_command():
    """Initialize local user configuration from examples."""
    console.print(Panel.fit("[bold cyan]Job Hunter[/bold cyan] - Project Initializer", border_style="cyan"))

    prof_dest = CONFIG_DIR / "profile.json"
    prof_src = CONFIG_DIR / "profile.example.json"
    if not prof_dest.exists() and prof_src.exists():
        shutil.copy(prof_src, prof_dest)
        console.print(f"[green][CREATED][/green] Config file: {prof_dest}")
    else:
        console.print(f"[yellow][INFO][/yellow] Config file already exists: {prof_dest}")

    excl_dest = CONFIG_DIR / "exclusions.py"
    excl_src = CONFIG_DIR / "exclusions.example.py"
    if not excl_dest.exists() and excl_src.exists():
        shutil.copy(excl_src, excl_dest)
        console.print(f"[green][CREATED][/green] Exclusions file (empty by default): {excl_dest}")

    console.print("\n[bold green]Setup Complete.[/bold green] Next steps:")
    console.print("1. Edit [cyan]config/profile.json[/cyan] with your contact info, years of experience, and target roles.")
    console.print("2. Run [cyan]python -m src.cli scan[/cyan] to discover remote openings.")

def scan_command(args):
    """Run concurrent ATS scanner."""
    profile = load_candidate_profile()
    roles = [r.strip() for r in args.roles.split(",")] if args.roles else profile.search_criteria.target_roles
    locations = [l.strip() for l in args.locations.split(",")] if args.locations else profile.search_criteria.location_keywords
    platforms = [p.strip().lower() for p in args.platforms.split(",")] if args.platforms else profile.ats_settings.enabled_platforms
    max_years = None if args.max_years == 0 else (args.max_years if args.max_years is not None else profile.effective_max_years)
    geo_scope = getattr(args, "geo_scope", None)
    countries = [c.strip() for c in args.countries.split(",")] if getattr(args, "countries", None) else None
    work_modes = [w.strip().lower() for w in args.work_modes.split(",")] if getattr(args, "work_modes", None) else None

    if getattr(args, "stream_json", False):
        def on_match(posting):
            sys.stdout.write(json.dumps({"type": "match", "posting": posting.model_dump()}, ensure_ascii=False) + "\n")
            sys.stdout.flush()

        def on_progress(checked, total, platform, company):
            if checked % 25 == 0 or checked == total:
                sys.stdout.write(
                    json.dumps(
                        {"type": "progress", "checked": checked, "total": total, "platform": platform, "company": company},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                sys.stdout.flush()

        def on_error(platform, company, error):
            sys.stdout.write(
                json.dumps({"type": "board_error", "platform": platform, "company": company, "error": str(error)}, ensure_ascii=False)
                + "\n"
            )
            sys.stdout.flush()

        allow_captcha = getattr(args, "allow_captcha", False)
        orchestrator = ScannerOrchestrator(profile)
        postings = asyncio.run(
            orchestrator.run(
                platforms=platforms,
                custom_roles=roles,
                custom_locations=locations,
                concurrency_limit=args.concurrency,
                max_years_experience=max_years,
                allow_captcha=allow_captcha,
                geo_scope=geo_scope,
                custom_countries=countries,
                work_modes=work_modes,
                on_match=on_match,
                on_progress=on_progress,
                on_error=on_error,
            )
        )
        sys.stdout.write(json.dumps({"type": "done", "total_matches": len(postings)}, ensure_ascii=False) + "\n")
        sys.stdout.flush()
        return

    exp_str = f"<= {max_years} years" if max_years is not None else "Any"
    console.print(Panel.fit(
        f"[bold]Target Roles:[/bold] {', '.join(roles)}\n"
        f"[bold]Locations:[/bold] {', '.join(locations)}\n"
        f"[bold]Experience Filter:[/bold] {exp_str}\n"
        f"[bold]Platforms:[/bold] {', '.join(platforms)}",
        title="ATS Scanner Active",
        border_style="blue"
    ))

    allow_captcha = getattr(args, "allow_captcha", False)
    orchestrator = ScannerOrchestrator(profile)
    postings = asyncio.run(orchestrator.run(
        platforms=platforms,
        custom_roles=roles,
        custom_locations=locations,
        concurrency_limit=args.concurrency,
        max_years_experience=max_years,
        allow_captcha=allow_captcha,
        geo_scope=geo_scope,
        custom_countries=countries,
        work_modes=work_modes,
    ))

    table = Table(title=f"Discovered Job Openings ({len(postings)} found)")
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("ATS", style="magenta")
    table.add_column("Company", style="green")
    table.add_column("Job Title", style="bold")
    table.add_column("Exp", justify="center", style="cyan")
    table.add_column("Location", style="yellow")
    table.add_column("Mode", justify="center", style="green")
    table.add_column("URL", style="blue")

    for i, p in enumerate(postings[:args.limit], 1):
        exp_col = f"{p.required_years}+ yrs" if p.required_years else "-"
        mode_col = (p.work_mode or "remote").capitalize()
        table.add_row(str(i), p.ats.value.upper(), p.company, p.title, exp_col, p.location or "Remote", mode_col, p.url)

    console.print(table)
    console.print(f"\n[green][SAVED][/green] Results written to: {OUTPUT_DIR / 'scan_results.json'}")

def apply_command(args):
    """Launch headed browser, pre-fill application form, and save per-company folder & script."""
    profile = load_candidate_profile()
    url = args.url
    company = args.company or _infer_company_from_url(url)
    role = args.role or ""

    # Organize inside output/applications/<YYYY-MM>_<Company>_<Role>/
    cv_path = Path(args.cv) if args.cv else None
    if cv_path and cv_path.exists():
        # If the CV is not already inside a dedicated subfolder under output/applications,
        # create a dedicated folder for this company and copy the tailored CV into it.
        try:
            is_in_app_subdir = (
                APPLICATIONS_DIR.resolve() in cv_path.resolve().parents
                and cv_path.resolve().parent != APPLICATIONS_DIR.resolve()
            )
        except Exception:
            is_in_app_subdir = False

        if is_in_app_subdir:
            app_dir = cv_path.resolve().parent
        else:
            app_dir = get_or_create_application_dir(company, role)
            dest_cv = app_dir / build_cv_filename(profile.personal_info.full_name, role, company)
            if cv_path.resolve() != dest_cv.resolve():
                shutil.copy2(cv_path, dest_cv)
                # Also copy HTML if it exists alongside the source PDF
                src_html = cv_path.with_suffix(".html")
                if src_html.exists():
                    shutil.copy2(src_html, app_dir / "cv_tailored.html")
                cv_path = dest_cv
    else:
        app_dir = get_or_create_application_dir(company, role)
        existing_pdfs = [f for f in app_dir.glob("*.pdf") if f.is_file() and f.stat().st_size > 1000]
        if existing_pdfs:
            cv_path = existing_pdfs[0]
        else:
            # Fallback to master base CV from my_cv/ if no tailored CV was compiled
            my_cv_dir = PROJECT_ROOT / "my_cv"
            base_pdfs = [f for f in my_cv_dir.glob("*.pdf") if f.is_file() and f.stat().st_size > 1000 and not f.name.startswith("skills_inventory")]
            if base_pdfs:
                dest_cv = app_dir / build_cv_filename(profile.personal_info.full_name, role, company)
                shutil.copy2(base_pdfs[0], dest_cv)
                cv_path = dest_cv

    console.print(Panel.fit(
        f"[bold]Company:[/bold] {company}\n"
        f"[bold]URL:[/bold] {url}\n"
        f"[bold]Candidate:[/bold] {profile.personal_info.full_name}\n"
        f"[bold]Application Folder:[/bold] {app_dir}\n"
        f"[bold]CV Attached:[/bold] {cv_path.name if cv_path and cv_path.exists() else 'None'}",
        title="Headed Application Assistant",
        border_style="green"
    ))

    async def _run():
        browser, context, page = await launch_stealth_browser(headless=False)

        try:
            console.print(f"[cyan]Navigating to {url}...[/cyan]")
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # Select appropriate applicator
            url_lower = url.lower()
            if "ashby" in url_lower:
                applicator = AshbyApplicator(page, profile, company=company, role=role)
            elif "greenhouse" in url_lower or "gh_jid" in url_lower:
                applicator = GreenhouseApplicator(page, profile, company=company, role=role)
            elif "lever" in url_lower:
                applicator = LeverApplicator(page, profile, company=company, role=role)
            elif "workable" in url_lower:
                applicator = WorkableApplicator(page, profile, company=company, role=role)
            elif "breezy" in url_lower:
                applicator = BreezyApplicator(page, profile, company=company, role=role)
            elif "recruitee" in url_lower:
                applicator = RecruiteeApplicator(page, profile, company=company, role=role)
            elif "bamboohr" in url_lower:
                applicator = BambooHRApplicator(page, profile, company=company, role=role)
            else:
                applicator = GreenhouseApplicator(page, profile, company=company, role=role)

            await applicator.fill_form(cv_path)

            # Audit and highlight any required fields (* or required attribute)
            missing_required = await applicator.audit_and_highlight_required_fields()
            if missing_required:
                console.print(f"[yellow][REQUIRED][/yellow] Detected {len(missing_required)} missing required field(s) highlighted in yellow in the browser.")
            else:
                console.print("[green][OK][/green] All required fields (*) have been completed.")

            detected_captcha = await applicator.detect_captcha()
            if detected_captcha:
                console.print(f"[yellow][CAPTCHA][/yellow] Form protected by [bold]{detected_captcha}[/bold]. Stealth evasion mode active.")
                if "Turnstile" in detected_captcha:
                    handled = await applicator.handle_turnstile_if_present()
                    if handled:
                        console.print("[green][CAPTCHA][/green] Turnstile challenge interaction completed.")

            # Save execution script and metadata with URL + completed fields inside the company folder
            target_url = page.url if page.url and not any(p in page.url for p in ["proxy.html", "about:blank", "googleapis.com"]) else url
            script_path = _save_application_artifacts(
                app_dir=app_dir,
                url=target_url,
                company=company,
                role=role,
                cv_path=cv_path,
                filled_fields=applicator.filled_fields,
            )

            console.print("\n[bold green][SUCCESS] All fields pre-filled.[/bold green]")
            console.print(f"[green][SAVED][/green] Application script & field log saved to: [cyan]{script_path}[/cyan]")
            console.print("Please review the details in the opened browser, complete any employer-specific questions, and click Submit.")
        except Exception as e:
            console.print(f"[yellow][WARNING][/yellow] Error during auto-fill: {e}")
            console.print("The browser will remain open so you can review or complete fields manually.")

        console.print("[dim]The session will close when you close the browser window.[/dim]\n")

        # Keep browser open until user closes all browser pages/windows
        while True:
            try:
                active_pages = [p for p in context.pages if not p.is_closed()]
                if not active_pages:
                    console.print("[yellow]Browser window closed by user.[/yellow]")
                    break
            except Exception:
                break
            await asyncio.sleep(1)

    asyncio.run(_run())

def build_cv_command(args):
    """Compile HTML CV into 1-page PDF inside a dedicated company folder if specified."""
    builder = CVBuilder()
    html_path = Path(args.html)
    profile = load_candidate_profile()

    if args.company:
        app_dir = get_or_create_application_dir(args.company, args.role or "")
        default_name = build_cv_filename(profile.personal_info.full_name, args.role or "", args.company)
        out_pdf = Path(args.out) if args.out else app_dir / default_name
        # Copy HTML into the application folder if it isn't already there
        target_html = app_dir / "cv_tailored.html"
        if html_path.exists() and html_path.resolve() != target_html.resolve():
            shutil.copy2(html_path, target_html)
            html_path = target_html
    else:
        out_pdf = Path(args.out) if args.out else html_path.with_suffix(".pdf")

    console.print(f"[cyan]Compiling PDF from {html_path}...[/cyan]")
    asyncio.run(builder.compile_to_pdf(html_path, out_pdf))
    console.print(f"[bold green][SUCCESS][/bold green] PDF compiled successfully: {out_pdf}")
    print(f"[CV_PATH] {out_pdf.resolve()}")

def main():
    parser = argparse.ArgumentParser(
        prog="job-hunter",
        description="Autonomous, human-in-the-loop job search & application assistant."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init
    subparsers.add_parser("init", help="Initialize configuration files")

    # scan
    scan_parser = subparsers.add_parser("scan", help="Scan ATS platforms for openings")
    scan_parser.add_argument("--roles", help="Comma-separated target role keywords")
    scan_parser.add_argument("--locations", help="Comma-separated location filters")
    scan_parser.add_argument("--platforms", help="Comma-separated platforms: ashby,greenhouse,lever")
    scan_parser.add_argument("--limit", type=int, default=30, help="Display limit")
    scan_parser.add_argument("--concurrency", type=int, default=200, help="Concurrent HTTP connections")
    scan_parser.add_argument("--max-years", type=int, default=None, help="Maximum required years of experience (0 = no limit)")
    scan_parser.add_argument("--allow-captcha", action="store_true", default=False, help="Include vacancies that require captcha solving")
    scan_parser.add_argument("--geo-scope", choices=["latam", "latam_na", "global"], default=None, help="Geographical scope (latam, latam_na, global)")
    scan_parser.add_argument("--countries", help="Comma-separated custom countries list")
    scan_parser.add_argument("--work-modes", help="Comma-separated work modes: remote,hybrid,onsite")
    scan_parser.add_argument("--stream-json", action="store_true", help="Stream progress and matches as JSON lines")

    # apply
    apply_parser = subparsers.add_parser("apply", help="Launch headed browser and pre-fill job application")
    apply_parser.add_argument("--url", required=True, help="Job application URL")
    apply_parser.add_argument("--cv", required=False, help="Path to tailored CV PDF")
    apply_parser.add_argument("--company", required=False, help="Company name for application folder")
    apply_parser.add_argument("--role", required=False, help="Job role title for application folder")

    # build-cv
    cv_parser = subparsers.add_parser("build-cv", help="Compile tailored HTML CV to ATS PDF")
    cv_parser.add_argument("--html", required=True, help="Input HTML file path")
    cv_parser.add_argument("--out", required=False, help="Destination PDF file path")
    cv_parser.add_argument("--company", required=False, help="Company name to create dedicated application folder")
    cv_parser.add_argument("--role", required=False, help="Role title for dedicated application folder")

    # update
    subparsers.add_parser("update", help="Check and apply updates from remote git repository")

    args = parser.parse_args()

    if args.command == "init":
        init_command()
    elif args.command == "scan":
        scan_command(args)
    elif args.command == "apply":
        apply_command(args)
    elif args.command == "build-cv":
        build_cv_command(args)
    elif args.command == "update":
        from src.updater import check_and_apply_updates
        check_and_apply_updates()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
