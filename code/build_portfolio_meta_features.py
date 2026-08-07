"""Build meta_features.csv for the 70/15/15 synthetic Training subset.

Rows are selected from:
  data/synthetic_constrained_portfolio/manifest_70_15_15.csv

Only instances whose path is under:
  data/synthetic_constrained_portfolio/instances_70_15_15/Training

Metadata JSON files are still used, when available, to add objectives,
constraints, format, and scale fields.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_SYNTHETIC_MANIFEST = Path("data/synthetic_constrained_portfolio/manifest_70_15_15.csv")
DEFAULT_SYNTHETIC_INSTANCE_DIR = Path(
    "data/synthetic_constrained_portfolio/instances_70_15_15/Training"
)
DEFAULT_SYNTHETIC_METADATA_ROOT = Path("data/synthetic_constrained_portfolio/metadata")
DEFAULT_ORLIB_DIR = Path("data/orlib")
DEFAULT_OUTPUT = Path("data/meta_features_train.csv")
DEFAULT_ORLIB_K_VALUES = (5, 10, 20, 30)

FIELDS = [
    "source",
    "instance",
    "split",
    "assets",
    "days",
    "k_ratio",
    "K",
    "corr_structure",
    "return_distribution",
    "risk_structure",
    "replicate",
    "seed",
    "path",
    "metadata_path",
    "source_file",
    "objectives",
    "constraints",
    "format",
    "mean_scale",
    "std_scale",
]


def workspace_root() -> Path:
    return Path(__file__).resolve().parent


def resolve_path(path: Path, root: Path) -> Path:
    if path.is_absolute():
        return path
    return root / path


def relpath(path: Path, root: Path) -> str:
    try:
        value = os.path.relpath(path.resolve(), root.resolve())
    except OSError:
        value = str(path)
    return value.replace("/", "\\")


def path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})


def normalize_scalar(value: Any) -> Any:
    if isinstance(value, list):
        return ";".join(str(item) for item in value)
    if isinstance(value, tuple):
        return ";".join(str(item) for item in value)
    if value is None:
        return ""
    return value


def load_metadata_index(metadata_root: Path) -> dict[str, Path]:
    if not metadata_root.exists():
        return {}
    return {path.stem: path for path in metadata_root.rglob("*.json")}


def synthetic_row_from_manifest(
    manifest_row: dict[str, str],
    metadata_index: dict[str, Path],
    workspace: Path,
) -> dict[str, Any]:
    instance = manifest_row["instance"]
    metadata_path = metadata_index.get(instance)
    metadata: dict[str, Any] = {}
    if metadata_path is not None:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    row: dict[str, Any] = {"source": "synthetic"}

    # Manifest is the authoritative index, metadata adds generation details.
    merged: dict[str, Any] = dict(metadata)
    merged.update(manifest_row)
    if "k" in metadata and "K" not in merged:
        merged["K"] = metadata["k"]

    row.update(
        {
            "instance": merged.get("instance") or merged.get("name", instance),
            "split": merged.get("split", ""),
            "assets": merged.get("assets", ""),
            "days": merged.get("days", ""),
            "k_ratio": merged.get("k_ratio", ""),
            "K": merged.get("K", merged.get("k", "")),
            "corr_structure": merged.get("corr_structure", ""),
            "return_distribution": merged.get("return_distribution", ""),
            "risk_structure": merged.get("risk_structure", ""),
            "replicate": merged.get("replicate", ""),
            "seed": merged.get("seed", ""),
            "path": merged.get("path", ""),
            "metadata_path": relpath(metadata_path, workspace) if metadata_path else "",
            "source_file": "",
            "objectives": normalize_scalar(merged.get("objectives", "")),
            "constraints": normalize_scalar(merged.get("constraints", "")),
            "format": merged.get("format", "orlib_portfolio_txt"),
            "mean_scale": merged.get("mean_scale", ""),
            "std_scale": merged.get("std_scale", ""),
        }
    )
    return row


def build_synthetic_rows(
    manifest: Path,
    metadata_root: Path,
    instance_dir: Path,
    workspace: Path,
) -> list[dict[str, Any]]:
    if not manifest.exists():
        raise FileNotFoundError(f"Synthetic manifest not found: {manifest}")
    if not instance_dir.exists():
        raise FileNotFoundError(f"Synthetic instance directory not found: {instance_dir}")

    metadata_index = load_metadata_index(metadata_root)
    rows: list[dict[str, Any]] = []
    for manifest_row in read_csv(manifest):
        data_path = resolve_path(Path(manifest_row.get("path", "")), workspace)
        if not path_is_relative_to(data_path, instance_dir):
            continue
        rows.append(synthetic_row_from_manifest(manifest_row, metadata_index, workspace))
    return rows


def first_number(path: Path) -> int:
    with path.open(encoding="utf-8-sig") as f:
        for line in f:
            parts = line.strip().split()
            if parts:
                return int(float(parts[0]))
    raise ValueError(f"No numeric content found in {path}")


def orlib_rows_from_manifest(manifest_path: Path, workspace: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for manifest_row in read_csv(manifest_path):
        row = {
            "source": "orlib",
            "instance": manifest_row.get("instance", ""),
            "split": manifest_row.get("split", "test"),
            "assets": manifest_row.get("assets", ""),
            "days": manifest_row.get("days", 0),
            "k_ratio": manifest_row.get("k_ratio", ""),
            "K": manifest_row.get("K", ""),
            "corr_structure": manifest_row.get("corr_structure", "or_library"),
            "return_distribution": manifest_row.get(
                "return_distribution", "or_library"
            ),
            "risk_structure": manifest_row.get("risk_structure", "or_library"),
            "replicate": manifest_row.get("replicate", 1),
            "seed": manifest_row.get("seed", 0),
            "path": manifest_row.get("path", ""),
            "metadata_path": "",
            "source_file": manifest_row.get("source_file", ""),
            "objectives": "minimize_variance;maximize_return",
            "constraints": "sum(w)=1;w>=0;cardinality<=K",
            "format": "orlib_portfolio_txt",
            "mean_scale": "or_library",
            "std_scale": "or_library",
        }
        if not row["source_file"] and row["path"]:
            row["source_file"] = Path(str(row["path"])).name
        rows.append(row)
    return rows


def build_orlib_rows(
    orlib_dir: Path,
    k_values: tuple[int, ...],
    workspace: Path,
) -> list[dict[str, Any]]:
    if not orlib_dir.exists():
        raise FileNotFoundError(f"OR-Library directory not found: {orlib_dir}")

    rows: list[dict[str, Any]] = []
    for port_file in sorted(orlib_dir.glob("port*.txt")):
        assets = first_number(port_file)
        port_id = port_file.stem
        for k_value in k_values:
            if k_value > assets:
                continue
            rows.append(
                {
                    "source": "orlib",
                    "instance": f"orlib_{port_id}_K{k_value:02d}",
                    "split": "test",
                    "assets": assets,
                    "days": 0,
                    "k_ratio": k_value / assets,
                    "K": k_value,
                    "corr_structure": "or_library",
                    "return_distribution": "or_library",
                    "risk_structure": "or_library",
                    "replicate": 1,
                    "seed": 0,
                    "path": relpath(port_file, workspace),
                    "metadata_path": "",
                    "source_file": port_file.name,
                    "objectives": "minimize_variance;maximize_return",
                    "constraints": "sum(w)=1;w>=0;cardinality<=K",
                    "format": "orlib_portfolio_txt",
                    "mean_scale": "or_library",
                    "std_scale": "or_library",
                }
            )
    return rows


def parse_k_values(raw: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if not values:
        raise ValueError("--orlib-k-values must contain at least one integer")
    return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build meta_features.csv for synthetic 70/15/15 Training instances."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_SYNTHETIC_MANIFEST)
    parser.add_argument("--instance-dir", type=Path, default=DEFAULT_SYNTHETIC_INSTANCE_DIR)
    parser.add_argument("--metadata-root", type=Path, default=DEFAULT_SYNTHETIC_METADATA_ROOT)
    parser.add_argument("--orlib-dir", type=Path, default=DEFAULT_ORLIB_DIR)
    parser.add_argument(
        "--orlib-manifest",
        type=Path,
        default=None,
        help="Optional constrained OR-Library manifest to use instead of expanding port*.txt.",
    )
    parser.add_argument(
        "--orlib-k-values",
        default=",".join(str(k) for k in DEFAULT_ORLIB_K_VALUES),
        help="Comma-separated K values used when expanding raw OR-Library port*.txt files.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--include-orlib",
        action="store_true",
        help="Also append OR-Library rows. Off by default for this Training-only file.",
    )
    parser.add_argument("--no-orlib", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workspace = workspace_root()
    manifest = resolve_path(args.manifest, workspace)
    instance_dir = resolve_path(args.instance_dir, workspace)
    metadata_root = resolve_path(args.metadata_root, workspace)
    output = resolve_path(args.output, workspace)

    rows = build_synthetic_rows(manifest, metadata_root, instance_dir, workspace)

    if args.include_orlib and not args.no_orlib:
        if args.orlib_manifest is not None:
            orlib_manifest = resolve_path(args.orlib_manifest, workspace)
            rows.extend(orlib_rows_from_manifest(orlib_manifest, workspace))
        else:
            orlib_dir = resolve_path(args.orlib_dir, workspace)
            rows.extend(build_orlib_rows(orlib_dir, parse_k_values(args.orlib_k_values), workspace))

    write_csv(output, rows)
    print(f"Wrote {len(rows)} rows to {output}")
    print(f"synthetic_rows={sum(1 for row in rows if row['source'] == 'synthetic')}")
    print(f"orlib_rows={sum(1 for row in rows if row['source'] == 'orlib')}")


if __name__ == "__main__":
    main()
