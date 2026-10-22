"""
Company Exclusion & Blacklist Configuration.
Add names or slugs of companies, agencies, or recruiters you want to ignore.
"""

from typing import List

# List of lowercased company slugs or substrings to exclude.
# Starts empty by default so each user can add their own exclusions.
EXCLUDED_COMPANIES: List[str] = [
    # Examples (uncomment or add your own):
    # "your-current-employer",
    # "already-applied-company",
]

def is_excluded_company(company_name: str) -> bool:
    """Returns True if company_name matches any excluded pattern."""
    if not company_name:
        return False
    clean = company_name.lower().strip()
    return any(ex.lower().strip() in clean for ex in EXCLUDED_COMPANIES if ex.strip())
