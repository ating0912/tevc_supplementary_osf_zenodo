import argparse
import csv
import os
import shutil


ROOT = r"C:\Users\yiting\Documents\Playground"
DEFAULT_SOURCE = r"C:\Users\yiting\Desktop\NCHU\lab\TEVC\OR-Library"
DEFAULT_OUTPUT = os.path.join(ROOT, "data", "orlib_constrained_portfolio")
PORT_FILES = [f"port{i}.txt" for i in range(1, 6)]
K_VALUES = [5, 10, 20, 30]


def first_number(path):
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line:
                return int(float(line.split()[0]))
    raise ValueError(f"No numeric content found in {path}")


def relpath(path):
    return os.path.relpath(path, ROOT).replace("/", "\\")


def main():
    parser = argparse.ArgumentParser(description="Build the formal OR-Library subset manifest for Experiment A.")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="Directory containing port1.txt ... port5.txt.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT, help="Workspace output directory for copied files and manifest.")
    args = parser.parse_args()

    source = os.path.abspath(args.source)
    output_dir = os.path.abspath(args.output_dir)
    instance_dir = os.path.join(output_dir, "instances")
    os.makedirs(instance_dir, exist_ok=True)

    rows = []
    for port_file in PORT_FILES:
        src = os.path.join(source, port_file)
        if not os.path.exists(src):
            raise FileNotFoundError(src)
        dst = os.path.join(instance_dir, port_file)
        shutil.copy2(src, dst)

        port_id = os.path.splitext(port_file)[0]
        assets = first_number(dst)
        for k in K_VALUES:
            if k > assets:
                continue
            rows.append(
                {
                    "instance": f"orlib_{port_id}_K{k:02d}",
                    "split": "test",
                    "assets": assets,
                    "days": 0,
                    "k_ratio": k / assets,
                    "K": k,
                    "corr_structure": "or_library",
                    "return_distribution": "or_library",
                    "risk_structure": "or_library",
                    "replicate": 1,
                    "seed": 0,
                    "path": relpath(dst),
                    "source_file": port_file,
                }
            )

    manifest = os.path.join(output_dir, "manifest.csv")
    with open(manifest, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"ORLIB_MANIFEST={manifest}")
    print(f"ORLIB_INSTANCES={len(PORT_FILES)}")
    print(f"ORLIB_ROWS={len(rows)}")


if __name__ == "__main__":
    main()
