# Phases (Version 1)

Each phase ends with something you can run against a real Workday URL. A phase is done only
after a live run passes its acceptance check.

---

## Phase 1: Foundation and first page

**Goal:** URL → Apply Manually → sign in → **My Information** filled → Save and Continue reaches My Experience.

**Status:** ✅ done (live run 2026-11-09).

Detailed plan: [PHASE1.md](PHASE1.md)

**Build**
- Scaffold: folders, `requirements.txt`, `behave.ini`, `config/config.yaml`, `.gitignore`, `README.md`.
- `core/`: `config`, `logger`, `driver` (Chrome/Firefox), `waits`, `actions` (`safe_click`,
  `safe_type`, `scroll_into_view`, `dismiss_overlays`, retry), `text` (normalize, best_match),
  `human.pause_for_human`.
- `core/widgets.py`: `select_dropdown`, `select_prompt`, `select_radio`, `set_checkbox`.
- Excel: `tools/make_template.py`, `excel_reader` + `models` for `Jobs`, `Accounts`, `Profile`.
- `tools/dump_page.py`: save HTML and a screenshot of the current page (for locator capture).
- Pages: `BasePage` (page detection, Save and Continue, error check), `JobPostingPage`,
  `SignInPage`, `MyInformationPage`.
- `features/apply_job.feature` (full scenario; later steps can be stubs that pause), steps for
  the above, and `environment.py` hooks with screenshots on failure.

**Locator work:** capture the Apply popup, the sign-in page and My Information from a real tenant
(see `LOCATORS.md`) and confirm or fix the locators.

**Acceptance**
- `behave -D url=<real CIBC URL>` signs in, fills every My Information field from Excel, and lands
  on My Experience with no validation errors.
- Country, Province and Phone Type dropdowns and the "How did you hear" prompt are chosen reliably
  over 3 consecutive runs.

---

## Phase 2: My Experience

**Status:** ✅ done (live run 2026-11-09).

**Goal:** the hardest page, filled completely.

**Build**
- Excel: `WorkExperience`, `Education`, `Languages`, `Skills`, `Certifications` sheets → models.
- `widgets.fill_date`, `widgets.upload_file`, repeatable-section helper (`entry_scope(i)`),
  handling of pre-filled entries.
- `MyExperiencePage`: resume upload → work experience (N entries, current-job checkbox, dates,
  description) → education (fallback degree and field-of-study lists) → certifications →
  languages (per-type proficiency) → skills (multiselect) → LinkedIn/websites.
- Step: `I complete the "My Experience" page`.

**Acceptance**
- 2+ work entries, 1+ education entry, 1 language and 5 skills filled. Save and Continue moves on
  with no validation errors.
- Re-running on a tenant where the resume upload pre-fills entries doesn't create duplicates.

---

## Phase 3: Questions, disclosures, review stop, batch

**Status (2026-11-09):** Application Questions built + mock-tested; disclosures, review stop, batch next.

**Goal:** complete end-to-end runs to Review, and batch mode.

**Build**
- Excel: `Questions` sheet → `core/answers.py` rule engine (any/all keywords, company scope, page scope).
- `ApplicationQuestionsPage`: iterate question blocks (fieldset/legend), detect the control type
  (dropdown / radio / checkbox group / text / textarea / date), answer it from the rules, pause on
  unknown required questions. Loops over Primary and Secondary question pages.
- `VoluntaryDisclosuresPage` (gender, ethnicity, veteran, terms/consent checkbox) and
  `SelfIdentifyPage` (disability form: name, date, checkbox).
- `ReviewPage`: detect Review, hard stop, leave the browser open, prompt for the final status.
- `run.py`: batch over `Pending` rows, one behave subprocess per job, write Status/LastRun/Notes
  back, plus a JSON run summary.

**Acceptance**
- 3 jobs at 2+ different companies run in batch, each reaches Review, and Excel statuses update.
- An unmatched question pauses with a clear message and screenshot. After you answer it in the
  browser and press Enter, the run continues.
- Nothing is ever submitted by the script.

---

## After V1 (not planned yet)
Account creation and email verification · "Use My Last Application" path · LLM fallback for
free-text questions · headless/CI runs · Allure/HTML reports.
