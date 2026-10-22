"""
Company Exclusion & Blacklist Configuration.

Each entry is "slug": "reason". A company is excluded when its lowercased name
contains the slug, so keep slugs specific. Managed from the web app ("Exclusiones"
page) and by the agent; one entry per line keeps both in sync.
"""

from typing import Dict, List

# Lowercased company slugs or substrings -> why they are excluded
EXCLUSION_REASONS: Dict[str, str] = {
    "bairesdev": "Agencia o plataforma que prefieres evitar",
    "revature": "Agencia o plataforma que prefieres evitar",
    "turing": "Agencia o plataforma que prefieres evitar",
}

# Plain list view of the slugs, used by the scanner
EXCLUDED_COMPANIES: List[str] = list(EXCLUSION_REASONS)

def is_excluded_company(company_name: str) -> bool:
    """Returns True if company_name matches any excluded pattern."""
    if not company_name:
        return False
    clean = company_name.lower().strip()
    return any(ex.lower().strip() in clean for ex in EXCLUDED_COMPANIES if ex.strip())
