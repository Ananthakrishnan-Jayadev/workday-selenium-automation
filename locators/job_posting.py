"""Job posting page and the 'Start Your Application' popup (verified: cibc_01, cibc_02)."""
from selenium.webdriver.common.by import By

from locators import aid

POSTING_HEADER = aid("jobPostingHeader")
APPLY_BUTTON = aid("adventureButton")                 # <a role="button">Apply</a>

APPLY_POPUP = aid("wd-popup-frame")                   # role=dialog, aria-label "Start Your Application"
APPLY_MANUALLY = aid("applyManually")
AUTOFILL_WITH_RESUME = aid("autofillWithResume")      # not used in V1
USE_MY_LAST_APPLICATION = aid("useMyLastApplication")  # not used in V1

# Unverified: the message Workday shows when you've already applied to this posting.
ALREADY_APPLIED = (By.XPATH, "//*[self::p or self::span or self::div or self::h2 or self::h3]"
                             "[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                             "'abcdefghijklmnopqrstuvwxyz'), 'already applied')]")
