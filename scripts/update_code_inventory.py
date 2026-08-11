from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "manifest" / "code_inventory.csv"
EXTENSIONS = {".py", ".m", ".ps1", ".bat", ".js", ".mjs", ".json"}


def main() -> None:
    paths = [path for path in (ROOT / "code").rglob("*") if path.is_file() and path.suffix.lower() in EXTENSIONS]
    paths.extend(path for path in (ROOT / "scripts").glob("*.py") if path.is_file())
    paths.append(ROOT / "audit_all_artifacts.py")
    unique = sorted(set(paths), key=lambda path: path.relative_to(ROOT).as_posix().lower())
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["code_path", "source_path", "size_bytes"], lineterminator="\n")
        writer.writeheader()
        for path in unique:
            relative = path.relative_to(ROOT).as_posix()
            writer.writerow({"code_path": relative, "source_path": relative, "size_bytes": path.stat().st_size})
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(unique)} code entries")


if __name__ == "__main__":
    main()
