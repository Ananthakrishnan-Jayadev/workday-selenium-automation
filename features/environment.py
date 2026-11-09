"""behave hooks (the equivalent of Cucumber's @Before / @After)."""
from __future__ import annotations

import sys
from pathlib import Path

# Make core/, pages/, locators/ importable from the step files.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import load_config  # noqa: E402
from core.driver import create_driver  # noqa: E402
from core.excel_reader import load_app_data  # noqa: E402
from core.excel_writer import update_job_status  # noqa: E402
from core.logger import get_logger, setup_logging  # noqa: E402
from core.models import Job  # noqa: E402
from core.reporter import Reporter  # noqa: E402
from core.session import Session  # noqa: E402


def _resolve_job(context) -> Job:
    ud = context.config.userdata
    if ud.get("url"):
        return context.data.job_for_url(ud["url"])
    if ud.get("row"):
        return context.data.job_for_row(int(ud["row"]))
    pending = [j for j in context.data.jobs if j.status.lower() == "pending"]
    if pending:
        return pending[0]
    raise SystemExit("No job given. Use  behave -D url=<job url>  or  -D row=<Jobs sheet row>, "
                     "or mark a row as Pending in the Jobs sheet.")


def before_all(context):
    context.cfg = load_config(context.config.userdata)
    setup_logging()
    context.data = load_app_data(context.cfg.paths.workbook_path)


def before_scenario(context, scenario):
    context.job = _resolve_job(context)
    reporter = Reporter(context.cfg.paths.reports_path, context.job.company)
    setup_logging(reporter.log_file)
    log = get_logger()
    log.info("=" * 70)
    log.info("job: %s | %s", context.job.company, context.job.url)
    log.info("run folder: %s", reporter.run_dir)
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
