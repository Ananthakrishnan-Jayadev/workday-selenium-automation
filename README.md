# Workday Auto-Apply (Python · Selenium · behave)

Fills in Workday job applications from an Excel workbook, from the job posting URL through to the
**Review** page, then stops so you can check the application and click **Submit** yourself.

```
job URL → Apply Manually → sign in → My Information → My Experience → Application Questions
        → Voluntary Disclosures → Self Identify → REVIEW (stops: you submit) → status written to Excel
```

**Status: V1 (2026-11).** Live-tested to Review on 11 Workday sites: CIBC, BMO, TD, Citi, RBC,
Accenture, Manulife, McKesson, Canadian Tire, NVIDIA and Thomson Reuters. A new company mostly needs
new rows in the Questions sheet (its own question wording and option labels). The script pauses on
anything it can't answer and lists the options, so you can add them.

- **It never clicks Submit.** That is always your decision.
- It doesn't create accounts, solve CAPTCHAs or get around verification.
- One job at a time, in a visible browser.

---

## Contents
1. [Quick start](#quick-start)
2. [Setup](#setup) (Linux, Windows)
3. [Your files: one folder per application](#your-files-one-folder-per-application)
4. [The workbook](#the-workbook)
5. [How answers are matched](#how-answers-are-matched)
6. [Running](#running)
7. [Troubleshooting](#troubleshooting)
8. [Things Workday does that the code handles](#things-workday-does-that-the-code-handles)
9. [Project layout and docs](#project-layout-and-docs)
10. [Next](#next)

---

## Quick start
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python tools/make_template.py            # creates data/applicant_data.xlsx (won't overwrite)
```
1. Open **`examples/applicant_data.example.xlsx`**. It is a reference workbook with every sheet and
   column filled in for a made-up applicant, plus a **Guide** sheet explaining each one.
2. Fill in **`data/applicant_data.xlsx`** the same way, with your own details. At minimum you need
   Jobs, Accounts, Profile, WorkExperience and Education.
3. Put each job's resume (and cover letter) in its own folder:
   `<ApplicationsFolder>/application_01/` ([details](#your-files-one-folder-per-application)).
4. Run `behave -D slow_mo_ms=200`, watch it fill the application, fix anything it asks about, and
   submit on the Review page.

---

## Setup

### Linux
```bash
python3 -m venv .venv
source .venv/bin/activate              # in each new terminal
pip install -r requirements.txt
python tools/make_template.py
```
- `activate` must be *sourced*, not executed (`.venv/bin/activate` on its own gives "Permission
  denied"). Without activating, call `.venv/bin/behave` directly. Don't use `sudo`.
- Tested on Ubuntu with Python 3.14, Selenium 4.52 and behave 1.3.3. Chrome/Chromium or Firefox must
  be installed.
- A snap-packaged browser (Ubuntu's default Chromium) uses the snap's own driver automatically.
  Otherwise Selenium Manager downloads a driver. To override, set `browser.driver_path` /
  `browser.binary` in `config/config.yaml`.

### Windows
In PowerShell:
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1             # in each new terminal
pip install -r requirements.txt
python tools\make_template.py
behave -D slow_mo_ms=200
```
- If PowerShell won't run `Activate.ps1`, allow local scripts once with
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. Or skip activating and run
  `.venv\Scripts\behave`. In cmd.exe, the activate script is `.venv\Scripts\activate.bat`.
- Install **Google Chrome** (or Firefox). Selenium Manager downloads the matching driver.
- Workbook paths are per machine: `ApplicationsFolder` must be a Windows path, e.g.
  `C:\Users\you\applications`.
- The console is switched to UTF-8 automatically. `run.log` is always UTF-8.

### Passwords
Put them in the Accounts sheet, or keep them out of the workbook: copy `.env.example` to `.env`, add
`CIBC_PASSWORD=...`, and write `ENV:CIBC_PASSWORD` in the Password cell. Passwords are never printed;
logs show `********`.

---

## Your files: one folder per application
Each job gets its own folder, so each application can have its own resume and cover letter. The
**file names are the same in every folder** and are set once in the Profile sheet. Nothing personal
is in the code.

```
ApplicationsFolder (Profile)         /home/you/applications
├─ application_01/                   ← Jobs sheet, Folder column
│   ├─ resume.pdf                    ← Profile: ResumeFileName
│   └─ cover_letter.pdf              ← Profile: CoverLetterFileName (optional)
├─ application_02/
│   └─ resume.pdf                    (no cover letter: applies without one)
└─ ...
```

| JobURL | Folder | Company | Status |
|---|---|---|---|
| https://…/job/A | application_01 | CIBC | Pending |
| https://…/job/B | application_02 | RBC | Pending |

- **Checked before the browser opens.** Any of these stops the run with a message that lists what is
  actually in the folder:
  - a blank Folder
  - a missing folder
  - a missing resume
  - a file over 5 MB

  The run never falls back to a different resume.
- **No cover letter** in the folder: the application goes ahead without one, with a warning in the log.
- File names match **regardless of upper/lower case**. Workday shows the file's real name.
- **Same-name files are replaced.** If the application already lists a file with that name (pre-filled
  from an earlier application), it is deleted and this job's file is uploaded.
- The Folder cell can also hold a full path. `-D folder=<name>` sets it for a single run.
- `result.json` records which files were uploaded.
- **Linux, snap Chromium:** keep `ApplicationsFolder` inside your home directory and outside hidden
  folders, or the browser can't read the files.

---

## The workbook
`data/applicant_data.xlsx` (git-ignored). **See `examples/applicant_data.example.xlsx` for every field
filled in.** Regenerate it with `python tools/make_example.py`.

| Sheet | One row per | What goes in it |
|---|---|---|
| **Jobs** | job | `JobURL`, `Folder`, `Company` (blank = taken from the URL), `Status`, `LastRun`, `Notes`. `behave` runs the first `Pending` row, else the first `Failed` one. |
| **Accounts** | company | An **existing** Workday account: `Company`, `TenantHost`, `Email`, `Password` (or `ENV:NAME`). Matched on Company, then on the URL host. |
| **Profile** | field | Name, address, phone (type, country code, number, extension), HowDidYouHear, PreviouslyWorkedHere, LinkedIn, Website(s), `ApplicationsFolder`, `ResumeFileName`, `CoverLetterFileName` |
| **WorkExperience** | job held | Title, company, location, `CurrentlyWorkHere` (Yes = no end date), start/end month name + year, description |
| **Education** | school | School, Degree (+ fallbacks), FieldOfStudy (+ fallbacks), GPA, start/end year |
| **Languages** | language | `Proficiency` (+ fallbacks) for every proficiency dropdown; `Reading` / `Writing` / `Speaking` / `Overall` override one dropdown |
| **Skills** | skill | Workday's exact skill name (+ fallbacks). A skill Workday doesn't list is skipped. |
| **Certifications** | certificate | Name, number, expiry day/month/year (all optional). A certificate the company doesn't list is skipped, and the empty entry is deleted. |
| **Questions** | rule | Keywords in the question → the answer (+ fallbacks), optionally limited to one company or page. Also covers the terms checkbox. |

### Fallback columns
Companies word the same option differently, so most values have fallbacks. They are tried left to
right, and the first option the form offers wins:

| Sheet | Columns | Example |
|---|---|---|
| Profile | `Value`, `Fallback 1`, `Fallback 2` | PhoneType: `Mobile` · `Personal Primary` · `Home Cellular` |
| Skills | `Skill`, `Fallback 1`, `Fallback 2` | `SQL` · `PostgreSQL` · `MySQL` |
| Questions | `Answer`, `Fallback 1..3` | `No` · `No, I don't have a disability` · `None` |
| Education | `Degree` / `FieldOfStudy` + `<Base> Fallback 1..3` | `Master's Degree` · `Masters` |
| Languages | `Proficiency`, `Proficiency Fallback 1..2` | `Fluent` · `Advanced` |

A `;` inside one cell also separates values, and a later run swaps a fallback for your first choice
if that becomes available. **When nothing matches, the log lists every option the company offered.**
Copy the right one into the next fallback column.

### Questions sheet
`Keywords | Answer | Fallback 1-3 | Company | Page | Notes`

| Keywords | Means |
|---|---|
| `authorized to work; eligible to work` | any of these phrases (whole words) |
| `relative; family member + td` | (relative OR family member) AND td |
| `worked for {company}` | `{company}` is the job's company: "worked for BMO" on a BMO job |

- **Which row wins:** the question's **first clause** (text before `?`, `(`, `.` or `:`) is matched
  first, and the phrase ending nearest the end of that clause wins. So "What is your gender? …gender
  identity…" uses the gender row, and "What is your gender identity?" uses the identity row. A row with
  a **Company** beats a general row.
- **Page** (`Application`, `Disclosure`, `SelfIdentify`, or blank for any) limits where a row applies.
- **Answers:**
  - Dropdowns and radio buttons: the option label.
  - Text boxes: the answer is typed in.
  - Dates: `today`, `today+N`, `today+Nw`, `dd/mm/yyyy` or `yyyy-mm-dd`.
  - Checkbox groups: `Yes` ticks all, or list the labels to tick.
- **Blank Answer = ask me.** The run pauses on that question and lists its options.
- **A new wording of a known question:** add its phrase to that row's Keywords, e.g.
  `employer support to obtain` on the sponsorship row.

---

## How answers are matched
- **Normalised:** case, apostrophes, dashes and slashes are ignored. `Category > Value` picks from
  nested lists, e.g. `Job Board/Social Media > LinkedIn`.
- **Whole words only:** `No` matches `No (Canada)` but never `Not applicable` or `Do not wish to
  declare`, and `Male` never matches `Female`.
- **List markers are ignored:** `No` matches `b. No, I Don't Have A Disability (Canada)`.
- **Profile / My Experience values:** an option that equals the value, starts with it
  (`Canada` → `Canada (+1)`) or contains it (`Fluent` → `5 - Fluent`).
- **Question answers are strict:** the option must equal the answer or start with it
  (`Yes` → `Yes - Newcomer`). `Man` never picks `Trans Man`.
- **Field of Study** takes the closest option by whole words before trying a fallback
  (`Artificial Intelligence` → `Artificial Intelligence and Robotics`). Generic words such as
  *science* don't count on their own.
- **Skills** need Workday's exact name, though a bracketed part is fine either way: `Python` →
  `Python (Programming Language)`, `SQL` → `Structured Query Language (SQL)`. An exact spelling is
  preferred, and `SQL` never picks `SQL Assistant`.

---

## Running
```bash
behave -D slow_mo_ms=200                 # the first Pending job (else the first Failed one); slowed down to watch
behave -D row=5                          # a specific Jobs sheet row
behave -D url="https://<company>.wd3.myworkdayjobs.com/.../job/..." -D folder=application_07
behave -D browser=firefox
behave -D on_unknown=skip                # log problems instead of pausing
```
Use a visible browser: headless sign-in didn't complete on CIBC.

**When it needs you**, it prints `ACTION NEEDED IN THE BROWSER` with the reason: a field it couldn't
fill, validation errors after Save and Continue, or required questions it couldn't answer (with their
options). Fix it in the browser, then press Enter in the terminal.

**On the Review page the run stops.** Check everything, click Submit yourself if you're happy, then
type the outcome in the terminal: `s` submitted, `k` skipped, `f` failed, `r` review later. It is
written to the Jobs sheet (Status, LastRun, Notes) and to `result.json`. A guard refuses any button
labelled Submit, and any button on the Review page.

**Re-running is safe.** Values that are already correct are left alone, existing entries are filled
in place (no duplicates), and this job's resume replaces a same-named file instead of being added
twice.

**Output:** `reports/<timestamp>_<company>/` holds `run.log` (full DEBUG detail), a screenshot and the
page HTML at each step and on every failure, and `result.json`.

---

## Troubleshooting
| You see | Do this |
|---|---|
| `CANNOT START … No application folder for row N` | Fill in that row's Folder cell, or pass `-D folder=` |
| `CANNOT START … No resume named '…'` | The message lists the folder's files: fix the name in the folder or in `ResumeFileName` |
| `CANNOT START … ApplicationsFolder is empty / does not exist` | Set it in the Profile sheet (an absolute path) |
| `CANNOT START … No job to run` | Add a row with Status `Pending`, or use `-D row=` / `-D url=` |
| Upload fails on Linux with snap Chromium | Move `ApplicationsFolder` under your home directory, outside hidden folders |
| "No row in the Accounts sheet for company …" | Add the company to Accounts (the account must already exist on that Workday site) |
| `… not found. Options there: [...]` / `none of [...] found. Available: [...]` | Copy the option you want into the next fallback column |
| "could not write the Jobs sheet" | Close the workbook in Excel/LibreOffice; the status is still in `result.json` |
| Something else on a page | Capture it ([docs/page_dumps/README.md](docs/page_dumps/README.md)) and check `run.log` |

---

## Things Workday does that the code handles
| Behaviour | Handling |
|---|---|
| "Something went wrong. Please refresh the page" after sign-in | detected; page refreshed (up to twice) |
| "Sign in with Apple / Google / email" choice before the form (NVIDIA, Thomson Reuters) | **Sign in with email** is clicked; Apple/Google never |
| Sign In button covered by an invisible `click_filter` div | the div is clicked |
| Questions appear seconds after the page heading (Thomson Reuters) | an empty questions page is waited on (15s) |
| An empty certification entry blocks Save ("Certification is required") | the empty entry is deleted |
| Options numbered `a.` / `b.` / `i.` (McKesson) | the marker is ignored when matching |
| Dates: each month/year box is covered by a display div | the display div is clicked, digits typed, value verified |
| Search lists show "No Items." / an A-Z list / "No matches found" before the real results | only a list containing a match counts; "No matches" only after ~2.5s |
| Enter with a single match selects it without showing a list | the field is checked first |
| A dropdown that won't open on click | mouse press, then Space / Enter / Alt+Down / Down |
| A list left open covers the next field | closed with Escape, else by clicking outside |
| Selected skills cover the search box | the box is focused directly |
| Hidden `beecatcher` input (bot trap) | never touched |

---

## Project layout and docs
```
features/   apply_job.feature, environment.py (hooks), steps/ (common_steps, auth_steps)
pages/      base_page, job_posting_page, auth_page, my_information_page, my_experience_page,
            questions_page (Application Questions, Voluntary Disclosures, Self Identify)
locators/   common, job_posting, auth, my_information, my_experience, questions
core/       actions (click/type/focus), widgets (dropdown, prompt, date, upload, checkbox, auto-detect),
            text (matching), answers (Questions rules), documents (per-job resume / cover letter),
            excel_reader / excel_writer, models, session (pause for you), reporter, waits, driver,
            config, logger
tools/      make_template.py (empty workbook), make_example.py (filled reference), dump_page.py
examples/   applicant_data.example.xlsx (fictional, every field filled)
config/     config.yaml (browser, timeouts, behaviour; any value can be overridden with -D)
docs/       design docs + page_dumps/ (captured HTML is git-ignored)
data/       your workbook (git-ignored)
reports/    run output (git-ignored)
```

| Doc | What's in it |
|---|---|
| [docs/PROJECT.md](docs/PROJECT.md) | Goals, scope, non-goals, risks |
| [docs/DESIGN.md](docs/DESIGN.md) | Architecture, flow, how Workday's controls are handled, Excel schema, config |
| [docs/PHASES.md](docs/PHASES.md) | Build phases, status and acceptance checks |
| [docs/PHASE1.md](docs/PHASE1.md) | Detailed Phase 1 plan |
| [docs/LOCATORS.md](docs/LOCATORS.md) | Every Workday locator, where it was verified, what's still unverified |
| [docs/page_dumps/README.md](docs/page_dumps/README.md) | How to capture a Workday page (DevTools console snippets) |

Git-ignored because they hold personal data: `data/`, `applications/`, `.env`, `reports/` and
`docs/page_dumps/*.html`.

---

## Next
- `run.py` batch runner: every Pending row, one browser per job, status written back.
- Headless runs that still let you review: fill headless, then review in a visible browser or through
  Chrome's remote debugging.
- Account creation and email verification, and the "Use My Last Application" path.
