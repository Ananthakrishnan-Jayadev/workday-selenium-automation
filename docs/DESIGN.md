# Design

## 1. Architecture (layers)

```
 features/*.feature          Gherkin: what the user does, in plain language
        │
 features/steps/*.py         Step definitions: glue only (get data → call page object)
        │
 pages/*.py                  Page Objects: one class per Workday page, business actions
        │                    e.g. MyInformationPage.fill(profile)
        │
 core/widgets.py             Workday-specific controls: dropdown, prompt/multiselect,
        │                    date, radio, checkbox, repeatable section, file upload
        │
 core/actions.py             Generic, robust Selenium actions: safe_click, safe_type,
        │                    scroll_into_view, retry, dismiss_overlays
        │
 core/waits.py, driver.py    WebDriverWait wrappers, driver factory
        │
 locators/*.py               Locators only. No logic. One module per page + common.py

 core/excel_reader.py  ──►  core/models.py (dataclasses: Profile, Job, Account, WorkEntry, ...)
 core/config.py, core/logger.py, core/human.py (pause-for-human)
```

**Rules**

- Steps never touch Selenium directly. Pages never read Excel directly (they get dataclasses).
- Pages call `widgets` and `actions` and never call `driver.find_element(...).click()` themselves.
- Locators are always passed as `(By, value)` tuples, never as found `WebElement`s, so every
  retry looks the element up again. This makes stale-element errors go away.
- No `time.sleep()` outside `core/` (and inside `core/` only short "settle" pauses after a known
  Workday re-render).

## 2. Folder structure

```
workday-selenium/
├── README.md
├── behave.ini                      # --no-capture so pause prompts show; format, paths
├── requirements.txt
├── config/
│   └── config.yaml                 # browser, timeouts, retries, paths, behaviour flags
├── .env.example                    # optional ENV: passwords
├── data/                           # git-ignored
│   └── applicant_data.xlsx
├── docs/
│   ├── PROJECT.md  DESIGN.md  PHASES.md  LOCATORS.md
│   └── page_dumps/                 # saved HTML of each Workday page (git-ignored)
├── features/
│   ├── apply_job.feature
│   ├── environment.py              # hooks
│   └── steps/
│       ├── common_steps.py         # open URL, save and continue, page assertions
│       ├── auth_steps.py
│       ├── my_information_steps.py
│       ├── my_experience_steps.py
│       ├── questions_steps.py
│       ├── disclosures_steps.py
│       └── review_steps.py
├── pages/
│   ├── base_page.py                # page detection, save_and_continue, error banner check
│   ├── job_posting_page.py         # Apply → Apply Manually popup
│   ├── sign_in_page.py
│   ├── my_information_page.py
│   ├── my_experience_page.py
│   ├── application_questions_page.py
│   ├── voluntary_disclosures_page.py
│   ├── self_identify_page.py
│   └── review_page.py
├── locators/
│   ├── common.py                   # page markers, nav buttons, listbox/option, popups, errors
│   ├── job_posting.py  sign_in.py  my_information.py  my_experience.py
│   ├── questions.py  disclosures.py  self_identify.py  review.py
├── core/
│   ├── driver.py                   # DriverFactory (chrome/firefox, options)
│   ├── waits.py
│   ├── actions.py                  # safe_click, safe_type, scroll, retry decorator
│   ├── widgets.py                  # Workday controls
│   ├── text.py                     # normalize(), best_match()
│   ├── excel_reader.py             # read workbook → models
│   ├── excel_writer.py             # write Status back to Jobs sheet
│   ├── models.py
│   ├── answers.py                  # question → answer rule engine
│   ├── human.py                    # pause_for_human(reason)
│   ├── config.py  logger.py
├── tools/
│   ├── make_template.py            # generates an empty applicant_data.xlsx with all sheets
│   └── dump_page.py                # saves page HTML + screenshot for locator work
├── run.py                          # batch runner over the Jobs sheet
└── reports/                        # git-ignored: logs/, screenshots/, page_dumps/, run JSON
```

## 3. Execution flow

### 3.1 Single job
```
behave -D url="https://cibc.wd3.myworkdayjobs.com/.../job/..." 
```

### 3.2 Batch (`python run.py`)
`run.py` reads the Jobs sheet and runs behave **once per Pending row** as a subprocess with
`-D row=<n>`. Each job therefore gets its own browser, its own log and report, and a crash in one
job can't take down the rest. After each job, `run.py` writes `Status`, `LastRun` and `Notes` back
to the Jobs sheet.

### 3.3 Feature file (shape)
```gherkin
Feature: Apply to a Workday job

  Scenario: Fill a Workday application up to Review
    Given the job to apply for is loaded
    And the applicant data is loaded from Excel
    When I open the job posting
    And I start the application manually
    And I sign in with the account for this company
    And I complete the "My Information" page
    And I complete the "My Experience" page
    And I complete the "Application Questions" pages
    And I complete the "Voluntary Disclosures" page
    And I complete the "Self Identify" page
    Then I should be on the "Review" page
    And I wait for the user to review and submit
```

