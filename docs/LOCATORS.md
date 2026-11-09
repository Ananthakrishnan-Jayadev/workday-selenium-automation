# Locator Inventory

Sources: **EXT** = `workday_extension/content.js` (used live, filling real pages),
**AGW** = `agentic_workday/app` (captured from live pages, or marked best-effort there).

Status: ✅ used successfully in a working tool · ⚠️ best-effort / unverified · ❓ needed, not known yet.

Convention: CSS on `data-automation-id` (aid) wherever possible, because it's stable across tenants.
XPath only where matching on visible text is unavoidable (e.g. a question's legend text,
a button with no aid).

## Page markers (current page detection)
| Page | Marker aid | Status |
|---|---|---|
| My Information | `applyFlowMyInfoPage` | ✅ EXT |
| My Experience | `applyFlowMyExpPage` | ✅ EXT |
| Application Questions | `applyFlowPrimaryQuestionsPage`, `applyFlowSecondaryQuestionsPage` | ✅ / ⚠️ |
| Voluntary Disclosures | `applyFlowVoluntaryDisclosuresPage` | ✅ EXT |
| Self Identify | `selfIdentificationPage` (?) | ⚠️ AGW |
| Review | `applyFlowReviewPage` / `summaryView` / `reviewPanel` | ⚠️ AGW |

## Navigation and common
| Element | Locator | Status |
|---|---|---|
| Save and Continue | `pageFooterNextButton` (CIBC ✅ DUMP), fallback `bottom-navigation-next-button` | ✅ |
| Back | `bottom-navigation-previous-button` (?) | ❓ |
| Submit (Review), only detected, never clicked | ❓ | ❓ |
| Dropdown trigger | `button[aria-haspopup="listbox"]` inside `formField-*` | ✅ EXT |
| Open listbox / options | `ul[role="listbox"]` appended at the end of `<body>` → `li[role="option"]`, label = text (first option is "Select One"); button gets `aria-expanded="true"` | ✅ DUMP (05b) |
| Prompt input | `[data-automation-id="searchBox"]`, `multiselectInputContainer input` | ✅ EXT |
| Prompt options | `[data-automation-id="promptOption"]` (exclude inside `selectedItemList` / `selectedItem`) | ✅ EXT |
| No matches | `[data-automation-id="promptTitle"]` text "No matches found" | ✅ EXT |
| Prompt checkbox | `input[type=checkbox][data-automation-id="checkboxPanel"]` | ✅ EXT |
| Date parts | `dateSectionMonth-input`, `dateSectionDay-input`, `dateSectionYear-input` | ✅ EXT |
| Field errors | `p[data-automation-id="inputAlert"]` under each field, text "Error: The field X is required…"; field gets `aria-invalid="true"` | ✅ DUMP (05d) |
| Error summary | `errorHeading` inside an "Errors Found" box at the top | ✅ DUMP (05d) |
| Loading spinner / mask | ❓ | ❓ |
| Popup frame | `wd-popup-frame` | ⚠️ AGW |

> **DUMP** = confirmed in `docs/page_dumps/` (captured 2026-11-08). Pages 01/02 were captured on
> Workday's own careers site (workday.wd5); pages 03–05 are CIBC.

## Apply flow shell (all apply pages)
| Element | Locator | Status |
|---|---|---|
| Apply-flow wrapper | `[data-automation-id="applyFlowPage"]` | ✅ DUMP |
| Job title heading | `jobTitleHeading` | ✅ DUMP |
| Progress bar / active step | `progressBar` → `li[data-automation-id="progressBarActiveStep"]`, 2nd `label` = step name | ✅ DUMP |
| Back to job posting | `backToJobPosting` | ✅ DUMP |
| Honeypot. **Never fill.** | `input[data-automation-id="beecatcher"]` (name="website", "for robots only") | ✅ DUMP |

**Page detection:** use the page marker (`applyFlowMyInfoPage`, …) first, with the active progress
step's name as a fallback. Steps on CIBC: *Create Account/Sign In → My Information → My Experience →
Application Questions → Voluntary Disclosures → Review*. Once signed in, the account step disappears,
so the numbering becomes "1 of 5". CIBC has **no separate Self Identify step**.

## Job posting → start
| Element | Locator | Status |
|---|---|---|
| Posting page marker | `jobPostingPage`, header `jobPostingHeader` | ✅ DUMP |
| Apply button | `a[data-automation-id="adventureButton"]` (an `<a role=button>`) | ✅ DUMP |
| Popup | `wd-popup-glass` → `[data-automation-id="wd-popup-frame"][role=dialog]` (aria-label "Start Your Application") | ✅ DUMP |
| Popup close | `wd-popup-frame [data-automation-id="closeButton"]` | ✅ DUMP |
| Apply Manually | `a[data-automation-id="applyManually"]` | ✅ DUMP |
| Others (not used) | `autofillWithResume`, `useMyLastApplication`, `applyWithSeek`, iframe `applyWithLinkedIn` | ✅ DUMP |
| Header Sign In (not used) | `utilityButtonSignIn` | ✅ DUMP |
| Cookie banner | none in the dumps; `dismiss_overlays` handles one if it appears | — |

