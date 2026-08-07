from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PERSONAL_PATHS = [
    re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s,\"']+", re.IGNORECASE),
    re.compile(r"/(?:home|Users)/[^/\s,\"']+"),
]
SKIP_SUFFIXES = {
    ".gif",
    ".joblib",
    ".jpeg",
    ".jpg",
    ".mat",
    ".pdf",
    ".png",
    ".pyc",
    ".xlsx",
    ".zip",
}


def tracked_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
    ).decode("utf-8")
    return [ROOT / item for item in output.split("\0") if item]


def main() -> None:
    failures: list[str] = []
    for path in tracked_files():
        if path.suffix.lower() in SKIP_SUFFIXES or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in PERSONAL_PATHS):
                failures.append(f"{path.relative_to(ROOT)}:{line_number}")

    if failures:
        print("FAIL: personal absolute paths remain in tracked text files:")
        print("\n".join(failures))
        raise SystemExit(1)
    print("PASS: no personal absolute paths in tracked text files")


if __name__ == "__main__":
    main()
