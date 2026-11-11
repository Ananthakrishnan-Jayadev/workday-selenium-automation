"""Create examples/applicant_data.example.xlsx: a reference workbook with EVERY sheet and column
filled in for a made-up applicant (Jane Doe). Open it to see what each cell expects, or copy it to
data/applicant_data.xlsx and replace the values with your own.

    python tools/make_example.py               # writes examples/applicant_data.example.xlsx
    python tools/make_example.py out.xlsx      # somewhere else

All data is fictional (example.com addresses, a 555 phone number). The column layout comes from
tools/make_template.py, so the two never drift apart.
"""
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_template import ROOT, SHEETS, build  # noqa: E402

DEFAULT_PATH = ROOT / "examples" / "applicant_data.example.xlsx"

ROWS: dict[str, list[list]] = {
    # JobURL | Folder | Company | Status | LastRun | Notes
    "Jobs": [
        ["https://examplebank.wd3.myworkdayjobs.com/External/job/Toronto-ON/Data-Engineer_R1001",
         "application_01", "Example Bank", "Pending", "", "Next to run (plain `behave` takes the first Pending row)"],
        ["https://acmecorp.wd5.myworkdayjobs.com/Careers/job/Remote-Canada/ML-Engineer_JR2002",
         "application_02", "", "Pending", "", "Company left blank: taken from the URL (ACMECORP)"],
        ["https://globex.wd1.myworkdayjobs.com/Jobs/job/Ottawa-ON/Software-Developer_3003",
         "application_03", "Globex", "Failed", "2026-11-01 10:15", "Retried by `behave` when no Pending row is left"],
        ["https://initech.wd3.myworkdayjobs.com/External/job/Toronto-ON/Analyst_4004",
         "application_04", "Initech", "Submitted", "2026-10-30 14:02", "Submitted by user (written by the script)"],
        ["https://umbrella.wd3.myworkdayjobs.com/External/job/Montreal-QC/Engineer_5005",
         "application_05", "Umbrella", "Skipped", "2026-10-29 09:40", "Statuses: Pending, ReadyForReview, Submitted, Skipped, Failed"],
    ],
    # Company | TenantHost | Email | Password
    "Accounts": [
        ["Example Bank", "examplebank.wd3.myworkdayjobs.com", "jane.doe@example.com", "ENV:EXAMPLEBANK_PASSWORD"],
        ["ACMECORP", "acmecorp.wd5.myworkdayjobs.com", "jane.doe@example.com", "plain-text-password-here"],
        ["Globex", "globex.wd1.myworkdayjobs.com", "jane.doe@example.com", "ENV:GLOBEX_PASSWORD"],
        ["Initech", "initech.wd3.myworkdayjobs.com", "jane.doe@example.com", "ENV:INITECH_PASSWORD"],
        ["Umbrella", "umbrella.wd3.myworkdayjobs.com", "jane.doe@example.com", "ENV:UMBRELLA_PASSWORD"],
    ],
    # Field | Value | Fallback 1 | Fallback 2 | Notes
    "Profile": [
        ["FirstName", "Jane", "", "", "Legal first name"],
        ["MiddleName", "Q", "", "", "Optional"],
        ["LastName", "Doe", "", "", ""],
        ["Country", "Canada", "", "", "As shown in Workday's Country dropdown"],
        ["AddressLine1", "123 Example Street", "", "", ""],
        ["AddressLine2", "Unit 4", "", "", "Optional"],
        ["City", "Toronto", "", "", ""],
        ["Province", "Ontario", "", "", "Province / State, as shown in the dropdown"],
        ["PostalCode", "A1A 1A1", "", "", ""],
        ["PhoneType", "Mobile", "Personal Primary", "Home Cellular", "Each company names it differently; first match wins"],
        ["PhoneCountryCode", "Canada (+1)", "", "", "Required. Sometimes pre-filled, sometimes empty"],
        ["Phone", "4165550123", "", "", "Digits only"],
        ["PhoneExtension", "12", "", "", "Optional"],
        ["HowDidYouHear", "LinkedIn", "Social Network: Linkedin", "Job Board/Social Media > LinkedIn; Social Media",
         "'Category > Value' for nested lists; ';' adds more fallbacks in one cell"],
        ["PreviouslyWorkedHere", "No", "", "", "Yes / No"],
        ["LinkedIn", "https://www.linkedin.com/in/jane-doe-example/", "", "", ""],
        ["Website", "https://janedoe.example.com", "https://github.com/jane-doe-example", "",
         "Every URL is added (Value and each Fallback)"],
        ["ApplicationsFolder", "/home/jane/applications", "", "",
         "Holds one sub-folder per job (the Jobs sheet's Folder column). Relative = inside the project"],
        ["ResumeFileName", "Jane_Doe_Resume.pdf", "", "", "The resume's file name inside every application folder (5MB max)"],
        ["CoverLetterFileName", "cover letter.pdf", "", "",
         "Optional. A folder without this file applies without a cover letter"],
    ],
    # JobTitle | Company | Location | CurrentlyWorkHere | StartMonth | StartYear | EndMonth | EndYear | Description
    "WorkExperience": [
        ["Data Engineer", "Example Analytics Inc.", "Toronto, ON", "Yes", "March", "2024", "", "",
         "Built batch and streaming pipelines (Python, Airflow, AWS); cut report latency from 6h to 20 min."],
        ["Junior Developer", "Sample Software Ltd.", "Ottawa, ON", "No", "June", "2021", "February", "2024",
         "Maintained REST APIs and a PostgreSQL warehouse; added CI tests that caught 30+ regressions."],
    ],
    # School | Degree | Degree Fallback 1 | Degree Fallback 2 | FieldOfStudy | FoS Fallback 1 | FoS Fallback 2 | GPA | StartYear | EndYear
    "Education": [
        ["Example University", "Master's Degree", "Masters", "Post Graduate", "Computer Science",
         "Information Technology", "Computer Engineering", "3.8", "2019", "2021"],
        ["Sample College", "Bachelor's Degree", "Bachelors", "Bachelor Degree", "Mathematics",
         "Applied Mathematics", "Statistics", "3.5", "2015", "2019"],
    ],
    # Language | Proficiency | Proficiency Fallback 1 | Reading | Writing | Speaking | Overall
    "Languages": [
        ["English", "Fluent", "Advanced", "", "", "", "", ],
        ["French", "Intermediate", "Basic", "Advanced", "Intermediate", "Intermediate", "Intermediate"],
    ],
    # Skill | Fallback 1 | Fallback 2
    "Skills": [
        ["Python", "", ""],
        ["SQL", "PostgreSQL", "MySQL"],
        ["Amazon Web Services (AWS)", "Amazon Web Services", ""],
        ["Apache Airflow", "", ""],
        ["Docker", "", ""],
        ["Machine Learning", "", ""],
        ["FastAPI", "Flask", ""],
    ],
    # Name | Number | ExpiryDay | ExpiryMonth | ExpiryYear
    "Certifications": [
        ["AWS Certified Developer - Associate", "ABC-123456", "15", "March", "2028"],
        ["Certified Kubernetes Application Developer (CKAD)", "", "", "", ""],
    ],
    # Keywords | Answer | Fallback 1 | Fallback 2 | Fallback 3 | Company | Page | Notes
    "Questions": [
        ["legally eligible; authorized to work; legally entitled to work; eligible to work", "Yes", "", "", "", "", "",
         "';' = any of these phrases (whole words)"],
        ["require sponsorship; sponsorship; employer support to obtain", "No", "", "", "", "", "",
         "Add new wordings of the same question as more phrases"],
        ["worked for {company}; employed by {company}; worked at {company}", "No", "", "", "", "", "",
         "{company} = the job's company ('worked for Example Bank')"],
        ["relative; family member + example bank", "No", "", "", "", "Example Bank", "",
         "'+' = AND: (relative OR family member) AND 'example bank'. Company column: only for that company"],
        ["18 years; age of majority; minimum legal age; minimum age requirement", "Yes", "", "", "", "", "", ""],
        ["available to start; start date; earliest start", "today+14", "", "", "", "", "",
         "Dates: today, today+N (days), today+Nw (weeks), dd/mm/yyyy or yyyy-mm-dd"],
        ["weekly hours; hours per week", "40", "", "", "", "", "", "Text boxes get the Answer typed in"],
        ["type of employment; employment you are seeking", "Full-Time", "Permanent", "", "", "", "",
         "Checkbox groups: the labels to tick (or Yes = tick all)"],
        ["salary expectation; expected salary; desired compensation", "", "", "", "", "", "",
         "Blank Answer = ask me: the run pauses on it and lists the options"],
        ["gender identity", "Woman", "Female", "", "", "", "",
         "First clause decides: 'What is your gender identity?' uses this row"],
        ["what is your gender; gender; sex", "Woman", "Female", "", "", "", "", ""],
        ["race/ethnicity; race; ethnicity; ethnic origin", "I do not wish to disclose", "Prefer not to say",
         "Decline to self-identify", "", "", "", "Each company words its options differently: add them as fallbacks"],
        ["disability; disabled", "No", "No, I don't have a disability", "I do not have a disability", "None",
         "", "", "Answers are strict: 'No' never matches 'Not applicable' or 'Do not wish to declare'"],
        ["military; armed forces; veteran", "No", "I am not a veteran", "", "", "", "", ""],
        ["i agree to the above; consent to the terms; terms and conditions; i have read and consent", "Yes",
         "", "", "", "", "Disclosure", "Page column: only on Voluntary Disclosures (the terms checkbox)"],
        ["disability status; self-identify", "No, I do not have a disability", "", "", "", "", "SelfIdentify",
         "Page values: Application, Disclosure, SelfIdentify (blank = any page)"],
    ],
}

