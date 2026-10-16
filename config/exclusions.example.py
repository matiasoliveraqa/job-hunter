"""
Company Exclusion & Blacklist Configuration.
Add names or slugs of companies, agencies, or recruiters you want to ignore.
"""

from typing import List

# List of lowercased company slugs or substrings to exclude
EXCLUDED_COMPANIES: List[str] = [
    # Agencies or platforms you wish to avoid
    "bairesdev",
    "revature",
    "turing",
    
    # Companies where you have already applied
    # "example-corp",
]

def is_excluded_company(company_name: str) -> bool:
    """Returns True if company_name matches any excluded pattern."""
    if not company_name:
        return False
    clean = company_name.lower().strip()
    return any(ex in clean for ex in EXCLUDED_COMPANIES)
