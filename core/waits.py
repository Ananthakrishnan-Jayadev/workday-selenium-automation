"""Explicit-wait helpers. Locators are always (By, value) tuples."""
from __future__ import annotations

import time
from typing import Callable, Sequence, TypeVar

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

Locator = tuple[str, str]
T = TypeVar("T")

_IGNORED = (StaleElementReferenceException,)


def wait(driver: WebDriver, timeout: float) -> WebDriverWait:
    return WebDriverWait(driver, timeout, poll_frequency=0.25, ignored_exceptions=_IGNORED)


def present(driver: WebDriver, locator: Locator, timeout: float) -> WebElement:
    return wait(driver, timeout).until(EC.presence_of_element_located(locator))


def visible(driver: WebDriver, locator: Locator, timeout: float) -> WebElement:
    return wait(driver, timeout).until(EC.visibility_of_element_located(locator))


def clickable(driver: WebDriver, locator: Locator, timeout: float) -> WebElement:
    return wait(driver, timeout).until(EC.element_to_be_clickable(locator))


def gone(driver: WebDriver, locator: Locator, timeout: float) -> bool:
    return wait(driver, timeout).until(EC.invisibility_of_element_located(locator))


def visible_elements(driver_or_el, locator: Locator) -> list[WebElement]:
    out = []
    for el in driver_or_el.find_elements(*locator):
        try:
            if el.is_displayed():
                out.append(el)
        except StaleElementReferenceException:
            continue
    return out


def is_present(driver_or_el, locator: Locator) -> bool:
    try:
        return bool(driver_or_el.find_elements(*locator))
    except WebDriverException:
        return False


def is_visible(driver_or_el, locator: Locator) -> bool:
    return bool(visible_elements(driver_or_el, locator))


def first_present(driver: WebDriver, locators: Sequence[Locator], timeout: float,
                  visible_only: bool = False) -> tuple[Locator, WebElement]:
    """Wait until any of several alternative locators matches; return (locator, element)."""
    def check(d):
        for loc in locators:
            els = visible_elements(d, loc) if visible_only else d.find_elements(*loc)
            if els:
                return loc, els[0]
        return False
    return wait(driver, timeout).until(check)


def poll(fn: Callable[[], T | None], timeout: float, interval: float = 0.25) -> T | None:
    """Call fn until it returns something truthy or the timeout expires. Exceptions count as 'not yet'."""
    end = time.monotonic() + timeout
    while True:
        try:
            result = fn()
            if result:
                return result
        except (StaleElementReferenceException, WebDriverException):
            pass
        if time.monotonic() >= end:
            return None
        time.sleep(interval)


__all__ = ["Locator", "TimeoutException", "wait", "present", "visible", "clickable", "gone",
           "visible_elements", "is_present", "is_visible", "first_present", "poll"]