GUIDE: list[tuple[str, str]] = [
    ("What this is", "A reference workbook with every sheet and column filled in for a made-up applicant. "
                     "The real one is data/applicant_data.xlsx (git-ignored). All data here is fictional."),
    ("Jobs", "One row per job. Folder = this job's sub-folder of ApplicationsFolder (Profile). Status: Pending runs "
             "next; Failed is retried when no Pending row is left; Submitted/Skipped are written back by the script."),
    ("Accounts", "An EXISTING Workday account per company (the script doesn't create accounts). Matched on Company, "
                 "then on TenantHost. Password: plain text, or ENV:NAME to read NAME from the .env file."),
    ("Profile", "Field / Value pairs for My Information plus the document settings. Fallback columns are tried left "
                "to right when the company's dropdown has no option for Value."),
    ("Documents", "Resume = <ApplicationsFolder>/<Folder>/<ResumeFileName>; cover letter likewise with "
                  "CoverLetterFileName. A missing folder or resume stops the run before the browser opens; a "
                  "missing cover letter only gives a warning."),
    ("WorkExperience", "One row per job, most recent first. Month names + years. CurrentlyWorkHere = Yes leaves the "
                       "end date empty."),
    ("Education", "One row per school. Degree and FieldOfStudy have their own fallback columns. Field of Study picks "
                  "the closest option by whole words before trying a fallback."),
    ("Languages", "Proficiency (with fallbacks) fills every proficiency dropdown; Reading / Writing / Speaking / "
                  "Overall override it for that one dropdown."),
    ("Skills", "Workday's exact skill name ('Python' also matches 'Python (Programming Language)', 'SQL' matches "
               "'Structured Query Language (SQL)'). Fallbacks are tried when the skill isn't listed. Unlisted = skipped."),
    ("Certifications", "Optional section. A certificate the company doesn't list is skipped (its empty entry is "
                       "deleted). Expiry date parts are optional."),
    ("Questions", "Keyword rules. ';' = any of, '+' = all of, {company} = the job's company. The question's first "
                  "clause is matched first; company-specific rows win. Answers must equal or start an option "
                  "(whole words). Blank Answer = pause and ask."),
    ("Fallbacks", "Different companies word the same option differently. When an answer isn't found, the run log "
                  "lists every option the company offered: copy the right one into the next Fallback column."),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    sheets = copy.deepcopy(SHEETS)
    for name, spec in sheets.items():
        rows = ROWS[name]
        width = len(spec["headers"])
        bad = [r for r in rows if len(r) != width]
        if bad:
            raise SystemExit(f"{name}: {len(bad)} row(s) don't have {width} columns ({spec['headers']})")
        spec["rows"] = rows
    build(args.path, sheets, guide=GUIDE)
    print(f"Created {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
