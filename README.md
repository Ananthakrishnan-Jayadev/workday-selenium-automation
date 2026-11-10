# Workday Auto-Apply (Python · Selenium · behave)

Fills Workday job applications from an Excel workbook, from the job URL through to the
**Review** page, then stops so you can check the application and submit it yourself.

> **Status: V1 complete (2026-11-09).** Live on CIBC end to end: job posting → Apply Manually →
> sign in → My Information → My Experience → Application Questions → Voluntary Disclosures →
> **stops on Review**. You submit; the outcome goes back into the Jobs sheet.
> Not built yet: the batch runner (`run.py`). Run jobs one at a time with `behave -D row=N`.
>
> **Live-tested (2026-11-09/10) on 11 tenants:** CIBC, BMO, TD, Citi, RBC, Accenture, Manulife,
> McKesson, Canadian Tire, NVIDIA, Thomson Reuters. Each new company mostly needs new rows in the
> Questions sheet (its own question wording and option labels); the script pauses and lists them.

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
source .venv/bin/activate              # each new terminal; Windows: see below
pip install -r requirements.txt
python tools/make_template.py          # creates data/applicant_data.xlsx (won't overwrite)
```
`activate` must be *sourced*, not executed (`.venv/bin/activate` on its own gives "Permission denied").
Without activating you can call `.venv/bin/behave` directly. Don't use `sudo`.

Tested on Linux (Ubuntu) with Python 3.14, Selenium 4.52, behave 1.3.3. Chrome/Chromium or Firefox must be installed.
A snap-packaged browser (Ubuntu's default) uses the snap's own driver automatically; otherwise Selenium
Manager downloads one. Override in `config/config.yaml` → `browser.driver_path` / `browser.binary`.

Passwords can go straight into the Accounts sheet, or into `.env`: copy `.env.example` to `.env`,
set `CIBC_PASSWORD=...`, and put `ENV:CIBC_PASSWORD` in the Password cell.

### Running on Windows
Not yet tried on Windows, but nothing in the code is Linux-only. In PowerShell:
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1             # each new terminal
pip install -r requirements.txt
python tools\make_template.py
behave -D slow_mo_ms=200
```
- If PowerShell won't run `Activate.ps1`, allow local scripts once:
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. Or skip activating and run
  `.venv\Scripts\behave -D slow_mo_ms=200`. (In cmd.exe the activate script is `.venv\Scripts\activate.bat`.)
- Install **Google Chrome** (or Firefox). Selenium Manager downloads the matching driver; the
  snap-driver handling above only applies on Linux.
- **File paths in the workbook are per machine.** `ResumePath` and `CoverLetterPath` in the Profile sheet
  must be Windows paths, e.g. `C:\Users\you\workday-selenium\data\resume.pdf`. The `data\` folder isn't
  in git: copy the workbook, resume and cover letter over yourself.
- The console is switched to UTF-8 automatically, so log lines with `→` print correctly. If an old
  console still shows `?` instead of the arrow, it's cosmetic; `run.log` is always UTF-8.
- Close the workbook in Excel before a run finishes. Excel locks the file, so the status can't be
  written back (the run warns and keeps the status in `result.json`).

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
| Certifications | certificate | only used if the tenant has the section (CIBC doesn't). Not in the company's list → skipped, and the empty entry is deleted so Save isn't blocked |
| Questions | rule | keywords in the question → answer (see below), incl. the terms checkbox |

**Fallbacks get their own columns** (tried left to right; the first one the company's form offers wins):
| Sheet | Columns |
|---|---|
| Profile | `Value`, `Fallback 1`, `Fallback 2` (e.g. PhoneType: `Mobile` · `Personal Primary`) |
| Skills | `Skill`, `Fallback 1`, `Fallback 2` (e.g. `SQL` · `PostgreSQL` · `MySQL`) |
| Questions | `Answer`, `Fallback 1`, `Fallback 2`, `Fallback 3` (e.g. `Man` · `Male`) |
| Education | `Degree`, `Degree Fallback 1..3`, `FieldOfStudy`, `FieldOfStudy Fallback 1..3` |
| Languages | `Proficiency`, `Proficiency Fallback 1..2` |

A later run replaces a fallback with your first choice if that becomes available. (A `;` inside one cell
still works as a separator, but columns are easier to read.)

**Matching**
- Case, apostrophes, dashes and slashes are ignored. `Category > Value` picks from nested lists
  (`Job Board/Social Media > LinkedIn`).
- **Everything matches whole words**: `No` matches `No (Canada)` but never `Not applicable` or
  `Do not wish to declare`; `Male` never matches `Female`.
- List markers in front of options are ignored: `No` matches `b. No, I Don't Have A Disability (Canada)`
  and `South Asian` matches `i. South Asian (e.g., East Indian…)` (McKesson).
- Profile / My Experience values match an option that equals them, starts with them
  (`Canada` → `Canada (+1)`) or contains them as whole words (`Fluent` → `5 - Fluent`).
- **Question answers are strict**: the option must equal the answer or start with it
  (`Yes` → `Yes - Newcomer`). `Man` never picks `Trans Man`; add the company's wording as a fallback.
- **Field of Study** takes the closest option by whole words before a fallback, searching your words in
  order (`Artificial Intelligence` → `Artificial Intelligence and Robotics`; `Data Analytics` looks for
  a `Data …` option first). Generic words such as *science* don't count on their own.
- **Skills** need Workday's exact name. A bracketed note is fine either way: `Python` →
  `Python (Programming Language)`, `SQL` → `Structured Query Language (SQL)`; the option spelled
  exactly as in Excel is preferred. `SQL` never picks `SQL Assistant`. A skill Workday doesn't list
  is skipped.
- **Different wording per company is normal.** When an answer isn't an option, the log prints every
  option the company offers: add the one you want as the next fallback (e.g. Race: `South Asian` ·
  `Asian - South Asian` · `Racialized/ South Asian`; PhoneType: `Mobile` · `Personal Primary` ·
  `Home Cellular`). To catch a new wording of a known question, add its phrase to that row's Keywords
  (e.g. `employer support to obtain` on the sponsorship row).

**Questions sheet**: `Keywords | Answer | Fallback 1-3 | Company | Page | Notes`
- `authorized to work; eligible to work`: any of these phrases. `relative; family member + td`:
  (relative OR family member) AND td. Phrases match whole words.
- `{company}` stands for the job's company: `worked for {company}` matches "worked for BMO Financial
  Group" on a BMO job and "worked for CIBC" on a CIBC job.
- Which row wins: the question's **first clause** (up to `?`, `(` or `.`) is matched first, and the
  phrase ending nearest the end of that clause wins. So "What is your gender? … gender identity in the
  next question" uses the gender row, and "What is your gender identity?" uses the identity row. A row
  with a Company beats a general row for that company.
- Blank Answer = ask me: a required question with no answer pauses the run and lists its options.
  For checkbox groups, `Yes` ticks every box; or list the labels to tick.

The `data/` folder is git-ignored: it contains your password and personal details.

## Run
```bash
behave                                   # first Pending job, else the first Failed one (retry)
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
| "Sign in with Apple / Google / OR / Sign in with email" chooser before the form (NVIDIA, Thomson Reuters) | **Sign in with email** is clicked; Apple/Google never |
| Questions render seconds after the page heading (Thomson Reuters) | an empty questions page is waited on (15s) before moving on |
| An added certification entry left empty makes Save fail ("Certification is required") | the empty entry is deleted |
| Options numbered `a.` / `b.` / `i.` (McKesson) | the marker is ignored when matching |
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
