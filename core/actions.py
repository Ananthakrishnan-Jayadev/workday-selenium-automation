"""Robust, generic Selenium actions: click, type, scroll, key presses.

Workday's UI covers elements with popups and sticky headers, lazy-loads sections and re-renders
React components, so plain `element.click()` / `send_keys()` fail often. Everything here:
  * looks elements up again on every attempt (pass locators, not elements, where possible)
  * scrolls the target to the middle of the viewport first
  * retries with backoff on interception / staleness / not-interactable
  * falls back to ActionChains and finally a JavaScript click (logged as a warning)
"""
from __future__ import annotations

import sys
import time
from typing import Union

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    JavascriptException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from core import waits
from core.config import Config
from core.logger import get_logger, mask
from core.text import digits, normalize
from core.waits import Locator

Target = Union[Locator, WebElement]
_SELECT_ALL = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL

# Inputs that must never be filled (bot traps). Typing into them flags the application as automated spam.
_HONEYPOT_IDS = {"beecatcher"}

_NEUTRAL_TARGETS = [
    (By.CSS_SELECTOR, '[data-automation-id="jobTitleHeading"]'),
    (By.CSS_SELECTOR, '[data-automation-id="jobPostingHeader"]'),
    (By.CSS_SELECTOR, '[data-automation-id="progressBar"]'),
]

_JS_POPUP_OPEN = """
const shown = el => el.getClientRects().length > 0;
const prompt = [...document.querySelectorAll('[data-automation-id="promptOption"]')].some(o =>
    shown(o) && !o.closest('[data-automation-id="selectedItemList"], [data-automation-id="selectedItem"]'));
const listbox = [...document.querySelectorAll('[role="listbox"]:not([data-automation-id="selectedItemList"])')]
    .some(l => shown(l) && l.querySelector('[role="option"]'));
return prompt || listbox;
"""


class ActionError(Exception):
    pass


