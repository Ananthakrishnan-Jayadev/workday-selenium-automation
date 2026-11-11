"""Read data/applicant_data.xlsx into AppData."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openpyxl import load_workbook as _open

from core import PROJECT_ROOT
from core.models import (Account, AppData, Certification, EducationEntry, Job, LanguageEntry, Profile,
                         WorkEntry, company_from_url)
from core.answers import QuestionRule
from core.text import normalize, split_list


class WorkbookError(Exception):
    pass


def _cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)  # 2024.0 → "2024", phone numbers typed as numbers
    return str(v).strip()


def _rows(ws) -> list[tuple[int, dict[str, str]]]:
    """[(row_number, {header: value})] for non-empty rows. Headers compared case-insensitively."""
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [_cell(h) for h in rows[0]]
    out = []
    for offset, values in enumerate(rows[1:], start=2):
        record = {h: _cell(v) for h, v in zip(headers, values) if h}
        if any(record.values()):
            out.append((offset, record))
    return out


def _get(record: dict[str, str], *names: str) -> str:
    lowered = {k.lower().replace(" ", ""): v for k, v in record.items()}
    for n in names:
        v = lowered.get(n.lower().replace(" ", ""))
        if v:
            return v
    return ""


def _with_fallbacks(record: dict[str, str], base: str, plain: bool = False) -> list[str]:
    """The `base` column followed by its fallback columns, in order, as one list.

    Fallback columns are named "<Base> Fallback 1", "<Base> Fallback 2", ... (Education, Languages)
    or just "Fallback 1", "Fallback 2", ... when plain=True (Profile, Skills, Questions).
    A ';' inside any cell also separates values, so older workbooks keep working."""
    values = split_list(_get(record, base))
    keys = {k.lower().replace(" ", ""): v for k, v in record.items()}
    prefix = "fallback" if plain else f"{base.lower().replace(' ', '')}fallback"
    numbered = sorted((int(m.group(1)), v) for k, v in keys.items()
                      if (m := re.fullmatch(rf"{re.escape(prefix)}(\d+)", k)) and v)
    for _n, v in numbered:
        values += split_list(v)
    return list(dict.fromkeys(values))


def _is_fallback_column(header: str) -> bool:
    return "fallback" in header.lower().replace(" ", "")


def _resolve_secret(value: str) -> tuple[str, str]:
    """'ENV:NAME' → (value of NAME from the environment / .env, 'env NAME'). Missing → ''.
    The sign-in step reports a missing password; loading the workbook never fails because of one."""
    if value.upper().startswith("ENV:"):
        name = value[4:].strip()
        return os.environ.get(name, ""), f"${name} (.env)"
    return value, "Accounts sheet"


def load_app_data(path: Path) -> AppData:
    load_dotenv(PROJECT_ROOT / ".env")
    if not path.exists():
        raise WorkbookError(f"Workbook not found: {path}\nCreate it with:  python tools/make_template.py")

    wb = _open(path, data_only=True, read_only=True)
    try:
        sheets = {name.lower(): wb[name] for name in wb.sheetnames}
        data = AppData()

        if "jobs" in sheets:
            for row, r in _rows(sheets["jobs"]):
                url = _get(r, "JobURL", "URL")
                if url:
                    # Company left blank → take it from the URL (https://cibc.wd3... → CIBC)
                    data.jobs.append(Job(url=url, company=_get(r, "Company") or company_from_url(url),
                                         status=_get(r, "Status") or "Pending", row=row, notes=_get(r, "Notes"),
                                         folder=_get(r, "Folder", "ApplicationFolder")))

        if "accounts" in sheets:
            for row, r in _rows(sheets["accounts"]):
                email = _get(r, "Email")
                if not email:
                    continue
                password, source = _resolve_secret(_get(r, "Password"))
                data.accounts.append(Account(
                    company=_get(r, "Company"),
                    tenant_host=_get(r, "TenantHost").lower(),
                    email=email,
                    password=password,
                    password_source=source,
                ))

        if "profile" in sheets:
            values = {}
            for _row, r in _rows(sheets["profile"]):
                key = _get(r, "Field", "Key")
                if key:
                    values[key] = _with_fallbacks(r, "Value", plain=True)
            data.profile = Profile(values)

        if "workexperience" in sheets:
            for _row, r in _rows(sheets["workexperience"]):
                if not _get(r, "JobTitle"):
                    continue
                data.work.append(WorkEntry(
                    job_title=_get(r, "JobTitle"), company=_get(r, "Company"), location=_get(r, "Location"),
                    currently_work_here=normalize(_get(r, "CurrentlyWorkHere")) in ("yes", "y", "true", "1"),
                    start_month=_get(r, "StartMonth"), start_year=_get(r, "StartYear"),
                    end_month=_get(r, "EndMonth"), end_year=_get(r, "EndYear"),
                    description=_get(r, "Description"),
                ))

        if "education" in sheets:
            for _row, r in _rows(sheets["education"]):
                if not _get(r, "School"):
                    continue
                data.education.append(EducationEntry(
                    school=_get(r, "School"), degree=_with_fallbacks(r, "Degree"),
                    field_of_study=_with_fallbacks(r, "FieldOfStudy"), gpa=_get(r, "GPA"),
                    start_year=_get(r, "StartYear"), end_year=_get(r, "EndYear"),
                ))

        if "languages" in sheets:
            for _row, r in _rows(sheets["languages"]):
                if not _get(r, "Language"):
                    continue
                per_type = {normalize(k): split_list(v) for k, v in r.items()
                            if v and normalize(k) not in ("language", "proficiency") and not _is_fallback_column(k)}
                data.languages.append(LanguageEntry(language=_get(r, "Language"),
                                                    proficiency=_with_fallbacks(r, "Proficiency"),
                                                    per_type=per_type))

        if "skills" in sheets:
            data.skills = ["; ".join(_with_fallbacks(r, "Skill", plain=True))
                           for _row, r in _rows(sheets["skills"]) if _get(r, "Skill")]

        if "certifications" in sheets:
            for _row, r in _rows(sheets["certifications"]):
                if _get(r, "Name"):
                    data.certifications.append(Certification(
                        name=_get(r, "Name"), number=_get(r, "Number"),
                        expiry_month=_get(r, "ExpiryMonth"), expiry_year=_get(r, "ExpiryYear"),
                        expiry_day=_get(r, "ExpiryDay")))

        if "questions" in sheets:
            for row, r in _rows(sheets["questions"]):
                if _get(r, "Keywords"):
                    data.questions.append(QuestionRule(
                        keywords=_get(r, "Keywords"), answer="; ".join(_with_fallbacks(r, "Answer", plain=True)),
                        company=_get(r, "Company"), page=_get(r, "Page"), row=row))

        return data
    finally:
        wb.close()