**Tenant tolerance.** Each "complete the X page" step first **detects the current page** by its
marker. If the tenant does not have that page, the step logs "skipped" and passes. The questions
step loops while a questions page is showing, which handles tenants that have both Primary and
Secondary question pages. Any page the script doesn't recognise triggers a pause for you.

### 3.4 Hooks (`environment.py`)
| Hook | Does |
|------|------|
| `before_all` | load config, set up logging, load workbook → `context.data` |
| `before_scenario` | resolve the job (`-D url` or `-D row`), create driver |
| `after_step` (failed) | screenshot + page HTML to `reports/`, log the URL and current page |
| `after_scenario` | record result for `run.py`; quit driver unless `keep_browser_open` or Review reached |

On reaching Review, the browser is **left open** and the final step blocks on
`input("Review the application in the browser, submit it, then press: [s]ubmitted / [k]skipped / [f]ailed")`.
Your answer becomes the job's status.

## 4. Robustness strategy (the Workday-specific part)

### 4.1 `safe_click(locator)`
```
for attempt in 1..N (config: click_retries, default 4):
    el = wait.until(presence_of_element_located(locator))
    scroll_into_view(el)                 # JS scrollIntoView({block:'center'})
    wait.until(element_to_be_clickable(locator))
    try:     el.click(); return
    except ElementClickInterceptedException:  dismiss_overlays(); 
    except StaleElementReferenceException:    pass            # re-find next loop
    except ElementNotInteractableException:   scroll + small settle
    backoff (0.3s, 0.6s, 1.2s ...)
fallback 1: ActionChains(move_to_element).click()
fallback 2: driver.execute_script("arguments[0].click()", el)   # logged as a warning
raise ClickFailed(locator, last_error) → screenshot
```
`dismiss_overlays()` presses Escape and closes known Workday popups (cookie banner, "wd-popup"
close button, toast) if visible. It never clicks anything that could submit.

### 4.2 `safe_type(locator, value, commit=True)`
1. `safe_click` the input to focus it.
2. Clear with **Ctrl+A, Delete**, because `element.clear()` doesn't fire React events, so Workday
   can keep the old value.
3. `send_keys(value)` with real keystrokes, which fire the input and change events Workday listens to.
4. Read back `get_attribute("value")`. If it doesn't match, retry once and then report.
5. If `commit`, press Tab (blur) so Workday commits the value. Your extension found that values
   which were never blurred get lost on Save and Continue.

### 4.3 Dropdowns: `select_dropdown(container_locator, candidates)`
Workday single-selects are `button[aria-haspopup="listbox"]`, not `<select>`.
1. `safe_click` the button, then wait for a **visible** `[role="listbox"]`. Workday appends popups to
   the end of the body, so the code uses the *last visible* listbox.
2. Collect `[role="option"]` labels (`data-automation-label` or text).
3. Pick the best match with `best_match(candidates, options)`: exact → starts-with → contains,
   case/punctuation-insensitive, trying each fallback candidate in order (e.g. a list of degree names).
4. Scroll the option into view inside the listbox and click it.
5. Verify the button text now shows the choice. If it doesn't, try once more using the keyboard
   (type the first letters, then Enter).
6. If nothing matches, press Escape to close, log all available options to help fill in Excel,
   and return `False`. The caller decides whether to pause.

### 4.4 Prompt / multiselect: `select_prompt(container_locator, candidates)`
Used for "How did you hear", Skills, Field of Study, School (some tenants), and multi-select
disclosure questions.
1. Click the `searchBox` or `multiselectInputContainer input`, type the candidate, press **Enter**.
   On Workday, typing alone doesn't run the search.
2. Wait until `promptOption` results appear **or** `promptTitle` says "No matches found".
3. Pick the best match, excluding options already in `selectedItemList`, and click its
   checkbox (`checkboxPanel`) or the option itself.
4. Verify it shows up as a selected pill. Some prompts are hierarchical (e.g. "Job Board → LinkedIn"):
   if the clicked option opens a sub-list, repeat the match on the sub-list.
5. If there are no matches, clear the box and try the next candidate.

### 4.5 Dates: `fill_date(container, month, year, day=None)`
Inputs are `dateSectionMonth-input`, `dateSectionDay-input` and `dateSectionYear-input`. The code
types month → (day) → year without blurring between them, blurs once at the end, then re-reads
the month, because Workday sometimes clears it when the year is entered. If it was cleared, the
month is typed again. Month names in Excel ("January") are converted to "01".

