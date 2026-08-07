from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LFS_ARTIFACTS = [
    "logs/full_run_logs.zip",
    "figures/paper_figures.zip",
    "selector/selector_no_replicate.joblib",
]


def is_lfs_pointer(path: Path) -> bool:
    if not path.is_file():
        return True
    with path.open("rb") as handle:
        return handle.read(80).startswith(b"version https://git-lfs.github.com/spec/")


def main() -> None:
    raw_pf_parts = sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "raw_pf").glob("raw_pf_csv_part*.zip"))
    if not raw_pf_parts:
        raise SystemExit("No raw PF archive parts are present")
    artifacts = LFS_ARTIFACTS + raw_pf_parts
    unresolved = [path for path in artifacts if is_lfs_pointer(ROOT / path)]
    if unresolved:
        print("Materializing Git LFS artifacts...")
        subprocess.run(["git", "lfs", "pull"], cwd=ROOT, check=True)
    unresolved = [path for path in artifacts if is_lfs_pointer(ROOT / path)]
    if unresolved:
        raise SystemExit("Git LFS artifacts are unavailable:\n- " + "\n- ".join(unresolved))
    subprocess.run([sys.executable, str(ROOT / "scripts" / "check_github_package.py")], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
