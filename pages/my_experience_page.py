"""My Experience: resume, work experience, education, certifications, languages, skills, websites, LinkedIn.

Repeatable sections (work, education, languages, ...) start empty with an Add button. For entry i the
page clicks Add until i entries exist, then fills fields inside that entry only. Entries are found by
their first field (e.g. formField-jobTitle) and tagged data-wdauto="work-1", "work-2", ... so their
fields can be addressed with plain CSS. Entries that already exist (from a previous run or a parsed
resume) are filled in place, not duplicated.
"""
from __future__ import annotations

from selenium.webdriver.common.by import By

from core import waits
from core.models import AppData, EducationEntry, LanguageEntry, WorkEntry
from core.text import normalize, split_list
from locators import my_experience as L
from pages.base_page import BasePage, FillReport

By_CSS = By.CSS_SELECTOR

_JS_TAG_ENTRIES = """
const [selectors, tag] = arguments;
document.querySelectorAll('[data-wdauto^="' + tag + '-"]').forEach(e => e.removeAttribute('data-wdauto'));
let fields = [], sel = null;
for (const s of selectors) {
    fields = [...document.querySelectorAll(s)].filter(f => !f.closest('[data-automation-id="selectedItemList"]'));
    if (fields.length) { sel = s; break; }
}
fields.forEach((f, i) => {
    let c = f;
    while (c.parentElement && c.parentElement !== document.body &&
           c.parentElement.querySelectorAll(sel).length === 1) c = c.parentElement;
    // c is now the largest container holding exactly this one entry
    c.setAttribute('data-wdauto', tag + '-' + (i + 1));
});
return fields.length;
"""

# Entry containers climb up to just below the element that holds 2+ entries. For the FIRST entry,
# when it's the only one, that climb goes all the way up the page, so cap it at the section.
_JS_TAG_SINGLE_GUARD = """
const [tag, heading] = arguments;
const el = document.querySelector('[data-wdauto="' + tag + '-1"]');
if (!el) return false;
const h = [...document.querySelectorAll('h4')].find(x => x.textContent.trim() === heading);
const section = h && h.closest('div[role="group"]');
if (section && el.contains(section)) {
    // climbed past the section: re-tag the section's own content instead
    el.removeAttribute('data-wdauto');
    section.setAttribute('data-wdauto', tag + '-1');
}
return true;
"""


