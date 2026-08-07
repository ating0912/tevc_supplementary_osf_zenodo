from __future__ import annotations

import argparse
import csv
import hashlib
import os
import zipfile
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = [
    "p0_lite_outputs/p1_mokp_experiment_c_no_replicate_full_20260731",
    "p0_lite_outputs/experiment_c_stability_ecmade_moo_no_replicate_20260730",
    "p0_lite_outputs/experiment_c_formal_five_method_no_replicate_20260731",
    "p0_lite_outputs/p1_mokp_config_comparison_no_replicate_audit_20260731",
    "p0_lite_outputs/p1_rolling_window_market_validation_20260719",
    "outputs/experiment_A_stats_delivery_20260706",
    "outputs/experiment_c_replicate_audit_20260730",
    "outputs/selector_level_ablation_20260728",
    "outputs/real_market_config_protocol_section_20260730",
    "outputs/experiment_c_feature_importance_20260725",
    "outputs/experiment_c_report_20260717",
]
NAME_PATTERNS = ("pf", "front", "archive", "obj")
MAX_PART_BYTES = 900_000_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect(workspace: Path) -> list[Path]:
    files: set[Path] = set()
    for relative in SOURCE_ROOTS:
        base = workspace / relative
        if not base.is_dir():
            continue
        for path in base.rglob("*.csv"):
            if path.is_file() and any(pattern in path.name.lower() for pattern in NAME_PATTERNS):
                files.add(path)
    return sorted(files, key=lambda path: path.relative_to(workspace).as_posix().lower())


def partition(files: list[Path]) -> list[list[Path]]:
    parts: list[list[Path]] = []
    current: list[Path] = []
    current_bytes = 0
    for path in files:
        size = path.stat().st_size
        if current and current_bytes + size > MAX_PART_BYTES:
            parts.append(current)
            current = []
            current_bytes = 0
        current.append(path)
        current_bytes += size
    if current:
        parts.append(current)
    return parts


def main() -> None:
    parser = argparse.ArgumentParser(description="Build standard ZIP64 raw-PF archive parts below the Git LFS single-file limit.")
    parser.add_argument("--workspace", type=Path, default=PACKAGE_ROOT.parent)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    files = collect(workspace)
    if not files:
        raise SystemExit(f"No raw PF CSV files found under {workspace}")
    parts = partition(files)
    output_dir = PACKAGE_ROOT / "raw_pf"
    output_dir.mkdir(parents=True, exist_ok=True)

    temporary_paths: list[Path] = []
    final_paths: list[Path] = []
    try:
        for index, part_files in enumerate(parts, start=1):
            final_path = output_dir / f"raw_pf_csv_part{index:02d}.zip"
            temporary = output_dir / f"raw_pf_csv_part{index:02d}.zip.tmp"
            if temporary.exists():
                temporary.unlink()
            print(f"Building part {index}/{len(parts)} with {len(part_files)} files", flush=True)
            with zipfile.ZipFile(
                temporary,
                "w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=1,
                allowZip64=True,
            ) as archive:
                for file_index, source in enumerate(part_files, start=1):
                    archive.write(source, source.relative_to(workspace).as_posix())
                    if file_index % 1000 == 0:
                        if archive.fp is not None:
                            archive.fp.flush()
                        print(f"  part {index}: {file_index}/{len(part_files)} files", flush=True)
            with zipfile.ZipFile(temporary) as archive:
                if len(archive.infolist()) != len(part_files):
                    raise SystemExit(f"Archive member count mismatch in {temporary.name}")
                corrupt = archive.testzip()
                if corrupt:
                    raise SystemExit(f"CRC failure in {temporary.name}: {corrupt}")
            temporary_paths.append(temporary)
            final_paths.append(final_path)

        for old in output_dir.glob("raw_pf_csv_part*.zip"):
            old.unlink()
        old_single = output_dir / "raw_pf_csv.zip"
        if old_single.exists():
            old_single.unlink()
        for temporary, final_path in zip(temporary_paths, final_paths):
            os.replace(temporary, final_path)

        manifest = PACKAGE_ROOT / "manifest" / "raw_pf_archive_parts.csv"
        with manifest.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["package_path", "size_bytes", "file_count", "sha256"])
            writer.writeheader()
            for path, part_files in zip(final_paths, parts):
                writer.writerow(
                    {
                        "package_path": path.relative_to(PACKAGE_ROOT).as_posix(),
                        "size_bytes": path.stat().st_size,
                        "file_count": len(part_files),
                        "sha256": sha256(path),
                    }
                )
        print(f"Wrote {len(files)} files across {len(final_paths)} validated ZIP parts", flush=True)
    finally:
        for temporary in temporary_paths:
            if temporary.exists():
                temporary.unlink()


if __name__ == "__main__":
    main()
