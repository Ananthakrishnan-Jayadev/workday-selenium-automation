"""Locators only: (By, value) tuples and lists of alternatives. No logic.

Status of each locator (verified from a page dump / extension / best effort) is in docs/LOCATORS.md.
"""
from selenium.webdriver.common.by import By


def aid(automation_id: str, tag: str = "") -> tuple[str, str]:
    """CSS locator for Workday's stable data-automation-id attribute."""
    return By.CSS_SELECTOR, f'{tag}[data-automation-id="{automation_id}"]'
