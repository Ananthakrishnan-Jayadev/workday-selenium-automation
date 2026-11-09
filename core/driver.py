"""WebDriver factory for Chrome/Chromium and Firefox.

Driver resolution order:
  1. browser.driver_path from config
  2. On Linux, a snap-packaged browser's bundled driver (/snap/bin/chromium.chromedriver,
     /snap/bin/geckodriver). Snap browsers don't work with downloaded drivers.
  3. Selenium Manager (built into Selenium) finds or downloads a matching driver.
"""
from __future__ import annotations

import os
import shutil

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService

from core.config import BrowserCfg
from core.logger import get_logger

_SNAP_CHROMEDRIVER = "/snap/bin/chromium.chromedriver"
_SNAP_GECKODRIVER = "/snap/bin/geckodriver"


def _auto_chromedriver() -> str | None:
    has_google_chrome = any(shutil.which(b) for b in ("google-chrome", "google-chrome-stable"))
    if not has_google_chrome and os.path.exists(_SNAP_CHROMEDRIVER):
        return _SNAP_CHROMEDRIVER
    return None


def _auto_geckodriver() -> str | None:
    if os.path.exists("/snap/bin/firefox") and os.path.exists(_SNAP_GECKODRIVER):
        return _SNAP_GECKODRIVER
    return None


def create_driver(cfg: BrowserCfg) -> webdriver.Remote:
    log = get_logger()
    name = cfg.name.lower()
    width, height = (int(x) for x in cfg.window_size.split(","))

    if name in ("chrome", "chromium"):
        opts = webdriver.ChromeOptions()
        if cfg.headless:
            opts.add_argument("--headless=new")
        opts.add_argument(f"--window-size={width},{height}")
        opts.add_argument("--disable-notifications")
        if cfg.user_data_dir:
            opts.add_argument(f"--user-data-dir={os.path.expanduser(cfg.user_data_dir)}")
        if cfg.binary:
            opts.binary_location = cfg.binary
        driver_path = cfg.driver_path or _auto_chromedriver()
        service = ChromeService(executable_path=driver_path) if driver_path else ChromeService()
        driver = webdriver.Chrome(service=service, options=opts)

    elif name == "firefox":
        opts = webdriver.FirefoxOptions()
        if cfg.headless:
            opts.add_argument("-headless")
        if cfg.user_data_dir:
            opts.add_argument("-profile")
            opts.add_argument(os.path.expanduser(cfg.user_data_dir))
        if cfg.binary:
            opts.binary_location = cfg.binary
        driver_path = cfg.driver_path or _auto_geckodriver()
        service = FirefoxService(executable_path=driver_path) if driver_path else FirefoxService()
        driver = webdriver.Firefox(service=service, options=opts)
        driver.set_window_size(width, height)

    else:
        raise ValueError(f"Unsupported browser: {cfg.name!r} (use chrome or firefox)")

    driver.implicitly_wait(0)  # all waiting is explicit
    driver.set_page_load_timeout(90)
    log.info("browser started: %s %s (driver: %s, headless=%s)",
             driver.capabilities.get("browserName"), driver.capabilities.get("browserVersion"),
             driver_path or "Selenium Manager", cfg.headless)
    return driver
