# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.1] - 2026-10-27

### Added
- Bidirectional role acronym expansions (`QA`, `QC`, `QE`, `QIA`, `SDET`) in `BaseScanner.matches_keywords` mapping abbreviations to expanded role titles and vice versa.
- Tokenized single-word matching with boundary checks to prevent false negatives caused by rigid multi-word matching.
- Preset search chips updated in `QA / SDET` and `Todos` with flexible tags: `QA`, `SDET`, `QA Automation`, `Test Engineer`, `Automation Engineer`, `QA Analyst`, `Quality Engineer`, `QE`, `QC`, `QIA`, `Software Tester`.
- Match score relevance boost in `scanController.js` for `QE`, `QC`, `QIA`, and `Test` roles.

### Fixed
- BambooHR `atsLocation` parser to read `city`, `state`, `province`, and `country` alongside `location`, preventing non-LATAM postings from falling back to generic remote.
- Delimiter regex in `RESTRICTED_LOCATION_RE` to detect space-delimited `Remote US` strings.

## [1.3.0] - 2026-10-27

### Added
- Modality column (`Modalidad` / `Modality`) in the search results table with distinct indicators and badges for Remote, Hybrid, and On-site positions.
- Work mode classification (`detect_work_mode`) across all 7 ATS scanners (Ashby, Greenhouse, Lever, Workable, Breezy HR, Recruitee, BambooHR) and stored on `JobPosting.work_mode`.
- Mode column in the CLI search results table output (`python -m src.cli scan`).
- Expanded company registry across all 7 ATS platforms to 20,000+ companies.
- Prioritized Uruguayan tech companies at the head of every platform scanning queue.
- 4 additional ATS platform scanners: Workable, Breezy HR, Recruitee, and BambooHR, expanding the total supported platforms to 7.
- Territorial scope selector with presets for Latin America, North America, Europe, Worldwide, and Country Whitelist.
- Work mode filters (Remote, Hybrid, On-site) linked to the candidate profile residence location.
- Anti-captcha filter toggle to bypass listings protected by Cloudflare Turnstile.
- Discrete radio button option selection (`choose_radio_option`) using local LLM agents to answer non-standard form questions based on the candidate profile.
- Deterministic experience range matcher (`match_experience_range`) for radio groups, mapping candidate experience years to options like `6-9 years`.
- Question title and option label extraction for radio button groups across ATS platforms.
- Cross-platform auto-updater (`python -m src.updater` and `POST /api/system/update`) with Git pull and dependency synchronization across Windows, macOS, and Linux.
- End-to-end user guide (`docs/HOW_TO_USE.md`) with anonymized visual walkthrough screenshots.
- Support for auto-reloading the local server in `start.sh` via `node --watch`.

### Changed
- Generalized radio button selection to remain fully role-agnostic without hardcoded job titles.
- Default search criteria and role tags now start empty on clean installations.
- Maximum experience limit defaults to 0 (no cap) until a value is set.
- Sanitized all documentation and screenshots to use purely synthetic demo data.

### Fixed
- Restricted global remote indicators (`worldwide`, `global`, `anywhere`) to the location field to prevent title false positives (e.g., "Conta Global").
- Enforced country whitelist on physical on-site and hybrid positions when specific country tags are selected.
- Eliminated hardcoded candidate CV file names from web views and translation dictionaries.
- Resolved branch identification in GitHub Actions CI pull request workflows operating in detached HEAD mode.
- Remote location detection for BambooHR jobs.
- Active company seed synchronization across new ATS platforms.
- Cross-platform file opening and path resolution for Windows, macOS, and Linux.

## [1.2.0] - 2026-10-25

### Added
- Obsidian Precision dark UI design system with consistent tokens and responsive layouts.
- Full internationalization (i18n) with real-time switching between English and Spanish.
- Applications Kanban tracking board with live metrics (Pending submission, Submitted, Interview, Offer, Rejected).
- Universal ATS open questions manager with candidate answer customization.
- Clean profile onboarding with zero hardcoded personal data.

### Changed
- Replaced free-form chat panel with direct scan controls and structured filter cards.
- Standardized 1-page PDF resumes with English role titles and strict candidate fidelity.

### Fixed
- Stable arrival ordering when updating application statuses.
- Headed browser launch and launcher banner output on Windows terminal (`start.bat`).

## [1.1.0] - 2026-10-24

### Added
- Local web dashboard powered by Express and Vue 3 (`job-hunter-web`).
- Live ATS scanner with real-time progress via Server-Sent Events (SSE).
- Multi-agent adapter for Claude, Agy (Gemini), and Codex for targeted resume tailoring.
- Base PDF resume upload and viewing.
- Company exclusions manager with documented reasons and import capabilities.

### Fixed
- Host authorization and DNS rebinding protections on local web server.
- Dynamic port allocation fallback if port 3100 is in use.

## [1.0.0] - 2026-10-23

### Added
- Initial Python core framework with CLI (`job-hunter`).
- Direct ATS API scanning for Ashby, Greenhouse, and Lever.
- Human-in-the-loop Playwright browser automation for form pre-filling.
- Strict LATAM and Global residency restriction filters.
- Dual salary compensation support (contractor vs dependent).
- Anti-bot stealth mode with human typing emulation.
- Cross-platform command-line support across Windows, macOS, and Linux.
