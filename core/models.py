"""Data loaded from the Excel workbook."""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

from core.text import normalize, split_list


@dataclass
class Job:
    url: str
    company: str
    status: str = "Pending"
    row: int | None = None  # worksheet row number (for writing status back)
    notes: str = ""

    @property
    def host(self) -> str:
        return urlparse(self.url).netloc.lower()


@dataclass
class Account:
    company: str
    email: str
    password: str
    tenant_host: str = ""
    password_source: str = "Accounts sheet"


class Profile:
    """Key/value rows from the Profile sheet. Keys are case- and space-insensitive."""

    def __init__(self, values: dict[str, str]):
        self._values = {self._key(k): v for k, v in values.items()}

    @staticmethod
    def _key(k: str) -> str:
        return normalize(k).replace(" ", "")

    def get(self, key: str, default: str = "") -> str:
        v = self._values.get(self._key(key))
        return default if v is None or str(v).strip() == "" else str(v).strip()

    def options(self, key: str) -> list[str]:
        """Value split on ';': fallbacks tried in order."""
        return split_list(self.get(key))

    def has(self, key: str) -> bool:
        return bool(self.get(key))

    def as_bool(self, key: str) -> bool | None:
        v = normalize(self.get(key))
        if v in ("yes", "y", "true", "1"):
            return True
        if v in ("no", "n", "false", "0"):
            return False
        return None

    def __repr__(self) -> str:
        return f"Profile({len(self._values)} keys)"


@dataclass
class WorkEntry:
    job_title: str
    company: str
    location: str = ""
    currently_work_here: bool = False
    start_month: str = ""
    start_year: str = ""
    end_month: str = ""
    end_year: str = ""
    description: str = ""


@dataclass
class EducationEntry:
    school: str
    degree: list[str] = field(default_factory=list)          # fallbacks, tried in order
    field_of_study: list[str] = field(default_factory=list)  # fallbacks, tried in order
    gpa: str = ""
    start_year: str = ""
    end_year: str = ""


@dataclass
class LanguageEntry:
    language: str
    proficiency: list[str] = field(default_factory=list)          # default for every proficiency dropdown
    per_type: dict[str, list[str]] = field(default_factory=dict)  # e.g. {"reading": [...]} overrides

    def proficiency_for(self, kind: str) -> list[str]:
        return self.per_type.get(normalize(kind), self.proficiency)


@dataclass
class Certification:
    name: str
    number: str = ""
    expiry_month: str = ""
    expiry_year: str = ""


@dataclass
class AppData:
    jobs: list[Job] = field(default_factory=list)
    accounts: list[Account] = field(default_factory=list)
    profile: Profile = field(default_factory=lambda: Profile({}))
    work: list[WorkEntry] = field(default_factory=list)
    education: list[EducationEntry] = field(default_factory=list)
    languages: list[LanguageEntry] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    certifications: list[Certification] = field(default_factory=list)
    questions: list = field(default_factory=list)  # core.answers.QuestionRule

    def find_account(self, job: Job) -> Account | None:
        """Match on company name first, then on the URL host (TenantHost column)."""
        for acc in self.accounts:
            if acc.company and normalize(acc.company) == normalize(job.company):
                return acc
        for acc in self.accounts:
            if acc.tenant_host and acc.tenant_host.lower() in job.host:
                return acc
        return None

    def job_for_url(self, url: str) -> Job:
        for job in self.jobs:
            if job.url.strip().rstrip("/") == url.strip().rstrip("/"):
                return job
        return Job(url=url, company=company_from_url(url))

    def job_for_row(self, row: int) -> Job:
        for job in self.jobs:
            if job.row == row:
                return job
        raise LookupError(f"No job on row {row} of the Jobs sheet")


def company_from_url(url: str) -> str:
    """https://cibc.wd3.myworkdayjobs.com/... → 'CIBC'."""
    host = urlparse(url).netloc
    return host.split(".")[0].upper() if host else "UNKNOWN"
