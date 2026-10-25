"""
Company Exclusion & Blacklist Configuration.

Each entry is "slug": "reason". A company is excluded when its lowercased name
contains the slug, so keep slugs specific. Managed from the web app ("Exclusiones"
page) and by the agent; one entry per line keeps both in sync.
"""

from typing import Dict, List

# Lowercased company slugs or substrings -> why they are excluded.
# Starts empty by default so each user can manage their own exclusions.
EXCLUSION_REASONS: Dict[str, str] = {
    # Examples (uncomment or manage from the Web App / AI Agent):
    # "your-current-employer": "Current employer",
    # "already-applied-corp": "Already applied",
}

# Plain list view of the slugs, used by the scanner
EXCLUDED_COMPANIES: List[str] = list(EXCLUSION_REASONS)

def is_excluded_company(company_name: str) -> bool:
    """Returns True if company_name matches any excluded pattern."""
    if not company_name:
        return False
    clean = company_name.lower().strip()
    return any(ex.lower().strip() in clean for ex in EXCLUDED_COMPANIES if ex.strip())
