from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def read(name: str) -> str:
    path = ROOT / name
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8", errors="ignore")


def require(label: str, condition: bool, failures: list[str]) -> None:
    if condition:
        print(f"PASS {label}")
    else:
        print(f"FAIL {label}")
        failures.append(label)


def main() -> int:
    failures: list[str] = []

    ecmade = read("ECMADE_MOO.m")
    ecmade_c = compact(ecmade)
    require("ECMADE subpops = 3", "subpops=3;" in ecmade_c, failures)
    require("ECMADE archiveSize/H = 20", "archiveSize=20;" in ecmade_c, failures)
    require("ECMADE theta = 1/13", "theta=1/13;" in ecmade_c, failures)
    require("ECMADE stagnationThreshold/C = 50", "stagnationThreshold=50;" in ecmade_c, failures)
    require("ECMADE exploitationAlpha = 0.8", "exploitationAlpha=0.8;" in ecmade_c, failures)
    require("ECMADE initMuF = [0.9 0.8 0.8]", "initMuF=[0.90.80.8];" in ecmade_c, failures)
    require("ECMADE initMuCR = [0.9 0.5 0.5]", "initMuCR=[0.90.50.5];" in ecmade_c, failures)
    require("ECMADE fScale = 0.1", "fScale=0.1;" in ecmade_c, failures)
    require("ECMADE crScale = 0.1", "crScale=0.1;" in ecmade_c, failures)
    require("ECMADE exchangeMode = paper", "exchangeMode='paper';" in ecmade_c, failures)

    ampmo = read("A_MPMO_NSGAII_v290.m")
    ampmo_c = compact(ampmo)
    require(
        "A-MPMO ParameterSet = (3,0.2,0.05,2,1)",
        "[k,beta,delta,mode,variant]=Global.ParameterSet(3,0.2,0.05,2,1);" in ampmo_c,
        failures,
    )
    require("A-MPMO proC = [1 1 0.5]", "proC=[1,1,0.5];" in ampmo_c, failures)
    require("A-MPMO proM = [0.5 1 1]", "proM=[0.5,1,1];" in ampmo_c, failures)
    require("A-MPMO disC = 20", "disC=20;" in ampmo_c, failures)
    require("A-MPMO disM = 20", "disM=20;" in ampmo_c, failures)

    if failures:
        print("\nPaper-locked parameter check failed:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("\nAll paper-locked parameters match the official baseline settings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