### 4.6 Repeatable sections (Work Experience, Education, Languages, Certifications)
Workday numbers entry containers `workExperience-1`, `education-2`, and so on. For entry *i*:
click the section's `Add` / `Add Another` button until container *i* exists, then look up
fields **inside that container only**. If the tenant doesn't number its containers, the fallback
is the last occurrence of each `formField-*` (as in the extension's `getEntryScope`).
**Pre-filled entries:** if containers already exist (for example from a resume parse), fill them
in place rather than adding duplicates.

### 4.7 Waiting for Workday
- Page change: after Save and Continue, wait until the old page marker is **stale** and a new
  `applyFlow*Page` marker is present.
- Lazy sections: wait for the section container before looking up its fields.
- Loading: wait for spinners/masks to disappear (locator to be confirmed from a page dump).
- After Save and Continue, check for an error banner or field errors. If any, screenshot, log the
  messages and pause for you to fix them on screen, then continue.

### 4.8 Pause for human (`core/human.py`)
`pause_for_human(reason)` takes a screenshot, prints the reason and waits for Enter in the terminal.
It's used for: unknown required question, no dropdown match, validation error after save, CAPTCHA
or verification screen detected, unexpected page. Config `on_unknown: pause | skip | fail`
controls whether it pauses (default `pause`).

## 5. Excel workbook (`data/applicant_data.xlsx`)

`tools/make_template.py` generates it with headers and example rows. Lists inside a cell are
separated by `;` and act as fallbacks tried in order.

### `Jobs`
| JobURL | Company | Status | LastRun | Notes |
|---|---|---|---|---|
| https://cibc.wd3.myworkdayjobs.com/... | CIBC | Pending | | |

Status values: `Pending`, `ReadyForReview`, `Submitted`, `Skipped`, `Failed`. Batch mode runs `Pending` only.

### `Accounts`
| Company | TenantHost (optional) | Email | Password |
|---|---|---|---|
| CIBC | cibc.wd3.myworkdayjobs.com | me@example.com | ******** or `ENV:CIBC_PW` |

Lookup: match the job's `Company` first, then the URL host against `TenantHost`. If no account is
found, the job is marked `Failed: no account` (V1 does not create accounts).

### `Profile` (key/value)
| Field | Value |
|---|---|
| FirstName, LastName, PreferredName | |
| Country, AddressLine1, City, Province, PostalCode | |
| PhoneType (`Mobile`), PhoneCountryCode, Phone | |
| HowDidYouHear | `LinkedIn;Job Board;Other` |
| PreviouslyWorkedHere | `No` |
| LinkedIn, Website | |
| ResumePath | `/home/.../resume.pdf` |

### `WorkExperience`
| JobTitle | Company | Location | CurrentlyWorkHere | StartMonth | StartYear | EndMonth | EndYear | Description |

### `Education`
| School | Degree (`;` fallbacks) | FieldOfStudy (`;` fallbacks) | GPA | StartYear | EndYear |

### `Languages`
| Language | Proficiency (`;` fallbacks) | Reading | Writing | Speaking | Overall |  (blank = use Proficiency)

### `Skills`
| Skill |

### `Certifications` (optional)
| Name | Number | ExpiryMonth | ExpiryYear |

### `Questions` (rule table, top-to-bottom, first match wins)
| Keywords | Answer | Company | Page | Notes |
|---|---|---|---|---|
| `authorized to work;legally entitled;eligible to work` | Yes | | Application | |
| `sponsorship` | No | | Application | |
| `relative;family member` + `TD` | No | TD | Application | company-scoped |
| `18 years;age of majority` | Yes | | Application | |
| `gender` | Man | | Disclosure | |
| `disability` | No, I do not have a disability | | SelfIdentify | |

- **Keywords:** `;` means *any of*. `+` means *all of* (e.g. `relative;family member + TD`).
  Matching is done on normalized question text.
- **Company:** blank applies to every company. A company-scoped rule takes priority over a blank one.
- **Page:** limits where the rule applies (`Application`, `Disclosure`, `SelfIdentify`, or blank for any).
- **Answer** must be the option label as Workday shows it (best-match is tolerant of case and
  punctuation). For checkbox groups, `;` selects several options. For text inputs, the value is typed.

This replaces the hard-coded TD/EY rules in the extension.

## 6. Configuration (`config/config.yaml`)
```yaml
browser: chrome            # chrome | firefox
headless: false
user_data_dir: null        # optional persistent profile
timeouts: { implicit: 0, default: 15, page_change: 30, prompt_results: 5 }
retries:  { click: 4, type: 2 }
behaviour:
  on_unknown: pause        # pause | skip | fail
  stop_at: review          # hard stop; there is no submit option in V1
  keep_browser_open_on_failure: true
  slow_mo_ms: 0            # optional delay between actions for watching/debugging
paths:
  workbook: data/applicant_data.xlsx
  reports: reports
```

## 7. Logging and reports
- `reports/logs/<timestamp>_<company>.log`: every action, locator and value (passwords masked).
- `reports/screenshots/`: on failure, on every pause, and one per page after filling.
- `reports/page_dumps/`: HTML of each page (when `dump_pages: true`). This is how locators get
  maintained as Workday changes.
- `reports/run_<timestamp>.json`: per-job summary (pages completed, fields skipped, unknown questions).
  Unknown questions are also appended to the log so they can be added to the Questions sheet.

## 8. Dependencies
`selenium>=4.20` (includes Selenium Manager), `behave>=1.2.7`, `openpyxl`, `pyyaml`, `python-dotenv`.
