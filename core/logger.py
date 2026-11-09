"""Console + per-run file logging."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

LOGGER_NAME = "workday"
_FMT = "%(asctime)s %(levelname)-7s %(message)s"


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def _utf8_console() -> None:
    """Make the terminal output UTF-8. Log lines contain characters such as '→'; a Windows console
    using a legacy code page (cp1252) can't print them and Python reports 'Logging error' for every
    such line. errors='replace' means an unprintable character becomes '?' instead of an error."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)  # absent if something replaced the stream
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def setup_logging(log_file: Path | None = None, console_level: int = logging.INFO) -> logging.Logger:
    _utf8_console()
    log = get_logger()
    log.setLevel(logging.DEBUG)
    log.propagate = False
    for h in list(log.handlers):
        log.removeHandler(h)
        h.close()

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(console_level)
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%H:%M:%S"))
    log.addHandler(console)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(_FMT))
        log.addHandler(fh)

    # Selenium and urllib3 are very chatty at DEBUG.
    for noisy in ("selenium", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return log


def mask(secret: str | None) -> str:
    if not secret:
        return "<empty>"
    return "*" * 8
