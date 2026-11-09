"""Load config/config.yaml into typed objects, with per-run overrides from `behave -D key=value`."""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Mapping

import yaml

from core import PROJECT_ROOT

CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"


@dataclass
class BrowserCfg:
    name: str = "chrome"
    headless: bool = False
    window_size: str = "1400,1000"
    binary: str | None = None
    driver_path: str | None = None
    user_data_dir: str | None = None


@dataclass
class TimeoutsCfg:
    default: float = 15
    page_change: float = 30
    prompt_results: float = 6
    short: float = 3


@dataclass
class RetriesCfg:
    click: int = 4
    type: int = 2


@dataclass
class BehaviourCfg:
    on_unknown: str = "pause"  # pause | skip | fail
    keep_browser_open_on_failure: bool = True
    pause_at_end: bool = True
    slow_mo_ms: int = 0
    dump_pages: bool = True


@dataclass
class PathsCfg:
    workbook: str = "data/applicant_data.xlsx"
    reports: str = "reports"

    def resolve(self, value: str) -> Path:
        p = Path(value).expanduser()
        return p if p.is_absolute() else PROJECT_ROOT / p

    @property
    def workbook_path(self) -> Path:
        return self.resolve(self.workbook)

    @property
    def reports_path(self) -> Path:
        return self.resolve(self.reports)


@dataclass
class Config:
    browser: BrowserCfg = field(default_factory=BrowserCfg)
    timeouts: TimeoutsCfg = field(default_factory=TimeoutsCfg)
    retries: RetriesCfg = field(default_factory=RetriesCfg)
    behaviour: BehaviourCfg = field(default_factory=BehaviourCfg)
    paths: PathsCfg = field(default_factory=PathsCfg)


# `-D <key>=<value>` → (section, attribute)
OVERRIDES = {
    "browser": ("browser", "name"),
    "headless": ("browser", "headless"),
    "user_data_dir": ("browser", "user_data_dir"),
    "on_unknown": ("behaviour", "on_unknown"),
    "pause_at_end": ("behaviour", "pause_at_end"),
    "slow_mo_ms": ("behaviour", "slow_mo_ms"),
    "workbook": ("paths", "workbook"),
}


def _coerce(value: Any, like: Any) -> Any:
    """Convert a string from the command line to the type of the default value."""
    if not isinstance(value, str):
        return value
    if isinstance(like, bool):
        return value.strip().lower() in ("1", "true", "yes", "y", "on")
    if isinstance(like, int):
        return int(value)
    if isinstance(like, float):
        return float(value)
    if value.strip().lower() in ("null", "none", ""):
        return None
    return value


def _fill(obj: Any, data: Mapping[str, Any] | None) -> None:
    for f in fields(obj):
        if data and f.name in data and data[f.name] is not None:
            setattr(obj, f.name, _coerce(data[f.name], getattr(obj, f.name)))


def load_config(userdata: Mapping[str, str] | None = None, path: Path = CONFIG_FILE) -> Config:
    raw = yaml.safe_load(path.read_text()) if path.exists() else {}
    cfg = Config()
    for section in ("browser", "timeouts", "retries", "behaviour", "paths"):
        _fill(getattr(cfg, section), (raw or {}).get(section))

    for key, value in (userdata or {}).items():
        if key in OVERRIDES:
            section, attr = OVERRIDES[key]
            target = getattr(cfg, section)
            setattr(target, attr, _coerce(value, getattr(target, attr)))

    if cfg.behaviour.on_unknown not in ("pause", "skip", "fail"):
        raise ValueError(f"behaviour.on_unknown must be pause|skip|fail, got {cfg.behaviour.on_unknown!r}")
    return cfg
