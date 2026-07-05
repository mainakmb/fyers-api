#!/usr/bin/env python3
"""Supervisor entrypoint: runs buy and sell loops as parallel child processes."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    scripts = [ROOT / "buy.py", ROOT / "sell.py"]
    for script in scripts:
        if not script.exists():
            print(f"Missing required script: {script}", file=sys.stderr)
            return 1

    procs = [subprocess.Popen([sys.executable, str(script)]) for script in scripts]

    try:
        exit_code = 0
        for proc in procs:
            code = proc.wait()
            if code != 0:
                exit_code = code
        return exit_code
    except KeyboardInterrupt:
        for proc in procs:
            proc.terminate()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
