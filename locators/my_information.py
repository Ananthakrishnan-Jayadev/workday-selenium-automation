"""My Information page (verified: cibc_05)."""
from selenium.webdriver.common.by import By

from locators import aid

PAGE = aid("applyFlowMyInfoPage")

# How did you hear about us: prompt (multiselect) field
SOURCE_FIELD = aid("formField-source")
SOURCE_INPUT = (By.CSS_SELECTOR, '[data-automation-id="formField-source"] input')

# Have you worked with us before: radio, value "true" / "false"
PREVIOUS_WORKER_FIELD = aid("formField-candidateIsPreviousWorker")


def previous_worker_radio(value: str):
    return By.CSS_SELECTOR, f'input[type="radio"][name="candidateIsPreviousWorker"][value="{value}"]'


COUNTRY_BUTTON = (By.CSS_SELECTOR, '[data-automation-id="formField-country"] button[aria-haspopup="listbox"]')

FIRST_NAME = (By.CSS_SELECTOR, 'input[name="legalName--firstName"]')
MIDDLE_NAME = (By.CSS_SELECTOR, 'input[name="legalName--middleName"]')
LAST_NAME = (By.CSS_SELECTOR, 'input[name="legalName--lastName"]')
PREFERRED_NAME_CHECK = (By.CSS_SELECTOR, 'input[name="preferredCheck"]')

ADDRESS_LINE_1 = (By.CSS_SELECTOR, 'input[name="addressLine1"]')
ADDRESS_LINE_2 = (By.CSS_SELECTOR, 'input[name="addressLine2"]')
CITY = (By.CSS_SELECTOR, 'input[name="city"]')
PROVINCE_BUTTON = (By.CSS_SELECTOR, '[data-automation-id="formField-countryRegion"] button[aria-haspopup="listbox"]')
POSTAL_CODE = (By.CSS_SELECTOR, 'input[name="postalCode"]')

PHONE_TYPE_BUTTON = (By.CSS_SELECTOR, '[data-automation-id="formField-phoneType"] button[aria-haspopup="listbox"]')
PHONE_CODE_FIELD = aid("formField-countryPhoneCode")
PHONE_CODE_INPUT = (By.CSS_SELECTOR, '[data-automation-id="formField-countryPhoneCode"] input')
PHONE_NUMBER = (By.CSS_SELECTOR, 'input[name="phoneNumber"]')
PHONE_EXTENSION = (By.CSS_SELECTOR, 'input[name="extension"]')

SMS_OPT_IN = aid("phone-sms-opt-in", "input")            # left unchecked
WHATSAPP_OPT_IN = aid("phone-whatsapp-opt-in", "input")  # left unchecked
