"""Job posting → Apply → 'Start Your Application' popup → Apply Manually."""
from __future__ import annotations

from core import waits
from core.waits import TimeoutException
from locators import common as C
from locators import job_posting as L
from pages.base_page import BasePage

# Pages that mean "the application has started"
AFTER_APPLY = {"sign_in", "create_account", "my_information", "my_experience", "application_questions",
               "voluntary_disclosures", "self_identify", "review"}


class JobPostingPage(BasePage):
    def open(self, url: str) -> None:
        self.log.info("opening %s", url)
        self.driver.get(url)
        try:
            _, el = waits.first_present(self.driver, [L.POSTING_HEADER, C.APPLY_FLOW],
                                        self.cfg.timeouts.page_change, visible_only=True)
        except TimeoutException as exc:
            raise AssertionError(f"Job posting did not load: {url} (title: {self.driver.title!r})") from exc
        self.log.info("loaded: %s", (el.text or self.driver.title).strip())

    def job_title(self) -> str:
        for loc in (L.POSTING_HEADER, C.JOB_TITLE_HEADING):
            els = waits.visible_elements(self.driver, loc)
            if els:
                return els[0].text.strip()
        return ""

    def is_already_applied(self) -> bool:
        return waits.is_visible(self.driver, L.ALREADY_APPLIED)

    def start_apply_manually(self) -> str:
        """Click Apply, then Apply Manually. Returns the page that loads (sign_in, create_account, my_information...)."""
        page = self.current_page()
        if page in AFTER_APPLY:
            self.log.info("application already started (%s)", page)
            return page

        self.act.click(L.APPLY_BUTTON, desc="Apply")

        # Most tenants open a popup; some go straight into the apply flow.
        def popup_or_flow():
            if waits.is_visible(self.driver, L.APPLY_MANUALLY):
                return "popup"
            p = self.current_page()
            return p if p in AFTER_APPLY else None

        state = waits.poll(popup_or_flow, self.cfg.timeouts.default)
        if state is None:
            if self.is_already_applied():
                return "already_applied"
            raise AssertionError("Clicked Apply but neither the 'Start Your Application' popup nor the "
                                 "application form appeared")
        if state == "popup":
            self.act.click(L.APPLY_MANUALLY, desc="Apply Manually")
            state = self.wait_for_page(AFTER_APPLY)
            if state is None:
                if self.is_already_applied():
                    return "already_applied"
                raise AssertionError("Clicked Apply Manually but no sign-in page or application form appeared")
        self.log.info("application started: %s", state)
        return state
