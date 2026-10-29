# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.1] - 2026-10-28

### Added
- Cloudflare Turnstile challenge interaction in `BaseApplicator.handle_turnstile_if_present`: detects Turnstile iframes and interacts with the verification checkbox when presented in interactive challenge mode.
- Turnstile detection and challenge interaction handling in `WorkableApplicator` and CLI application flow.
- Scanner test coverage in `tests/test_scanners.py` for Workable captcha model and Anti-CAPTCHA filtering.
- Automated API test coverage in `web/tests/api.test.js` for base CV assignment (`POST /api/applications/:id/use-base-cv`).
- Unit test in `tests/test_salary_and_questions.py` validating that a single Resume file input is uploaded when a Cover Letter field is present on the page.

### Fixed
- Workable ATS scanner (`WorkableScanner`): flagged postings with `has_captcha=True` so the Anti-CAPTCHA toggle (`--allow-captcha` / UI Anti-CAPTCHA switch) filters out Workable listings protected by Cloudflare Turnstile.
- Playwright browser stealth launcher (`src/automation/browser.py`): passed `ignore_default_args=['--enable-automation']` to strip the default automation flag that caused Cloudflare Turnstile verification failures.
- Native browser property simulation: updated stealth script with realistic `Plugin` and `PluginArray` structures, genuine `window.chrome` properties, and clean `navigator.webdriver` undefined getter handling across documents and child frames.
- Base CV assignment in web backend (`web/server/store.js`): implemented `store.get(id)` in `createStore` to resolve the `store.get is not a function` error when calling `POST /api/applications/:id/use-base-cv`.
- Resume upload routing when Cover Letter is present (`safe_upload_resume` in `src/automation/applicators/base.py`): bounded ancestor traversal to local field containers (depth < 3, stopping before `form`, `main`, or `body`) so presence of a Cover Letter textarea elsewhere on the form does not misclassify the single Resume file input as a cover letter.
- Added explicit selectors for Workable dropzones (`[data-ui*='resume']`, `div[data-ui='file-upload']`, `div:has(> label:has-text('Resume'))`) and fallback file upload in `WorkableApplicator`.

## [1.4.0] - 2026-10-28

### Added
- Bilingual country registry (`web/src/countries.js`) with 52 countries, ISO 3166-1 alpha-2 codes, Spanish names, English names, territorial scopes, and aliases.
- Table pagination in `SearchView.vue` with 25, 50, and 100 rows per page selectors, range indicators, and navigation controls.
- Debounced search input (150 ms) with a quick-clear button in `SearchView.vue`.
- Indexed memory cache (`existingAppsIndex`) with `Set` lookups (O(1)) for prepared and tailored vacancy checks.
- Throttled event buffer (80 ms) for high-frequency SSE messages in `scanController.js`.
- Bidirectional role acronym expansions (`QA`, `QC`, `QE`, `QIA`, `SDET`) in `BaseScanner.matches_keywords`.
- Tokenized single-word matching with boundary checks for flexible title matching.
- Match score relevance boost in `scanController.js` for `QE`, `QC`, `QIA`, and `Test` roles.
- Frontend and scanner test suites for country normalization, translation, and filtering (`web/tests/countries.test.js` and `tests/test_scanners.py`).

### Fixed
- Specific countries filter language synchronization: dropdown options, autocomplete matching, and selected country chips update when the active language changes in `SearchView.vue`.
- Cross-lingual ATS location matching: `getCountrySearchTerms` in `scanController.js` and `expand_country_terms` in `BaseScanner` expand selected countries into bilingual search terms. Postings written as `Tokyo, Japan` or `Berlin, Germany` match when filters are selected in Spanish.
- BambooHR SPA cold-start synchronization: `ensure_application_tab_open` and `BambooHRApplicator` wait for client-side JavaScript elements (`Apply for This Job` button and form inputs) to mount before field filling begins.
- BambooHR Province field completion: maps `input[name='state.value']` when the platform switches the US state dropdown into a required `Province *` text input for non-US countries.
- Resume upload routing: added `safe_upload_resume` across all 7 ATS applicators (BambooHR, Greenhouse, Lever, Ashby, Workable, Breezy, Recruitee). Evaluates parent container text to reject Cover Letter file inputs and attach the CV strictly to Resume inputs.
- Generic location resolution: `city`, `country`, `resolved_state`, and `resolved_address` in `PersonalInfo` dynamically parse multi-part location strings without hardcoded city defaults.
- Deterministic handling for ZIP / postal codes and Date Available: added factual resolvers to prevent open-ended essay generation for structured form inputs.
- BambooHR `atsLocation` parser to read `city`, `state`, `province`, and `country` alongside `location`, which prevents non-LATAM postings from falling back to generic remote.
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
