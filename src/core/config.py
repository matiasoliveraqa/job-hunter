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
    """Return active profile.json if exists, else fallback to example.

    JOBHUNTER_PROFILE overrides the location (used by the web app's demo mode
    so demos never load the real candidate profile).
    """
    override = os.environ.get("JOBHUNTER_PROFILE")
    if override and Path(override).exists():
        return Path(override)
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
    """Dynamically load exclusion checking function (prefers exclusions.json, falls back to .py)."""
    json_path = CONFIG_DIR / "exclusions.json"
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                excluded_keys = []
                if isinstance(data, dict):
                    excluded_keys = [k.lower().strip() for k in data.keys()]
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "company" in item:
                            excluded_keys.append(str(item["company"]).lower().strip())
                        elif isinstance(item, str):
                            excluded_keys.append(item.lower().strip())
                if excluded_keys:
                    return lambda name: bool(name and any(ex in name.lower() for ex in excluded_keys))
        except Exception:
            pass

    import importlib.util

    for filename in ["exclusions.py", "exclusions.example.py"]:
        file_path = CONFIG_DIR / filename
        if file_path.exists():
            try:
                spec = importlib.util.spec_from_file_location("exclusions_module", str(file_path))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "is_excluded_company"):
                        return mod.is_excluded_company
            except Exception:
                pass

    return lambda name: False
