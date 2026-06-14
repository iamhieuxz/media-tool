"""Script đóng gói ứng dụng thành tệp thực thi bằng PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CMD = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--clean",
    "--name",
    "MediaTool",
    "--onefile",
    "--windowed",
    "--uac-admin",
    "main.py",
    "--distpath",
    "dist",
    "--workpath",
    "build",
    "--specpath",
    "build",
]

if __name__ == "__main__":
    raise SystemExit(subprocess.call(CMD, cwd=ROOT))