## Create Account / Sign In (same form, two modes)
| Element | Locator | Status |
|---|---|---|
| Form container | `signInContent` → `form[data-automation-id="signInFormo"]` (sic, "Formo") | ✅ DUMP |
| Mode title | `h3#authViewTitle`: text "Create Account" or "Sign In" | ✅ DUMP |
| Switch to Sign In | `button[data-automation-id="signInLink"]` (on Create Account) | ✅ DUMP |
| Switch to Create Account | `button[data-automation-id="createAccountLink"]` (on Sign In) | ✅ DUMP |
| Email | `input[data-automation-id="email"]` | ✅ DUMP |
| Password | `input[data-automation-id="password"]` | ✅ DUMP |
| Verify password (create only) | `input[data-automation-id="verifyPassword"]` | ✅ DUMP |
| Terms checkbox (create only) | `input[data-automation-id="createAccountCheckbox"]` | ✅ DUMP |
| **Sign In click target** | `div[data-automation-id="click_filter"][aria-label="Sign In"]` **over** `button[data-automation-id="signInSubmitButton"]`. A normal click on the button is intercepted, so click the `click_filter` div. | ✅ DUMP |
| Create Account click target | `click_filter[aria-label="Create Account"]` over `createAccountSubmitButton` | ✅ DUMP |
| Forgot password | `forgotPasswordLink` | ✅ DUMP |
| Error "wrong email/password" | ❓ | ❓ |

Notes:
- The email input had `value=" "` (a single space) in the sign-in dump, so always clear with
  Ctrl+A/Delete before typing.
- The "Generate new mask" button next to the email field comes from a browser extension (an
  email-masking add-on), not Workday. The Selenium browser profile won't have it.

## My Information (CIBC, field order as rendered)
| Field | Locator | Control | Status |
|---|---|---|---|
| How did you hear * | `formField-source` → `input#source--source` | **nested** prompt: top level has categories such as "Job Board/Social Media"; clicking one opens a sub-list whose rows have `input[type=radio][data-automation-id="radioBtn"]`. Searching "LinkedIn" at the top level finds nothing on CIBC. Excel: `Job Board/Social Media > Indeed`. Selected value is read from `promptAriaInstruction` ("1 item selected, Indeed"). Escape does NOT close the sub-list; clicking outside does | ✅ RUN 2026-11-09 |
| Worked here before * | `input[type=radio][name="candidateIsPreviousWorker"][value="true"/"false"]` | radio | ✅ DUMP |
| Country * | `button#country--country` (name=`country`), in `formField-country` | dropdown, **pre-set to Canada** | ✅ DUMP |
| First name * | `input[name="legalName--firstName"]` | text | ✅ DUMP |
| Middle name | `input[name="legalName--middleName"]` | text | ✅ DUMP |
| Last name * | `input[name="legalName--lastName"]` | text | ✅ DUMP |
| I have a preferred name | `input[name="preferredCheck"]` | checkbox (leave unchecked in V1) | ✅ DUMP |
| Address line 1 * | `input[name="addressLine1"]` | text | ✅ DUMP |
| Address line 2 | `input[name="addressLine2"]` | text | ✅ DUMP |
| City * | `input[name="city"]` | text | ✅ DUMP |
| Province or Territory * | `button#address--countryRegion` (name=`countryRegion`) | dropdown | ✅ DUMP |
| Postal code * | `input[name="postalCode"]` | text | ✅ DUMP |
| Email | read-only text (account email) | — | ✅ DUMP |
| Phone device type * | `button#phoneNumber--phoneType` (name=`phoneType`) | dropdown | ✅ DUMP |
| Country phone code * | `formField-countryPhoneCode` → `input#phoneNumber--countryPhoneCode` | prompt; **sometimes pre-filled "Canada (+1)", sometimes empty** (05d), so always set it | ✅ DUMP |
| Phone number * | `input[name="phoneNumber"]` | text, digits | ✅ DUMP |
| Phone extension | `input[name="extension"]` | text | ✅ DUMP |
| SMS / WhatsApp opt-in | `phone-sms-opt-in`, `phone-whatsapp-opt-in` | checkbox (leave unchecked) | ✅ DUMP |
| Save and Continue | `pageFooter` → `button[data-automation-id="pageFooterNextButton"]` | button | ✅ DUMP |

