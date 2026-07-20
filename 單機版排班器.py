"""完整單機版排班器的啟動器：在封裝後直接開啟既有 Streamlit 介面。"""
from __future__ import annotations

import sys
from pathlib import Path

from streamlit.web import cli as streamlit_cli


def main() -> None:
    app_path = Path(__file__).with_name("排班器.py")
    sys.argv = [
        "streamlit", "run", str(app_path),
        "--server.address=127.0.0.1",
        "--server.headless=false",
        "--browser.gatherUsageStats=false",
    ]
    raise SystemExit(streamlit_cli.main())


if __name__ == "__main__":
    main()
