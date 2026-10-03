"""Verify the runtime lock resolves to Linux wheels for every CI Python."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_PYTHONS = ("3.12", "3.13", "3.14")


def resolution_command(python_version: str) -> list[str]:
    compact = python_version.replace(".", "")
    return [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--dry-run",
        "--ignore-installed",
        "--only-binary=:all:",
        "--platform",
        "manylinux_2_28_x86_64",
        "--platform",
        "manylinux_2_17_x86_64",
        "--implementation",
        "cp",
        "--python-version",
        python_version,
        "--abi",
        f"cp{compact}",
        "-r",
        str(ROOT / "requirements.lock"),
    ]


def main() -> int:
    for python_version in SUPPORTED_PYTHONS:
        subprocess.run(resolution_command(python_version), check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
