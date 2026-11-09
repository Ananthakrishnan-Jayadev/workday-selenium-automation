"""Everything a page object needs for one run, bundled together."""
from __future__ import annotations

import sys
from dataclasses import dataclass

from selenium.webdriver.remote.webdriver import WebDriver

from core.actions import Actions
from core.config import Config
from core.logger import get_logger
from core.reporter import Reporter
from core.widgets import Widgets


class NeedsHuman(Exception):
    """Raised when on_unknown=fail and something needs a person."""


@dataclass
class Session:
    driver: WebDriver
    cfg: Config
    reporter: Reporter
    act: Actions
    widgets: Widgets

    @classmethod
    def create(cls, driver: WebDriver, cfg: Config, reporter: Reporter) -> "Session":
        act = Actions(driver, cfg)
        return cls(driver=driver, cfg=cfg, reporter=reporter, act=act, widgets=Widgets(act))

    @property
    def log(self):
        return get_logger()

    def checkpoint(self, name: str) -> None:
        """Screenshot (+ HTML if dump_pages) of the current state."""
        self.reporter.capture(self.driver, name, html=self.cfg.behaviour.dump_pages)

    def pause_for_human(self, reason: str) -> bool:
        """Ask the person at the keyboard to deal with something in the browser.

        Returns True if they handled it (continue), False if on_unknown=skip.
        Raises NeedsHuman if on_unknown=fail, or if there's no terminal to ask in.
        """
        self.reporter.capture(self.driver, "needs_human", html=True)
        mode = self.cfg.behaviour.on_unknown
        if mode == "skip":
            self.log.warning("SKIPPED (on_unknown=skip): %s", reason)
            return False
        if mode == "fail" or not sys.stdin.isatty():
            raise NeedsHuman(reason)

        self.log.warning("NEEDS YOU: %s", reason)
        print("\n" + "=" * 78)
        print("  ACTION NEEDED IN THE BROWSER")
        for line in reason.splitlines():
            print(f"  {line}")
        print("  Fix it in the browser window, then press Enter here to continue.")
        print("=" * 78)
        try:
            input()
        except EOFError as exc:
            raise NeedsHuman(reason) from exc
        self.log.info("continuing after manual fix")
        return True
