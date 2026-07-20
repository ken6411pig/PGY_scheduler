"""Launcher for the packaged standalone Streamlit scheduler."""
from __future__ import annotations

import sys
from pathlib import Path

from streamlit.web import cli as streamlit_cli


def main() -> None:
    folder = Path(__file__).parent
    signature = "st.set" + "_page_config"
    candidates = [path for path in folder.glob("*.py") if signature in path.read_text(encoding="utf-8")]
    if len(candidates) != 1:
        raise RuntimeError("找不到唯一的排班器主程式")
    sys.argv = [
        "streamlit", "run", str(candidates[0]),
        "--server.address=127.0.0.1",
        "--server.port=8501",
        "--server.headless=false",
        "--browser.serverAddress=127.0.0.1",
        "--browser.serverPort=8501",
        "--browser.gatherUsageStats=false",
    ]
    raise SystemExit(streamlit_cli.main())


if __name__ == "__main__":
    main()
