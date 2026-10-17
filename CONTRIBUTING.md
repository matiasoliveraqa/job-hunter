# Contributing to Job Hunter

Thank you for your interest in contributing to **Job Hunter**! We welcome community contributions to expand ATS coverage, improve anti-detection heuristics, and enhance CV rendering.

## How to Contribute

### 1. Adding a New ATS Platform Scanner
1. Create a new scanner in `src/scanners/<platform_name>.py` inheriting from `BaseScanner`.
2. Implement the `scan_company` method using async HTTP (`aiohttp`).
3. Add the company slug dataset into `data/companies/<platform_name>.json`.
4. Register the new scanner in `src/scanners/orchestrator.py`.

### 2. Adding a New ATS Form Applicator
1. Create an applicator in `src/automation/applicators/<platform_name>_applicator.py` inheriting from `BaseApplicator`.
2. Map the standard fields (Name, Email, Phone, Location, URLs, Resume upload).
3. Connect the new applicator in `src/cli.py` (`apply_command`).

### 3. Improving CV Templates
- Ensure any added templates strictly conform to the **1-Page Letter ATS Rule**.
- Avoid multi-column table layouts that confuse parsing software.

## Testing

Run pytest before submitting PRs:
```bash
pytest tests/
```

## Commit Convention
Follow conventional commits:
- `feat: add SmartRecruiters scanner`
- `fix: improve stealth args for Lever`
- `docs: update quickstart in README`
