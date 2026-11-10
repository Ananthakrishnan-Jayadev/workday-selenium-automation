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
├── README.md  behave.ini  requirements.txt  .env.example  .gitignore
├── config/config.yaml              # browser, timeouts, retries, behaviour, paths
├── data/                           # git-ignored: applicant_data.xlsx, resume, backups
├── docs/                           # PROJECT, DESIGN, PHASES, PHASE1, LOCATORS, page_dumps/
├── features/
│   ├── apply_job.feature
│   ├── environment.py              # hooks: config, Excel, driver, screenshots, result.json
│   └── steps/
│       ├── common_steps.py         # job/data, open posting, Apply Manually, complete "<page>", on "<page>"
│       └── auth_steps.py           # sign in
├── pages/
│   ├── base_page.py                # page detection, error-page recovery, Save and Continue, errors
│   ├── job_posting_page.py         # Apply → Apply Manually
│   ├── auth_page.py                # Create Account / Sign In form (one form, two modes)
│   ├── my_information_page.py
│   ├── my_experience_page.py       # resume, repeatable entries, languages, skills, websites
│   └── questions_page.py           # any questionnaire page, answered from the Questions sheet
├── locators/                       # (By, value) only: common, job_posting, auth, my_information,
│                                   # my_experience, questions
├── core/
│   ├── actions.py                  # click / type / focus with retries, popup closing, honeypot guard
│   ├── widgets.py                  # dropdown, prompt, date, upload, radio, checkbox(es), auto-detect
│   ├── text.py                     # normalize, best_match, strong_match, contains_words, closest_by_words
│   ├── answers.py                  # Questions-sheet rules
│   ├── excel_reader.py  models.py  session.py  reporter.py  waits.py  driver.py  config.py  logger.py
├── tools/make_template.py  tools/dump_page.py
└── reports/                        # git-ignored run output
```
`run.py` (batch) arrives with Phase 3.

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

### 3.3 Feature file (current)
```gherkin
  Scenario: Fill a Workday application
    Given the job to apply for is loaded
    And the applicant data is loaded from Excel
    When I open the job posting
    And I start the application manually
    And I sign in with the account for this company
    And I complete the "My Information" page
    And I complete the "My Experience" page
    And I complete the "Application Questions" page
    Then I should be on the "Voluntary Disclosures" page
```
`I complete the "<page>" page` is one generic step: it waits for the page's own form marker
(refreshing on Workday's error screen), fills it, pauses for you if anything failed, clicks Save and
Continue, and repeats if the same page continues (Primary → Secondary questions). A page the tenant
doesn't have is skipped.

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

### 4.3 Matching rules (`core/text.py`)
All comparisons use `normalize()` (lowercase; apostrophes, dashes, slashes and extra spaces ignored).
| Function | Meaning | Used for |
|---|---|---|
| `match_score` | 3 exact, 2 starts-with, 1 contains, 0 none; starts-with/contains are **whole words** (`No` ≠ `Not applicable`, `Male` ≠ `Female`) | everything below |
| `best_match` | exact > starts-with > contains; `min_score=2` (exact mode, question answers) drops "contains" | picking an option from a list |
| `strong_match` | equal, equal plus a bracketed note (`Python (Programming Language)`), or the bracketed abbreviation (`SQL` ~ `Structured Query Language (SQL)`) | skills; "already set" for multi-select |
| `contains_words` | whole-word containment (`Fluent` in `5 - Fluent`, not `Male` in `Female`) | "already set" for dropdowns |
| `closest_by_words` | most shared distinctive whole words; generic words (science, engineering, ...) don't count alone | Field of Study (`loose`) |

A leading list marker on an option (`a. `, `b) `, `ii. `, `3. `) is stripped before matching
(`_bare`), so McKesson's `b. No, I Don't Have A Disability (Canada)` starts with `No`.

### 4.4 Dropdowns: `select_dropdown(button, candidates)`
Workday single-selects are `button[aria-haspopup="listbox"]`, not `<select>`.
1. If the button already shows a matching value (starts-with or whole words), skip it, because
   re-selecting can re-render dependent fields.
2. Click; wait for the **last visible** `[role=listbox]` (popups are appended to `<body>`; the
   `selectedItemList` of prompt fields also has role=listbox and is excluded).
3. Pick with `best_match` over the fallbacks in order. Long lists: type to jump if not rendered.
4. Verify the button text. If the list won't open on click, try Enter / Arrow Down on the button.
5. No match → Escape, log every option, return None (the page decides whether to pause).

### 4.5 Prompt / multiselect: `select_prompt(field, input, candidates, multi, loose)`
Used for How did you hear, phone code, Field of Study, Skills.
- **Already set?** Single fields: matches the *first* candidate (a fallback in the field is
  replaced if something better is found). Multi (skills): `strong_match` only; near-misses left
  by earlier runs are removed once the right value is picked.
