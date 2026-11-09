"""Open a page and save its HTML + a screenshot every time you press Enter.

    python tools/dump_page.py <url> [--name cibc]   # files go to docs/page_dumps/<name>_<n>.html/.png

Click through to the state you want in the browser (open a dropdown, trigger errors, ...), then press
Enter in the terminal. Type q + Enter to quit.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.config import load_config  # noqa: E402
from core.driver import create_driver  # noqa: E402
from core.logger import setup_logging  # noqa: E402

OUT_DIR = ROOT / "docs" / "page_dumps"


def save(driver, out_dir: Path, name: str, n: int, label: str = "") -> None:
    stem = f"{name}_{n:02d}" + (f"_{label}" if label else "")
    html = out_dir / f"{stem}.html"
    html.write_text(driver.page_source, encoding="utf-8")
    driver.save_screenshot(str(out_dir / f"{stem}.png"))
    print(f"saved {html} (+ .png)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url")
    parser.add_argument("--name", default="dump", help="file name prefix, e.g. the company")
    parser.add_argument("--browser", default=None, help="chrome | firefox (default: config.yaml)")
    args = parser.parse_args()

    setup_logging()
    cfg = load_config({"browser": args.browser} if args.browser else None)
    cfg.browser.headless = False
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    driver = create_driver(cfg.browser)
    try:
        driver.get(args.url)
        n = 0
        while True:
            answer = input("\nEnter = save this page, or type a label then Enter (e.g. 'source_open'); q = quit: ")
            if answer.strip().lower() == "q":
                break
            n += 1
            save(driver, OUT_DIR, args.name, n, answer.strip().replace(" ", "_"))
    finally:
        driver.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
