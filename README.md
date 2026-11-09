# Workday Auto-Apply (Python · Selenium · behave)

Fills Workday job applications from an Excel workbook, from the job URL through to the
**Review** page, then stops so you can check the application and submit it yourself.

> **Status: V1 complete (2026-11-09).** Live on CIBC end to end: job posting → Apply Manually →
> sign in → My Information → My Experience → Application Questions → Voluntary Disclosures →
> **stops on Review**. You submit; the outcome goes back into the Jobs sheet.
> Not built yet: the batch runner (`run.py`). Run jobs one at a time with `behave -D row=N`.

## Documents
| Doc | What's in it |
|---|---|
| [docs/PROJECT.md](docs/PROJECT.md) | Goals, scope, non-goals, risks |
| [docs/DESIGN.md](docs/DESIGN.md) | Architecture, flow, how Workday's controls are handled, Excel schema, config |
| [docs/PHASES.md](docs/PHASES.md) | The 3 build phases, status and acceptance checks |
| [docs/PHASE1.md](docs/PHASE1.md) | Detailed Phase 1 plan |
| [docs/LOCATORS.md](docs/LOCATORS.md) | Every Workday locator, where it was verified, and what's still unverified |
| [docs/page_dumps/README.md](docs/page_dumps/README.md) | How to capture a Workday page for locator work |

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python tools/make_template.py          # creates data/applicant_data.xlsx (won't overwrite)
```
Tested with Python 3.14, Selenium 4.52, behave 1.3.3. Chrome/Chromium or Firefox must be installed.
A snap-packaged browser (Ubuntu's default) uses the snap's own driver automatically; otherwise Selenium
Manager downloads one. Override in `config/config.yaml` → `browser.driver_path` / `browser.binary`.

Passwords can go straight into the Accounts sheet, or into `.env`: copy `.env.example` to `.env`,
set `CIBC_PASSWORD=...`, and put `ENV:CIBC_PASSWORD` in the Password cell.

## The workbook (`data/applicant_data.xlsx`)
| Sheet | One row per | Notes |
|---|---|---|
| Jobs | job URL | `Status = Pending` to include it |
| Accounts | company | an **existing** Workday account (V1 doesn't create accounts) |
| Profile | field (key/value) | name, address, phone, How did you hear, LinkedIn, Website, ResumePath, CoverLetterPath (optional) |
| WorkExperience | job | dates as month name + year; `CurrentlyWorkHere = Yes` hides the end date |
| Education | school | Degree / FieldOfStudy can list fallbacks |
| Languages | language | Proficiency applies to every proficiency dropdown |
| Skills | skill | must be Workday's **exact** skill name (a bracketed note is fine) |
| Certifications | certificate | only used if the tenant has the section (CIBC doesn't) |
| Questions | rule | keywords in the question → answer (see below), incl. the terms checkbox |

**Writing values**
- `A; B; C`: fallbacks, tried in order. The first one Workday has wins, and a later run replaces a
  fallback with your first choice if it becomes available.
- `Category > Value`: nested lists, e.g. `Job Board/Social Media > LinkedIn`.
- Matching ignores case, apostrophes, dashes and slashes. A value matches an option that equals it,
  starts with it (`Canada` → `Canada (+1)`), or contains it as whole words (`Fluent` → `5 - Fluent`,
  but `Male` never matches `Female`).
- **Field of Study** also takes the closest option by whole words before using a fallback
  (`Artificial Intelligence` → `Artificial Intelligence and Robotics`). Generic words such as
  *science* or *engineering* don't count on their own.
- **Skills** are strict: `SQL` does not accept `SQL Assistant`. A skill Workday doesn't list exactly is
  skipped with a warning; the log shows what Workday offered.

**Questions sheet**: `Keywords | Answer | Company | Page | Notes`
- `authorized to work; eligible to work`: any of these phrases. `relative; family member + td`:
  (relative OR family member) AND td. Phrases match whole words.
- Top-to-bottom, first match wins; a row with a Company beats a blank-Company row for that company.
- Leave Answer blank to be asked: a required question with no answer pauses the run and lists the
  options its dropdown offers. For checkbox groups, list the labels to tick separated by `;`.

The `data/` folder is git-ignored: it contains your password and personal details.

## Run
```bash
behave                                   # first Pending job in the Jobs sheet
behave -D url="https://<company>.wd3.myworkdayjobs.com/.../job/..."
behave -D row=2                          # a specific Jobs sheet row

behave -D slow_mo_ms=200                 # slow down to watch
behave -D browser=firefox
behave -D on_unknown=skip                # log problems instead of pausing
```
Run it in a visible browser: headless sign-in didn't complete on CIBC.

Each run writes `reports/<timestamp>_<company>/`: `run.log` (DEBUG detail, every search step),
a screenshot + HTML at each step and whenever something fails, and `result.json`.

**When it needs you**, it prints `ACTION NEEDED IN THE BROWSER` with the reason (field it couldn't
fill, validation errors after Save and Continue, unanswered required questions with their options).
Fix it in the browser, then press Enter in the terminal.

**Re-running is safe.** Values already correct are left alone, existing entries are filled in place
(no duplicates), and a resume or cover letter already listed isn't uploaded twice.

**On the Review page the run stops.** Check the application, click Submit yourself if you're happy,
then answer in the terminal: `s` submitted, `k` skipped, `f` failed, `r` review later. The answer is
written to the Jobs sheet (Status, LastRun, Notes) and to the run's `result.json`. The script never
clicks Submit: a guard refuses any footer button labelled Submit, and any button on the Review page.

## Things Workday does that the code handles
| Behaviour | Handling |
|---|---|
| "Something went wrong. Please refresh the page" right after sign-in | detected, page refreshed (up to twice) |
| Sign In button covered by an invisible `click_filter` div | the div is clicked |
| Dates: each month/year box is covered by a display div | the display div is clicked, digits typed, value verified |
| Search lists show "No Items." / the full A-Z list / "No matches found" before the real results | only a list containing a match counts; "No matches" only after ~2.5s |
| Enter with a single match selects it without showing a list | the field is checked first |
| A list left open covers the next field | closed with Escape, else by clicking outside |
| Selected skills cover the search box | the box is focused directly |
| Hidden `beecatcher` input (bot trap) | never touched |

## Project layout
```
features/   apply_job.feature, environment.py (hooks), steps/ (common_steps, auth_steps)
pages/      base_page, job_posting_page, auth_page, my_information_page, my_experience_page,
            questions_page (Application Questions, Voluntary Disclosures, Self Identify)
locators/   common, job_posting, auth, my_information, my_experience, questions
core/       actions (robust click/type/focus), widgets (dropdown, prompt, date, upload, checkbox,
            auto-detect), text (matching), answers (Questions rules), excel_reader, models,
            session (pause-for-human), reporter, waits, driver, config, logger
tools/      make_template.py, dump_page.py
docs/       project docs + page_dumps/ (captured HTML is git-ignored)
data/       applicant_data.xlsx, resume (git-ignored)
reports/    run output (git-ignored)
```

## Next (V2 ideas)
- `run.py` batch runner: every Pending row, one browser per job, status written back.
- Account creation + email verification, "Use My Last Application", headless runs.
- More tenants: capture their pages (`tools/dump_page.py`) and extend `docs/LOCATORS.md`.

## Safety
- The script **never clicks Submit**.
- It doesn't create accounts, solve CAPTCHAs or bypass verification.
- One job at a time, in a visible browser.
