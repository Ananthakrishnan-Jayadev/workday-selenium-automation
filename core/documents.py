"""Which resume and cover letter to upload for a job.

Layout (names are examples; the real ones live in the Profile sheet, never in the code):

    <ApplicationsFolder>/            Profile: ApplicationsFolder   e.g. /home/you/applications
        application_01/              Jobs sheet: Folder            e.g. application_01
            resume.pdf               Profile: ResumeFileName       e.g. resume.pdf
            cover_letter.pdf         Profile: CoverLetterFileName  e.g. cover_letter.pdf
        application_02/
            ...

Every job must name its folder. The resume must be there (otherwise the run doesn't start);
the cover letter is optional (missing → skipped with a warning).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from core import PROJECT_ROOT
from core.models import Job, Profile

MAX_BYTES = 5 * 1024 * 1024  # Workday's upload limit


class DocumentsError(Exception):
    """The job's documents can't be found. The message says exactly what to fix."""


@dataclass
class JobDocuments:
    folder: Path
    resume: Path
    cover_letter: Path | None = None
    warnings: list[str] = field(default_factory=list)


def _find(folder: Path, name: str) -> Path | None:
    """`name` inside `folder`, ignoring upper/lower case ('Resume.PDF' finds 'resume.pdf')."""
    exact = folder / name
    if exact.is_file():
        return exact
    wanted = name.strip().lower()
    return next((p for p in sorted(folder.iterdir()) if p.is_file() and p.name.lower() == wanted), None)


def _listing(folder: Path, dirs: bool = False, limit: int = 12) -> str:
    try:
        items = sorted(p.name for p in folder.iterdir() if (p.is_dir() if dirs else p.is_file()))
    except OSError:
        return "(can't list it)"
    if not items:
        return "(empty)"
    more = f", ... ({len(items) - limit} more)" if len(items) > limit else ""
    return ", ".join(items[:limit]) + more


def _check_size(path: Path, label: str) -> None:
    size = path.stat().st_size
    if size > MAX_BYTES:
        raise DocumentsError(f"The {label} is {size / 1024 / 1024:.1f} MB; Workday accepts 5 MB at most:\n  {path}")


def resolve_documents(profile: Profile, job: Job, folder_override: str = "") -> JobDocuments:
    base_value = profile.get("ApplicationsFolder")
    resume_name = profile.get("ResumeFileName")
    cover_name = profile.get("CoverLetterFileName")
    folder_name = (folder_override or job.folder).strip()

    if not base_value:
        raise DocumentsError("Profile sheet: ApplicationsFolder is empty.\n"
                             "Set it to the folder that holds one sub-folder per application, e.g.\n"
                             "  ApplicationsFolder = /home/you/applications")
    if not resume_name:
        raise DocumentsError("Profile sheet: ResumeFileName is empty.\n"
                             "Set it to the resume's file name inside each application folder, e.g. resume.pdf")
    base = Path(base_value).expanduser()
    if not base.is_absolute():
        base = PROJECT_ROOT / base
    if not base.is_dir():
        raise DocumentsError(f"ApplicationsFolder (Profile sheet) does not exist:\n  {base}")
    if not folder_name:
        where = f"row {job.row} of the Jobs sheet" if job.row else "this job (it isn't in the Jobs sheet)"
        raise DocumentsError(f"No application folder for {where}.\n"
                             f"Put the folder name in the Folder column (or run with -D folder=<name>).\n"
                             f"Folders in {base}: {_listing(base, dirs=True)}")

    folder = Path(folder_name).expanduser()
    if not folder.is_absolute():
        folder = base / folder
    if not folder.is_dir():
        raise DocumentsError(f"Application folder not found: {folder}\n"
                             f"Folders in {base}: {_listing(base, dirs=True)}")

    resume = _find(folder, resume_name)
    if resume is None:
        raise DocumentsError(f"No resume named {resume_name!r} (ResumeFileName) in\n  {folder}\n"
                             f"Files there: {_listing(folder)}")
    _check_size(resume, "resume")

    docs = JobDocuments(folder=folder, resume=resume)
    if not cover_name:
        docs.warnings.append("no CoverLetterFileName in the Profile sheet: no cover letter uploaded")
    else:
        docs.cover_letter = _find(folder, cover_name)
        if docs.cover_letter is None:
            docs.warnings.append(f"no cover letter named {cover_name!r} in {folder}: skipped "
                                 f"(files there: {_listing(folder)})")
        else:
            _check_size(docs.cover_letter, "cover letter")
    return docs