- **Search** (`_run_search`): focus the input (via JavaScript if covered by the selected pills),
  type the term, wait ~1.5s; press **Enter** only if typing alone produced nothing (on lists that
  filter as you type, Enter picks the highlighted option). Each poll checks, in order:
  1. the **field**: did Workday select something by itself? (Enter with a single match selects it
     and shows no list) → accept if it matches, else remove it;
  2. the **list**: only a list that contains a match for the term counts (Workday first shows
     'No Items.' or the full A-Z list), and it must be unchanged across two polls;
  3. "No matches found" only if it stays ~2.5s (it flashes up before the real results).
- **Pick**: `best_match`; if only a partial match, wait 1.2s for the exact option to load.
  Multi: options already selected are never clicked again (Workday rejects duplicate skills), and
  with no exact option nothing is picked. Among exact options, the one spelled as in Excel wins
  over a bracketed variant.
- **Exact** (question answers, `exact=True`): equal or starts-with only, also for an option Workday
  auto-selects on Enter.
- **Hierarchy**: `Category > Value`. If clicking an option opens a sub-list (radio rows), go down.
- **Loose** (Field of Study): if a candidate isn't listed, search its distinctive words one by one
  and take the closest option before moving to the next fallback.
- Every poll is traced at DEBUG; a search that finds nothing saves a screenshot + HTML.

### 4.6 Dates: `fill_date(field_css, month, year, day)`
Each part is a `role=spinbutton` input covered by a `dateSection<Part>-display` div. Click the display
div (focuses the input), Backspace over the old digits, type the new ones, Tab out, then verify each
part from `aria-valuetext` and retype any that didn't take. Month names are converted to `01`–`12`.

### 4.7 Repeatable sections (Work Experience, Education, Languages, Websites, Certifications)
Sections are found by their `<h4>` heading. Entries are found **page-wide** by their first field
(`formField-jobTitle`, `formField-schoolName`, `button[name=language]`); each entry's container is
the largest ancestor holding exactly one such field, tagged at runtime as `data-wdauto="work-1"`, so
its fields are addressed with plain CSS. Add is clicked until entry *i* exists; existing entries are
filled in place. "I currently work here" is set before the dates (it removes the end date).
Certifications are optional: one not in the company's list is skipped, and if its entry is still
empty, the panel's **Delete** button (`[role=group][aria-labelledby$="-panel"] button` "Delete") is
clicked, because an empty entry fails Save with "Certification is required" (Manulife, McKesson).

### 4.8 Questionnaire pages (`pages/questions_page.py`)
Questions are the top-level `formField-<hex id>` containers (ids differ per company, so they're
matched by **text**). For each: read the legend text and required flag, find the Questions rule,
auto-detect the control (`widgets.detect`: date / prompt / dropdown / textarea / radio / checkbox /
text) and fill it (`widgets.fill_auto`). Already-answered questions without a rule are left alone;
required unanswered ones are reported with their dropdown options. If a questions page shows no
questions at first, they are waited for (up to 15s): on Thomson Reuters they rendered late.

### 4.9 Waiting, errors and recovery
- `current_page()` returns `error` for Workday's "Something went wrong" screen, otherwise the page
  marker (`applyFlow*Page`), sign-in/create-account form, `sign_in_chooser` (the "Sign in with
  email" button some tenants show before the form; it is clicked), or progress-bar step name.
- After sign-in and before filling any page, the page's own form marker is awaited; on the error
  screen, or if the form never loads, the page is refreshed (up to twice).
- Save and Continue waits for the page (or the exact marker, for Primary → Secondary) to change;
  if it doesn't, the per-field `inputAlert` messages (else the `errorHeading` summary) are reported.

### 4.10 Pause for human (`Session.pause_for_human`)
Screenshot + HTML, the reason in the terminal, wait for Enter. `on_unknown: skip` logs and carries
on; `fail` (or no terminal) raises.

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
| PhoneType (`Mobile` · `Personal Primary` · `Home Cellular`), PhoneCountryCode, Phone | |
| HowDidYouHear | `LinkedIn` · `Social Network: Linkedin` · `Job Board/Social Media > LinkedIn` · `Social Media` |
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
| Name | Number | ExpiryDay | ExpiryMonth | ExpiryYear |

### Fallback columns (all sheets)
Fallbacks have their own columns, tried left to right: Profile `Value, Fallback 1, Fallback 2`;
Skills `Skill, Fallback 1, Fallback 2`; Questions `Answer, Fallback 1..3`; Education
`Degree / FieldOfStudy` + `<Base> Fallback N`; Languages `Proficiency` + `Proficiency Fallback N`
(`excel_reader._with_fallbacks`). A `;` inside a cell still separates values.

### `Questions` (rule table)
Rule choice (`core/answers.find_rule`): match the question's first clause (text before `?`, `(`, `.`
or `:`); among matches, company-specific first, then the phrase ending latest in that clause, then the
longer phrase, then sheet order. If nothing matches the first clause, the whole text is used (sheet
order). `{company}` in Keywords is replaced by the job's company. Answers are applied in **exact**
mode (equal or starts-with only), so each company's wording goes in the fallback columns.

Original column notes:
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

This replaces the hard-coded TD/EY rules in the extension. CIBC puts its diversity questions on the
Application Questions page, so those rows leave **Page** blank. A blank Answer means "ask me":
the run pauses on that required question and lists its options.

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
