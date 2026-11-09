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
        "headers": ["JobURL", "Company", "Status", "LastRun", "Notes"],
        "widths": [90, 14, 16, 20, 40],
        "rows": [["https://cibc.wd3.myworkdayjobs.com/search/job/Toronto-ON/Senior-Data-Engineer_2622337",
                  "CIBC", "Pending", "", ""]],
    },
    "Accounts": {
        "headers": ["Company", "TenantHost", "Email", "Password"],
        "widths": [14, 34, 34, 24],
        "rows": [["CIBC", "cibc.wd3.myworkdayjobs.com", "you@example.com", "ENV:CIBC_PASSWORD"]],
    },
    "Profile": {
        "headers": ["Field", "Value", "Notes"],
        "widths": [24, 40, 70],
        "rows": [
            ["FirstName", "Jane", "Legal first name"],
            ["MiddleName", "", "Optional"],
            ["LastName", "Doe", ""],
            ["Country", "Canada", "As shown in Workday's Country dropdown"],
            ["AddressLine1", "123 Example Street", ""],
            ["AddressLine2", "", "Optional"],
            ["City", "Toronto", ""],
            ["Province", "Ontario", "Province / State, as shown in the dropdown"],
            ["PostalCode", "A1A 1A1", ""],
            ["PhoneType", "Mobile", "Phone Device Type dropdown"],
            ["PhoneCountryCode", "Canada (+1)", "Required. Sometimes pre-filled, sometimes empty"],
            ["Phone", "4165550123", "Digits only"],
            ["PhoneExtension", "", "Optional"],
            ["HowDidYouHear", "LinkedIn; Job Board > LinkedIn; Other",
             "Fallbacks separated by ';'. Use 'Category > Value' for nested lists"],
            ["PreviouslyWorkedHere", "No", "Yes / No"],
            ["LinkedIn", "https://www.linkedin.com/in/your-profile/", "Phase 2"],
            ["Website", "", "Phase 2"],
            ["ResumePath", "/home/you/Documents/resume.pdf", "Absolute path to your resume (5MB max)"],
            ["CoverLetterPath", "", "Optional: absolute path to your cover letter (5MB max)"],
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
        "headers": ["School", "Degree", "FieldOfStudy", "GPA", "StartYear", "EndYear"],
        "widths": [30, 50, 40, 8, 10, 10],
        "rows": [["Example College", "Bachelor's Degree; Bachelors", "Computer Science", "", "2019", "2023"]],
    },
    "Languages": {
        "headers": ["Language", "Proficiency", "Reading", "Writing", "Speaking", "Overall"],
        "widths": [16, 24, 12, 12, 12, 12],
        "rows": [["English", "Fluent; Advanced", "", "", "", ""]],
    },
    "Skills": {"headers": ["Skill"], "widths": [40], "rows": [["Python"], ["SQL"]]},
    "Certifications": {
        "headers": ["Name", "Number", "ExpiryMonth", "ExpiryYear"],
        "widths": [40, 20, 12, 12],
        "rows": [],
    },
    # ---- Phase 3 -------------------------------------------------------------------------
    "Questions": {
        "headers": ["Keywords", "Answer", "Company", "Page", "Notes"],
        "widths": [60, 40, 12, 16, 50],
        "rows": [
            ["authorized to work; legally entitled; eligible to work", "Yes", "", "Application", ""],
            ["sponsorship", "No", "", "Application", ""],
            ["18 years; age of majority", "Yes", "", "Application", ""],
        ],
    },
}

STATUS_VALUES = '"Pending,ReadyForReview,Submitted,Skipped,Failed"'


def build(path: Path) -> None:
    wb = Workbook()
    wb.remove(wb.active)
    for name, spec in SHEETS.items():
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
        if name == "Profile":
            for (notes,) in ws.iter_rows(min_row=2, min_col=3, max_col=3):
                notes.font = NOTE_FONT
        if name == "Jobs":
            dv = DataValidation(type="list", formula1=STATUS_VALUES, allow_blank=True)
            ws.add_data_validation(dv)
            dv.add("C2:C1000")
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
