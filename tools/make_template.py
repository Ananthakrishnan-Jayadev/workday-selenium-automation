"""Create data/applicant_data.xlsx with every sheet, headers and example rows.

    python tools/make_template.py            # refuses to overwrite an existing workbook
    python tools/make_template.py --force    # overwrite
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "data" / "applicant_data.xlsx"

HEADER_FILL = PatternFill("solid", fgColor="DDE7F3")
NOTE_FONT = Font(italic=True, color="666666")

SHEETS: dict[str, dict] = {
    "Jobs": {
        "headers": ["JobURL", "Folder", "Company", "Status", "LastRun", "Notes"],
        "widths": [90, 18, 14, 16, 20, 40],
        "rows": [["https://cibc.wd3.myworkdayjobs.com/search/job/Toronto-ON/Senior-Data-Engineer_2622337",
                  "application_01", "CIBC", "Pending", "", ""]],
    },
    "Accounts": {
        "headers": ["Company", "TenantHost", "Email", "Password"],
        "widths": [14, 34, 34, 24],
        "rows": [["CIBC", "cibc.wd3.myworkdayjobs.com", "you@example.com", "ENV:CIBC_PASSWORD"]],
    },
    "Profile": {
        "headers": ["Field", "Value", "Fallback 1", "Fallback 2", "Notes"],
        "widths": [22, 40, 28, 28, 60],
        "rows": [
            ["FirstName", "Jane", "", "", "Legal first name"],
            ["MiddleName", "", "", "", "Optional"],
            ["LastName", "Doe", "", "", ""],
            ["Country", "Canada", "", "", "As shown in Workday's Country dropdown"],
            ["AddressLine1", "123 Example Street", "", "", ""],
            ["AddressLine2", "", "", "", "Optional"],
            ["City", "Toronto", "", "", ""],
            ["Province", "Ontario", "", "", "Province / State, as shown in the dropdown"],
            ["PostalCode", "A1A 1A1", "", "", ""],
            ["PhoneType", "Mobile", "Personal Primary", "", "Fallbacks are tried left to right (BMO has no 'Mobile')"],
            ["PhoneCountryCode", "Canada (+1)", "", "", "Required. Sometimes pre-filled, sometimes empty"],
            ["Phone", "4165550123", "", "", "Digits only"],
            ["PhoneExtension", "", "", "", "Optional"],
            ["HowDidYouHear", "LinkedIn", "Social Network: Linkedin", "Job Board/Social Media > LinkedIn",
             "Use 'Category > Value' for nested lists"],
            ["PreviouslyWorkedHere", "No", "", "", "Yes / No"],
            ["LinkedIn", "https://www.linkedin.com/in/your-profile/", "", "", ""],
            ["Website", "https://your-portfolio.example", "", "", "All URLs are added (Value, Fallback 1, ...)"],
            ["ApplicationsFolder", "/home/you/applications", "", "",
             "Holds one sub-folder per job (named in the Jobs sheet's Folder column)"],
            ["ResumeFileName", "resume.pdf", "", "", "The resume's file name inside every application folder (5MB max)"],
            ["CoverLetterFileName", "cover_letter.pdf", "", "",
             "Optional: the cover letter's file name; a folder without it uploads no cover letter"],
        ],
    },
    # ---- Phase 2 -------------------------------------------------------------------------
    "WorkExperience": {
        "headers": ["JobTitle", "Company", "Location", "CurrentlyWorkHere", "StartMonth", "StartYear",
                    "EndMonth", "EndYear", "Description"],
        "widths": [26, 22, 18, 18, 12, 10, 12, 10, 80],
        "rows": [["Software Developer", "Example Company", "Toronto, ON", "Yes", "January", "2024", "", "",
                  "What you did, tools used, measurable impact."]],
    },
    "Education": {
        "headers": ["School", "Degree", "Degree Fallback 1", "Degree Fallback 2", "FieldOfStudy",
                    "FieldOfStudy Fallback 1", "FieldOfStudy Fallback 2", "GPA", "StartYear", "EndYear"],
        "widths": [28, 26, 22, 22, 26, 22, 22, 6, 10, 10],
        "rows": [["Example College", "Bachelor's Degree", "Bachelors", "", "Computer Science", "Information Technology",
                  "", "", "2019", "2023"]],
    },
    "Languages": {
        "headers": ["Language", "Proficiency", "Proficiency Fallback 1", "Reading", "Writing", "Speaking", "Overall"],
        "widths": [16, 16, 22, 12, 12, 12, 12],
        "rows": [["English", "Fluent", "Advanced", "", "", "", ""]],
    },
    "Skills": {"headers": ["Skill", "Fallback 1", "Fallback 2"], "widths": [36, 28, 28],
               "rows": [["Python", "", ""], ["SQL", "PostgreSQL", "MySQL"]]},
    "Certifications": {
        "headers": ["Name", "Number", "ExpiryDay", "ExpiryMonth", "ExpiryYear"],
        "widths": [40, 20, 10, 12, 12],
        "rows": [],
    },
    # ---- Phase 3 -------------------------------------------------------------------------
    "Questions": {
        "headers": ["Keywords", "Answer", "Fallback 1", "Fallback 2", "Fallback 3", "Company", "Page", "Notes"],
        "widths": [60, 22, 18, 18, 18, 10, 12, 60],
        "rows": [
            ["legally eligible; authorized to work; eligible to work", "Yes", "", "", "", "", "", ""],
            ["sponsorship", "No", "", "", "", "", "", ""],
            ["worked for {company}; employed by {company}", "No", "", "", "", "", "",
             "{company} = the job's company"],
            ["18 years; age of majority", "Yes", "", "", "", "", "", ""],
            ["gender identity", "Man", "Male", "", "", "", "", "first clause decides: 'What is your gender identity?'"],
            ["what is your gender; gender", "Man", "Male", "", "", "", "", ""],
            ["i agree to the above; consent to the terms; terms and conditions", "", "", "", "", "", "Disclosure",
             "Yes = tick the terms checkbox automatically"],
        ],
    },
}

STATUS_VALUES = '"Pending,ReadyForReview,Submitted,Skipped,Failed"'


def build(path: Path, sheets: dict[str, dict] | None = None, guide: list[tuple[str, str]] | None = None) -> None:
    """Write the workbook. `sheets` defaults to SHEETS (the template); tools/make_example.py passes a
    fully filled copy. `guide` adds a first sheet of (topic, explanation) rows."""
    sheets = SHEETS if sheets is None else sheets
    wb = Workbook()
    wb.remove(wb.active)
    if guide:
        ws = wb.create_sheet("Guide")
        ws.append(["Topic", "Explanation"])
        for row in guide:
            ws.append(list(row))
        ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 26, 140
        for cell in ws[1]:
            cell.font, cell.fill = Font(bold=True), HEADER_FILL
        for row in ws.iter_rows(min_row=2):
            row[0].font = Font(bold=True)
            row[1].alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "A2"
    for name, spec in sheets.items():
        ws = wb.create_sheet(name)
        ws.append(spec["headers"])
        for row in spec["rows"]:
            ws.append(row)
        for col, width in enumerate(spec["widths"], start=1):
            ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = width
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = HEADER_FILL
            cell.alignment = Alignment(vertical="center")
        ws.freeze_panes = "A2"
        if "Notes" in spec["headers"]:  # notes in grey italics, so they read as comments
            col = spec["headers"].index("Notes") + 1
            for (notes,) in ws.iter_rows(min_row=2, min_col=col, max_col=col):
                notes.font = NOTE_FONT
        if name == "Jobs":
            dv = DataValidation(type="list", formula1=STATUS_VALUES, allow_blank=True)
            ws.add_data_validation(dv)
            dv.add("D2:D1000")  # Status
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--force", action="store_true", help="overwrite an existing workbook")
    args = parser.parse_args()
    if args.path.exists() and not args.force:
        print(f"{args.path} already exists. Use --force to overwrite it.", file=sys.stderr)
        return 1
    build(args.path)
    print(f"Created {args.path}. Fill in the Accounts and Profile sheets before running.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
