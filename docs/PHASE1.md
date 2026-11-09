# Phase 1: Detailed Plan

**Target URL:** https://cibc.wd3.myworkdayjobs.com/search/job/Toronto-ON/Senior-Data-Engineer_2622337
**Goal:** URL → Apply → Apply Manually → (Create Account page) → Sign In → fill **My Information**
→ Save and Continue → land on **My Experience**, then pause.

## 1. Expected CIBC flow and what each step does

| # | Screen | Page object | What the script does | Done when |
|---|---|---|---|---|
| 1 | Job posting | `JobPostingPage` | open URL, dismiss cookie banner, click **Apply** | popup visible |
| 2 | Apply popup | `JobPostingPage` | click **Apply Manually** | URL contains `/apply` or a create-account/sign-in form appears |
| 3 | Create Account | `CreateAccountPage` | V1 does not create accounts: click the **Sign In** link | sign-in form visible |
| 4 | Sign In | `SignInPage` | type email and password from the `Accounts` sheet, click **Sign In** | `applyFlowMyInfoPage` present, or an error message |
| 5 | My Information | `MyInformationPage` | fill all fields from `Profile`, Save and Continue | `applyFlowMyExpPage` present, no errors |
| 6 | My Experience | | Phase 1 stops here: screenshot and pause | |

The page objects also handle these variations:
- **Already signed in** (persistent profile or session): step 3/4 detects the My Information marker
  and skips sign-in.
- **Sign-in form shown first** instead of Create Account: skip step 3.
- **Sign-in fails** (wrong password, locked account, verification needed): screenshot, log the
  on-screen message, mark `Failed: sign-in`, stop.
- **Already applied** ("You've already applied" message): mark `Skipped: already applied`, stop.
- **CAPTCHA or anything unrecognised**: pause for you.

## 2. Files to build (in order)

### 2.1 Scaffold
- `requirements.txt`: `selenium`, `behave`, `openpyxl`, `pyyaml`, `python-dotenv`
- `behave.ini`: `paths=features`, `stdout_capture=no`, `stderr_capture=no`, `log_capture=no`,
  `format=pretty`, `show_skipped=false`
- `config/config.yaml`: as in DESIGN §6
- `.gitignore`: `data/`, `reports/`, `docs/page_dumps/*.html`, `.env`, `.venv/`, `__pycache__/`
- **Step 0 check:** install into a venv on Python 3.14 and confirm behave and selenium import and
  run. If behave has trouble on 3.14, fall back to a 3.12 venv.

### 2.2 `core/` (the library)
| File | Contents |
|---|---|
| `config.py` | `load_config()` → dataclass. Values can be overridden with `-D key=value`. |
| `logger.py` | console + file log per run, `mask()` for passwords |
| `driver.py` | `create_driver(cfg)`: Chrome/Firefox, window size, optional user-data dir, headless flag, `page_load_strategy=normal`, implicit wait 0 |
| `waits.py` | `wait_present`, `wait_visible`, `wait_clickable`, `wait_gone`, `wait_any(markers)` → which one appeared, `wait_url_contains` |
| `actions.py` | `scroll_into_view`, `safe_click`, `safe_type`, `press`, `dismiss_overlays`, `is_present`, `@retry` decorator (DESIGN §4.1–4.2) |
| `text.py` | `normalize()`, `best_match(candidates, options)` (exact → starts-with → contains) |
| `widgets.py` | `select_dropdown`, `select_prompt`, `select_radio`, `set_checkbox` (DESIGN §4.3–4.4) |
| `human.py` | `pause_for_human(driver, reason)`: screenshot, page dump, print the reason, wait for Enter |
| `models.py` | `Job`, `Account`, `Profile` dataclasses |
| `excel_reader.py` | `load_workbook(path)` → `AppData(jobs, accounts, profile)`; `find_account(job)` |
| `screens.py` | `save_screenshot(name)`, `save_page_dump(name)` → `reports/` |

### 2.3 Locators (`locators/`)
Each module holds `(By, value)` tuples, and lists of alternatives where tenants differ.

```python
# locators/common.py
PAGE_MARKERS = {
    "my_information": (By.CSS_SELECTOR, '[data-automation-id="applyFlowMyInfoPage"]'),
    "my_experience":  (By.CSS_SELECTOR, '[data-automation-id="applyFlowMyExpPage"]'),
    ...
}
NEXT_BUTTON = [(By.CSS_SELECTOR, '[data-automation-id="bottom-navigation-next-button"]'),
               (By.CSS_SELECTOR, '[data-automation-id="pageFooterNextButton"]')]
OPEN_LISTBOX, OPTION, PROMPT_OPTION, PROMPT_NO_MATCH, SELECTED_ITEM, ERROR_BANNER, COOKIE_ACCEPT ...
```
- `job_posting.py`: `APPLY_BUTTON`, `APPLY_POPUP`, `APPLY_MANUALLY`, `ALREADY_APPLIED`
- `auth.py`: `CREATE_ACCOUNT_FORM`, `SIGN_IN_LINK`, `EMAIL`, `PASSWORD`, `SIGN_IN_SUBMIT`,
  `SIGN_IN_ERROR`. Note: on many tenants the Sign In button is covered by a
  `[data-automation-id="click_filter"]` div, and the click has to go to that div. To confirm from the dump.
