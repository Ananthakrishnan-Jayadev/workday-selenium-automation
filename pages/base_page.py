"""Shared behaviour for every Workday page: where am I, Save and Continue, error detection."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from selenium.common.exceptions import WebDriverException

from core import waits
from core.session import Session
from core.text import normalize
from locators import auth as A
from locators import common as C
from locators import job_posting as J


@dataclass
class FillReport:
    """What happened to each field on a page."""
    page: str
    filled: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)   # no data in Excel, or field not on this tenant
    failed: list[str] = field(default_factory=list)    # tried and couldn't

    def summary(self) -> str:
        return (f"{self.page}: filled {len(self.filled)}, skipped {len(self.skipped)}, "
                f"failed {len(self.failed)}" + (f" → {', '.join(self.failed)}" if self.failed else ""))


@dataclass
class SaveResult:
    ok: bool
    page: str | None
    errors: list[str] = field(default_factory=list)


class BasePage:
    def __init__(self, s: Session):
        self.s = s
        self.driver = s.driver
        self.act = s.act
        self.w = s.widgets
        self.cfg = s.cfg
        self.log = s.log

    # ------------------------------------------------------------------ where am I
    def current_page(self) -> str | None:
        """Name of the current page: job_posting, sign_in, create_account, my_information, ..., or None."""
        try:
            for name, markers in C.PAGE_MARKERS.items():
                if any(waits.is_present(self.driver, m) for m in markers):
                    return name
            if waits.is_present(self.driver, A.SIGN_IN_SUBMIT_BUTTON):
                return "sign_in"
            if waits.is_present(self.driver, A.CREATE_ACCOUNT_SUBMIT_BUTTON):
                return "create_account"
            step = self.active_step_name()
            if step and normalize(step) in C.STEP_NAMES:
                return C.STEP_NAMES[normalize(step)]
            if waits.is_present(self.driver, C.JOB_POSTING_PAGE) or waits.is_present(self.driver, J.APPLY_BUTTON):
                return "job_posting"
        except WebDriverException:
            return None
        return None

    def active_step_name(self) -> str:
        els = self.driver.find_elements(*C.ACTIVE_STEP_NAME)
        return (els[0].text or "").strip() if els else ""

    def wait_for_page(self, names: set[str] | Callable[[str], bool], timeout: float | None = None) -> str | None:
        """Wait until the current page is one of `names` (or satisfies the predicate)."""
        accept = names if callable(names) else (lambda p: p in names)
        t = self.cfg.timeouts.page_change if timeout is None else timeout
        return waits.poll(lambda: (lambda p: p if p and accept(p) else None)(self.current_page()), t)

    # ------------------------------------------------------------------ errors
    def _texts(self, locator) -> list[str]:
        out: list[str] = []
        for el in waits.visible_elements(self.driver, locator):
            text = " ".join((el.text or "").split())
            if text.lower().startswith("error:"):
                text = text[6:].strip()
            if text and text not in out:
                out.append(text)
        return out

    def read_errors(self) -> list[str]:
        """Validation errors on the page, most specific first: per-field alerts, else the summary,
        else other banners, else the names of fields marked aria-invalid."""
        field_errors = self._texts(C.FIELD_ERROR)
        if field_errors:
            return field_errors
        summary = self._texts(C.ERROR_SUMMARY)
        if summary:
            return summary
        for loc in C.OTHER_ERRORS:
            other = self._texts(loc)
            if other:
                return other
        invalid = []
        for el in waits.visible_elements(self.driver, C.INVALID_FIELDS):
            label = el.get_attribute("aria-label") or el.get_attribute("name") or el.get_attribute("id")
            if label and f"invalid: {label}" not in invalid:
                invalid.append(f"invalid: {label}")
        return invalid

    # ------------------------------------------------------------------ navigation
    def save_and_continue(self) -> SaveResult:
        """Click Save and Continue and wait for the page to change. Returns errors if it doesn't."""
        before = self.current_page()
        loc, _ = waits.first_present(self.driver, C.NEXT_BUTTONS, self.cfg.timeouts.default, visible_only=True)
        self.act.click(loc, desc="Save and Continue")

        start = time.monotonic()
        while time.monotonic() - start < self.cfg.timeouts.page_change:
            page = self.current_page()
            if page and page != before:
                self.log.info("moved from %s to %s", before, page)
                return SaveResult(ok=True, page=page)
            if time.monotonic() - start > 2.0:
                errors = self.read_errors()
                if errors:
                    self.log.warning("Save and Continue on %s blocked by: %s", before, errors)
                    return SaveResult(ok=False, page=before, errors=errors)
            time.sleep(0.4)
        return SaveResult(ok=False, page=self.current_page(), errors=self.read_errors()
                          or ["page did not change within the timeout"])
