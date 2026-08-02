from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest" / "external_artifacts.csv"


def main() -> None:
    with MANIFEST.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    missing_urls = [row["package_path"] for row in rows if row.get("external_url", "TODO") in {"", "TODO"}]
    if missing_urls:
        print("External artifact URLs are not filled yet. Update manifest/external_artifacts.csv first.")
        for item in missing_urls[:20]:
            print(f"- {item}")
        raise SystemExit(1)
    print("Download implementation placeholder: use urllib/request or your preferred artifact manager after URLs are finalized.")


if __name__ == "__main__":
    main()
