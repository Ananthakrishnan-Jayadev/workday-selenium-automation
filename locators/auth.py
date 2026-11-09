"""Create Account / Sign In. One form with two modes (verified: cibc_03, cibc_04)."""
from selenium.webdriver.common.by import By

from locators import aid

SIGN_IN_CONTENT = aid("signInContent")
FORM = aid("signInFormo")                      # sic: Workday's id really is "signInFormo"
TITLE = (By.CSS_SELECTOR, "#authViewTitle")    # "Create Account" or "Sign In"

SIGN_IN_LINK = aid("signInLink", "button")              # Create Account mode → switch to Sign In
CREATE_ACCOUNT_LINK = aid("createAccountLink", "button")  # Sign In mode → switch to Create Account

EMAIL = aid("email", "input")
PASSWORD = aid("password", "input")
VERIFY_PASSWORD = aid("verifyPassword", "input")        # Create Account mode only

# The real submit buttons are covered by a transparent div[data-automation-id="click_filter"],
# which is what receives the click. Click the filter first, the button as a fallback.
SIGN_IN_SUBMIT_TARGETS = [
    (By.CSS_SELECTOR, 'div[data-automation-id="click_filter"][aria-label="Sign In"]'),
    (By.XPATH, "//button[@data-automation-id='signInSubmitButton']"
               "/preceding-sibling::div[@data-automation-id='click_filter']"),
    aid("signInSubmitButton", "button"),
]
SIGN_IN_SUBMIT_BUTTON = aid("signInSubmitButton", "button")
CREATE_ACCOUNT_SUBMIT_BUTTON = aid("createAccountSubmitButton", "button")

# Unverified: error shown after a failed sign-in (wrong password, locked account).
SIGN_IN_ERRORS = [
    aid("errorMessage"),
    (By.CSS_SELECTOR, '[data-automation-id="signInContent"] [role="alert"]'),
    (By.CSS_SELECTOR, '[data-automation-id="signInFormo"] [role="alert"]'),
]
