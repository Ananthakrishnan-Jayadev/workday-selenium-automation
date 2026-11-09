"""My Experience page.

Verified (CIBC run 2026-11-09): page marker, section headings + Add buttons, Skills prompt,
resume file input, LinkedIn. Fields INSIDE an added entry come from the browser extension
(used live on Workday tenants); entries are located by their first field, see MyExperiencePage.
"""
from selenium.webdriver.common.by import By

from locators import aid

PAGE = aid("applyFlowMyExpPage")


def section(heading: str):
    """The <div role="group"> that holds a section, found by its <h4> heading text."""
    return (By.XPATH, f"//h4[normalize-space(.)='{heading}']/ancestor::div[@role='group'][1]")


SECTION_HEADINGS = {
    "work": "Work Experience",
    "education": "Education",
    "languages": "Languages",
    "certifications": "Certifications",
    "websites": "Websites",
    "skills": "Skills",
    "resume": "Resume/CV",
}


def add_buttons(heading: str):
    """The section's Add / Add Another button. Section-scoped first, then by aria-label."""
    return [
        (By.XPATH,
         f"(//h4[normalize-space(.)='{heading}']/ancestor::div[@role='group'][1]"
         "//button[@data-automation-id='add-button' or @data-automation-id='Add'"
         " or @data-automation-id='Add Another' or @data-automation-id='add-another-button'"
         " or starts-with(normalize-space(.), 'Add')])[last()]"),
        (By.XPATH, f"(//button[starts-with(@aria-label, 'Add') and contains(@aria-label, '{heading}')])[last()]"),
    ]


# CSS of each entry type's first field: used to count entries and find each entry's container.
# These ids appear only inside that kind of entry, so they're searched page-wide. Alternatives = other tenants.
ENTRY_FIRST_FIELD = {
    "work": ['[data-automation-id="formField-jobTitle"]'],
    "education": ['[data-automation-id="formField-schoolName"]', '[data-automation-id="formField-school"]',
                  '[data-automation-id="formField-university"]', '[data-automation-id="formField-institution"]'],
    "languages": ['button[aria-haspopup="listbox"][name="language"]', '[data-automation-id="formField-language"]'],
    "certifications": ['[data-automation-id="formField-certification"]'],
    "websites": ['[data-automation-id="formField-url"]', '[data-automation-id="formField-webAddress"]',
                 '[data-automation-id="formField-website"]', 'input[name="url"]'],
}

# Field automation ids inside an entry (first match wins).
WORK = {
    "job_title": ["formField-jobTitle"],
    "company": ["formField-companyName", "formField-company"],
    "location": ["formField-location"],
    "current": ["formField-currentlyWorkHere"],
    "start": ["formField-startDate"],
    "end": ["formField-endDate"],
    "description": ["formField-roleDescription", "formField-description"],
}
EDUCATION = {
    "school": ["formField-schoolName", "formField-school", "formField-university", "formField-institution"],
    "degree": ["formField-degree", "formField-degreeLevel", "formField-degreeName"],
    "field_of_study": ["formField-fieldOfStudy", "formField-major", "formField-fieldofstudy"],
    "gpa": ["formField-gradeAverage", "formField-overallResult", "formField-gpa"],
    "start_year": ["formField-firstYearAttended", "formField-startYear"],
    "end_year": ["formField-lastYearAttended", "formField-endYear"],
}
CERTIFICATION = {
    "name": ["formField-certification"],
    "number": ["formField-certificationNumber"],
    "expiry": ["formField-expirationDate"],
}

# Languages: the language dropdown is button[name="language"]; the proficiency dropdowns are the other
# listbox buttons in the entry, their aria-label starts with the type ("Reading Fluent Required").
LANGUAGE_BUTTON_CSS = 'button[aria-haspopup="listbox"][name="language"]'

SKILLS_FIELD = aid("formField-skills")
SKILLS_INPUT = (By.CSS_SELECTOR, '[data-automation-id="formField-skills"] input')

RESUME_FILE_INPUT = (By.CSS_SELECTOR, 'input[type="file"][data-automation-id="file-upload-input-ref"], '
                                      'input[type="file"][data-automation-id="file-upload-input-file"], '
                                      'input[type="file"]')
RESUME_SECTION = section("Resume/CV")
# Unverified: the uploaded-file row. We also look for the file name anywhere in the section.
UPLOADED_FILE = (By.CSS_SELECTOR, '[data-automation-id="file-upload-successful"], '
                                  '[data-automation-id="file-upload-item"], [data-automation-id="fileName"]')

LINKEDIN = (By.CSS_SELECTOR, 'input[name="linkedInAccount"]')

# Date widget parts (inside a formField-*Date)
DATE_MONTH = aid("dateSectionMonth-input")
DATE_DAY = aid("dateSectionDay-input")
DATE_YEAR = aid("dateSectionYear-input")