- `my_information.py`: everything in LOCATORS.md › My Information

**These get confirmed or corrected from your 5 page dumps before the pages are coded.**

### 2.4 Pages (`pages/`)
```python
class BasePage:                          # driver, cfg, log, wait helpers
    current_page() -> str | None         # checks PAGE_MARKERS
    save_and_continue(expect_next: str)  # click next, wait for old marker to go, check for errors
    read_errors() -> list[str]

class JobPostingPage(BasePage):
    open(url); accept_cookies(); click_apply(); choose_apply_manually()
    is_already_applied() -> bool

class CreateAccountPage(BasePage):
    is_displayed() -> bool; go_to_sign_in()

class SignInPage(BasePage):
    is_displayed() -> bool; sign_in(account) -> SignInResult   # OK / BAD_CREDENTIALS / VERIFY / UNKNOWN

class MyInformationPage(BasePage):
    fill(profile) -> FillReport          # records filled / skipped / failed fields
    # order matters: country → source → previous worker → names → address → province
    #                → phone type → phone (last: dropdowns can re-render and clear it)
```

### 2.5 Features and steps
```gherkin
# features/apply_job.feature
Feature: Apply to a Workday job
  Scenario: Fill a Workday application up to Review
    Given the job to apply for is loaded
    And the applicant data is loaded from Excel
    When I open the job posting
    And I start the application manually
    And I sign in with the account for this company
    And I complete the "My Information" page
    Then I should be on the "My Experience" page
```
- `features/environment.py`: `before_all` (config, logging, Excel), `before_scenario` (resolve
  job from `-D url` or `-D row`, create driver), `after_step` (screenshot and dump on failure),
  `after_scenario` (pause before quitting if configured, quit).
- `features/steps/common_steps.py`, `auth_steps.py`, `my_information_steps.py`.
- If `-D url` isn't in the Jobs sheet, the company comes from the URL subdomain (`cibc`), which
  is used to look up the account.

### 2.6 Excel and tools
- `tools/make_template.py`: creates `data/applicant_data.xlsx` with the `Jobs`, `Accounts` and
  `Profile` sheets (Phase 1) plus headers for the later sheets, with example rows. It doesn't
  overwrite an existing workbook unless given `--force`.
- `tools/dump_page.py`: `human.pause_for_human` and `after_step` use its save function. It can
  also be run on its own as `python tools/dump_page.py <url>`: it opens the page, you click through
  to the state you want, and each Enter saves a numbered dump (useful for capturing later pages).

**Phase 1 Profile keys:** `FirstName, MiddleName, LastName, Country, AddressLine1, AddressLine2,
City, Province, PostalCode, PhoneType, PhoneCountryCode, Phone, PhoneExtension, HowDidYouHear,
PreviouslyWorkedHere`

## 3. Build order
1. Scaffold + venv check (Step 0)
2. **Read the 5 dumps → update `docs/LOCATORS.md` statuses → write `locators/`**
3. `core/` config, logger, driver, waits, actions, text
4. Excel template, reader, models
5. `JobPostingPage` + steps → test: reaches the Create Account page
6. `CreateAccountPage`, `SignInPage` + steps → test: signed in, on My Information
7. `widgets.py` + `MyInformationPage` + steps → test: full page filled, lands on My Experience
8. Hardening: 3 consecutive clean runs; deliberately cause a failure (wrong password, bad
   dropdown value) and confirm screenshots, logs and pauses behave correctly

## 4. Acceptance (from PHASES.md)
- `behave -D url=<CIBC URL>` reaches My Experience with every My Information field filled from Excel.
- Country, Province, Phone Type and How Did You Hear are chosen correctly in 3 consecutive runs.
- A wrong password produces a clean `Failed: sign-in` with a screenshot and doesn't crash.
- Nothing in the logs shows the password.

## 5. Answered by the page dumps (2026-11-08)
- CIBC shows **Create Account** first. The script clicks `signInLink` to switch, and both modes
  share one form (`signInFormo`).
- The Sign In button is covered by a `click_filter` div (confirmed), so the click goes to that div.
- My Information extras: middle name, address line 2, phone extension, preferred-name checkbox,
  SMS/WhatsApp opt-ins. Country is pre-set to Canada and the phone code is pre-selected to "Canada (+1)".
  The script skips a field whose current value already matches.
- Field order on the page: source → previous worker → country → name → address → province →
  postal → phone type → phone code → phone → extension. Fill in that order, with phone number last.
- Never touch the `beecatcher` honeypot input.
- Profile keys added: `MiddleName`, `AddressLine2`, `PhoneExtension`.

## 6. Still open
- The structure of the "How did you hear" options: a flat list or nested (e.g. "Job Board › LinkedIn")?
- What the error looks like for a wrong password, and for validation errors after Save and Continue.
- After signing in once, does "Apply Manually" go straight to My Information or to a
  "resume your saved application" screen?