class Actions:
    def __init__(self, driver: WebDriver, cfg: Config):
        self.driver = driver
        self.cfg = cfg
        self.log = get_logger()

    # ------------------------------------------------------------------ lookup
    @staticmethod
    def describe(target: Target) -> str:
        if isinstance(target, tuple):
            return target[1]
        try:
            aid = target.get_attribute("data-automation-id")
            return f"<{target.tag_name} {aid or target.get_attribute('id') or ''}>"
        except WebDriverException:
            return "<element>"

    def find(self, target: Target, timeout: float | None = None, visible: bool = False) -> WebElement:
        if isinstance(target, WebElement):
            return target
        t = self.cfg.timeouts.default if timeout is None else timeout
        return waits.visible(self.driver, target, t) if visible else waits.present(self.driver, target, t)

    def exists(self, locator: Locator, timeout: float = 0, visible: bool = False) -> bool:
        if timeout <= 0:
            return waits.is_visible(self.driver, locator) if visible else waits.is_present(self.driver, locator)
        try:
            self.find(locator, timeout, visible=visible)
            return True
        except TimeoutException:
            return False

    # ------------------------------------------------------------------ helpers
    def settle(self, seconds: float = 0.3) -> None:
        """Short pause after a known Workday re-render. Use sparingly."""
        time.sleep(seconds)

    def _slow_mo(self) -> None:
        if self.cfg.behaviour.slow_mo_ms:
            time.sleep(self.cfg.behaviour.slow_mo_ms / 1000)

    def scroll_into_view(self, el: WebElement) -> None:
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", el)
        except (JavascriptException, StaleElementReferenceException):
            pass

    def press(self, *keys: str, target: WebElement | None = None) -> None:
        """Send keys to an element, or to whatever currently has focus."""
        if target is not None:
            target.send_keys(*keys)
        else:
            ActionChains(self.driver).send_keys(*keys).perform()

    def popup_open(self) -> bool:
        """Is a Workday dropdown list or prompt list open?"""
        try:
            return bool(self.driver.execute_script(_JS_POPUP_OPEN))
        except WebDriverException:
            return False

    def close_popups(self) -> None:
        """Close an open list: Escape first, then click a harmless spot outside it (Escape alone
        doesn't close prompt sub-lists)."""
        if not self.popup_open():
            return
        try:
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
        except WebDriverException:
            pass
        time.sleep(0.3)
        if not self.popup_open():
            return
        for loc in _NEUTRAL_TARGETS:
            for el in waits.visible_elements(self.driver, loc):
                try:
                    self.scroll_into_view(el)
                    ActionChains(self.driver).move_to_element(el).click().perform()
                    time.sleep(0.3)
                    if not self.popup_open():
                        self.log.debug("closed popup by clicking %s", loc[1])
                        return
                except WebDriverException:
                    continue
        self.log.debug("popup still open after Escape and outside clicks")

    def dismiss_overlays(self) -> None:
        """Close whatever is covering the page (open list, tooltip, toast)."""
        try:
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
        except WebDriverException:
            pass
        time.sleep(0.2)
        self.close_popups()

    def _check_not_honeypot(self, el: WebElement) -> None:
        if (el.get_attribute("data-automation-id") or "") in _HONEYPOT_IDS:
            raise ActionError("Refusing to interact with a honeypot field (beecatcher)")

    # ------------------------------------------------------------------ click
    def click(self, target: Target, timeout: float | None = None, desc: str | None = None) -> WebElement:
        """Click with retries. Raises ActionError if every strategy fails."""
        what = desc or self.describe(target)
        retries = max(1, self.cfg.retries.click)
        last_error: Exception | None = None
        el: WebElement | None = None

        for attempt in range(1, retries + 1):
            try:
                el = self.find(target, timeout)
                self._check_not_honeypot(el)
                self.scroll_into_view(el)
                if isinstance(target, tuple):
                    waits.clickable(self.driver, target, self.cfg.timeouts.short)
                el.click()
                self.log.debug("clicked %s", what)
                self._slow_mo()
                return el
            except TimeoutException as exc:
                if el is None:  # never appeared at all: retrying won't help
                    raise ActionError(f"Element not found: {what}") from exc
                last_error = exc  # present but not clickable yet
            except ElementClickInterceptedException as exc:
                last_error = exc
                blocker = (exc.msg or "").split("Other element would receive the click:")[-1].strip()[:160]
                self.log.debug("click on %s intercepted (attempt %d) by %s", what, attempt, blocker)
                self.close_popups()          # an open list left behind is the usual culprit
                if attempt >= 2:
                    self.dismiss_overlays()
            except (StaleElementReferenceException, ElementNotInteractableException) as exc:
                last_error = exc
                self.log.debug("click on %s failed (attempt %d): %s", what, attempt, type(exc).__name__)
            time.sleep(0.3 * 2 ** (attempt - 1))

        # Fallback 1: real mouse move + click
        try:
            el = self.find(target, self.cfg.timeouts.short)
            self.scroll_into_view(el)
            ActionChains(self.driver).move_to_element(el).pause(0.1).click().perform()
            self.log.info("clicked %s via ActionChains after %d failed attempts", what, retries)
            self._slow_mo()
            return el
        except WebDriverException as exc:
            last_error = exc

        # Fallback 2: JavaScript click (bypasses overlays, but skips some real-user events)
        try:
            el = self.find(target, self.cfg.timeouts.short)
            self.driver.execute_script("arguments[0].click();", el)
            self.log.warning("clicked %s via JavaScript (normal click kept failing: %s)",
                             what, type(last_error).__name__)
            self._slow_mo()
            return el
        except WebDriverException as exc:
            last_error = exc

        raise ActionError(f"Could not click {what}: {type(last_error).__name__}: {last_error}")

    def focus(self, target: Target, desc: str | None = None) -> WebElement:
        """Put keyboard focus in an input. Clicks it normally; if something covers it (e.g. the
        selected-items list sitting on top of a prompt's search box), focuses it via JavaScript.
        Typing afterwards still uses real keystrokes."""
        what = desc or self.describe(target)
        el = self.find(target)
        self._check_not_honeypot(el)
        self.scroll_into_view(el)
        try:
            el.click()
        except (ElementClickInterceptedException, ElementNotInteractableException):
            self.driver.execute_script("arguments[0].focus();", el)
            self.log.debug("focused %s via JavaScript (it is covered)", what)
        self._slow_mo()
        return el

    # ------------------------------------------------------------------ type
    def clear(self, el: WebElement) -> None:
        """Select-all + Delete. element.clear() doesn't fire React events, so Workday can keep the old value."""
        el.send_keys(_SELECT_ALL, "a")
        el.send_keys(Keys.DELETE)

    def type(self, target: Target, value: str | int, commit: bool = True, secret: bool = False,
             desc: str | None = None, compare: str = "exact") -> WebElement:
        """Click, clear, type with real keystrokes, verify the value, then Tab out to commit it.

        compare: 'exact' (normalised text) or 'digits' (phone numbers get reformatted by Workday).
        """
        value = str(value)
        what = desc or self.describe(target)
        shown = mask(value) if secret else repr(value)
        attempts = max(1, self.cfg.retries.type)

        el: WebElement | None = None
        actual = ""
        for attempt in range(1, attempts + 1):
            try:
                el = self.click(target, desc=what)
                self.clear(el)
                el.send_keys(value)
                actual = el.get_attribute("value") or ""
                ok = digits(actual) == digits(value) if compare == "digits" else normalize(actual) == normalize(value)
                if ok:
                    break
                self.log.debug("typed %s into %s but it reads %r (attempt %d)",
                               shown, what, "<hidden>" if secret else actual, attempt)
            except StaleElementReferenceException:
                self.log.debug("%s went stale while typing (attempt %d)", what, attempt)
        else:
            raise ActionError(f"Value did not stick in {what}: wanted {shown}, "
                              f"got {'<hidden>' if secret else repr(actual)}")

        if commit:
            try:
                el.send_keys(Keys.TAB)
            except StaleElementReferenceException:
                pass
        self.log.debug("typed %s into %s", shown, what)
        self._slow_mo()
        return el

    def value_of(self, target: Target) -> str:
        return self.find(target).get_attribute("value") or ""

    def text_of(self, target: Target) -> str:
        return (self.find(target).text or "").strip()