class MyExperiencePage(BasePage):
    NAME = "My Experience"

    def is_displayed(self, timeout: float = 0) -> bool:
        return self.act.exists(L.PAGE, timeout)

    # ================================================================== entries
    def _count_entries(self, kind: str) -> int:
        n = self.driver.execute_script(_JS_TAG_ENTRIES, L.ENTRY_FIRST_FIELD[kind], kind)
        if n == 1:
            self.driver.execute_script(_JS_TAG_SINGLE_GUARD, kind, L.SECTION_HEADINGS[kind])
        return n

    def _section_present(self, kind: str) -> bool:
        return waits.is_present(self.driver, L.section(L.SECTION_HEADINGS[kind]))

    def _entry(self, kind: str, i: int) -> str | None:
        """CSS for entry i (1-based), clicking the section's Add button as needed."""
        heading = L.SECTION_HEADINGS[kind]
        for _attempt in range(3):
            n = self._count_entries(kind)
            if n >= i:
                return f'[data-wdauto="{kind}-{i}"]'
            buttons = [b for b in L.add_buttons(heading) if waits.is_visible(self.driver, b)]
            if not buttons:
                self.log.warning("%s: no Add button found", heading)
                return None
            self.act.click(buttons[0], desc=f"{heading}: Add")
            if not waits.poll(lambda: self._count_entries(kind) > n, self.cfg.timeouts.default):
                self.log.debug("%s: Add clicked but no new entry appeared", heading)
        self.s.checkpoint(f"{kind}_entry_{i}_missing")
        return None

    def _field(self, entry: str, aids: list[str]) -> str | None:
        """CSS of the first of `aids` present inside the entry (re-tags first, in case of a re-render)."""
        for a in aids:
            css = f'{entry} [data-automation-id="{a}"]'
            if waits.is_present(self.driver, (By_CSS, css)):
                return css
        return None

    def _do(self, r: FillReport, label: str, value, fn) -> None:
        if value in (None, "", []):
            r.skipped.append(f"{label} (no value in Excel)")
            return
        self.act.close_popups()
        try:
            result = fn()
        except Exception as exc:  # noqa: BLE001 - one field never stops the page
            self.log.warning("%s failed: %s", label, exc)
            result = None
        if result is None or result is False:
            r.failed.append(label)
        else:
            r.filled.append(label)

    def _fill_in(self, r: FillReport, kind: str, i: int, label: str, aids: list[str], value, multi=False,
                 loose=False):
        entry = f'[data-wdauto="{kind}-{i}"]'
        self._count_entries(kind)  # re-tag in case the entry re-rendered
        css = self._field(entry, aids)
        if css is None:
            if value not in (None, "", []):
                r.skipped.append(f"{label} (not on this page)")
            return
        self._do(r, label, value, lambda: self.w.fill_auto(css, value, desc=label, multi=multi, loose=loose))

    # ================================================================== sections
    def fill_resume(self, r: FillReport, path: str) -> None:
        if not path:
            r.skipped.append("Resume (no ResumePath in Profile)")
            return
        if not self._section_present("resume"):
            r.skipped.append("Resume (not on this page)")
            return
        self._do(r, "Resume", path, lambda: self.w.upload_file(L.RESUME_FILE_INPUT, path, L.RESUME_SECTION,
                                                               desc="Resume"))

    def fill_work(self, r: FillReport, entries: list[WorkEntry]) -> None:
        if entries and not self._section_present("work"):
            r.skipped.append("Work Experience (not on this page)")
            return
        for i, e in enumerate(entries, 1):
            tag = f"Work {i} ({e.job_title})"
            if self._entry("work", i) is None:
                r.failed.append(f"{tag}: could not add entry")
                continue
            self._fill_in(r, "work", i, f"{tag} title", L.WORK["job_title"], e.job_title)
            self._fill_in(r, "work", i, f"{tag} company", L.WORK["company"], e.company)
            self._fill_in(r, "work", i, f"{tag} location", L.WORK["location"], e.location)
            # Set 'currently work here' before the dates: ticking it removes the end date.
            entry = f'[data-wdauto="work-{i}"]'
            cur = self._field(entry, L.WORK["current"])
            if cur:
                self._do(r, f"{tag} currently work here", True, lambda: self.w.set_checkbox(
                    (By_CSS, f'{cur} input[type="checkbox"]'), e.currently_work_here,
                    desc=f"{tag} currently work here"))
            start = self._field(entry, L.WORK["start"])
            if start and e.start_year:
                self._do(r, f"{tag} start date", e.start_year,
                         lambda: self.w.fill_date(start, f"{tag} start", month=e.start_month, year=e.start_year))
            if not e.currently_work_here and e.end_year:
                self._count_entries("work")
                end = self._field(entry, L.WORK["end"])
                if end:
                    self._do(r, f"{tag} end date", e.end_year,
                             lambda: self.w.fill_date(end, f"{tag} end", month=e.end_month, year=e.end_year))
                else:
                    r.failed.append(f"{tag} end date (field missing)")
            self._fill_in(r, "work", i, f"{tag} description", L.WORK["description"], e.description)

    def fill_education(self, r: FillReport, entries: list[EducationEntry]) -> None:
        if entries and not self._section_present("education"):
            r.skipped.append("Education (not on this page)")
            return
        for i, e in enumerate(entries, 1):
            tag = f"Education {i} ({e.school})"
            if self._entry("education", i) is None:
                r.failed.append(f"{tag}: could not add entry")
                continue
            self._fill_in(r, "education", i, f"{tag} school", L.EDUCATION["school"], e.school)
            self._fill_in(r, "education", i, f"{tag} degree", L.EDUCATION["degree"], e.degree)
            # loose: a close option ('Artificial Intelligence and Robotics', 'Data Science') beats the fallbacks
            self._fill_in(r, "education", i, f"{tag} field of study", L.EDUCATION["field_of_study"], e.field_of_study,
                          loose=True)
            self._fill_in(r, "education", i, f"{tag} GPA", L.EDUCATION["gpa"], e.gpa)
            self._fill_in(r, "education", i, f"{tag} start year", L.EDUCATION["start_year"], e.start_year)
            self._fill_in(r, "education", i, f"{tag} end year", L.EDUCATION["end_year"], e.end_year)

    def fill_certifications(self, r: FillReport, data: AppData) -> None:
        if not data.certifications:
            return
        if not self._section_present("certifications"):
            r.skipped.append("Certifications (no such section on this tenant)")
            return
        for i, c in enumerate(data.certifications, 1):
            tag = f"Certification {i} ({c.name})"
            if self._entry("certifications", i) is None:
                r.failed.append(f"{tag}: could not add entry")
                continue
            self._fill_in(r, "certifications", i, f"{tag} name", L.CERTIFICATION["name"], c.name)
            self._fill_in(r, "certifications", i, f"{tag} number", L.CERTIFICATION["number"], c.number)
            if c.expiry_year:
                css = self._field(f'[data-wdauto="certifications-{i}"]', L.CERTIFICATION["expiry"])
                if css:
                    self._do(r, f"{tag} expiry", c.expiry_year,
                             lambda: self.w.fill_date(css, f"{tag} expiry", month=c.expiry_month, year=c.expiry_year))

    def fill_languages(self, r: FillReport, entries: list[LanguageEntry]) -> None:
        if entries and not self._section_present("languages"):
            r.skipped.append("Languages (not on this page)")
            return
        for i, e in enumerate(entries, 1):
            tag = f"Language {i} ({e.language})"
            entry = self._entry("languages", i)
            if entry is None:
                r.failed.append(f"{tag}: could not add entry")
                continue
            lang_btn = (By_CSS, f"{entry} {L.LANGUAGE_BUTTON_CSS}")
            if not waits.is_present(self.driver, lang_btn):
                lang_btn = (By_CSS, f'{entry} button[aria-haspopup="listbox"]')
            self._do(r, f"{tag} language", e.language,
                     lambda: self.w.select_dropdown(lang_btn, [e.language], desc=f"{tag} language"))

            # Proficiency dropdowns: every other listbox button in the entry. Their aria-label starts with
            # the type, e.g. "Reading Fluent Required". Re-read by id each time (Workday re-renders them).
            self._count_entries("languages")
            ids = self.driver.execute_script(
                "return [...document.querySelectorAll(arguments[0] + ' button[aria-haspopup=\"listbox\"]')]"
                ".filter(b => b.getAttribute('name') !== 'language').map(b => b.id).filter(Boolean);", entry)
            for bid in ids:
                btn = (By_CSS, f'[id="{bid}"]')
                aria = (self.driver.find_element(*btn).get_attribute("aria-label") or "") if \
                    waits.is_present(self.driver, btn) else ""
                kind = aria.split(" ")[0] if aria else "Proficiency"
                wanted = e.proficiency_for(kind)
                self._do(r, f"{tag} {kind}", wanted,
                         lambda: self.w.select_dropdown(btn, wanted, desc=f"{tag} {kind}"))
            # Checkboxes such as "I am fluent in this language" are left alone.

    def fill_skills(self, r: FillReport, skills: list[str]) -> None:
        if not skills:
            return
        if not waits.is_present(self.driver, L.SKILLS_INPUT):
            r.skipped.append("Skills (not on this page)")
            return
        for skill in skills:
            self._do(r, f"Skill {skill}", skill,
                     lambda: self.w.select_prompt(L.SKILLS_FIELD, L.SKILLS_INPUT, split_list(skill),
                                                  desc=f"Skill {skill}", multi=True))
        self.act.close_popups()

    def fill_websites(self, r: FillReport, urls: list[str]) -> None:
        if not urls:
            return
        if not self._section_present("websites"):
            r.skipped.append("Websites (not on this page)")
            return
        for i, url in enumerate(urls, 1):
            entry = self._entry("websites", i)
            if entry is None:
                r.failed.append(f"Website {i}: could not add entry")
                continue
            css = self._field(entry, ["formField-url", "formField-webAddress", "formField-website"]) or entry
            self._do(r, f"Website {i}", url, lambda: self.act.type((By_CSS, f"{css} input"), url, desc=f"Website {i}"))

    # ================================================================== page
    def fill(self, data: AppData, job=None) -> FillReport:
        if not self.is_displayed(self.cfg.timeouts.page_change):
            raise AssertionError("My Experience page is not displayed")
        self.act.settle(0.5)
        p = data.profile
        r = FillReport(page=self.NAME)

        self.fill_resume(r, p.get("ResumePath"))
        self.fill_work(r, data.work)
        self.fill_education(r, data.education)
        self.fill_certifications(r, data)
        self.fill_languages(r, data.languages)
        self.fill_skills(r, data.skills)
        self.fill_websites(r, split_list(p.get("Website")))
        if p.get("LinkedIn") and waits.is_present(self.driver, L.LINKEDIN):
            self._do(r, "LinkedIn", p.get("LinkedIn"),
                     lambda: self.act.type(L.LINKEDIN, p.get("LinkedIn"), desc="LinkedIn"))

        self.act.close_popups()
        self.log.info(r.summary())
        return r

