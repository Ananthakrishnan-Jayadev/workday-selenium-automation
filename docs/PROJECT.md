# Project: Workday Auto-Apply (Selenium + Python + behave)

## 1. Summary

A Python test-automation-style framework that fills out Workday job applications end to end.
You give it a Workday job posting URL (or a list of them in Excel). It opens the posting, clicks
**Apply → Apply Manually**, signs in with the account for that company, fills every page of the
application from data in an Excel workbook, and **stops on the Review page**. You check the
application and click **Submit** yourself.

The code is laid out like a Java Cucumber framework:

| Java / Cucumber             | This project                          |
|-----------------------------|---------------------------------------|
| `.feature` files            | `features/*.feature` (behave, Gherkin) |
| Step definitions            | `features/steps/*.py`                 |
| Hooks (`@Before`, `@After`) | `features/environment.py`             |
| Page Object classes         | `pages/*.py`                          |
| Locator repository          | `locators/*.py`                       |
| Utility library             | `core/` (driver, waits, actions, widgets, Excel, config, logging) |
| Apache POI                  | `openpyxl`                            |

## 2. Goals (Version 1)

1. **One URL in, one filled application out.** Given a URL, reach the Review page with every field
   that the Excel data covers filled in.
2. **Excel is the only source of data.** Profile, work history, education, skills, question answers,
   disclosures, and per-company login credentials all come from one workbook.
3. **Never submit automatically.** The run always stops on Review and waits for you. There is no
   flag that turns on auto-submit in V1.
4. **Survive Workday's UI.** Clicks retry when covered by popups, elements are scrolled into view,
   lazy sections are waited for, and the custom dropdowns are handled by dedicated helpers.
5. **Batch mode.** Work through every `Pending` row in the Jobs sheet, one browser per job, and write
   the outcome back to Excel.
6. **Fail loudly, not silently.** Unknown questions, missing options and validation errors produce
   a screenshot, a log entry and a pause for you to decide. The script does not guess.

## 3. Out of scope for V1

| Not in V1                              | Why / plan                                              |
|----------------------------------------|---------------------------------------------------------|
| Creating Workday accounts              | You add existing accounts to the `Accounts` sheet by hand. Could come later. |
| Email verification links               | Only needed for new accounts.                           |
| CAPTCHA handling                       | Never automated. If one appears, the run pauses for you. |
| Auto-submit                            | Deliberately excluded.                                  |
| AI/LLM answers for free-text questions | Unknown questions pause for you instead.                |
| "Autofill with Resume" / "Use My Last Application" | V1 always takes **Apply Manually**, which gives a predictable empty form. |
| Headless runs                          | Possible via config, but V1 is meant to be watched (headed). |
| Parallel jobs                          | Sequential only. Workday rate limits and you need to review each one. |

## 4. Users and environment

- Single user, running locally on Linux (also works on Windows/macOS).
- Python 3.11+ (3.14 on this machine; confirm compatibility in Phase 1).
- Chrome by default, Firefox optional. Drivers are resolved automatically by Selenium Manager.

## 5. Success criteria

| Phase | Done when |
|-------|-----------|
| 1 | From a real URL: Apply → Apply Manually → sign in → My Information fully filled → Save and Continue lands on My Experience. |
| 2 | My Experience fully filled (resume, all work and education entries, languages, skills, links), with no validation errors after Save and Continue. |
| 3 | Questions, Voluntary Disclosures and Self Identify filled from the Questions sheet; stops on Review; batch mode over the Jobs sheet writes status back to Excel. |

## 6. Constraints and risks

| Risk | Mitigation |
|------|------------|
| Every company's Workday ("tenant") differs slightly. | Locators are based on `data-automation-id` (shared across tenants), with fallback lists of alternate IDs, and page detection by marker instead of a fixed order. |
| Application Questions differ per company. | A keyword → answer table in Excel, optionally scoped to one company. Anything unmatched pauses for you. |
| Workday's React inputs ignore programmatic value changes. | Real keystrokes via `send_keys`, read-back verification, then Tab/blur to commit. |
| Clicks are intercepted by popups and overlays. | `safe_click`: wait → scroll to centre → click → on interception dismiss overlays and retry → ActionChains → JS click as a last resort. |
| Passwords stored in Excel in plain text. | The workbook lives in `data/`, which is git-ignored. Optionally the password column can say `ENV:CIBC_PASSWORD` to read from `.env` instead. |
| Workday's terms of use / anti-bot measures. | Human-paced, headed, one job at a time, no CAPTCHA bypass, human submits. Use at your own discretion. |

## 7. Reference material

- `../workday_extension/content.js`: the browser extension that already fills Workday pages. It is
  the main source of the verified locators and the dropdown, multiselect and date techniques.
- `../agentic_workday/app/field_map.py` and `app/handlers/`: an earlier Playwright version with
  page markers, account-page locators and the Apply popup flow.
- `docs/LOCATORS.md`: the merged locator list, showing which locators are verified and which still need a page capture.
