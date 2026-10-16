"""
Job Hunter Command Line Interface.
"""

import sys
import os
import asyncio
import argparse
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.core.config import load_candidate_profile, CONFIG_DIR, OUTPUT_DIR
from src.core.models import ATSPlatform
from src.scanners.orchestrator import ScannerOrchestrator
from src.automation.browser import launch_stealth_browser
from src.automation.applicators.ashby_applicator import AshbyApplicator
from src.automation.applicators.greenhouse_applicator import GreenhouseApplicator
from src.automation.applicators.lever_applicator import LeverApplicator
from src.cv.builder import CVBuilder

console = Console()

def init_command():
    """Initialize local user configuration from examples."""
    console.print(Panel.fit("[bold cyan]Job Hunter[/bold cyan] - Project Initializer", border_style="cyan"))
    
    prof_dest = CONFIG_DIR / "profile.json"
    prof_src = CONFIG_DIR / "profile.example.json"
    if not prof_dest.exists() and prof_src.exists():
        import shutil
        shutil.copy(prof_src, prof_dest)
        console.print(f"[green]✓ Created config file:[/green] {prof_dest}")
    else:
        console.print(f"[yellow]i Config file already exists:[/yellow] {prof_dest}")

    excl_dest = CONFIG_DIR / "exclusions.py"
    excl_src = CONFIG_DIR / "exclusions.example.py"
    if not excl_dest.exists() and excl_src.exists():
        import shutil
        shutil.copy(excl_src, excl_dest)
        console.print(f"[green]✓ Created exclusions file:[/green] {excl_dest}")

    console.print("\n[bold green]Setup Complete![/bold green] Next steps:")
    console.print("1. Edit [cyan]config/profile.json[/cyan] with your contact info and target roles.")
    console.print("2. Run [cyan]job-hunter scan[/cyan] to discover remote openings.")

def scan_command(args):
    """Run concurrent ATS scanner."""
    profile = load_candidate_profile()
    roles = [r.strip() for r in args.roles.split(",")] if args.roles else profile.search_criteria.target_roles
    locations = [l.strip() for l in args.locations.split(",")] if args.locations else profile.search_criteria.location_keywords
    platforms = [p.strip().lower() for p in args.platforms.split(",")] if args.platforms else profile.ats_settings.enabled_platforms

    console.print(Panel.fit(
        f"[bold]Target Roles:[/bold] {', '.join(roles)}\n"
        f"[bold]Locations:[/bold] {', '.join(locations)}\n"
        f"[bold]Platforms:[/bold] {', '.join(platforms)}",
        title="🔍 ATS Scanner Active",
        border_style="blue"
    ))

    orchestrator = ScannerOrchestrator(profile)
    postings = asyncio.run(orchestrator.run(
        platforms=platforms,
        custom_roles=roles,
        custom_locations=locations,
        concurrency_limit=args.concurrency
    ))

    table = Table(title=f"Discovered Job Openings ({len(postings)} found)")
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("ATS", style="magenta")
    table.add_column("Company", style="green")
    table.add_column("Job Title", style="bold")
    table.add_column("Location", style="yellow")
    table.add_column("URL", style="blue")

    for i, p in enumerate(postings[:args.limit], 1):
        table.add_row(str(i), p.ats.value.upper(), p.company, p.title, p.location or "Remote", p.url)

    console.print(table)
    console.print(f"\n[green]✓ Results saved to:[/green] {OUTPUT_DIR / 'scan_results.json'}")

def apply_command(args):
    """Launch headed browser and pre-fill application form."""
    profile = load_candidate_profile()
    cv_path = Path(args.cv) if args.cv else None
    url = args.url

    console.print(Panel.fit(
        f"[bold]URL:[/bold] {url}\n"
        f"[bold]Candidate:[/bold] {profile.personal_info.full_name}\n"
        f"[bold]CV Attached:[/bold] {cv_path.name if cv_path else 'None'}",
        title="🚀 Headed Application Assistant",
        border_style="green"
    ))

    async def _run():
        browser, context, page = await launch_stealth_browser(headless=False)
        
        console.print(f"[cyan]Navigating to {url}...[/cyan]")
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(2)

        # Select appropriate applicator
        url_lower = url.lower()
        if "ashby" in url_lower:
            applicator = AshbyApplicator(page, profile)
        elif "greenhouse" in url_lower:
            applicator = GreenhouseApplicator(page, profile)
        elif "lever" in url_lower:
            applicator = LeverApplicator(page, profile)
        else:
            # Fallback to general form filling
            applicator = AshbyApplicator(page, profile)

        await applicator.fill_form(cv_path)

        console.print("\n[bold green]✅ All fields pre-filled![/bold green]")
        console.print("Please review the details in the opened browser, complete any employer-specific questions, and click Submit.")
        console.print("[dim]The session will close when you close the browser window.[/dim]\n")

        # Keep browser open until user closes window
        while True:
            try:
                if len(context.pages) == 0 or page.is_closed():
                    console.print("[yellow]Browser window closed by user.[/yellow]")
                    break
            except Exception:
                break
            await asyncio.sleep(1)

    asyncio.run(_run())

def build_cv_command(args):
    """Compile HTML CV into 1-page PDF."""
    builder = CVBuilder()
    html_path = Path(args.html)
    out_pdf = Path(args.out)

    console.print(f"[cyan]Compiling PDF from {html_path}...[/cyan]")
    asyncio.run(builder.compile_to_pdf(html_path, out_pdf))
    console.print(f"[bold green]✓ PDF compiled successfully:[/bold green] {out_pdf}")

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
    scan_parser.add_argument("--concurrency", type=int, default=50, help="Concurrent HTTP connections")

    # apply
    apply_parser = subparsers.add_parser("apply", help="Launch headed browser and pre-fill job application")
    apply_parser.add_argument("--url", required=True, help="Job application URL")
    apply_parser.add_argument("--cv", required=False, help="Path to tailored CV PDF")

    # build-cv
    cv_parser = subparsers.add_parser("build-cv", help="Compile tailored HTML CV to ATS PDF")
    cv_parser.add_argument("--html", required=True, help="Input HTML file path")
    cv_parser.add_argument("--out", required=True, help="Destination PDF file path")

    args = parser.parse_args()

    if args.command == "init":
        init_command()
    elif args.command == "scan":
        scan_command(args)
    elif args.command == "apply":
        apply_command(args)
    elif args.command == "build-cv":
        build_cv_command(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
