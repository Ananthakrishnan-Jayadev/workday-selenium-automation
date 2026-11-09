"""Per-run output folder: reports/<timestamp>_<company>/ with log, screenshots, page dumps, result.json."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from core.logger import get_logger


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")[:60] or "run"


class Reporter:
    def __init__(self, reports_root: Path, label: str):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = reports_root / f"{stamp}_{_slug(label)}"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._counter = 0
        self.result: dict[str, Any] = {"label": label, "started": datetime.now().isoformat(timespec="seconds")}

    @property
    def log_file(self) -> Path:
        return self.run_dir / "run.log"

    def _next(self, name: str) -> str:
        self._counter += 1
        return f"{self._counter:02d}_{_slug(name)}"

    def screenshot(self, driver, name: str) -> Path | None:
        path = self.run_dir / f"{self._next(name)}.png"
        try:
            driver.save_screenshot(str(path))
            get_logger().info("screenshot: %s", path)
            return path
        except Exception as exc:  # noqa: BLE001 - reporting must never break a run
            get_logger().warning("screenshot failed (%s): %s", name, exc)
            return None

    def dump_page(self, driver, name: str) -> Path | None:
        path = self.run_dir / f"{self._next(name)}.html"
        try:
            path.write_text(driver.page_source, encoding="utf-8")
            get_logger().debug("page dump: %s", path)
            return path
        except Exception as exc:  # noqa: BLE001
            get_logger().warning("page dump failed (%s): %s", name, exc)
            return None

    def capture(self, driver, name: str, html: bool = True) -> None:
        self.screenshot(driver, name)
        if html:
            self.dump_page(driver, name)

    def write_result(self, **data: Any) -> Path:
        self.result.update(data)
        self.result["finished"] = datetime.now().isoformat(timespec="seconds")
        path = self.run_dir / "result.json"
        path.write_text(json.dumps(self.result, indent=2, default=str), encoding="utf-8")
        return path
