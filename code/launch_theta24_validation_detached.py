from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path


ROOT = Path(r"C:\Users\yiting\Documents\Playground")
OUT_ROOT = ROOT / r"p0_lite_outputs\theta24_70_15_15_validation_label_full_20260713"
MATLAB = r"C:\Program Files\MATLAB\R2026a\bin\matlab.exe"
BATCH = (
    r"THETA24_FULL_OUT_ROOT='C:\Users\yiting\Documents\Playground\p0_lite_outputs\theta24_70_15_15_validation_label_full_20260713'; "
    r"THETA24_FULL_SPLITS={'Validation'}; "
    r"THETA24_FULL_MAX_INSTANCES=29; "
    r"run_theta24_192instance_label_full"
)


def main() -> None:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    stdout = OUT_ROOT / f"resume_stdout_{stamp}.log"
    stderr = OUT_ROOT / f"resume_stderr_{stamp}.log"
    status = OUT_ROOT / f"resume_status_{stamp}.txt"
    status.write_text(
        "\n".join(
            [
                f"started={dt.datetime.now().isoformat()}",
                f"stdout={stdout}",
                f"stderr={stderr}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    flags = subprocess.CREATE_NEW_PROCESS_GROUP
    so = stdout.open("w", encoding="utf-8")
    se = stderr.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [MATLAB, "-batch", BATCH],
        cwd=ROOT,
        stdout=so,
        stderr=se,
        creationflags=flags,
        close_fds=True,
    )
    print(f"pid={proc.pid}")
    print(f"stdout={stdout}")
    print(f"stderr={stderr}")
    print(f"status={status}")


if __name__ == "__main__":
    main()
