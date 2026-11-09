"""Create Account / Sign In. One form, two modes. V1 only signs in to existing accounts."""
from __future__ import annotations

from dataclasses import dataclass

from core import waits
from core.logger import mask
from core.models import Account
from locators import auth as L
from pages.base_page import BasePage

APPLICATION_PAGES = {"my_information", "my_experience", "application_questions",
                     "voluntary_disclosures", "self_identify", "review"}


@dataclass
class SignInResult:
    ok: bool
    page: str | None = None
    message: str = ""


class AuthPage(BasePage):
    def mode(self) -> str | None:
        """'sign_in', 'create_account', or None if the form isn't showing."""
        if waits.is_visible(self.driver, L.SIGN_IN_SUBMIT_BUTTON):
            return "sign_in"
        if waits.is_visible(self.driver, L.CREATE_ACCOUNT_SUBMIT_BUTTON):
            return "create_account"
        return None

    def switch_to_sign_in(self) -> None:
        if self.mode() == "sign_in":
            return
        self.act.click(L.SIGN_IN_LINK, desc="'Sign In' link")
        if not waits.poll(lambda: self.mode() == "sign_in", self.cfg.timeouts.default):
            raise AssertionError("Clicked 'Sign In' but the sign-in form did not appear")
        self.log.info("switched to the Sign In form")

    def _sign_in_errors(self) -> list[str]:
        msgs = []
        for loc in L.SIGN_IN_ERRORS:
            for el in waits.visible_elements(self.driver, loc):
                text = " ".join((el.text or "").split())
                if text and text not in msgs:
                    msgs.append(text)
        return msgs

    def sign_in(self, account: Account) -> SignInResult:
        if not account.password:
            return SignInResult(False, message=f"No password for {account.company}: "
                                               f"check {account.password_source}")
        self.switch_to_sign_in()
        self.log.info("signing in as %s (password %s)", account.email, mask(account.password))

        self.act.type(L.EMAIL, account.email, desc="email")
        self.act.type(L.PASSWORD, account.password, secret=True, desc="password", commit=False)

        # The visible button is covered by a click_filter div. Click the first target that exists.
        target, _ = waits.first_present(self.driver, L.SIGN_IN_SUBMIT_TARGETS, self.cfg.timeouts.short)
        self.act.click(target, desc="Sign In")

        def outcome():
            page = self.current_page()
            if page in APPLICATION_PAGES:
                return ("ok", page)
            errors = self._sign_in_errors()
            if errors:
                return ("error", "; ".join(errors))
            return None

        result = waits.poll(outcome, self.cfg.timeouts.page_change)
        if result is None:
            return SignInResult(False, self.current_page(),
                                "Still on the sign-in page after clicking Sign In (no error shown). "
                                "Possibly a verification step or CAPTCHA.")
        if result[0] == "ok":
            self.log.info("signed in → %s", result[1])
            return SignInResult(True, result[1])
        return SignInResult(False, self.current_page(), result[1])
