# Workday Auto-Apply (Python · Selenium · behave)

Fills Workday job applications from an Excel workbook, from the job URL through to the
**Review** page, then stops so you can check the application and submit it yourself.

> Status: **Phase 1 built.** Job posting → Apply Manually → sign in → My Information → Save and Continue.
> Phases 2–3 (My Experience, questions, disclosures, review stop, batch) are next. See `docs/PHASES.md`.

## Documents
| Doc | What's in it |
|---|---|
| [docs/PROJECT.md](docs/PROJECT.md) | Goals, scope, non-goals, risks |
| [docs/DESIGN.md](docs/DESIGN.md) | Architecture, folder layout, flow, robustness strategy, Excel schema, config |
| [docs/PHASES.md](docs/PHASES.md) | The 3 build phases with acceptance checks |
| [docs/LOCATORS.md](docs/LOCATORS.md) | Every Workday locator, its source and verification status, and pages still to capture |

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python tools/make_template.py          # creates data/applicant_data.xlsx
```
Chrome/Chromium or Firefox must be installed. If the browser is a snap package (Ubuntu's default
Chromium/Firefox), the snap's own driver is used automatically. Otherwise Selenium Manager downloads
a matching driver. Override either in `config/config.yaml` → `browser.driver_path` / `browser.binary`.

Passwords can go straight into the Accounts sheet, or be kept in `.env`: copy `.env.example` to
`.env`, set `CIBC_PASSWORD=...`, and put `ENV:CIBC_PASSWORD` in the sheet's Password cell.

## Fill in the workbook (`data/applicant_data.xlsx`)
- **Jobs:** one row per posting URL, with Company and `Status = Pending`.
- **Accounts:** an existing Workday account per company (email and password).
- **Profile, WorkExperience, Education, Languages, Skills:** your data.
- **Questions:** keyword → answer rules for screening and disclosure questions.

Full column reference: `docs/DESIGN.md` §5. The `data/` folder is git-ignored because it contains passwords.

## Run
```bash
# first Pending job in the Jobs sheet
behave

# a specific URL, or a specific Jobs sheet row
behave -D url="https://<company>.wd3.myworkdayjobs.com/.../job/..."
behave -D row=2

# useful overrides
behave -D slow_mo_ms=500          # slow down to watch
behave -D browser=firefox
behave -D on_unknown=skip         # don't pause on problems, just log them

# every Pending job in the Jobs sheet (Phase 3)
python run.py
```
Each run writes `reports/<timestamp>_<company>/` containing `run.log`, a screenshot and HTML dump at
each step, and `result.json`.

Capturing a page for locator work: `python tools/dump_page.py <url> --name cibc`.
The run stops on **Review** and leaves the browser open. Check the application, click Submit
yourself, then type `s` (submitted), `k` (skipped) or `f` (failed) in the terminal. The Jobs sheet
is updated with that status.

When the script hits something it can't handle (an unknown question, no matching option, a
validation error, a CAPTCHA), it takes a screenshot, prints the reason and waits. Fix it in the
browser and press Enter to continue.

## Project layout
```
features/   apply_job.feature, steps/ (common, auth), environment.py (hooks)
pages/      base_page, job_posting_page, auth_page, my_information_page
locators/   common, job_posting, auth, my_information
core/       config, driver, waits, actions (safe click/type), widgets (dropdown/prompt/radio),
            text (matching), excel_reader, models, session (pause-for-human), reporter, logger
tools/      make_template.py, dump_page.py
data/       applicant_data.xlsx (git-ignored)
reports/    logs, screenshots, page dumps (git-ignored)
```

## Safety
- The script **never clicks Submit**.
- It doesn't create accounts, solve CAPTCHAs or bypass verification.
- One job at a time, in a visible browser.
