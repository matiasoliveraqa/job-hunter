"""
Configuration and environment paths manager.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Callable
from src.core.models import CandidateProfile

# Root directory of job-hunter project
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data" / "companies"
TEMPLATES_DIR = PROJECT_ROOT / "src" / "cv" / "templates"
OUTPUT_DIR = PROJECT_ROOT / "output"

def get_profile_path() -> Path:
    """Return active profile.json if exists, else fallback to example."""
    active_path = CONFIG_DIR / "profile.json"
    if active_path.exists():
        return active_path
    return CONFIG_DIR / "profile.example.json"

def load_candidate_profile() -> CandidateProfile:
    """Load and validate the candidate profile."""
    path = get_profile_path()
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return CandidateProfile.model_validate(data)

def get_exclusion_checker() -> Callable[[str], bool]:
    """Dynamically load exclusion checking function."""
    sys.path.insert(0, str(CONFIG_DIR))
    try:
        from exclusions import is_excluded_company  # type: ignore
        return is_excluded_company
    except ImportError:
        try:
            from exclusions_example import is_excluded_company  # type: ignore
            return is_excluded_company
        except ImportError:
            return lambda name: False