Notes:
- Dropdown buttons show the current value as their text and `aria-label` (e.g. "Country Canada
  Required"). If it already matches, **skip it**, because re-selecting can re-render the dependent fields.
- Already-selected prompt values show up as `selectedItemList` → `selectedItem` →
  `p[data-automation-id="promptOption"][data-automation-label="Canada (+1)"]`. If the wanted value
  is already a pill, skip the field.
- Prompt selection count text: `promptAriaInstruction` ("0 items selected"). This is useful for verification.

## My Experience (CIBC run 2026-11-09: page shell ✅; fields inside entries ✅ EXT)
| Element | Locator | Status |
|---|---|---|
| Page marker | `applyFlowMyExpPage` | ✅ RUN |
| Sections | `div[role=group]` containing `h4` "Work Experience", "Education", "Languages", "Skills", "Resume/CV", "Websites", "Social Network URLs". No Certifications section on CIBC | ✅ RUN |
| Add button (empty section) | `button[data-automation-id="add-button"]` inside the section group | ✅ RUN |
| Add Another (after first entry) | `Add`, `Add Another`, `add-another-button` or text starting "Add" | ⚠️ |
| Entry container | found from the entry's first field (`formField-jobTitle`, `formField-schoolName`, `button[name=language]`); tagged `data-wdauto="work-1"` at runtime | logic tested on mock |
| Work fields | `formField-jobTitle`, `-companyName`, `-location`, `-currentlyWorkHere`, `-startDate`, `-endDate`, `-roleDescription` | ✅ EXT |
| Education fields | `formField-schoolName` (alias school/university/institution), `-degree` (dropdown), `-fieldOfStudy` (prompt), `-gradeAverage`, `-firstYearAttended`, `-lastYearAttended` | ✅ EXT |
| Language | `button[aria-haspopup=listbox][name="language"]`; proficiency = other listbox buttons in the entry, aria-label starts with the type | ✅ EXT |
| Skills | `formField-skills` → `input#skills--skills` (prompt, multi) | ✅ RUN |
| Resume input | `input[type=file][data-automation-id="file-upload-input-ref"]` next to `select-files` button, "Upload a file (5MB max) *" (required) | ✅ RUN |
| Uploaded file row | ❓ (detected by the file name appearing in the Resume/CV section) | ❓ |
| Websites entry field | `formField-url`? | ❓ |
| LinkedIn | `input[name="linkedInAccount"]` | ✅ RUN |
| Back button | `pageFooterBackButton` | ✅ RUN |
| Date parts | `dateSectionMonth-input`, `dateSectionYear-input` inside `formField-*Date` | ✅ EXT |

## Application Questions (CIBC run 2026-11-09 ✅)
| Element | Locator | Status |
|---|---|---|
| Page marker | `applyFlowPrimaryQuestionsPage` (also `applyFlowSecondaryQuestionsPage` on some tenants) | ✅ RUN |
| Question container | top-level `[data-automation-id="formField-<32 hex>"]`: ids differ per company/question, so questions are matched by **text** | ✅ RUN |
| Question text | `fieldset > legend` (a `richText` div); trailing `*` = required | ✅ RUN |
| Dropdown answer | `button[aria-haspopup="listbox"]` (text "Select One" when unanswered) | ✅ RUN |
| Checkbox group | `fieldset[data-automation-id="<id>-CheckboxGroup"]` → `input[type=checkbox]` + `label[for]` | ✅ RUN |

CIBC puts its diversity questions (gender, LGBTQ+, visible minority, race, disability, Indigenous,
newcomer, military) on this page, not on Voluntary Disclosures, so Questions-sheet rows for them leave
**Page** blank.

## Voluntary Disclosures
| Field | Locator | Status |
|---|---|---|
| Gender | `button[aria-haspopup=listbox][name="gender"]` | ✅ EXT |
| Ethnicity | `button[aria-haspopup=listbox][name="ethnicity"]` | ✅ EXT |
| Other questions (multiselect) | `searchBox` inside a `formField-*`, matched by label text | ✅ EXT |
| Veteran status | `formField-veteranStatus` (?) | ⚠️ AGW |
| Terms / consent checkbox | ❓ | ❓ |

## Self Identify (disability)
All ❓: name, date, disability-status checkboxes. **Needs a page capture.**

---

## Pages to capture (please send these)
1. **Job posting page** + the **"Start Your Application" popup** (after clicking Apply).
2. **Sign-in page** (whichever form appears after Apply Manually).
3. **Review page** (to confirm the marker and the Submit button, which we only detect).
4. **Self Identify** page.
5. **Voluntary Disclosures** page on a Canadian tenant (consent checkbox).
6. ~~Validation errors~~ ✅ captured (05d).
8. **"How did you hear" list open**: still needed (05c caught the field closed, see page_dumps/README.md).
7. Optional: My Information / My Experience from the same tenant, to double-check the ✅ list.

**How to capture:** on the page, open DevTools → Console and run
`copy(document.documentElement.outerHTML)`, then paste into
`docs/page_dumps/<company>_<page>.html`. From Phase 1 on, `python tools/dump_page.py` does
this automatically while a run is paused.
