"""Workday's custom form controls.

* Dropdown: `button[aria-haspopup="listbox"]` → click → a [role=listbox] popup (appended at the end of
  <body>) → click the [role=option]. These are NOT <select> elements, so Selenium's Select() won't work.
* Prompt (multiselect / search) field: type into the input, press Enter to search, wait for
  [data-automation-id=promptOption] results (or "No matches found"), click the match. The chosen value
  shows up as a "pill" in selectedItemList. Some prompts are hierarchical: clicking a category opens a
  sub-list. Write such values as "Category > Value" in Excel.
* Radio / checkbox: the input may be visually hidden, so click its <label> and verify the state.

Every select_* method returns the label it ended up with, or None if it couldn't (and logs the options
that were available, so the Excel value can be corrected).
"""
from __future__ import annotations

import re
import time
from typing import Sequence

from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement

from core import waits
from core.actions import Actions
from core.logger import get_logger
from core.text import (best_match, closest_by_words, contains_words, key_words, match_score, normalize,
                       split_list, strong_match, word_overlap)
from core.waits import Locator
from locators import common as C

_JS_VISIBLE_PROMPT_OPTIONS = """
return [...document.querySelectorAll('[data-automation-id="promptOption"]')].filter(o =>
    o.getClientRects().length > 0 &&
    !o.closest('[data-automation-id="selectedItemList"], [data-automation-id="selectedItem"]'));
"""

# The checkbox (multi-select) or radio button (sub-lists) that belongs to one prompt option row,
# not a neighbouring row's.
_JS_OPTION_CHECKBOX = """
let el = arguments[0];
for (let i = 0; i < 5 && el; i++) {
    const cb = el.querySelector('input[type="checkbox"][data-automation-id="checkboxPanel"], '
                              + 'input[type="radio"][data-automation-id="radioBtn"]');
    if (cb) return cb;
    el = el.parentElement;
    if (!el || el.querySelectorAll('[data-automation-id="promptOption"]').length > 1) break;
}
return null;
"""


def _label(el: WebElement) -> str:
    try:
        return (el.get_attribute("data-automation-label") or el.text or "").strip()
    except StaleElementReferenceException:
        return ""


