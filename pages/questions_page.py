"""Questionnaire pages: every question is answered from the Questions sheet.

For each question on the page:
  1. read its text and whether it's required
  2. find the rule for it in the Questions sheet (keywords → answer, company/page aware)
  3. work out what kind of control it is (dropdown / prompt / radio / checkboxes / text / date)
     and fill it with the answer: Excel says WHAT to answer, the code works out HOW
Required questions with no rule (or a rule with a blank answer) are reported, together with the
options the dropdown offers, so you can add the row to the Questions sheet.
"""
from __future__ import annotations

from selenium.webdriver.common.by import By

from core.answers import find_rule
from core.models import AppData, Job
from locators import questions as L
from pages.base_page import BasePage, FillReport


class QuestionsPage(BasePage):
    NAME = "Application Questions"
    PAGE_SCOPE = "Application"       # matched against the Questions sheet's Page column
    ROOT_CSS = L.ROOT_CSS

    def _root_css(self) -> str:
        """The questionnaire root actually on the page (Primary or Secondary)."""
        for css in (c.strip() for c in self.ROOT_CSS.split(",")):
            if self.driver.find_elements(By.CSS_SELECTOR, css):
                return css
        return self.ROOT_CSS.split(",")[0].strip()

    def questions(self) -> list[tuple[str, str, bool]]:
        """[(formField automation id, question text, required)] in page order."""
        return self.driver.execute_script(L.JS_QUESTIONS, self.ROOT_CSS) or []

    def fill(self, data: AppData, job: Job | None = None) -> FillReport:
        self.act.settle(0.5)
        r = FillReport(page=self.NAME)
        company = job.company if job else ""
        questions = self.questions()
        if not questions:
            self.log.warning("%s: no questions found on the page", self.NAME)
        self.unanswered: list[str] = []

        for field_aid, text, required in questions:
            css = f'{self._root_css()} [data-automation-id="{field_aid}"]'
            short = text if len(text) <= 90 else text[:87] + "..."
            rule = find_rule(data.questions, text, company=company, page=self.PAGE_SCOPE)
            current = self.w.current_answer(css)

            if rule is None or not rule.answers:
                if current:
                    self.log.info("Q: %s → already answered %r (no rule)", short, current)
                    r.skipped.append(f"{short} (already answered)")
                elif required:
                    self._report_unknown(r, css, short, rule)
                else:
                    self.log.info("Q: %s → optional, no rule, left blank", short)
                    r.skipped.append(f"{short} (optional, no rule)")
                continue

            self.act.close_popups()
            try:
                # exact: an option must equal the answer or start with it; otherwise the next
                # fallback column is tried ('Man' must not pick 'Trans Man')
                result = self.w.fill_auto(css, rule.answers, desc=f"Q: {short[:60]}", exact=True)
            except Exception as exc:  # noqa: BLE001 - one question never stops the page
                self.log.warning("Q: %s failed: %s", short, exc)
                result = None
            if result:
                self.log.info("Q: %s → %r (Questions row %s)", short, result, rule.row)
                r.filled.append(short)
            else:
                r.failed.append(f"{short} (none of {rule.answers} from Questions row {rule.row} is an option;"
                                f" add the right one as a fallback)")

        self.act.close_popups()
        self.log.info(r.summary())
        return r

    def _report_unknown(self, r: FillReport, css: str, short: str, rule) -> None:
        options = []
        if self.w.detect(css) == "dropdown":
            options = self.w.dropdown_options((By.CSS_SELECTOR, f'{css} button[aria-haspopup="listbox"]'))
        why = f"answer is blank in Questions row {rule.row}" if rule else "no matching row in the Questions sheet"
        self.log.warning("Q (required, unanswered): %s\n    %s%s", short, why,
                         f"\n    options: {options}" if options else "")
        self.unanswered.append(f"{short}" + (f"\n      options: {', '.join(options)}" if options else ""))
        r.failed.append(f"{short} ({why})")


class ApplicationQuestionsPage(QuestionsPage):
    pass


class VoluntaryDisclosuresPage(QuestionsPage):
    NAME = "Voluntary Disclosures"
    PAGE_SCOPE = "Disclosure"
    ROOT_CSS = L.DISCLOSURES_ROOT_CSS


class SelfIdentifyPage(QuestionsPage):
    NAME = "Self Identify"
    PAGE_SCOPE = "SelfIdentify"
    ROOT_CSS = L.SELF_IDENTIFY_ROOT_CSS
