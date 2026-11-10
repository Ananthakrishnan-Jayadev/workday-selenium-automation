"""My Information: source, previous worker, country, name, address, phone.

Fill order follows the page and two lessons from the browser extension:
  * Country before Province (Province options depend on Country).
  * Phone number last: changing the dropdowns can re-render the phone section and wipe it.
"""
from __future__ import annotations

from typing import Callable

from core import waits
from core.models import AppData
from core.waits import Locator
from locators import my_information as L
from pages.base_page import BasePage, FillReport


class MyInformationPage(BasePage):
    NAME = "My Information"

    def is_displayed(self, timeout: float = 0) -> bool:
        return self.act.exists(L.PAGE, timeout)

    # ------------------------------------------------------------------ helpers
    def _present(self, locator: Locator) -> bool:
        return waits.is_present(self.driver, locator)

    def _step(self, report: FillReport, label: str, locator: Locator, value, action: Callable[[], object]) -> None:
        """Run one field action and record the outcome. One field failing never stops the rest."""
        if value in (None, "", []):
            report.skipped.append(f"{label} (no value in Excel)")
            return
        if not self._present(locator) and not waits.poll(lambda: self._present(locator), 3):
            # Some fields render a moment after the rest of the form (Citi: How did you hear,
            # "employed by Citi"), so give them a few seconds before calling them absent.
            report.skipped.append(f"{label} (not on this page)")
            return
        self.act.close_popups()  # a list left open by the previous field would cover this one
        try:
            result = action()
            if result is None or result is False:
                report.failed.append(label)
            else:
                report.filled.append(label)
        except Exception as exc:  # noqa: BLE001 - recorded and reported, page carries on
            self.log.warning("%s failed: %s", label, exc)
            report.failed.append(label)

    def _text(self, report: FillReport, label: str, locator: Locator, value: str, compare: str = "exact") -> None:
        self._step(report, label, locator, value,
                   lambda: self.act.type(locator, value, desc=label, compare=compare))

    # ------------------------------------------------------------------ fill
    def fill(self, data: AppData, job=None) -> FillReport:
        p = data.profile
        if not self.is_displayed(self.cfg.timeouts.page_change):
            raise AssertionError("My Information page is not displayed")
        # The page marker appears before the fields: wait for the form itself, or every field would be
        # skipped as "not on this page" (BMO run 2026-11-09: 14 fields skipped).
        if not waits.poll(lambda: any(self._present(x) for x in (L.FIRST_NAME, L.SOURCE_FIELD, L.COUNTRY_BUTTON)),
                          self.cfg.timeouts.default):
            self.log.warning("My Information: form fields did not appear within %ss", self.cfg.timeouts.default)
        self.act.settle(0.8)
        r = FillReport(page=self.NAME)

        # How did you hear about us: a search field on CIBC, a dropdown on BMO, so let the widget decide
        self._step(r, "How did you hear", L.SOURCE_FIELD, p.options("HowDidYouHear"),
                   lambda: self.w.fill_auto(L.SOURCE_FIELD[1], p.options("HowDidYouHear"), desc="How did you hear"))

        # Have you worked with us before
        prev = p.as_bool("PreviouslyWorkedHere")
        radio = L.previous_worker_radio("true" if prev else "false")
        self._step(r, "Previously worked here", radio, None if prev is None else prev,
                   lambda: self.w.select_radio(radio, desc=f"Previously worked here = {'Yes' if prev else 'No'}"))

        # Country (often pre-set; skipped if it already matches)
        self._step(r, "Country", L.COUNTRY_BUTTON, p.get("Country"),
                   lambda: self.w.select_dropdown(L.COUNTRY_BUTTON, p.options("Country"), desc="Country"))

        # Legal name
        self._text(r, "First name", L.FIRST_NAME, p.get("FirstName"))
        self._text(r, "Middle name", L.MIDDLE_NAME, p.get("MiddleName"))
        self._text(r, "Last name", L.LAST_NAME, p.get("LastName"))

        # Address
        self._text(r, "Address line 1", L.ADDRESS_LINE_1, p.get("AddressLine1"))
        self._text(r, "Address line 2", L.ADDRESS_LINE_2, p.get("AddressLine2"))
        self._text(r, "City", L.CITY, p.get("City"))
        self._step(r, "Province", L.PROVINCE_BUTTON, p.get("Province"),
                   lambda: self.w.select_dropdown(L.PROVINCE_BUTTON, p.options("Province"), desc="Province"))
        self._text(r, "Postal code", L.POSTAL_CODE, p.get("PostalCode"))

        # Phone: type and code first, number last
        self._step(r, "Phone type", L.PHONE_TYPE_BUTTON, p.get("PhoneType"),
                   lambda: self.w.select_dropdown(L.PHONE_TYPE_BUTTON, p.options("PhoneType"), desc="Phone type"))
        self._step(r, "Phone country code", L.PHONE_CODE_FIELD, p.get("PhoneCountryCode"),
                   lambda: self.w.fill_auto(L.PHONE_CODE_FIELD[1], p.options("PhoneCountryCode"),
                                            desc="Phone country code"))
        self._text(r, "Phone number", L.PHONE_NUMBER, p.get("Phone"), compare="digits")
        self._text(r, "Phone extension", L.PHONE_EXTENSION, p.get("PhoneExtension"))

        self.log.info(r.summary())
        return r
