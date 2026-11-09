"""Locators shared by every Workday page."""
from selenium.webdriver.common.by import By

from locators import aid

# ---- Page identity ---------------------------------------------------------------------------
JOB_POSTING_PAGE = aid("jobPostingPage")
APPLY_FLOW = aid("applyFlowPage")
JOB_TITLE_HEADING = aid("jobTitleHeading")
ACTIVE_STEP_NAME = (By.XPATH, "//li[@data-automation-id='progressBarActiveStep']/label[last()]")

# Page name → marker. Checked in this order; the first one present wins.
PAGE_MARKERS = {
    "my_information": [aid("applyFlowMyInfoPage")],
    "my_experience": [aid("applyFlowMyExpPage")],
    "application_questions": [aid("applyFlowPrimaryQuestionsPage"), aid("applyFlowSecondaryQuestionsPage")],
    "voluntary_disclosures": [aid("applyFlowVoluntaryDisclosuresPage")],
    "self_identify": [aid("applyFlowSelfIdentifyPage"), aid("selfIdentificationPage")],  # unverified
    "review": [aid("applyFlowReviewPage"), aid("reviewPanel"), aid("summaryView")],       # unverified;
    # falls back to the progress-bar step name "Review" (verified on CIBC)
}

# Progress-bar step names → page name (fallback when no marker matches).
STEP_NAMES = {
    "create account/sign in": "sign_in",
    "my information": "my_information",
    "my experience": "my_experience",
    "application questions": "application_questions",
    "voluntary disclosures": "voluntary_disclosures",
    "self identify": "self_identify",
    "review": "review",
}

# ---- Navigation ------------------------------------------------------------------------------
NEXT_BUTTONS = [
    aid("pageFooterNextButton", "button"),          # CIBC (verified)
    aid("bottom-navigation-next-button", "button"),  # other tenants
]

# ---- Dropdowns (button + listbox) ------------------------------------------------------------
DROPDOWN_BUTTON = (By.CSS_SELECTOR, 'button[aria-haspopup="listbox"]')
# Open listboxes. selectedItemList (the pills of a prompt field) also has role=listbox, so exclude it.
OPEN_LISTBOX = (By.CSS_SELECTOR, '[role="listbox"]:not([data-automation-id="selectedItemList"])')
LISTBOX_OPTION = (By.CSS_SELECTOR, '[role="option"]')

# ---- Prompt / multiselect fields -------------------------------------------------------------
PROMPT_INPUT = (By.CSS_SELECTOR, '[data-automation-id="multiselectInputContainer"] input, '
                                 '[data-automation-id="searchBox"]')
PROMPT_OPTION = aid("promptOption")
PROMPT_NO_MATCHES = aid("promptTitle")              # text "No matches found"
SELECTED_PILL = aid("selectedItem")
SELECTED_PILL_LABEL = (By.CSS_SELECTOR, '[data-automation-id="selectedItem"] [data-automation-id="promptOption"]')
PILL_DELETE = aid("DELETE_charm")
PROMPT_CHECKBOX = (By.CSS_SELECTOR, 'input[type="checkbox"][data-automation-id="checkboxPanel"]')
PROMPT_RADIO = (By.CSS_SELECTOR, 'input[type="radio"][data-automation-id="radioBtn"]')  # sub-list rows
# "0 items selected" / "1 item selected, Indeed": Workday's screen-reader text, the reliable way to
# read what a prompt field holds.
PROMPT_ARIA_INSTRUCTION = aid("promptAriaInstruction")

# Something harmless to click to close an open popup (clicking outside a Workday popup closes it).
NEUTRAL_CLICK_TARGETS = [aid("jobTitleHeading"), aid("jobPostingHeader"), aid("progressBar")]

# ---- Errors (verified: cibc_05d) ---------------------------------------------------------------
# After a failed Save and Continue: an "Errors Found" summary (errorHeading) at the top, and one
# <p data-automation-id="inputAlert">Error: The field X is required...</p> under each bad field.
FIELD_ERROR = aid("inputAlert")
ERROR_SUMMARY = aid("errorHeading")
OTHER_ERRORS = [aid("errorMessage"), aid("errorBanner")]  # unverified, other tenants
INVALID_FIELDS = (By.CSS_SELECTOR, '[aria-invalid="true"]')

# ---- Workday's "Something went wrong / Please refresh the page" screen (no automation id) ----------
# Seen right after sign-in on CIBC (cibc run 2026-11-09); a page refresh fixes it.
ERROR_PAGE = (By.XPATH, "//h1[contains(normalize-space(.), 'Something went wrong')]"
                        " | //div[contains(normalize-space(.), 'Please refresh the page and then try again')]"
                        "[not(.//div[contains(normalize-space(.), 'Please refresh the page')])]")

# ---- Popups ----------------------------------------------------------------------------------
POPUP_FRAME = aid("wd-popup-frame")
POPUP_CLOSE = (By.CSS_SELECTOR, '[data-automation-id="wd-popup-frame"] [data-automation-id="closeButton"]')

# ---- Never touch -----------------------------------------------------------------------------
HONEYPOT = aid("beecatcher", "input")
