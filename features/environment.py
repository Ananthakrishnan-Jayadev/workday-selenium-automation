"""behave hooks (the equivalent of Cucumber's @Before / @After)."""
from __future__ import annotations

import sys
from pathlib import Path

# Make core/, pages/, locators/ importable from the step files.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import load_config  # noqa: E402
from core.documents import DocumentsError, resolve_documents  # noqa: E402
from core.driver import create_driver  # noqa: E402
from core.excel_reader import WorkbookError, load_app_data  # noqa: E402
from core.excel_writer import update_job_status  # noqa: E402
from core.logger import get_logger, setup_logging  # noqa: E402
from core.models import Job  # noqa: E402
from core.reporter import Reporter  # noqa: E402
from core.session import Session  # noqa: E402


class SetupError(Exception):
    """A problem with the run's setup (no job, bad row, workbook missing). Shown as a clear message."""


def _fatal(message: str) -> None:
    """Print a readable error and stop. behave only prints 'HOOK-ERROR ...: SystemExit' for an
    exception raised in a hook, so the explanation is printed here first."""
    bar = "=" * 78
    print(f"\n{bar}\n  CANNOT START\n", file=sys.stderr)
    for line in message.splitlines():
        print(f"  {line}", file=sys.stderr)
    print(bar + "\n", file=sys.stderr, flush=True)
    raise SystemExit(1)


def _jobs_overview(context) -> str:
    jobs = context.data.jobs
    if not jobs:
        return "The Jobs sheet has no job URLs."
    rows = [f"  row {j.row}: {j.status or '(blank)':<15} {j.company or '?':<10} {j.url[:70]}" for j in jobs]
    return "Jobs sheet:\n" + "\n".join(rows)


def _resolve_job(context) -> Job:
    ud = context.config.userdata
    if ud.get("url"):
        return context.data.job_for_url(ud["url"])
    if ud.get("row"):
        try:
            return context.data.job_for_row(int(ud["row"]))
        except (LookupError, ValueError):
            raise SetupError(f"There is no job on row {ud['row']} of the Jobs sheet.\n\n{_jobs_overview(context)}")
    # Pending jobs first, then Failed ones (so a run that failed is retried by a plain `behave`).
    for wanted in ("pending", "failed"):
        jobs = [j for j in context.data.jobs if j.status.lower() == wanted]
        if jobs:
            return jobs[0]
    raise SetupError(
        "No job to run: there is no row with Status = Pending or Failed in the Jobs sheet.\n\n"
        f"{_jobs_overview(context)}\n\n"
        "Do one of these:\n"
        "  - add the job URL to the Jobs sheet with Status = Pending, then run:  behave\n"
        "  - run a specific row:   behave -D row=<row number>\n"
        "  - run any URL:          behave -D url=\"<job url>\"")


def before_all(context):
    context.cfg = load_config(context.config.userdata)
    setup_logging()
    try:
        context.data = load_app_data(context.cfg.paths.workbook_path)
    except WorkbookError as exc:
        _fatal(str(exc))
    except PermissionError:
        _fatal(f"Can't read {context.cfg.paths.workbook_path}.\nIs it open in Excel/LibreOffice with a lock? "
               "Close it and try again.")
    try:
        context.job = _resolve_job(context)
    except SetupError as exc:
        _fatal(str(exc))
    # The job's resume / cover letter: checked before the browser opens, so a wrong or missing file
    # never gets as far as the application.
    try:
        docs = resolve_documents(context.data.profile, context.job, context.config.userdata.get("folder", ""))
    except DocumentsError as exc:
        _fatal(f"{exc}\n\nJob: {context.job.company} | {context.job.url}")
    context.job.resume, context.job.cover_letter = docs.resume, docs.cover_letter
    context.documents = docs


def before_scenario(context, scenario):
    reporter = Reporter(context.cfg.paths.reports_path, context.job.company)
    setup_logging(reporter.log_file)
    log = get_logger()
    log.info("=" * 70)
    log.info("job: %s | %s", context.job.company, context.job.url)
    log.info("run folder: %s", reporter.run_dir)
    docs = context.documents
    log.info("application folder: %s", docs.folder)
    log.info("resume: %s | cover letter: %s", docs.resume.name,
             docs.cover_letter.name if docs.cover_letter else "none")
    for w in docs.warnings:
        log.warning("cover letter: %s", w)
    driver = create_driver(context.cfg.browser)
    context.session = Session.create(driver, context.cfg, reporter)
    context.outcome = {"status": "Failed", "notes": ""}


def after_step(context, step):
    if step.status == "failed":
        s = context.session
        log = get_logger()
        log.error("STEP FAILED: %s", step.name)
        if step.error_message:
            log.error("%s", step.error_message.strip().splitlines()[-1][:500])
        try:
            log.error("url: %s", s.driver.current_url)
        except Exception:  # noqa: BLE001
            pass
        s.reporter.capture(s.driver, f"FAILED_{step.name}", html=True)


def after_scenario(context, scenario):
    s = getattr(context, "session", None)
    if s is None:
        return
    log = get_logger()
    failed = scenario.status == "failed"
    if failed and context.outcome.get("status") not in ("Skipped",):
        context.outcome["status"] = "Failed"
        if not context.outcome.get("notes"):
            failed_steps = [st for st in scenario.steps if st.status == "failed"]
            if failed_steps:
                msg = (failed_steps[0].error_message or "").strip().splitlines()
                context.outcome["notes"] = f"{failed_steps[0].name}: {msg[-1] if msg else ''}"[:300]

    s.reporter.write_result(url=context.job.url, company=context.job.company, row=context.job.row,
                            resume=str(context.job.resume or ""), cover_letter=str(context.job.cover_letter or ""),
                            **context.outcome)
    if context.job.row and context.outcome.get("status") != "InProgress":
        update_job_status(context.cfg.paths.workbook_path, context.job.row, context.outcome["status"],
                          context.outcome.get("notes", ""))
    log.info("result: %s %s", context.outcome["status"], context.outcome.get("notes", ""))
    log.info("run folder: %s", s.reporter.run_dir)

    answered = context.outcome.get("status") in ("Submitted", "Skipped", "Failed", "ReadyForReview") and not failed
    keep_open = (failed and s.cfg.behaviour.keep_browser_open_on_failure) or (s.cfg.behaviour.pause_at_end
                                                                            and not answered)
    if keep_open and sys.stdin.isatty() and not s.cfg.browser.headless:
        try:
            input("\nBrowser left open for you to inspect. Press Enter to close it... ")
        except EOFError:
            pass
    try:
        s.driver.quit()
    except Exception:  # noqa: BLE001
        pass
