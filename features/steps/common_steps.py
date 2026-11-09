"""Steps shared by every job: loading data, opening the posting, page checks, completing a page."""
from __future__ import annotations

import sys

from behave import given, then, when

from core.logger import get_logger
from pages.base_page import BasePage
from pages.job_posting_page import JobPostingPage
from pages.my_experience_page import MyExperiencePage
from pages.my_information_page import MyInformationPage
from pages.questions_page import ApplicationQuestionsPage, SelfIdentifyPage, VoluntaryDisclosuresPage

log = get_logger()

# Page title in the feature file → (page name used by BasePage.current_page, page object class)
PAGES = {
    "my information": ("my_information", MyInformationPage),
    "my experience": ("my_experience", MyExperiencePage),
    "application questions": ("application_questions", ApplicationQuestionsPage),
    "voluntary disclosures": ("voluntary_disclosures", VoluntaryDisclosuresPage),
    "self identify": ("self_identify", SelfIdentifyPage),
}
PAGE_NAMES = {
    "my information": "my_information",
    "my experience": "my_experience",
    "application questions": "application_questions",
    "voluntary disclosures": "voluntary_disclosures",
    "self identify": "self_identify",
    "review": "review",
}


def _page_key(title: str) -> str:
    key = title.strip().lower()
    if key not in PAGE_NAMES:
        raise AssertionError(f"Unknown page {title!r}. Known: {', '.join(PAGE_NAMES)}")
    return key


@given("the job to apply for is loaded")
def step_job_loaded(context):
    job = context.job
    assert job.url.startswith("http"), f"Invalid job URL: {job.url!r}"
    log.info("job: %s (row %s)", job.company, job.row if job.row else "not in Jobs sheet")


@given("the applicant data is loaded from Excel")
def step_data_loaded(context):
    data = context.data
    missing = [k for k in ("FirstName", "LastName") if not data.profile.has(k)]
    assert not missing, f"Profile sheet is missing: {', '.join(missing)}"
    context.account = data.find_account(context.job)
    if context.account is None:
        context.outcome["notes"] = "no account in the Accounts sheet"
        raise AssertionError(f"No row in the Accounts sheet for company {context.job.company!r} "
                             f"or host {context.job.host!r}")
    log.info("using account %s for %s", context.account.email, context.job.company)


@when("I open the job posting")
def step_open_posting(context):
    page = JobPostingPage(context.session)
    page.open(context.job.url)
    context.session.checkpoint("job_posting")


@when("I start the application manually")
def step_start_manually(context):
    state = JobPostingPage(context.session).start_apply_manually()
    if state == "already_applied":
        context.outcome = {"status": "Skipped", "notes": "already applied"}
        context.session.checkpoint("already_applied")
        context.scenario.skip("Already applied to this job")
        return
    context.session.checkpoint(f"after_apply_manually_{state}")


@when('I complete the "{title}" page')
def step_complete_page(context, title):
    key = _page_key(title)
    if key not in PAGES:
        raise NotImplementedError(f'Completing the "{title}" page is not built yet')
    name, page_cls = PAGES[key]
    s = context.session
    page = page_cls(s)

    current = page.wait_for_page(lambda p: p not in ("sign_in", "create_account", "job_posting"))
    if current == "error":
        if not page.recover_from_error_page():
            raise AssertionError(f'Workday error page instead of "{title}", and refreshing did not fix it')
        current = page.wait_for_page(lambda p: p not in ("sign_in", "create_account", "job_posting", "error"))
    if current != name:
        log.info('"%s" page not shown (on %s), so skipping it', title, current)
        return
    if not page.wait_for_form(name):
        raise AssertionError(f'"{title}" form never loaded (refreshed twice)')

    # A page can repeat (e.g. Primary then Secondary application questions), so loop while we're on it.
    for _round in range(3):
        report = page.fill(context.data, job=context.job)
        s.checkpoint(f"{name}_filled")
        if report.failed:
            unanswered = getattr(page, "unanswered", [])
            detail = ("\nUnanswered required questions (add rows to the Questions sheet for next time):\n  - "
                      + "\n  - ".join(unanswered)) if unanswered else ""
            if s.pause_for_human(f"{title}: could not fill {len(report.failed)} field(s):\n  - "
                                 + "\n  - ".join(report.failed[:15]) + detail
                                 + "\nSee the log for the options that were available."):
                report.failed.clear()

        result = page.save_and_continue()
        while not result.ok:
            errors = "\n  - ".join(result.errors)
            if not s.pause_for_human(f'{title}: Save and Continue did not go through:\n  - {errors}'):
                raise AssertionError(f"{title}: Save and Continue blocked: {result.errors}")
            if page.current_page() != name:   # you clicked Save and Continue yourself
                break
            result = page.save_and_continue()

        if page.current_page() != name:
            break
        log.info('"%s" continues on another page, filling that too', title)


@then('I should be on the "{title}" page')
def step_on_page(context, title):
    expected = PAGE_NAMES[_page_key(title)]
    page = BasePage(context.session)
    actual = page.wait_for_page({expected})
    context.session.checkpoint(f"on_{expected}")
    assert actual == expected, (f'Expected the "{title}" page but on {page.current_page()!r} '
                                f'(step: {page.active_step_name()!r})')
    context.outcome = {"status": "InProgress", "notes": f"reached {title}"}


STATUS_KEYS = {"s": "Submitted", "k": "Skipped", "f": "Failed", "r": "ReadyForReview"}


@then("I wait for the user to review and submit")
def step_wait_for_user(context):
    """The script stops here. It never clicks Submit: you review the application in the browser,
    submit it yourself (or not), and say what happened."""
    s = context.session
    s.checkpoint("review_page")
    context.outcome = {"status": "ReadyForReview", "notes": "stopped on Review"}
    if s.cfg.browser.headless or not sys.stdin.isatty():
        log.info("Review reached; no terminal to ask, leaving status ReadyForReview")
        return
    print("\n" + "=" * 78)
    print(f"  REVIEW: {context.job.company} | {context.job.url}")
    print("  The application is filled in and waiting on the Review page.")
    print("  Check it in the browser and click Submit YOURSELF if you're happy with it.")
    print("  Then type:  s = submitted   k = skipped (not submitting)   f = failed   r = review later")
    print("=" * 78)
    while True:
        try:
            answer = input("  status [s/k/f/r]: ").strip().lower()[:1]
        except EOFError:
            answer = "r"
        if answer in STATUS_KEYS:
            break
    note = ""
    if answer in ("k", "f"):
        try:
            note = input("  note (optional): ").strip()
        except EOFError:
            pass
    context.outcome = {"status": STATUS_KEYS[answer], "notes": note or f"{STATUS_KEYS[answer]} by user"}
    log.info("user marked the job: %s %s", context.outcome["status"], note)
