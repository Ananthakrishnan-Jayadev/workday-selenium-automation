"""Create Account / Sign In steps."""
from __future__ import annotations

from behave import when

from core.logger import get_logger
from pages.auth_page import APPLICATION_PAGES, AuthPage

log = get_logger()


@when("I sign in with the account for this company")
def step_sign_in(context):
    s = context.session
    page = AuthPage(s)

    current = page.wait_for_page(lambda p: p in APPLICATION_PAGES or p in ("sign_in", "create_account", "sign_in_chooser"))
    if current in APPLICATION_PAGES:
        log.info("already signed in (on %s)", current)
        return
    if current is None:
        raise AssertionError("Expected a sign-in form or the application, but found neither")

    result = page.sign_in(context.account)
    s.checkpoint("after_sign_in")
    if not result.ok:
        context.outcome["notes"] = f"sign-in: {result.message}"
        raise AssertionError(f"Sign-in failed for {context.account.email}: {result.message}")
