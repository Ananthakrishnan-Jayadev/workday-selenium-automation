"""Write a job's outcome back to the Jobs sheet (Status, LastRun, Notes)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from core.logger import get_logger


def update_job_status(workbook: Path, row: int, status: str, notes: str = "") -> bool:
    """Update one Jobs row. Returns False (and logs why) instead of raising: a run's result must never
    be lost because the workbook is open in Excel/LibreOffice or was moved."""
    log = get_logger()
    try:
        wb = load_workbook(workbook)
        ws = next((wb[n] for n in wb.sheetnames if n.lower() == "jobs"), None)
        if ws is None:
            log.warning("no Jobs sheet in %s; status not written", workbook)
            return False
        headers = {str(c.value).strip().lower(): c.column for c in ws[1] if c.value}
        for name, value in (("status", status), ("lastrun", datetime.now().strftime("%Y-%m-%d %H:%M")),
                            ("notes", notes[:500])):
            if name in headers:
                ws.cell(row=row, column=headers[name], value=value)
        wb.save(workbook)
        log.info("Jobs sheet row %d → %s", row, status)
        return True
    except PermissionError:
        log.warning("could not write the Jobs sheet (is the workbook open in Excel/LibreOffice?). "
                    "Status for row %d was: %s", row, status)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not write the Jobs sheet: %s (row %d status %s)", exc, row, status)
    return False