class Widgets:
    def __init__(self, act: Actions):
        self.act = act
        self.driver = act.driver
        self.cfg = act.cfg
        self.log = get_logger()
        # Optional hook (set by Session): save a screenshot + HTML when a search finds nothing.
        self.debug_capture = None

    # ============================================================== dropdown (button + listbox)
    def dropdown_value(self, button: Locator) -> str:
        try:
            return (self.act.find(button, self.cfg.timeouts.short).text or "").strip()
        except WebDriverException:
            return ""

    def _open_listbox(self) -> WebElement | None:
        def find():
            boxes = [b for b in waits.visible_elements(self.driver, C.OPEN_LISTBOX)
                     if b.find_elements(*C.LISTBOX_OPTION)]
            return boxes[-1] if boxes else None  # Workday appends popups at the end of <body>
        return waits.poll(find, self.cfg.timeouts.short)

    def _listbox_options(self, listbox: WebElement) -> tuple[list[WebElement], list[str]]:
        options = listbox.find_elements(*C.LISTBOX_OPTION)
        return options, [_label(o) for o in options]

    def select_dropdown(self, button: Locator, candidates: str | Sequence[str], desc: str,
                        exact: bool = False) -> str | None:
        """exact=True (question answers): an option must equal the value or start with it
        ('Yes' → 'Yes - Newcomer'); 'Man' never picks 'Trans Man'. The next fallback is tried instead."""
        wanted = split_list(candidates)
        if not wanted:
            return None
        min_score = 2 if exact else 1

        current = self.dropdown_value(button)
        if any(match_score(w, current) >= 2 or (not exact and contains_words(w, current)) for w in wanted):
            self.log.info("%s: already %r", desc, current)  # e.g. 'Fluent' ~ '5 - Fluent'
            return current

        for attempt in (1, 2, 3):
            if attempt < 3:
                self.act.click(button, desc=f"{desc} dropdown")
            else:  # the list wouldn't open on click: try the keyboard
                el = self.act.find(button)
                self.act.scroll_into_view(el)
                el.send_keys(Keys.ENTER)
                if self._open_listbox() is None:
                    el.send_keys(Keys.ARROW_DOWN)
            listbox = self._open_listbox()
            if listbox is None:
                self.log.debug("%s: listbox did not open (attempt %d)", desc, attempt)
                self.act.dismiss_overlays()
                self.act.release_focus()  # another field may still hold focus and swallow the click
                continue

            options, labels = self._listbox_options(listbox)
            match = best_match(wanted, labels, min_score=min_score)
            if match is None:
                match = self._listbox_type_ahead(wanted, min_score)
                if match is not None:
                    options, labels = match[2], [_label(o) for o in match[2]]
                    match = match[:2]
            if match is None:
                self.log.warning("%s: none of %s found. Available: %s", desc, wanted, labels[:60])
                self.act.dismiss_overlays()
                return None

            idx, label = match
            try:
                self.act.click(options[idx], desc=f"{desc} option {label!r}")
            except Exception as exc:  # noqa: BLE001 - option went stale; retry the whole open/pick
                self.log.debug("%s: clicking option failed (%s), retrying", desc, exc)
                self.act.dismiss_overlays()
                continue

            if waits.poll(lambda: match_score(label, self.dropdown_value(button)) >= 1, self.cfg.timeouts.short):
                self.log.info("%s: selected %r", desc, label)
                return label
            self.log.debug("%s: button shows %r after picking %r (attempt %d)",
                           desc, self.dropdown_value(button), label, attempt)
        self.log.warning("%s: could not select any of %s", desc, wanted)
        return None

    def _listbox_type_ahead(self, wanted: list[str], min_score: int = 1):
        """Long lists may not render every option. Type the value so the listbox jumps to it, then re-read."""
        for candidate in wanted:
            self.act.press(candidate)
            self.act.settle(0.6)
            listbox = self._open_listbox()
            if listbox is None:
                return None
            options, labels = self._listbox_options(listbox)
            m = best_match([candidate], labels, min_score=min_score)
            if m:
                return m[0], m[1], options
        return None

    # ============================================================== prompt / multiselect
    def selected_pills(self, field: Locator) -> list[str]:
        try:
            container = self.driver.find_element(*field)
            return [_label(p) for p in container.find_elements(*C.SELECTED_PILL_LABEL)]
        except WebDriverException:
            return []

    def clear_pills(self, field: Locator) -> None:
        for _ in range(10):
            try:
                charms = self.driver.find_element(*field).find_elements(*C.PILL_DELETE)
            except WebDriverException:
                return
            if not charms:
                return
            self.act.click(charms[0], desc="remove selected value")
            self.act.settle(0.3)

    def _visible_prompt_options(self) -> list[WebElement]:
        return self.driver.execute_script(_JS_VISIBLE_PROMPT_OPTIONS) or []

    def _no_matches(self) -> bool:
        for el in waits.visible_elements(self.driver, C.PROMPT_NO_MATCHES):
            if "no matches" in normalize(el.get_attribute("title") or el.text):
                return True
        return False

    _PLACEHOLDERS = {"no items", "no items.", "loading", "loading..."}

    def _result_options(self) -> tuple[list[WebElement], list[str]]:
        """Visible, real options (not pills, not 'No Items.' placeholders, not unrendered blanks)."""
        opts, labels = [], []
        for o in self._visible_prompt_options():
            label = _label(o)
            if label and normalize(label) not in self._PLACEHOLDERS:
                opts.append(o)
                labels.append(label)
        return opts, labels

    def _selection_items(self, field: Locator) -> list[str]:
        """Values currently selected in a prompt field (accessibility text + pills)."""
        text = self.prompt_selection_text(field)
        items = [i.strip() for i in text.split(",")[1:]] if "," in text else []
        for p in self.selected_pills(field):
            if p and p not in items:
                items.append(p)
        return items

    def _wait_for_outcome(self, field: Locator, before: set[str], term: str, timeout: float,
                          trust_no_match: bool) -> tuple[str, str | None]:
        """Wait for the result of a search. Checked on every poll, in this order:
          1. the FIELD: did Workday select a value by itself? (Enter with a single match selects it
             straight away and shows no list) → ('auto', that value)
          2. the LIST: options containing a match for `term`, unchanged across two polls → ('list', None)
          3. 'No matches found' on screen for ~2.5s (only if trust_no_match) → ('none', None)
        Workday often shows an unrelated list first ('No Items.', the full A-Z list) and the real
        results later, so only a list containing a match counts."""
        end = time.monotonic() + timeout
        time.sleep(0.4)
        last_trace, no_match_polls, seen_match = None, 0, None
        while time.monotonic() < end:
            new = [i for i in self._selection_items(field) if i not in before]
            if new:
                return "auto", new[0]
            _, labels = self._result_options()
            no_match = self._no_matches()
            trace = (tuple(labels[:6]), no_match)
            if trace != last_trace:
                self.log.debug("  search %r: %d options %s%s", term, len(labels), labels[:6],
                               " + 'No matches found'" if no_match else "")
                last_trace = trace
            if labels and best_match([term], labels) is not None:
                if seen_match == labels:  # same list on two polls in a row: settled
                    return "list", None
                seen_match = labels
            else:
                seen_match = None
            no_match_polls = no_match_polls + 1 if (no_match and not labels) else 0
            if trust_no_match and no_match_polls >= 8:  # ~2.5s: it can flash up while the search runs
                return "none", None
            time.sleep(0.3)
        return "none", None

    def _run_search(self, field: Locator, input_: Locator, term: str, desc: str) -> tuple[str, str | None]:
        """Type `term`; press Enter only if typing alone didn't produce a result (on lists that filter
        as you type, Enter can pick the highlighted option). Returns ('auto', value), ('list', None)
        or ('none', None) as described in _wait_for_outcome."""
        before = set(self._selection_items(field))
        box = self.act.focus(input_, desc=f"{desc} input")
        self.act.clear(box)
        box.send_keys(term)
        outcome = self._wait_for_outcome(field, before, term, 1.5, trust_no_match=False)
        if outcome[0] == "none":
            box.send_keys(Keys.ENTER)
            outcome = self._wait_for_outcome(field, before, term, self.cfg.timeouts.prompt_results,
                                             trust_no_match=True)
        return outcome

    def remove_selected(self, field: Locator, label: str) -> None:
        """Remove one selected value (pill) from a prompt field."""
        js = """
        const [fieldEl, label] = arguments;
        for (const item of fieldEl.querySelectorAll('[data-automation-id="selectedItem"]')) {
            const opt = item.querySelector('[data-automation-id="promptOption"]');
            const l = opt && (opt.getAttribute('data-automation-label') || opt.textContent).trim();
            if (l === label) return item.querySelector('[data-automation-id="DELETE_charm"]');
        }
        return null;
        """
        try:
            charm = self.driver.execute_script(js, self.driver.find_element(*field), label)
        except WebDriverException:
            charm = None
        if charm:
            self.act.click(charm, desc=f"remove {label!r}")
            self.act.settle(0.3)
        else:
            self.log.debug("could not find a remove button for %r", label)

    def _click_prompt_option(self, option: WebElement, desc: str) -> None:
        checkbox = self.driver.execute_script(_JS_OPTION_CHECKBOX, option)
        self.act.click(checkbox or option, desc=desc)

    def select_prompt(self, field: Locator, input_: Locator, candidates: str | Sequence[str], desc: str,
                      multi: bool = False, loose: bool = False) -> str | None:
        """Pick a value in a prompt field. Each candidate may be a path: 'Job Board > LinkedIn'.

        Candidates are tried in order, and the first choice wins:
          * a value already in the field counts as done only if it matches the FIRST candidate;
            if it only matches a fallback, the field is searched again for the better choices
          * loose=True: when a candidate isn't found as written, its key words are searched one at
            a time and the option sharing the most whole words is taken ('Data Analytics' →
            'Data Science') BEFORE moving on to the next fallback
        """
        wanted = split_list(candidates)
        if not wanted:
            return None
        leaf = lambda w: w.split(">")[-1].strip()  # noqa: E731

        first = leaf(wanted[0])
        weak: list[str] = []
        if multi:
            # Multi-select (skills): each value is its own pick, so "already set" needs a real match.
            # 'SQL Assistant' does not count as 'SQL'; it's remembered and removed once SQL is picked.
            items = self._selection_items(field)
            for w in wanted:
                hit = next((i for i in items if strong_match(leaf(w), i)), None)
                if hit:
                    self.log.info("%s: already set (%s)", desc, hit)
                    return hit
            weak = [i for i in items if any(match_score(leaf(w), i) >= 2 for w in wanted)]
        elif self.prompt_has(field, [first]) or (loose and self._has_close(field, first)):
            self.log.info("%s: already set (%s)", desc, self.prompt_selection_text(field))
            return first
        fallback = None if multi else next((leaf(w) for w in wanted[1:] if self.prompt_has(field, [leaf(w)])), None)
        pills = self.selected_pills(field)
        if fallback:
            self.log.info("%s: currently the fallback %r; looking for %r first", desc, fallback, first)
        if pills and not multi:
            self.log.info("%s: replacing %s", desc, pills)
            self.clear_pills(field)

        for candidate in wanted:
            path = [s.strip() for s in candidate.split(">") if s.strip()]
            label = self._search_and_pick(field, input_, path, desc, strict=multi)
            if not label and loose and len(path) == 1:
                label = self._search_by_words(field, input_, candidate, desc)
            if label:
                for wrong in weak:
                    if wrong != label and not strong_match(label, wrong):
                        self.log.info("%s: removing near-miss %r (now have %r)", desc, wrong, label)
                        self.remove_selected(field, wrong)
                if not multi:
                    self.act.close_popups()
                    self.act.release_focus()  # leave the search box so the next dropdown can open
                self.log.info("%s: selected %r", desc, label)
                return label
            self.act.close_popups()  # never leave a list open: it covers the fields below it
        self.log.warning("%s: could not select any of %s", desc, wanted)
        return None

    def _has_close(self, field: Locator, candidate: str) -> bool:
        """Does the field already hold an option sharing at least half the candidate's key words?"""
        text = self.prompt_selection_text(field)
        items = [i.strip() for i in text.split(",")[1:]] if "," in text else []
        items += self.selected_pills(field)
        return any(word_overlap(candidate, i) >= 0.5 for i in items)

    def _search_by_words(self, field: Locator, input_: Locator, candidate: str, desc: str) -> str | None:
        """Search each key word of the candidate on its own (longest first) and take the option that
        shares the most whole words with the candidate (also when Workday auto-selects one)."""
        for word in key_words(candidate, in_order=True):
            if len(word) < 3:
                continue
            kind, auto = self._run_search(field, input_, word, desc)
            if kind == "auto":
                if word_overlap(candidate, auto) > 0:
                    self.log.info("%s: %r not listed; Workday selected %r for %r (close by words)",
                                  desc, candidate, auto, word)
                    return auto
                self.log.info("%s: Workday selected %r for %r, not close to %r; removing it", desc, auto, word, candidate)
                self.remove_selected(field, auto)
                continue
            options, labels = self._result_options()
            match = closest_by_words(candidate, labels) if kind == "list" else None
            if match is None:
                self.log.debug("%s: nothing close to %r when searching %r", desc, candidate, word)
                continue
            idx, label = match
            self._click_prompt_option(options[idx], desc=f"{desc} option {label!r}")
            if waits.poll(lambda: self.prompt_has(field, [label]), self.cfg.timeouts.short):
                self.log.info("%s: %r not listed; closest by words: %r (searched %r)", desc, candidate, label, word)
                return label
        return None

    def _search_and_pick(self, field: Locator, input_: Locator, path: list[str], desc: str,
                         strict: bool = False) -> str | None:
        """Search for the first path segment, then walk down the hierarchy until a pill appears.

        strict (multi-select fields such as skills): only an exact option counts (a bracketed note
        is allowed: 'Python (Programming Language)'), and options already selected are never clicked
        again (Workday rejects duplicate skills). 'SQL Assistant' is a different skill from 'SQL'."""
        # "Canada (+1)" may not match Workday's search because of the brackets, so also try "Canada".
        terms = [path[0]]
        plain = re.sub(r"\s*\(.*?\)\s*", " ", path[0]).strip()
        if plain and plain != path[0]:
            terms.append(plain)

        found = False
        target = path[-1]
        for term in terms:
            kind, auto = self._run_search(field, input_, term, desc)
            if kind == "auto":
                # Enter with a single match: Workday selected it without showing a list.
                ok = (strong_match(target, auto) or strong_match(term, auto)) if strict else \
                     (match_score(target, auto) >= 1 or match_score(term, auto) >= 1)
                if ok:
                    self.log.info("%s: Workday selected %r for %r", desc, auto, term)
                    return auto
                self.log.info("%s: Workday selected %r for %r, which isn't what we want; removing it",
                              desc, auto, term)
                self.remove_selected(field, auto)
                continue
            if kind == "list":
                found = True
                break
            _, seen = self._result_options()
            self.log.info("%s: no option matching %r%s", desc, term,
                          " (No matches found)" if self._no_matches() else f". List showed: {seen[:15]}")
            if self.debug_capture:
                self.debug_capture(f"prompt_no_match_{term}")
        if not found:
            return None

        segments = list(path)
        trail: list[str] = []
        for _level in range(4):
            options, labels = self._result_options()
            if strict:
                selected = self._selection_items(field)
                keep = [i for i, l in enumerate(labels) if l not in selected]
                options, labels = [options[i] for i in keep], [labels[i] for i in keep]
            match = best_match([segments[0]], labels)
            if strict and match and not strong_match(segments[0], match[1]):
                self.act.settle(1.2)  # the exact option may still be loading
                options, labels = self._result_options()
                selected = self._selection_items(field)
                pairs = [(o, l) for o, l in zip(options, labels) if l not in selected]
                exact = next(((o, l) for o, l in pairs if strong_match(segments[0], l)), None)
                if exact is None:
                    self.log.warning("%s: no exact %r in Workday's list (has: %s). Not picking a near-miss; "
                                     "put the exact name you want in Excel", desc, segments[0], labels[:15])
                    return None
                options, labels = [exact[0]], [exact[1]]
                match = (0, exact[1])
            if match and not strong_match(segments[0], match[1]):
                # Only a partial match ('SQL Assistant' for 'SQL'): the exact option may still be loading.
                self.act.settle(1.2)
                options, labels = self._result_options()
                match = best_match([segments[0]], labels) or match
                if match and not strong_match(segments[0], match[1]):
                    self.log.debug("%s: no exact %r, best is %r (options: %s)", desc, segments[0], match[1], labels[:15])
            if match is None and len(segments) > 1:  # search may have jumped straight to the leaf
                match = best_match([segments[-1]], labels)
                if match:
                    segments = [segments[-1]]
            if match is None:
                where = f" under {' > '.join(trail)}" if trail else ""
                self.log.warning("%s: %r not found%s. Options there: %s", desc, segments[0], where, labels[:40])
                return None

            idx, label = match
            self._click_prompt_option(options[idx], desc=f"{desc} option {label!r}")
            self.act.settle(0.6)
            target = segments[-1]

            # Selected? (checked first: in multi-select lists the list re-renders after a pick, which
            # must not be mistaken for a sub-list)
            if self.prompt_has(field, [label, target]):
                return " > ".join(trail + [label])

            # A category opens a sub-list (different options, often with radio buttons): go one level down.
            _, new_labels = self._result_options()
            if new_labels and new_labels != labels:
                trail.append(label)
                self.log.debug("%s: %r opened a sub-list: %s", desc, label, new_labels[:30])
                if len(segments) > 1:
                    segments = segments[1:]
                continue

            if waits.poll(lambda: self.prompt_has(field, [label, target]), self.cfg.timeouts.short):
                return " > ".join(trail + [label])
            self.log.debug("%s: clicked %r but the field doesn't show it as selected", desc, label)
            return None
        return None

    def prompt_selection_text(self, field: Locator) -> str:
        """Workday's own accessibility text, e.g. '1 item selected, Indeed' or '0 items selected'."""
        try:
            el = self.driver.find_element(*field).find_element(*C.PROMPT_ARIA_INSTRUCTION)
            return (el.get_attribute("textContent") or "").strip()
        except WebDriverException:
            return ""

    def prompt_has(self, field: Locator, names: Sequence[str]) -> bool:
        """True if the field reports one of `names` as selected.

        Sources: the pills, plus Workday's accessibility text ("2 items selected, Python, SQL").
        Matching is exact or starts-with, so a short skill like "Go" doesn't match "Google Cloud".
        """
        text = self.prompt_selection_text(field)
        items = [i.strip() for i in text.split(",")[1:]] if "," in text else []
        items += self.selected_pills(field)
        return any(match_score(n, s) >= 2 or match_score(s, n) >= 2 for n in names for s in items if n and s)

    # ============================================================== dates
    _MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                           "august", "september", "october", "november", "december"], 1)}

    @classmethod
    def month_number(cls, month: str) -> str:
        m = normalize(month)
        if m.isdigit():
            return f"{int(m):02d}"
        for name, num in cls._MONTHS.items():
            if name.startswith(m[:3]) and len(m) >= 3:
                return f"{num:02d}"
        raise ValueError(f"Not a month: {month!r}")

    _DATE_PLACEHOLDERS = {"mm", "dd", "yyyy", ""}

    def _date_part_value(self, input_loc: Locator) -> str:
        try:
            el = self.driver.find_element(*input_loc)
        except WebDriverException:
            return ""
        v = (el.get_attribute("aria-valuetext") or el.get_attribute("value") or "").strip()
        return "" if v.lower() in self._DATE_PLACEHOLDERS else v

    def fill_date(self, field_css: str, desc: str, month: str = "", year: str = "", day: str = "") -> bool:
        """Workday date widget: Month / Day / Year spinbutton inputs, each covered by a visible
        `dateSection<Part>-display` div. Click the display div (that focuses the input underneath),
        clear what's there with Backspace, type the digits, Tab out, then verify each part from the
        input's aria-valuetext and retype any part that didn't take."""
        wanted = []
        if month:
            wanted.append(("Month", self.month_number(month)))
        if day:
            wanted.append(("Day", f"{int(day):02d}"))
        if year:
            wanted.append(("Year", str(year)))

        def locs(part):
            return ((By.CSS_SELECTOR, f'{field_css} [data-automation-id="dateSection{part}-display"]'),
                    (By.CSS_SELECTOR, f'{field_css} [data-automation-id="dateSection{part}-input"]'))

        def matches(part, val):
            got = self._date_part_value(locs(part)[1])
            return got.isdigit() and int(got) == int(val) if part != "Year" else got == val

        parts = [(p, v) for p, v in wanted if waits.is_present(self.driver, locs(p)[1])]
        if not parts:
            self.log.warning("%s: no date inputs found in %s", desc, field_css)
            return False

        for attempt in (1, 2):
            todo = [(p, v) for p, v in parts if not matches(p, v)]
            if not todo:
                break
            for part, val in todo:
                display, input_loc = locs(part)
                target = display if waits.is_visible(self.driver, display) else input_loc
                self.act.click(target, desc=f"{desc} {part.lower()}")
                current = self._date_part_value(input_loc)
                if current:
                    self.act.press(Keys.BACKSPACE * len(current))
                self.act.press(val)
                self.act.settle(0.2)
            self.act.press(Keys.TAB)
            self.act.settle(0.4)

        bad = [(p, v, self._date_part_value(locs(p)[1])) for p, v in parts if not matches(p, v)]
        if bad:
            self.log.warning("%s: date not accepted: %s", desc,
                             ", ".join(f"{p} wanted {v} got {g or 'empty'}" for p, v, g in bad))
            return False
        self.log.info("%s: %s", desc, "/".join(v for _, v in parts))
        return True

    # ============================================================== file upload
    def upload_file(self, input_: Locator, path: str, container: Locator, desc: str) -> bool:
        """Send a file to a (usually hidden) <input type=file> and wait for its name to show up."""
        from pathlib import Path as _P
        file = _P(path).expanduser()
        if not file.is_file():
            self.log.warning("%s: file not found: %s", desc, file)
            return False
        # Match the full file name only: the stem alone ("resume") can appear in the section heading.
        if file.name.lower() in self._text_of(container).lower():
            self.log.info("%s: %s already uploaded", desc, file.name)
            return True
        el = self.act.find(input_)
        el.send_keys(str(file.resolve()))
        shown = waits.poll(lambda: file.name.lower() in self._text_of(container).lower(), self.cfg.timeouts.page_change)
        (self.log.info if shown else self.log.warning)("%s: %s %s", desc, file.name,
                                                        "uploaded" if shown else "did not appear after upload")
        return bool(shown)

    def _text_of(self, locator: Locator) -> str:
        try:
            return self.driver.find_element(*locator).text or ""
        except WebDriverException:
            return ""

    # ============================================================== auto-detect
    def detect(self, field_css: str) -> str:
        """What kind of control is inside a formField container?"""
        js = """
        const f = document.querySelector(arguments[0]);
        if (!f) return 'missing';
        if (f.querySelector('[data-automation-id^="dateSection"]')) return 'date';
        if (f.querySelector('[data-automation-id="multiselectInputContainer"], [data-automation-id="searchBox"]')) return 'prompt';
        if (f.querySelector('button[aria-haspopup="listbox"]')) return 'dropdown';
        if (f.querySelector('textarea')) return 'textarea';
        if (f.querySelector('input[type="radio"]')) return 'radio';
        if (f.querySelector('input[type="checkbox"]')) return 'checkbox';
        if (f.querySelector('input')) return 'text';
        return 'unknown';
        """
        return self.driver.execute_script(js, field_css)

    def fill_auto(self, field_css: str, value, desc: str, multi: bool = False, loose: bool = False,
                  exact: bool = False):
        """Fill a formField container with `value`, whatever kind of control it turns out to be.
        Returns something truthy on success, None/False on failure."""
        kind = self.detect(field_css)
        values = split_list(value) if not isinstance(value, bool) else []
        # Text boxes get one value: a string as-is (it may legitimately contain ';'), or the first
        # of a list of fallbacks.
        text_value = value if isinstance(value, str) else (values[0] if values else "")
        loc = lambda sub="": (By.CSS_SELECTOR, f"{field_css} {sub}".strip())  # noqa: E731
        self.log.debug("%s: %s field", desc, kind)
        if kind == "missing":
            return None
        if kind == "prompt":
            return self.select_prompt(loc(), loc("input"), values, desc=desc, multi=multi, loose=loose)
        if kind == "dropdown":
            return self.select_dropdown(loc('button[aria-haspopup="listbox"]'), values, desc=desc, exact=exact)
        if kind == "date":
            return self.fill_date(field_css, desc, year=values[0] if values else "")
        if kind == "textarea":
            return self.act.type(loc("textarea"), text_value, desc=desc)
        if kind == "checkbox":
            boxes = self.driver.find_elements(By.CSS_SELECTOR, f'{field_css} input[type="checkbox"]')
            if len(boxes) > 1 and len(values) == 1 and normalize(values[0]) in ("yes", "true", "all"):
                # A group answered "Yes"/"All" (e.g. CIBC's two statements): tick every box.
                labels = [lab for _, lab in self._labelled_inputs(field_css, "checkbox") if lab]
                return self.select_checkboxes_by_label(field_css, labels, desc=desc)
            if len(boxes) > 1 or (values and normalize(values[0]) not in ("yes", "true", "no", "false")):
                return self.select_checkboxes_by_label(field_css, values, desc=desc)
            on = value if isinstance(value, bool) else normalize(values[0] if values else "") in ("yes", "true")
            return self.set_checkbox(loc('input[type="checkbox"]'), on, desc=desc)
        if kind == "radio":
            return self.select_radio_by_label(field_css, values, desc=desc, exact=exact)
        if kind == "text":
            return self.act.type(loc("input"), text_value, desc=desc)
        self.log.warning("%s: don't know how to fill this field (%s)", desc, kind)
        return None

    def _labelled_inputs(self, field_css: str, kind: str) -> list[tuple[str, str]]:
        """[(input id, label text)] for the radio buttons / checkboxes in a field."""
        out = []
        for inp in self.driver.find_elements(By.CSS_SELECTOR, f'{field_css} input[type="{kind}"]'):
            iid = inp.get_attribute("id")
            lab = self.driver.find_elements(By.CSS_SELECTOR, f'label[for="{iid}"]') if iid else []
            out.append((iid, (lab[0].text if lab else inp.get_attribute("value") or "").strip()))
        return out

    def select_checkboxes_by_label(self, field_css: str, wanted: Sequence[str], desc: str) -> str | None:
        """Tick every checkbox whose label matches one of `wanted` (others are left as they are)."""
        boxes = self._labelled_inputs(field_css, "checkbox")
        labels = [lab for _, lab in boxes]
        ticked = []
        for w in wanted:
            m = best_match([w], labels)
            if not m:
                self.log.warning("%s: no checkbox matching %r in %s", desc, w, labels)
                return None
            iid = boxes[m[0]][0]
            if self.set_checkbox((By.CSS_SELECTOR, f'[id="{iid}"]'), True, desc=f"{desc}: {m[1]}"):
                ticked.append(m[1])
        self.log.info("%s: ticked %s", desc, ticked)
        return "; ".join(ticked) if ticked else None

    def current_answer(self, field_css: str) -> str:
        """What the field currently holds ('' if unanswered), whatever kind of control it is."""
        js = """
        const f = document.querySelector(arguments[0]);
        if (!f) return '';
        const btn = f.querySelector('button[aria-haspopup="listbox"]');
        if (btn) { const t = btn.textContent.trim(); return /^select one$/i.test(t) ? '' : t; }
        const aria = f.querySelector('[data-automation-id="promptAriaInstruction"]');
        if (aria) { const t = aria.textContent.trim(); return t.includes(',') ? t.split(',').slice(1).join(',').trim() : ''; }
        const checked = [...f.querySelectorAll('input[type="radio"], input[type="checkbox"]')].filter(i => i.checked);
        if (checked.length) return checked.map(i => {
            const l = i.id && document.querySelector('label[for="' + CSS.escape(i.id) + '"]');
            return l ? l.textContent.trim() : (i.value || 'checked'); }).join('; ');
        const date = f.querySelector('[data-automation-id^="dateSection"][data-automation-id$="-input"]');
        if (date) return [...f.querySelectorAll('[data-automation-id^="dateSection"][data-automation-id$="-input"]')]
            .map(i => i.value).filter(Boolean).join('/');
        const t = f.querySelector('textarea, input[type="text"], input:not([type])');
        return t ? t.value.trim() : '';
        """
        try:
            return (self.driver.execute_script(js, field_css) or "").strip()
        except WebDriverException:
            return ""

    def dropdown_options(self, button: Locator) -> list[str]:
        """Open a dropdown, read its options, close it (used to tell you what an unknown question offers)."""
        try:
            self.act.click(button, desc="peek dropdown")
            listbox = self._open_listbox()
            labels = self._listbox_options(listbox)[1] if listbox else []
        except Exception:  # noqa: BLE001 - purely informational
            labels = []
        self.act.close_popups()
        return [l for l in labels if l and normalize(l) != "select one"]

    def select_radio_by_label(self, field_css: str, candidates: Sequence[str], desc: str,
                              exact: bool = False) -> str | None:
        radios = self.driver.find_elements(By.CSS_SELECTOR, f'{field_css} input[type="radio"]')
        labels = []
        for r in radios:
            rid = r.get_attribute("id")
            lab = self.driver.find_elements(By.CSS_SELECTOR, f'label[for="{rid}"]') if rid else []
            labels.append((lab[0].text if lab else r.get_attribute("value") or "").strip())
        match = best_match(candidates, labels, min_score=2 if exact else 1)
        if not match:
            self.log.warning("%s: none of %s in %s", desc, list(candidates), labels)
            return None
        idx, label = match
        rid = radios[idx].get_attribute("id")
        ok = self.select_radio((By.CSS_SELECTOR, f'[id="{rid}"]'), desc=f"{desc} = {label}")
        return label if ok else None

    # ============================================================== radio / checkbox
    def _is_checked(self, locator: Locator) -> bool:
        el = self.act.find(locator, self.cfg.timeouts.short)
        return el.is_selected() or (el.get_attribute("aria-checked") == "true")

    def _click_input_or_label(self, locator: Locator, desc: str) -> None:
        el = self.act.find(locator)
        input_id = el.get_attribute("id")
        label = (By.CSS_SELECTOR, f'label[for="{input_id}"]') if input_id else None
        if label and waits.is_visible(self.driver, label):
            self.act.click(label, desc=desc)
        else:
            self.act.click(locator, desc=desc)

    def select_radio(self, radio: Locator, desc: str) -> bool:
        if self._is_checked(radio):
            self.log.info("%s: already selected", desc)
            return True
        self._click_input_or_label(radio, desc)
        ok = bool(waits.poll(lambda: self._is_checked(radio), self.cfg.timeouts.short))
        (self.log.info if ok else self.log.warning)("%s: %s", desc, "selected" if ok else "did not stay selected")
        return ok

    def set_checkbox(self, checkbox: Locator, checked: bool, desc: str) -> bool:
        if self._is_checked(checkbox) == checked:
            return True
        self._click_input_or_label(checkbox, desc)
        ok = bool(waits.poll(lambda: self._is_checked(checkbox) == checked, self.cfg.timeouts.short))
        if not ok:
            self.log.warning("%s: checkbox did not change to %s", desc, checked)
        return ok
