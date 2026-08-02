from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "p0_lite_outputs" / "synthetic_constrained_portfolio" / "logs"


METHOD_SCRIPT = {
    "ECMADE_MOO": "run_p0_lite_synthetic_ecmade_moo",
    "A_MPMO": "run_p0_lite_synthetic_ampmo",
}


def matlab_batch(method: str, log_path: Path, smoke: bool) -> str:
    script = METHOD_SCRIPT[method]
    smoke_part = "SYNTHETIC_SMOKE=true;" if smoke else ""
    return (
        f"cd('{ROOT}'); "
        f"diary('{log_path}'); "
        f"{smoke_part} "
        "SYNTHETIC_SPLITS={'train','validation','test'}; "
        "SYNTHETIC_SKIP_SUMMARY=true; "
        "SYNTHETIC_FORCE_RERUN=true; "
        f"{script}; "
        "diary off;"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("method", choices=sorted(METHOD_SCRIPT))
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"{args.method}_python_launcher_{stamp}.log"
    command = ["matlab.exe", "-batch", matlab_batch(args.method, log_path, args.smoke)]

    creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    process = subprocess.Popen(command, cwd=ROOT, creationflags=creationflags)
    print(f"PID={process.pid}")
    print(f"LOG={log_path}")

    if args.wait:
        return process.wait()
    return 0


if __name__ == "__main__":
    sys.exit(main())
